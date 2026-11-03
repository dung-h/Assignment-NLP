"""Regression guards for the versioned end-to-end gold evaluation set."""

from __future__ import annotations

from src.assistant import CourseAssistant
from src.evaluation.gold import evaluate_cases, load_gold_cases, summarize


def _results():
    metadata, cases = load_gold_cases()
    return metadata, cases, evaluate_cases(cases, CourseAssistant)


def test_gold_fixture_covers_every_declared_grammar_frame():
    metadata, cases, _ = _results()
    declared = set(metadata["scope_frames"])
    covered = {
        case.expected.get("parser", {}).get("query_frame")
        for case in cases
        if case.expected.get("parser", {}).get("valid") is True
    }
    assert covered == declared


def test_gold_fixture_keeps_development_and_held_out_cases_separate():
    _, cases, _ = _results()
    splits = {case.split for case in cases}
    assert splits == {"development", "held_out"}
    assert {case.query for case in cases if case.split == "development"}.isdisjoint(
        {case.query for case in cases if case.split == "held_out"}
    )


def test_all_current_failures_are_explicitly_triaged():
    _, _, results = _results()
    unexpected = [
        result.case.case_id
        for result in results
        if not result.passed and result.case.known_failure is None
    ]
    assert unexpected == []


def test_known_failure_cases_still_reproduce_until_their_markers_are_removed():
    _, _, results = _results()
    summary = summarize(results)
    marked = {result.case.case_id for result in results if result.case.known_failure}
    observed = {result.case.case_id for result in summary["observed_known_failures"]}
    assert observed == marked
    assert summary["stale_known_failures"] == []


def test_gold_results_preserve_contract_invariants_for_every_non_error_response():
    _, _, results = _results()
    for result in results:
        retrieval = result.response.get("person_3_retrieval_result")
        if retrieval is None:
            continue
        if retrieval["status"] == "FOUND":
            assert retrieval["values"]
            assert retrieval["sources"]
        else:
            assert retrieval == {"status": "NOT_FOUND", "values": [], "sources": []}
