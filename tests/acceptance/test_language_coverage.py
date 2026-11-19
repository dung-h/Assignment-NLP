"""Language-coverage and pipeline handoff checks beyond the frozen gold set.

The tests deliberately check individual pipeline boundaries as well as full
requests. A parser rejection and a semantic-mapping mismatch are distinct
failures, even when they originate from the same example question. These extra
cases are not part of the frozen gold evaluation score.
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
        id='course-ects',
    ),
    pytest.param(
        'Môn NLP thuộc khoa nào?',
        'ASK_COURSE_ATTRIBUTE',
        {'course': ['NLP'], 'attribute_cue': ['thuộc khoa nào']},
        {'intent': 'GET_COURSE_INFO', 'entities': {'course': ['CO3085']},
         'attribute': 'department', 'answer_mode': 'VALUE'},
        id='course-department',
    ),
    pytest.param(
        'Chương nào nói về CFG và PCFG?',
        'ASK_CHAPTER_BY_TOPIC',
        {'topic': ['CFG', 'PCFG']},
        {'intent': 'GET_TOPIC', 'entities': {'topic': ['CFG', 'PCFG']},
         'attribute': 'chapter', 'answer_mode': 'LIST'},
        id='multiple-topics',
    ),
]

ADDITIONAL_CASES = [
    pytest.param(
        'NLP có những phần chính nào?',
        'ASK_COURSE_PARTS',
        {},
        {'intent': 'GET_COURSE_INFO', 'entities': {},
         'attribute': 'parts', 'answer_mode': 'LIST'},
        id='course-parts',
    ),
    pytest.param(
        'Chương nào học về Features và Augmented Grammar?',
        'ASK_CHAPTER_BY_TOPIC',
        {'topic': ['Features', 'Augmented Grammar']},
        {'intent': 'GET_TOPIC', 'entities': {'topic': ['FEATURES', 'AUGMENTED_GRAMMAR']},
         'attribute': 'chapter', 'answer_mode': 'LIST'},
        id='features-and-augmented-grammar',
    ),
    pytest.param(
        'Chương nào học về knowledge representation?',
        'ASK_CHAPTER_BY_TOPIC',
        {'topic': ['knowledge representation']},
        {'intent': 'GET_TOPIC', 'entities': {'topic': ['KNOWLEDGE_REPRESENTATION']},
         'attribute': 'chapter', 'answer_mode': 'LIST'},
        id='knowledge-representation',
    ),
    pytest.param(
        'Chương nào học về local discourse context?',
        'ASK_CHAPTER_BY_TOPIC',
        {'topic': ['local discourse context']},
        {'intent': 'GET_TOPIC', 'entities': {'topic': ['LOCAL_DISCOURSE_CONTEXT']},
         'attribute': 'chapter', 'answer_mode': 'LIST'},
        id='local-discourse-context',
    ),
    pytest.param(
        'L.O.4.2 liên quan đến nội dung gì?',
        'ASK_LO_RELATED_CONTENT',
        {'learning_outcome': ['L.O.4.2']},
        {'intent': 'GET_LO', 'entities': {'learning_outcome': ['LO4.2']},
         'attribute': 'related_content', 'answer_mode': 'LIST'},
        id='lo4.2-related-content',
    ),
    pytest.param(
        'L.O.2.5 liên quan đến nội dung gì?',
        'ASK_LO_RELATED_CONTENT',
        {'learning_outcome': ['L.O.2.5']},
        {'intent': 'GET_LO', 'entities': {'learning_outcome': ['LO2.5']},
         'attribute': 'related_content', 'answer_mode': 'LIST'},
        id='lo2.5-related-content',
    ),
    pytest.param(
        'L.O.3.3 liên quan đến nội dung gì?',
        'ASK_LO_RELATED_CONTENT',
        {'learning_outcome': ['L.O.3.3']},
        {'intent': 'GET_LO', 'entities': {'learning_outcome': ['LO3.3']},
         'attribute': 'related_content', 'answer_mode': 'LIST'},
        id='lo3.3-related-content',
    ),
    pytest.param(
        'Bài tập lớn có thể sử dụng LLM hoặc RAG không?',
        'ASK_PERMISSION',
        {'assignment': ['Bài tập lớn'], 'regulation': ['LLM', 'RAG']},
        {'intent': 'GET_RULE', 'entities': {'regulation': ['LLM_RAG']},
         'attribute': 'permission', 'answer_mode': 'BOOLEAN'},
        id='llm-or-rag-permission',
    ),
    pytest.param(
        'Midterm kéo dài bao lâu?',
        'ASK_EXAM_ATTRIBUTE',
        {'exam': ['Midterm'], 'attribute_cue': ['kéo dài bao lâu']},
        {'intent': 'GET_COURSE_INFO', 'entities': {'exam': ['MIDTERM']},
         'attribute': 'duration', 'answer_mode': 'VALUE'},
        id='midterm-duration',
    ),
    pytest.param(
        'Final kéo dài bao lâu?',
        'ASK_EXAM_ATTRIBUTE',
        {'exam': ['Final'], 'attribute_cue': ['kéo dài bao lâu']},
        {'intent': 'GET_COURSE_INFO', 'entities': {'exam': ['FINAL']},
         'attribute': 'duration', 'answer_mode': 'VALUE'},
        id='final-duration',
    ),
]


@pytest.mark.parametrize('query,frame,slots,semantic', CASES)
def test_parser_recognizes_core_language_forms(query, frame, slots, semantic):
    parsed = RuleParser().parse(query)
    assert parsed.valid, f'Unsupported natural-language form: {query}'
    assert parsed.query_frame == frame
    assert parsed.slots == slots


@pytest.mark.parametrize('query,frame,slots,semantic', CASES)
def test_semantic_mapper_maps_parser_output_to_contract(query, frame, slots, semantic):
    # Supply a valid parser result to isolate semantic mapping from parsing.
    parsed = ParserResult(True, 'WH_QUESTION', frame, slots, None)
    actual, _ = SemanticMapper().map(parsed)
    assert actual.to_dict() == semantic


@pytest.mark.parametrize('query,frame,slots,semantic', CASES)
def test_core_language_forms_reach_grounded_answers(query, frame, slots, semantic):
    actual = CourseAssistant().ask(query)
    assert actual['person_2_semantic_query'] == semantic
    assert actual['person_3_retrieval_result']['status'] == 'FOUND'
    if len(semantic['entities'].get('topic', [])) > 1:
        assert actual['person_3_retrieval_result']['values'] == ['CH03', 'CH06']
        assert 'ít nhất một chủ đề' in actual['answer']


@pytest.mark.parametrize('query,frame,slots,semantic', ADDITIONAL_CASES)
def test_parser_recognizes_additional_language_forms(query, frame, slots, semantic):
    parsed = RuleParser().parse(query)
    assert parsed.valid, f'Unsupported natural-language form: {query}'
    assert parsed.query_frame == frame
    assert parsed.slots == slots


@pytest.mark.parametrize('query,frame,slots,semantic', ADDITIONAL_CASES)
def test_semantic_mapper_handles_additional_parser_frames(query, frame, slots, semantic):
    actual, _ = SemanticMapper().map(
        ParserResult(True, 'WH_QUESTION', frame, slots, None)
    )
    assert actual.to_dict() == semantic


@pytest.mark.parametrize(
    'query,expected_values',
    [
        ('NLP có những phần chính nào?', [
            'Part I - Syntactic Processing', 'Part II - Semantic Interpretation',
            'Part III - Context and World Knowledge',
        ]),
        ('Chương nào học về Features và Augmented Grammar?', ['CH04']),
        ('Chương nào học về knowledge representation?', ['CH11']),
        ('Chương nào học về local discourse context?', ['CH12']),
        ('Bài tập lớn có thể sử dụng LLM hoặc RAG không?', [True]),
        ('Midterm kéo dài bao lâu?', [60]),
        ('Final kéo dài bao lâu?', [90]),
    ],
)
def test_additional_language_forms_reach_expected_retrieval(query, expected_values):
    actual = CourseAssistant().ask(query)
    assert actual['person_3_retrieval_result']['values'] == expected_values


def test_sample_dialogue_resolves_week_to_chapter_reference():
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
