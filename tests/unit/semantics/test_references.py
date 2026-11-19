"""References follow current focus or an explicitly named entity type."""

import pytest

from src.assistant import CourseAssistant
from src.contracts import ContextState, ParserResult
from src.semantics.semantic_mapper import SemanticMapper
from src.semantics.semantic_query_validator import SemanticQueryValidator


def parsed(frame, slots):
    return ParserResult(True, "WH_QUESTION", frame, slots)


def part_then_chapter(mapper):
    _, context = mapper.map(parsed("ASK_ASSIGNMENT_PART_INFO", {"assignment_part": ["phần I"]}))
    _, context = mapper.map(parsed("ASK_CHAPTER_CONTENT", {"chapter": ["chương 4"]}), context)
    return context


@pytest.mark.parametrize("reference", ["chương này", "nó"])
def test_part_then_chapter_reference_selects_current_chapter(reference):
    mapper = SemanticMapper()
    context = part_then_chapter(mapper)
    query, _ = mapper.map(parsed("ASK_CHAPTER_CONTENT", {"reference": [reference]}), context)
    assert query.entities == {"chapter": ["CH04"]}
    assert SemanticQueryValidator().validate(query) == "ASK_CHAPTER_CONTENT"


def test_chapter_then_part_pronoun_selects_current_part():
    mapper = SemanticMapper()
    _, context = mapper.map(parsed("ASK_CHAPTER_CONTENT", {"chapter": ["chương 4"]}))
    _, context = mapper.map(parsed("ASK_ASSIGNMENT_PART_INFO", {"assignment_part": ["phần I"]}), context)
    query, _ = mapper.map(parsed("ASK_ASSIGNMENT_OUTPUTS", {"reference": ["nó"]}), context)
    assert query.entities == {"assignment_part": ["BTL_PART_1"]}
    assert SemanticQueryValidator().validate(query) == "ASK_ASSIGNMENT_OUTPUTS"


def test_explicit_chapter_reference_can_return_to_an_earlier_chapter():
    mapper = SemanticMapper()
    _, context = mapper.map(parsed("ASK_CHAPTER_CONTENT", {"chapter": ["chương 4"]}))
    _, context = mapper.map(parsed("ASK_ASSIGNMENT_PART_INFO", {"assignment_part": ["phần I"]}), context)
    query, _ = mapper.map(parsed("ASK_CHAPTER_CONTENT", {"reference": ["chương này"]}), context)
    assert query.entities == {"chapter": ["CH04"]}


def test_pronoun_does_not_skip_current_chapter_for_an_old_compatible_part():
    mapper = SemanticMapper()
    context = part_then_chapter(mapper)
    query, updated = mapper.map(parsed("ASK_ASSIGNMENT_OUTPUTS", {"reference": ["nó"]}), context)
    assert query.intent == "UNKNOWN"
    assert updated is context


@pytest.mark.parametrize(
    "frame,reference,focus",
    [
        ("ASK_ASSIGNMENT_OUTPUTS", "phần này", []),
        ("ASK_RESOURCE_BY_CHAPTER", "chương này", [{"type": "topic", "id": "CFG"}]),
        ("ASK_ASSIGNMENT_OUTPUTS", "chương này", [{"type": "chapter", "id": "CH04"}]),
        ("ASK_CHAPTER_CONTENT", "chương này", [
            {"type": "chapter", "id": "CH03"}, {"type": "chapter", "id": "CH06"}
        ]),
        ("ASK_CHAPTER_CONTENT", "nó", [
            {"type": "chapter", "id": "CH03"}, {"type": "chapter", "id": "CH06"}
        ]),
    ],
)
def test_missing_incompatible_or_ambiguous_reference_is_unknown(frame, reference, focus):
    context = ContextState(focus)
    query, updated = SemanticMapper().map(parsed(frame, {"reference": [reference]}), context)
    assert query.intent == "UNKNOWN"
    assert updated is context


@pytest.mark.parametrize(
    "frame,entity_type,entity_id,reference,expected",
    [
        ("ASK_CHAPTER_CONTENT", "chapter", "CH04", "chương sau", "CH05"),
        ("ASK_CHAPTER_CONTENT", "chapter", "CH04", "chương trước", "CH03"),
        ("ASK_WEEK_CONTENT", "week", "WEEK_03", "tuần sau", "WEEK_04"),
        ("ASK_WEEK_CONTENT", "week", "WEEK_03", "tuần trước", "WEEK_02"),
        ("ASK_ASSIGNMENT_OUTPUTS", "assignment_part", "BTL_PART_2", "phần sau", "BTL_PART_3"),
        ("ASK_ASSIGNMENT_OUTPUTS", "assignment_part", "BTL_PART_2", "phần trước", "BTL_PART_1"),
    ],
)
def test_relative_reference_keeps_canonical_ids(frame, entity_type, entity_id, reference, expected):
    context = ContextState([{"type": entity_type, "id": entity_id}])
    query, _ = SemanticMapper().map(parsed(frame, {"reference": [reference]}), context)
    assert query.entities == {entity_type: [expected]}
    assert SemanticQueryValidator().validate(query) == frame


def test_shift_before_first_chapter_is_unknown_and_keeps_context():
    context = ContextState([{"type": "chapter", "id": "CH01"}])
    query, updated = SemanticMapper().map(
        parsed("ASK_CHAPTER_CONTENT", {"reference": ["chương trước"]}), context
    )
    assert query.intent == "UNKNOWN"
    assert updated is context


def test_real_pipeline_survives_part_to_chapter_topic_switch():
    bot = CourseAssistant()
    bot.ask("Phần I cần xuất file gì?")
    bot.ask("Chương 4 nói về gì?")
    result = bot.ask("Nó có liên quan đến parsing không?")
    assert result["person_2_semantic_query"]["entities"] == {
        "topic": ["PARSING"], "chapter": ["CH04"]
    }
    retrieval = result["person_3_retrieval_result"]
    assert retrieval["status"] == "FOUND"
    assert retrieval["values"] == [True]
    assert retrieval["sources"] == ["topics:CH04"]
    assert "Có." in result["answer"]
    assert "topics:CH04" in result["answer"]


def test_reset_context_makes_unresolved_reference_unknown():
    bot = CourseAssistant()
    bot.ask("Chương 4 nói về gì?")
    bot.reset_context()
    result = bot.ask("Nó có liên quan đến parsing không?")
    assert result["person_2_semantic_query"]["intent"] == "UNKNOWN"
    assert result["person_3_retrieval_result"] == {
        "status": "NOT_FOUND", "values": [], "sources": []
    }
    assert result["context_state"] == {"focus_entities": []}
