"""Person 1/2 handoff acceptance extensions beyond the 84-case regression set.

Run: python -m pytest tests/test_person12_improvements.py -v
Also discovered by the default full pytest run. These assertions expose three
requested coverage extensions and one missed sample-dialogue requirement.
Do not turn them into xfail/skip or fold their results into the frozen gold score.
"""

import pytest

from src.assistant import CourseAssistant
from src.contracts import ParserResult
from src.semantics.semantic_mapper import SemanticMapper
from src.syntax.parser import RuleParser


CASES = [
    pytest.param(
        'Môn NLP có bao nhiêu ECTS?',
        'ASK_COURSE_ATTRIBUTE',
        {'course': ['NLP'], 'attribute_cue': ['bao nhiêu ECTS']},
        {'intent': 'GET_COURSE_INFO', 'entities': {'course': ['CO3085']},
         'attribute': 'ects', 'answer_mode': 'VALUE'},
        id='P1-ECTS',
    ),
    pytest.param(
        'Môn NLP thuộc khoa nào?',
        'ASK_COURSE_ATTRIBUTE',
        {'course': ['NLP'], 'attribute_cue': ['thuộc khoa nào']},
        {'intent': 'GET_COURSE_INFO', 'entities': {'course': ['CO3085']},
         'attribute': 'department', 'answer_mode': 'VALUE'},
        id='P1-DEPARTMENT',
    ),
    pytest.param(
        'Chương nào nói về CFG và PCFG?',
        'ASK_CHAPTER_BY_TOPIC',
        {'topic': ['CFG', 'PCFG']},
        {'intent': 'GET_TOPIC', 'entities': {'topic': ['CFG', 'PCFG']},
         'attribute': 'chapter', 'answer_mode': 'LIST'},
        id='P1-MULTI-TOPIC',
    ),
]

ADDITIONAL_CASES = [
    pytest.param(
        'NLP có những phần chính nào?',
        'ASK_COURSE_PARTS',
        {},
        {'intent': 'GET_COURSE_INFO', 'entities': {},
         'attribute': 'parts', 'answer_mode': 'LIST'},
        id='P1-COURSE-PARTS',
    ),
    pytest.param(
        'Chương nào học về Features và Augmented Grammar?',
        'ASK_CHAPTER_BY_TOPIC',
        {'topic': ['Features', 'Augmented Grammar']},
        {'intent': 'GET_TOPIC', 'entities': {'topic': ['FEATURES', 'AUGMENTED_GRAMMAR']},
         'attribute': 'chapter', 'answer_mode': 'LIST'},
        id='P1-FEATURES-AUGMENTED-GRAMMAR',
    ),
    pytest.param(
        'Chương nào học về knowledge representation?',
        'ASK_CHAPTER_BY_TOPIC',
        {'topic': ['knowledge representation']},
        {'intent': 'GET_TOPIC', 'entities': {'topic': ['KNOWLEDGE_REPRESENTATION']},
         'attribute': 'chapter', 'answer_mode': 'LIST'},
        id='P1-KNOWLEDGE-REPRESENTATION',
    ),
    pytest.param(
        'Chương nào học về local discourse context?',
        'ASK_CHAPTER_BY_TOPIC',
        {'topic': ['local discourse context']},
        {'intent': 'GET_TOPIC', 'entities': {'topic': ['LOCAL_DISCOURSE_CONTEXT']},
         'attribute': 'chapter', 'answer_mode': 'LIST'},
        id='P1-LOCAL-DISCOURSE-CONTEXT',
    ),
    pytest.param(
        'L.O.4.2 liên quan đến nội dung gì?',
        'ASK_LO_RELATED_CONTENT',
        {'learning_outcome': ['L.O.4.2']},
        {'intent': 'GET_LO', 'entities': {'learning_outcome': ['LO4.2']},
         'attribute': 'content', 'answer_mode': 'LIST'},
        id='P1-LO4.2-CONTENT',
    ),
    pytest.param(
        'L.O.2.5 liên quan đến nội dung gì?',
        'ASK_LO_RELATED_CONTENT',
        {'learning_outcome': ['L.O.2.5']},
        {'intent': 'GET_LO', 'entities': {'learning_outcome': ['LO2.5']},
         'attribute': 'content', 'answer_mode': 'LIST'},
        id='P1-LO2.5-CONTENT',
    ),
    pytest.param(
        'L.O.3.3 liên quan đến nội dung gì?',
        'ASK_LO_RELATED_CONTENT',
        {'learning_outcome': ['L.O.3.3']},
        {'intent': 'GET_LO', 'entities': {'learning_outcome': ['LO3.3']},
         'attribute': 'content', 'answer_mode': 'LIST'},
        id='P1-LO3.3-CONTENT',
    ),
    pytest.param(
        'Bài tập lớn có thể sử dụng LLM hoặc RAG không?',
        'ASK_PERMISSION',
        {'assignment': ['Bài tập lớn'], 'regulation': ['LLM', 'RAG']},
        {'intent': 'GET_RULE', 'entities': {'regulation': ['LLM_RAG']},
         'attribute': 'permission', 'answer_mode': 'BOOLEAN'},
        id='P1-LLM-OR-RAG',
    ),
    pytest.param(
        'Midterm kéo dài bao lâu?',
        'ASK_EXAM_ATTRIBUTE',
        {'exam': ['Midterm'], 'attribute_cue': ['kéo dài bao lâu']},
        {'intent': 'GET_COURSE_INFO', 'entities': {'exam': ['MIDTERM']},
         'attribute': 'duration', 'answer_mode': 'VALUE'},
        id='P1-P2-MIDTERM-DURATION',
    ),
    pytest.param(
        'Final kéo dài bao lâu?',
        'ASK_EXAM_ATTRIBUTE',
        {'exam': ['Final'], 'attribute_cue': ['kéo dài bao lâu']},
        {'intent': 'GET_COURSE_INFO', 'entities': {'exam': ['FINAL']},
         'attribute': 'duration', 'answer_mode': 'VALUE'},
        id='P1-P2-FINAL-DURATION',
    ),
]


@pytest.mark.parametrize('query,frame,slots,semantic', CASES)
def test_person1_requested_coverage(query, frame, slots, semantic):
    parsed = RuleParser().parse(query)
    assert parsed.valid, f'Unsupported natural-language form: {query}'
    assert parsed.query_frame == frame
    assert parsed.slots == slots


@pytest.mark.parametrize('query,frame,slots,semantic', CASES)
def test_person2_with_correct_upstream_input(query, frame, slots, semantic):
    # Isolate Person 2: a Person 1 rejection must not be blamed on the mapper.
    parsed = ParserResult(True, 'WH_QUESTION', frame, slots, None)
    actual, _ = SemanticMapper().map(parsed)
    assert actual.to_dict() == semantic


@pytest.mark.parametrize('query,frame,slots,semantic', CASES)
def test_person12_cases_reach_grounded_retrieval(query, frame, slots, semantic):
    actual = CourseAssistant().ask(query)
    assert actual['person_2_semantic_query'] == semantic
    assert actual['person_3_retrieval_result']['status'] == 'FOUND'
    if len(semantic['entities'].get('topic', [])) > 1:
        assert actual['person_3_retrieval_result']['values'] == ['CH03', 'CH06']
        assert 'ít nhất một chủ đề' in actual['answer']


@pytest.mark.parametrize('query,frame,slots,semantic', ADDITIONAL_CASES)
def test_person1_additional_handoff_parsing(query, frame, slots, semantic):
    parsed = RuleParser().parse(query)
    assert parsed.valid, f'Unsupported natural-language form: {query}'
    assert parsed.query_frame == frame
    assert parsed.slots == slots


@pytest.mark.parametrize('query,frame,slots,semantic', ADDITIONAL_CASES)
def test_person2_additional_handoff_mapping(query, frame, slots, semantic):
    actual, _ = SemanticMapper().map(
        ParserResult(True, 'WH_QUESTION', frame, slots, None)
    )
    assert actual.to_dict() == semantic


@pytest.mark.parametrize(
    'query,expected_values',
    [
        ('NLP có những phần chính nào?', [
            'Grammar and Parser', 'Semantic Interpretation and QA',
            'Local Discourse Context', 'Evaluation',
        ]),
        ('Chương nào học về Features và Augmented Grammar?', ['CH04']),
        ('Chương nào học về knowledge representation?', ['CH11']),
        ('Chương nào học về local discourse context?', ['CH12']),
        ('Bài tập lớn có thể sử dụng LLM hoặc RAG không?', [True]),
        ('Midterm kéo dài bao lâu?', [60]),
        ('Final kéo dài bao lâu?', [90]),
    ],
)
def test_additional_handoff_cases_reach_expected_retrieval(query, expected_values):
    actual = CourseAssistant().ask(query)
    assert actual['person_3_retrieval_result']['values'] == expected_values


def test_integration_sample_dialogue01_week_to_chapter_reference():
    # data/raw/dialogues.txt, DIALOGUE 01 explicitly expects CH03 here.
    bot = CourseAssistant()
    bot.ask('Tuần 3 học gì?')
    actual = bot.ask('Tài liệu của chương này là gì?')
    assert actual['person_1_parser_result']['valid'] is True
    assert actual['person_2_semantic_query'] == {
        'intent': 'GET_RESOURCE', 'entities': {'chapter': ['CH03']},
        'attribute': 'resource', 'answer_mode': 'LIST',
    }
    # This is a topic-based relation, not a prescribed reading list.
    assert actual['person_3_retrieval_result'] == {
        'status': 'FOUND', 'values': ['Natural Language Processing with Python'],
        'sources': ['topics:CH03', 'annotation:resource_topics:RES05', 'resources:RES05'],
    }
