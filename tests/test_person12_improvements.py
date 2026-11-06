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
    # No chapter-to-resource relation is present in the current KB.
    assert actual['person_3_retrieval_result'] == {
        'status': 'NOT_FOUND', 'values': [], 'sources': [],
    }
