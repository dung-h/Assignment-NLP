"""Ground week-to-chapter conversation focus in the loaded schedule."""

from types import SimpleNamespace

import pytest

from src.assistant import CourseAssistant
from src.contracts import ContextState, RetrievalResult, SemanticQuery
from src.knowledge.focus import week_chapter_focus
from src.knowledge.loader import KnowledgeBase
from src.semantics.semantic_mapper import SemanticMapper
from src.syntax.parser import RuleParser


def test_week_three_chapter_relation_is_loaded_from_schedule():
    assert KnowledgeBase().weeks['WEEK_03']['chapter_ids'] == ['CH03']


def test_named_chapter_reference_resolves_when_context_is_available():
    parsed = RuleParser().parse('Tài liệu của chương này là gì?')
    context = ContextState([{'type': 'chapter', 'id': 'CH03'}])
    actual, _ = SemanticMapper().map(parsed, context)
    assert actual.to_dict() == {
        'intent': 'GET_RESOURCE', 'entities': {'chapter': ['CH03']},
        'attribute': 'resource', 'answer_mode': 'LIST',
    }


def test_week_focus_uses_kb_relation_and_keeps_week_as_current_focus():
    kb = SimpleNamespace(weeks={'WEEK_03': {'chapter_ids': ['CH07']}})
    query = SemanticQuery('GET_SCHEDULE', {'week': ['WEEK_03']}, 'topics', 'LIST')
    result = RetrievalResult('FOUND', ['topic'], ['schedule:WEEK_03'])
    context = ContextState([{'type': 'week', 'id': 'WEEK_03'}, {'type': 'chapter', 'id': 'CH01'}])
    updated = week_chapter_focus(query, result, kb, context)
    assert updated.focus_entities == [
        {'type': 'week', 'id': 'WEEK_03'}, {'type': 'chapter', 'id': 'CH07'},
    ]
    assert context.focus_entities[1]['id'] == 'CH01'


@pytest.mark.parametrize('chapter_ids,status', [([], 'FOUND'), (['CH03', 'CH04'], 'FOUND'), (['CH03'], 'NOT_FOUND')])
def test_no_stale_chapter_when_relation_is_missing_ambiguous_or_unretrieved(chapter_ids, status):
    kb = SimpleNamespace(weeks={'WEEK_03': {'chapter_ids': chapter_ids}})
    query = SemanticQuery('GET_SCHEDULE', {'week': ['WEEK_03']}, 'topics', 'LIST')
    result = RetrievalResult(status, ['topic'] if status == 'FOUND' else [], [])
    context = ContextState([{'type': 'week', 'id': 'WEEK_03'}, {'type': 'chapter', 'id': 'CH01'}])
    assert week_chapter_focus(query, result, kb, context).focus_entities == [
        {'type': 'week', 'id': 'WEEK_03'},
    ]


def test_multiple_weeks_do_not_select_a_chapter():
    kb = SimpleNamespace(weeks={'WEEK_03': {'chapter_ids': ['CH03']}, 'WEEK_04': {'chapter_ids': ['CH04']}})
    query = SemanticQuery('GET_SCHEDULE', {'week': ['WEEK_03', 'WEEK_04']}, 'topics', 'LIST')
    result = RetrievalResult('FOUND', ['topic'], ['schedule:WEEK_03'])
    context = ContextState([{'type': 'week', 'id': 'WEEK_03'}, {'type': 'chapter', 'id': 'CH01'}])
    assert all(item['type'] != 'chapter' for item in week_chapter_focus(query, result, kb, context).focus_entities)


def test_unrelated_query_leaves_context_unchanged():
    kb = SimpleNamespace(weeks={})
    query = SemanticQuery('GET_TOPIC', {'chapter': ['CH03']}, 'summary', 'VALUE')
    result = RetrievalResult('FOUND', ['summary'], ['topics:CH03'])
    context = ContextState([{'type': 'chapter', 'id': 'CH03'}])
    assert week_chapter_focus(query, result, kb, context) is context


def test_end_to_end_resolves_week_chapter_without_inventing_resource_relation():
    bot = CourseAssistant()
    first = bot.ask('Tuần 3 học gì?')
    assert {'type': 'chapter', 'id': 'CH03'} in first['context_state']['focus_entities']
    second = bot.ask('Tài liệu của chương này là gì?')
    assert second['person_2_semantic_query'] == {
        'intent': 'GET_RESOURCE', 'entities': {'chapter': ['CH03']},
        'attribute': 'resource', 'answer_mode': 'LIST',
    }
    assert second['person_3_retrieval_result'] == {'status': 'NOT_FOUND', 'values': [], 'sources': []}


@pytest.mark.parametrize('chapter_ids', [[], ['CH03', 'CH04']])
def test_end_to_end_does_not_reuse_old_chapter_when_week_is_unclear(chapter_ids):
    bot = CourseAssistant()
    bot.ask('Chương 4 nói về gì?')
    bot.kb.weeks['WEEK_03']['chapter_ids'] = chapter_ids
    first = bot.ask('Tuần 3 học gì?')
    assert all(item['type'] != 'chapter' for item in first['context_state']['focus_entities'])
    second = bot.ask('Tài liệu của chương này là gì?')
    assert second['person_2_semantic_query']['intent'] == 'UNKNOWN'
