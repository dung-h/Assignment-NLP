"""Evaluate the system response with one set of output criteria."""

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import sys

import yaml

from src.assistant import CourseAssistant


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / 'data/annotations/evaluation.yaml'


def normalize(text):
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def typed_value(value):
    if isinstance(value, list):
        return ('list', tuple(typed_value(item) for item in value))
    if isinstance(value, dict):
        return ('dict', tuple(sorted((key, typed_value(item)) for key, item in value.items())))
    return (type(value).__name__, value)


def same_values(actual, expected):
    """Require the same values and types, allowing different list order."""
    return (isinstance(actual, list) and isinstance(expected, list)
            and Counter(map(typed_value, actual)) == Counter(map(typed_value, expected)))


def load_cases(path=DATASET):
    data = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    if data.get('version') != 2 or not data.get('cases'):
        raise ValueError('Tập đánh giá cần version: 2 và danh sách cases không rỗng')
    ids, inputs = set(), set()
    for case in data['cases']:
        key = tuple(map(normalize, [*case['input']['history'], case['input']['query']]))
        if case['id'] in ids or key in inputs:
            raise ValueError(f"Trường hợp trùng: {case['id']}")
        ids.add(case['id'])
        inputs.add(key)
        if not case.get('provenance'):
            raise ValueError(f"Thiếu nguồn đối chiếu: {case['id']}")
        for source in case['provenance']:
            source_path = (ROOT / source).resolve()
            if not source_path.is_relative_to(ROOT.resolve()) or not source_path.is_file():
                raise ValueError(f'Nguồn không tồn tại: {source}')
        if not case['expected'].get('alternatives'):
            raise ValueError('Phải có ít nhất một phản hồi mong đợi')
        for expected in case['expected']['alternatives']:
            if expected['outcome'] not in {'FOUND', 'MISSING', 'OUT_OF_SCOPE', 'CLARIFY'}:
                raise ValueError('Loại phản hồi không hợp lệ')
            if not expected.get('answer_facts'):
                raise ValueError('Phải ghi thông tin cần có trong câu trả lời')
            if any(not group or any(not isinstance(phrase, str) or not phrase.strip() for phrase in group)
                   for group in expected['answer_facts']):
                raise ValueError('Thông tin mong đợi phải là nhóm các cách diễn đạt không rỗng')
            if not isinstance(expected.get('values'), list) or not isinstance(expected.get('sources'), list):
                raise ValueError('Giá trị và nguồn mong đợi phải là danh sách')
            if expected['outcome'] == 'FOUND' and (not expected['values'] or not expected['sources']):
                raise ValueError('Kết quả có dữ liệu cần có giá trị và nguồn')
            if expected['outcome'] != 'FOUND' and (expected['values'] or expected['sources']):
                raise ValueError('Phản hồi không có dữ liệu phải để trống giá trị và nguồn')
    return data


def phrase_present(phrase, answer):
    phrase = normalize(phrase)
    left = r'(?<!\w)' if phrase[0].isalnum() or phrase[0] == '_' else ''
    right = r'(?!\w)' if phrase[-1].isalnum() or phrase[-1] == '_' else ''
    return re.search(left + re.escape(phrase) + right, answer) is not None


def check_response(response, expected):
    """Check returned data and final text; never grade parser/semantic labels."""
    errors = []
    retrieval = response.get('person_3_retrieval_result', {})
    wanted_status = 'FOUND' if expected['outcome'] == 'FOUND' else 'NOT_FOUND'
    if retrieval.get('status') != wanted_status:
        errors.append('Trạng thái kết quả không đúng')
    if not same_values(retrieval.get('values'), expected['values']):
        errors.append('Giá trị trả về thiếu, thừa, sai nội dung hoặc sai kiểu dữ liệu')
    if not same_values(retrieval.get('sources'), expected['sources']):
        errors.append('Nguồn trả về thiếu hoặc không đúng')
    answer = response.get('answer')
    if not isinstance(answer, str) or not answer.strip():
        return errors + ['Câu trả lời rỗng hoặc không phải chuỗi']
    # Source identifiers cannot satisfy a required content fact by themselves.
    body = normalize(answer.split('Nguồn:')[0])
    full_answer = normalize(answer)
    for alternatives in expected['answer_facts']:
        if not any(phrase_present(phrase, body) for phrase in alternatives):
            errors.append('Thiếu thông tin trả lời: ' + ' / '.join(alternatives))
    for phrase in expected.get('forbidden', []):
        if phrase_present(phrase, full_answer):
            errors.append('Có thông tin không được phép khẳng định: ' + phrase)
    for source in expected['sources']:
        if source not in answer:
            errors.append('Câu trả lời chưa nêu nguồn: ' + source)
    if expected['outcome'] == 'FOUND':
        if re.search(r'^(?:xin lỗi[,\s]*)?(?:tôi )?không (?:có|tìm thấy)', body):
            errors.append('Câu trả lời phủ nhận dữ liệu cần trả lời')
        if len(expected['values']) == 1 and type(expected['values'][0]) is bool:
            positive = expected['values'][0]
            if (positive and body.startswith('không')) or (not positive and body.startswith('có')):
                errors.append('Câu trả lời Có/Không ngược với kết quả')
        if expected.get('quantity'):
            number, unit = expected['quantity']
            quantities = re.findall(r'(?<!\d)(\d+)\s*' + re.escape(normalize(unit)) + r'(?!\w)', full_answer)
            if any(int(found) != number for found in quantities):
                errors.append('Câu trả lời có số liệu mâu thuẫn')
    if expected['outcome'] == 'MISSING' and re.search(r'\b\d{1,2}[/\-]\d{1,2}[/\-]\d{4}\b', full_answer):
        errors.append('Câu trả lời thêm ngày cụ thể dù kỳ vọng chưa có thông tin')
    return errors


def first_failure_stage(response, case):
    if not response.get('person_1_parser_result', {}).get('valid'):
        return 'parser'
    if response.get('person_2_semantic_query', {}).get('intent') == 'UNKNOWN':
        if any(item['outcome'] == 'CLARIFY' for item in case['expected']['alternatives']):
            return 'clarification_response'
        return 'semantic_or_context'
    semantic = response.get('person_2_semantic_query', {})
    actual_task = f"{semantic.get('intent')}:{semantic.get('attribute')}"
    if case.get('task', actual_task) != actual_task:
        return 'question_type_selection'
    return 'retrieval_or_answer'


def evaluate_case(case, assistant_factory=CourseAssistant):
    trace = []
    try:
        assistant = assistant_factory()
        for query in case['input']['history']:
            trace.append(assistant.ask(query))
        response = assistant.ask(case['input']['query'])
        alternatives = [check_response(response, item) for item in case['expected']['alternatives']]
        errors = min(alternatives, key=len)
        passed = not errors
        return {'id': case['id'], 'passed': passed, 'errors': errors,
                'first_failure': None if passed else first_failure_stage(response, case),
                'actual': response, 'history_trace': trace,
                'matched_alternative': alternatives.index([]) if passed else None}
    except Exception as exc:
        return {'id': case['id'], 'passed': False, 'errors': [f'{type(exc).__name__}: {exc}'],
                'first_failure': 'runtime', 'actual': None, 'history_trace': trace,
                'matched_alternative': None}


def summarize(cases, results):
    groups = {}
    outcomes = {}
    by_id = {case['id']: case for case in cases}
    for result in results:
        case = by_id[result['id']]
        outcome = ' hoặc '.join(dict.fromkeys(item['outcome'] for item in case['expected']['alternatives']))
        for mapping, key in ((groups, case['category']), (outcomes, outcome)):
            counts = mapping.setdefault(key, {'passed': 0, 'total': 0})
            counts['total'] += 1
            counts['passed'] += int(result['passed'])
    return {'passed': sum(row['passed'] for row in results), 'total': len(results),
            'groups': groups, 'outcomes': outcomes,
            'failures': dict(Counter(row['first_failure'] for row in results if not row['passed']))}


def render_report(data, results):
    summary = summarize(data['cases'], results)
    passed, total = summary['passed'], summary['total']
    lines = ['ĐÁNH GIÁ COURSE ASSISTANT', '', f"Tập câu hỏi: {data['name']}",
             f'Đáp ứng các điều kiện kiểm tra: {passed}/{total} ({100 * passed / total:.1f}%)',
             f'Chưa đáp ứng: {total - passed}', '',
             'Cách đánh giá:',
             '- Một lượt gồm câu hỏi hiện tại và lịch sử hội thoại được ghi trong testcase.',
             '- Mọi lượt dùng cùng cách kiểm tra dữ liệu trả về, nguồn và thông tin cần có trong câu trả lời.',
             '- Nhãn parser, intent và entity chỉ dùng để phân tích lỗi, không làm điều kiện đạt.',
             '- Các phản hồi thay thế được chấp nhận khi đã ghi trong testcase trước khi chấm.',
             '- Nhóm CLARIFY khảo sát khả năng hỏi lại do nhóm đề xuất; đề bài yêu cầu thông báo phù hợp nhưng không bắt buộc mọi trường hợp nhập nhằng phải dùng đúng cách này.',
             '- Đây là kiểm tra tự động theo các điều kiện đã ghi; không thay thế chấm ngữ nghĩa toàn bộ câu trả lời bởi người đánh giá độc lập.',
             '- Tập có các câu đã dùng khi phát triển; không đại diện thống kê cho câu hỏi thực tế.', '',
             'Kết quả theo nhóm:']
    lines.extend(f"- {group}: {counts['passed']}/{counts['total']}" for group, counts in summary['groups'].items())
    lines.extend(['', 'Kết quả theo loại phản hồi mong đợi:'])
    lines.extend(f"- {kind}: {counts['passed']}/{counts['total']}" for kind, counts in summary['outcomes'].items())
    lines.extend(['', 'Bước đầu tiên quan sát thấy lỗi:'])
    stage_names = {'parser': 'Không nhận diện câu ở parser',
                   'question_type_selection': 'Chọn nhầm loại yêu cầu',
                   'clarification_response': 'Thiếu phản hồi làm rõ ngữ cảnh',
                   'semantic_or_context': 'Chưa diễn giải được yêu cầu hoặc ngữ cảnh',
                   'retrieval_or_answer': 'Kết quả truy xuất hoặc câu trả lời chưa đúng',
                   'runtime': 'Lỗi khi chạy chương trình'}
    lines.extend(f'- {stage_names.get(stage, stage)}: {count}' for stage, count in summary['failures'].items())
    for case, result in zip(data['cases'], results):
        lines.extend(['', f"{case['id']} | {'ĐẠT' if result['passed'] else 'CHƯA ĐẠT'} | {case['input']['query']}"])
        if case['input']['history']:
            lines.append('  Hội thoại trước: ' + ' → '.join(case['input']['history']))
        lines.append('  Mong đợi: ' + case['expectation_note'])
        lines.append('  Nguồn đối chiếu: ' + ', '.join(case['provenance']))
        if result['actual']:
            lines.append('  Thực tế: ' + result['actual']['answer'].replace('\n', ' '))
        lines.extend('  ' + error for error in result['errors'])
    return '\n'.join(lines) + '\n'


def run_evaluation(dataset=DATASET, output=ROOT / 'output'):
    data = load_cases(dataset)
    results = [evaluate_case(case) for case in data['cases']]
    output = Path(output)
    output.mkdir(exist_ok=True, parents=True)
    digest = hashlib.sha256(Path(dataset).read_bytes()).hexdigest()
    payload = {'dataset': str(Path(dataset).name), 'dataset_sha256': digest,
               'summary': summarize(data['cases'], results),
               'results': [{'case': case, **result} for case, result in zip(data['cases'], results)]}
    (output / 'evaluation.txt').write_text(render_report(data, results), encoding='utf-8', newline='\n')
    (output / 'evaluation_results.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    return payload


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Đánh giá đầu vào–đầu ra theo bộ testcase thống nhất.')
    parser.add_argument('--strict', action='store_true', help='Trả mã 1 nếu có trường hợp chưa đạt')
    parser.add_argument('--output', type=Path, default=ROOT / 'output', help='Thư mục lưu kết quả')
    args = parser.parse_args(argv)
    payload = run_evaluation(output=args.output)
    summary = payload['summary']
    print(f"Đáp ứng điều kiện kiểm tra: {summary['passed']}/{summary['total']}. Xem {args.output / 'evaluation.txt'}.")
    return int(args.strict and summary['passed'] < summary['total'])
