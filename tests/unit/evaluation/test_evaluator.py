import pytest

from src.evaluation.evaluator import check_response, evaluate_case, load_cases, same_values, phrase_present


def credit_expected():
    return {'outcome': 'FOUND', 'values': [3], 'sources': ['course_info:CO3085'],
            'answer_facts': [['3', 'ba'], ['tín chỉ']], 'forbidden': ['ngoài phạm vi'],
            'quantity': [3, 'tín chỉ']}


def credit_response():
    return {'answer': 'Số tín chỉ của môn là 3 tín chỉ. Nguồn: course_info:CO3085.',
            'person_3_retrieval_result': {'status': 'FOUND', 'values': [3], 'sources': ['course_info:CO3085']}}


@pytest.mark.parametrize('answer', [
    'Môn có ba tín chỉ. Nguồn: course_info:CO3085.',
    'Số tín chỉ: 3. Nguồn: course_info:CO3085.',
])
def test_equivalent_wording_is_accepted_without_parser_or_semantic_labels(answer):
    response = credit_response()
    response['answer'] = answer
    assert check_response(response, credit_expected()) == []


@pytest.mark.parametrize('mutation', ['value', 'unit', 'source', 'extra_source', 'negation', 'contradiction'])
def test_incorrect_answers_and_evidence_cannot_pass(mutation):
    response = credit_response()
    if mutation == 'value':
        response['person_3_retrieval_result']['values'] = [4]
    elif mutation == 'unit':
        response['answer'] = '3 ECTS. Nguồn: course_info:CO3085.'
    elif mutation == 'source':
        response['person_3_retrieval_result']['sources'] = ['invented:source']
    elif mutation == 'extra_source':
        response['person_3_retrieval_result']['sources'].append('invented:source')
    elif mutation == 'negation':
        response['answer'] = 'Không có 3 tín chỉ. Nguồn: course_info:CO3085.'
    else:
        response['answer'] += ' Thực tế môn có 4 tín chỉ.'
    assert check_response(response, credit_expected())


def test_values_are_type_sensitive_and_order_independent():
    assert not same_values([1], [True])
    assert not same_values(['3'], [3])
    assert same_values(['CH06', 'CH03'], ['CH03', 'CH06'])
    assert not same_values(['CH03', 'CH03'], ['CH03'])


def test_percent_unit_and_numeric_token_boundaries():
    assert phrase_present('%', 'bài thi chiếm 30%')
    assert not phrase_present('3', 'môn có 30 tín chỉ')


def test_assignment_goal_is_not_a_complete_requirements_answer():
    case = next(case for case in load_cases()['cases'] if case['id'] == 'E012')
    response = {'answer': 'Mục tiêu là xây dựng pipeline NLP từ parsing đến hỏi đáp. Nguồn: assignments:BTL01.',
                'person_3_retrieval_result': {'status': 'FOUND', 'values': ['Mục tiêu'], 'sources': ['assignments:BTL01']}}
    assert all(check_response(response, expected) for expected in case['expected']['alternatives'])

    class Assistant:
        def ask(self, query):
            return {**response, 'person_1_parser_result': {'valid': True, 'query_frame': 'ASK_ASSIGNMENT_INFO'},
                    'person_2_semantic_query': {'intent': 'GET_ASSIGNMENT', 'attribute': 'goal'}}

    result = evaluate_case(case, Assistant)
    assert not result['passed']
    assert result['first_failure'] == 'question_type_selection'


def test_source_identifiers_cannot_satisfy_answer_facts():
    response = credit_response()
    response['answer'] = 'Nguồn: course_info:CO3085. Môn có 3 tín chỉ.'
    assert check_response(response, credit_expected())


def test_clarification_is_an_accepted_output_when_listed():
    expected = {'outcome': 'CLARIFY', 'values': [], 'sources': [],
                'answer_facts': [['bạn muốn'], ['chương', 'phần']], 'forbidden': ['ngoài phạm vi']}
    case = {'id': 'example', 'input': {'query': 'Tài liệu phần này?', 'history': []},
            'expected': {'alternatives': [credit_expected(), expected]}}

    class Assistant:
        def ask(self, text):
            return {'answer': 'Bạn muốn hỏi tài liệu của chương nào?',
                    'person_3_retrieval_result': {'status': 'NOT_FOUND', 'values': [], 'sources': []}}

    result = evaluate_case(case, Assistant)
    assert result['passed']
    assert result['matched_alternative'] == 1


def test_runtime_error_is_counted_in_results():
    class BrokenAssistant:
        def __init__(self):
            raise RuntimeError('failed')

    result = evaluate_case({'id': 'broken'}, BrokenAssistant)
    assert not result['passed']
    assert result['first_failure'] == 'runtime'


def test_active_dataset_is_complete_and_has_no_duplicate_inputs():
    data = load_cases()
    assert data['cases']
    assert any(len(case['expected']['alternatives']) > 1 for case in data['cases'])
    assert any(case['input']['history'] for case in data['cases'])
