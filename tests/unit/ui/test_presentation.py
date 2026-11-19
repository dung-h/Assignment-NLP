"""Tests for the UI display boundary and isolated conversation sessions."""

from app import append_turn, new_session, pipeline_html, presentation_state, suggested_questions
from src.assistant import CourseAssistant
from src.syntax.generator import generate


def test_ui_found_missing_and_unknown_are_distinct():
    bot = CourseAssistant()
    found = bot.ask("Chương nào nói về CFG?")
    missing = bot.ask("Ai dạy môn NLP?")
    unknown = bot.ask("Hôm nay ở TP.HCM có mưa không?")

    assert presentation_state(found)["status"] == "FOUND"
    assert "topics:CH03" in pipeline_html(found)
    assert presentation_state(missing)["status"] == "NOT_FOUND"
    assert "Đã tra cứu" in pipeline_html(missing)
    assert unknown["person_3_retrieval_result"]["status"] == "NOT_FOUND"
    assert presentation_state(unknown)["status"] == "UNKNOWN"
    assert "Chưa tra cứu cơ sở tri thức" in pipeline_html(unknown)
    assert "Đã tra cứu nhưng" not in pipeline_html(unknown)


def test_pipeline_escapes_html_in_dynamic_values():
    result = {
        "person_1_parser_result": {"valid": True, "tree": "<script>tree</script>"},
        "person_2_semantic_query": {"intent": "<script>alert(1)</script>", "entities": {}},
        "person_3_retrieval_result": {"status": "FOUND", "sources": ["<img src=x>"]},
    }
    output = pipeline_html(result)
    assert "<script>" not in output and "<img src=x>" not in output
    assert "&lt;script&gt;" in output and "&lt;img src=x&gt;" in output
    assert "&lt;script&gt;tree&lt;/script&gt;" in output


def test_pipeline_shows_full_parser_tree_and_sentence_type():
    result = CourseAssistant().ask("Tuần 3 học gì?")
    output = pipeline_html(result)
    assert result['person_1_parser_result']['tree'] in output
    assert 'WH_QUESTION' in output


def test_chat_history_is_appended_without_mutating_input():
    original = [{"role": "user", "content": "Trước đó"}]
    result = {"answer": "3 tín chỉ"}
    updated = append_turn(original, "Bao nhiêu tín chỉ?", result)
    assert original == [{"role": "user", "content": "Trước đó"}]
    assert updated[-2:] == [
        {"role": "user", "content": "Bao nhiêu tín chỉ?"},
        {"role": "assistant", "content": "3 tín chỉ"},
    ]


def test_sessions_and_reset_do_not_leak_context():
    first, second = new_session(), new_session()
    first.ask("Tuần 3 học gì?")
    followup = first.ask("Tài liệu của chương này là gì?")
    isolated = second.ask("Tài liệu của chương này là gì?")
    assert followup["person_2_semantic_query"]["entities"]["chapter"] == ["CH03"]
    assert isolated["person_2_semantic_query"]["intent"] == "UNKNOWN"
    first.reset_context()
    assert first.ask("Tài liệu của chương này là gì?")["person_2_semantic_query"]["intent"] == "UNKNOWN"


def test_supplied_template_is_copied_and_reset_per_session():
    template = CourseAssistant()
    template.ask("Tuần 3 học gì?")
    fresh = new_session(template)
    assert fresh is not template
    assert fresh.ask("Tài liệu của chương này là gì?")["person_2_semantic_query"]["intent"] == "UNKNOWN"
    assert template.ask("Tài liệu của chương này là gì?")["person_2_semantic_query"]["entities"]["chapter"] == ["CH03"]


def test_suggestions_come_from_grammar_and_work_without_prior_context():
    suggestions = suggested_questions()
    assert len(suggestions) == 8
    assert len(set(suggestions)) == len(suggestions)
    assert set(suggestions) <= set(generate())
    outcomes = []
    for question in suggestions:
        result = CourseAssistant().ask(question)
        assert result['person_1_parser_result']['valid']
        assert result['person_2_semantic_query']['intent'] != 'UNKNOWN'
        outcomes.append(result['person_3_retrieval_result']['status'])
    assert 'FOUND' in outcomes
    assert 'NOT_FOUND' in outcomes
