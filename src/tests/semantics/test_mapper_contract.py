"""Person 2 must emit queries accepted by the frozen Person 3 boundary."""

import pytest

from src.contracts import ContextState, ParserResult
from src.semantics.semantic_mapper import SemanticMapper
from src.semantics.semantic_query_validator import SemanticQueryValidator


def parsed(frame, slots=None):
    return ParserResult(True, "WH_QUESTION", frame, slots or {})


@pytest.mark.parametrize(
    "frame,cue,entities,attribute",
    [
        ("ASK_COURSE_ATTRIBUTE", "tín chỉ", {}, "credits"),
        ("ASK_COURSE_ATTRIBUTE", "ECTS", {}, "ects"),
        ("ASK_COURSE_ATTRIBUTE", "khoa", {}, "department"),
        ("ASK_COURSE_ATTRIBUTE", "học kỳ", {}, "semester"),
        ("ASK_COURSE_ATTRIBUTE", "loại môn", {}, "course_type"),
        ("ASK_COURSE_ATTRIBUTE", "hình thức", {}, "format"),
        ("ASK_COURSE_ATTRIBUTE", "tổng giờ", {}, "total_course_hours"),
        ("ASK_COURSE_ATTRIBUTE", "giờ lý thuyết", {}, "lecture_hours"),
        ("ASK_COURSE_ATTRIBUTE", "giờ bài tập", {}, "major_assignment_hours"),
        ("ASK_COURSE_ATTRIBUTE", "giờ tự học", {}, "self_study_hours"),
        ("ASK_COURSE_ATTRIBUTE", "mô tả", {}, "description"),
        ("ASK_EXAM_ATTRIBUTE", "thời lượng", {"exam": ["midterm"]}, "duration"),
        ("ASK_EXAM_ATTRIBUTE", "hình thức", {"exam": ["final"]}, "format"),
        ("ASK_EXAM_ATTRIBUTE", "trọng số", {"exam": ["final"]}, "weight"),
        ("ASK_INSTRUCTOR_ATTRIBUTE", "tên", {}, "name"),
        ("ASK_INSTRUCTOR_ATTRIBUTE", "email", {}, "email"),
        ("ASK_INSTRUCTOR_ATTRIBUTE", "văn phòng", {}, "office"),
        ("ASK_RESOURCE_ATTRIBUTE", "tác giả", {"resource": ["RES01"]}, "authors"),
        ("ASK_RESOURCE_ATTRIBUTE", "năm", {"resource": ["RES01"]}, "year"),
        ("ASK_RESOURCE_ATTRIBUTE", "nhà xuất bản", {"resource": ["RES01"]}, "publisher"),
        ("ASK_RESOURCE_ATTRIBUTE", "sử dụng", {"resource": ["RES01"]}, "usage"),
    ],
)
def test_supported_attribute_matches_frozen_frame(frame, cue, entities, attribute):
    query, _ = SemanticMapper().map(
        parsed(frame, {**entities, "attribute_cue": [cue]})
    )
    assert query.attribute == attribute
    assert query.answer_mode == "VALUE"
    assert SemanticQueryValidator().validate(query) == frame


@pytest.mark.parametrize(
    "frame,cue,entities",
    [
        ("ASK_COURSE_ATTRIBUTE", "tên tiếng anh", {"course": ["NLP"]}),
        ("ASK_COURSE_ATTRIBUTE", "tên", {}),
        ("ASK_COURSE_ATTRIBUTE", "đánh giá", {}),
        ("ASK_COURSE_ATTRIBUTE", "parts", {}),
        ("ASK_COURSE_ATTRIBUTE", "", {}),
        ("ASK_RESOURCE_ATTRIBUTE", "title", {"resource": ["RES01"]}),
        ("ASK_RESOURCE_ATTRIBUTE", "tài liệu", {"resource": ["RES01"]}),
        ("ASK_RESOURCE_ATTRIBUTE", "màu bìa", {"resource": ["RES01"]}),
        ("ASK_INSTRUCTOR_ATTRIBUTE", "số điện thoại", {}),
    ],
)
def test_unsupported_attribute_returns_unknown_without_changing_context(frame, cue, entities):
    context = ContextState([{"type": "chapter", "id": "CH04"}])
    query, updated = SemanticMapper().map(
        parsed(frame, {**entities, "attribute_cue": [cue]}), context
    )
    assert query.to_dict() == {
        "intent": "UNKNOWN", "entities": {}, "attribute": None, "answer_mode": "VALUE"
    }
    assert updated is context


@pytest.mark.parametrize(
    "frame,slots",
    [
        ("NOT_A_SHARED_FRAME", {}),
        ("ASK_CHAPTER_CONTENT", {}),
        ("ASK_EXAM_ATTRIBUTE", {"attribute_cue": ["duration"]}),
        ("ASK_RESOURCE_ATTRIBUTE", {"attribute_cue": ["authors"]}),
        ("ASK_COURSE_ATTRIBUTE", {"chapter": ["CH04"], "attribute_cue": ["credits"]}),
        ("ASK_WEEK_OF_CHAPTER", {"topic": ["CFG"]}),
    ],
)
def test_invalid_frame_or_entities_do_not_cross_retrieval_boundary(frame, slots):
    query, _ = SemanticMapper().map(parsed(frame, slots))
    assert query.intent == "UNKNOWN"


def test_course_parts_keeps_the_list_frame():
    query, _ = SemanticMapper().map(parsed("ASK_COURSE_PARTS"))
    assert query.attribute == "parts"
    assert query.answer_mode == "LIST"
    assert SemanticQueryValidator().validate(query) == "ASK_COURSE_PARTS"


def test_kb_existence_is_not_a_semantic_validation_requirement():
    query, _ = SemanticMapper().map(parsed("ASK_CHAPTER_CONTENT", {"chapter": ["CH99"]}))
    assert query.entities == {"chapter": ["CH99"]}
    assert SemanticQueryValidator().validate(query) == "ASK_CHAPTER_CONTENT"
