"""End-to-end coverage for the previously unrecognized query frames."""

import pytest

from src.assistant import CourseAssistant
from src.semantics.semantic_query_validator import SemanticQueryValidator


@pytest.fixture(scope="module")
def assistant():
    return CourseAssistant()


@pytest.mark.parametrize(
    "question, frame, intent, attribute, status, expected",
    [
        ("Email của giảng viên là gì?", "ASK_INSTRUCTOR_ATTRIBUTE", "GET_INSTRUCTOR", "email", "NOT_FOUND", None),
        ("Tuần 5 có hoạt động gì?", "ASK_WEEK_ACTIVITY", "GET_SCHEDULE", "activity", "FOUND", "feature-based parsing exercises"),
        ("Tuần 8 có mốc gì?", "ASK_WEEK_MILESTONE", "GET_SCHEDULE", "milestone", "FOUND", "BTL checkpoint 1 - grammar and parser"),
        ("Những tuần nào có mốc?", "ASK_MILESTONE_WEEK", "GET_SCHEDULE", "week", "FOUND", "WEEK_08"),
        ("Chương 3 có tên là gì?", "ASK_CHAPTER_TITLE", "GET_TOPIC", "title", "FOUND", "GRAMMAR AND PARSING"),
        ("Chương 3 thuộc phần môn nào?", "ASK_PART_OF_CHAPTER", "GET_TOPIC", "part", "FOUND", "Syntactic Processing"),
        ("Phần môn I có những chương nào?", "ASK_CHAPTERS_OF_PART", "GET_TOPIC", "chapter", "FOUND", "CH03"),
        ("Bài tập lớn gồm những phần nào?", "ASK_ASSIGNMENT_PARTS", "GET_ASSIGNMENT", "parts", "FOUND", "BTL_PART_3"),
        ("Bài tập lớn có những yêu cầu gì?", "ASK_ASSIGNMENT_REQUIREMENTS", "GET_ASSIGNMENT", "requirements", "FOUND", "xây dựng parser"),
        ("Hạn nộp phần I của bài tập lớn khi nào?", "ASK_ASSIGNMENT_PART_DEADLINE", "GET_DEADLINE", "date", "NOT_FOUND", None),
        ("Hạn nộp DEADLINE_01 là ngày nào?", "ASK_DEADLINE_INFO", "GET_DEADLINE", "date", "NOT_FOUND", None),
        ("Tác giả của tài liệu RES05 là gì?", "ASK_RESOURCE_ATTRIBUTE", "GET_RESOURCE", "authors", "FOUND", "Steven Bird; Ewan Klein; Edward Loper"),
    ],
)
def test_frame_through_pipeline(assistant, question, frame, intent, attribute, status, expected):
    assistant.reset_context()
    result = assistant.ask(question)
    assert result["person_1_parser_result"]["query_frame"] == frame
    query = result["person_2_semantic_query"]
    assert (query["intent"], query["attribute"]) == (intent, attribute)
    retrieval = result["person_3_retrieval_result"]
    assert retrieval["status"] == status
    if expected is None:
        assert retrieval["values"] == [] and retrieval["sources"] == []
    else:
        assert expected in retrieval["values"]
        assert retrieval["sources"]


def test_all_contract_frames_have_grammar_rules(assistant):
    configured = {rule["frame"] for rule in assistant.parser.spec["rules"]}
    assert set(SemanticQueryValidator().frames) <= configured


def test_assignment_parts_are_flat_and_requirements_mark_extension(assistant):
    parts = assistant.ask("Bài tập lớn gồm những phần nào?")
    assert parts["person_3_retrieval_result"]["values"] == [
        "BTL_PART_1", "BTL_PART_2", "BTL_PART_3", "BTL_PART_4"
    ]
    assert "Local Discourse Context" in parts["answer"]
    requirements = assistant.ask("Bài tập lớn có những yêu cầu gì?")
    assert requirements["person_1_parser_result"]["query_frame"] == "ASK_ASSIGNMENT_REQUIREMENTS"
    assert "ngữ cảnh" in requirements["answer"] and "mở rộng" in requirements["answer"]
