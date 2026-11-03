"""Deterministic, fact-level evaluation of end-to-end gold cases.

The evaluator deliberately reports failed expectations instead of treating a
successful process exit as evidence that the assistant answered correctly.
It is used by both the report exporter and regression tests.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD_PATH = ROOT / "data" / "annotations" / "evaluation_v1.yaml"


@dataclass(frozen=True)
class GoldCase:
    case_id: str
    query: str
    split: str
    group: str
    expected: dict[str, Any]
    provenance: list[str]
    known_failure: dict[str, str] | None = None
    conversation_id: str | None = None
    turn: int | None = None


@dataclass(frozen=True)
class CaseResult:
    case: GoldCase
    passed: bool
    layer_ok: dict[str, bool]
    failures: tuple[str, ...]
    response: dict[str, Any]


def _as_sources(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError("provenance must be a string or list of strings")


def load_gold_cases(path: Path = DEFAULT_GOLD_PATH) -> tuple[dict[str, Any], list[GoldCase]]:
    """Load and minimally validate the versioned gold-case fixture."""

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("version") != 1:
        raise ValueError("gold fixture must be a mapping with version: 1")
    if not isinstance(raw.get("scope_frames"), list):
        raise ValueError("gold fixture must list scope_frames")
    raw_cases = raw.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("gold fixture must contain a non-empty cases list")

    cases: list[GoldCase] = []
    seen: set[str] = set()
    for item in raw_cases:
        if not isinstance(item, dict):
            raise ValueError("every gold case must be a mapping")
        required = {"id", "query", "split", "group", "provenance", "expected"}
        missing = required - set(item)
        if missing:
            raise ValueError(f"gold case missing {sorted(missing)}")
        case_id = item["id"]
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise ValueError(f"invalid or duplicate gold case id: {case_id!r}")
        if item["split"] not in {"development", "held_out"}:
            raise ValueError(f"{case_id}: split must be development or held_out")
        if item["group"] not in {"independent", "context"}:
            raise ValueError(f"{case_id}: unsupported group")
        if not isinstance(item["expected"], dict):
            raise ValueError(f"{case_id}: expected must be a mapping")
        if item["group"] == "context" and (
            not item.get("conversation_id") or not isinstance(item.get("turn"), int)
        ):
            raise ValueError(f"{case_id}: context case needs conversation_id and turn")
        known = item.get("known_failure")
        if known is not None and (
            not isinstance(known, dict)
            or not isinstance(known.get("owner"), str)
            or not isinstance(known.get("reason"), str)
        ):
            raise ValueError(f"{case_id}: known_failure needs owner and reason")
        seen.add(case_id)
        cases.append(
            GoldCase(
                case_id=case_id,
                query=item["query"],
                split=item["split"],
                group=item["group"],
                provenance=_as_sources(item["provenance"]),
                expected=item["expected"],
                known_failure=known,
                conversation_id=item.get("conversation_id"),
                turn=item.get("turn"),
            )
        )
    return raw, cases


def _same(actual: Any, expected: Any) -> bool:
    return actual == expected


def _expect_mapping(
    layer: str, actual: dict[str, Any], expected: dict[str, Any]
) -> list[str]:
    failures: list[str] = []
    for key, wanted in expected.items():
        if key == "tree":
            tree = actual.get("tree")
            ok = bool(tree) if wanted == "non_empty" else tree is None
        else:
            ok = _same(actual.get(key), wanted)
        if not ok:
            failures.append(
                f"{layer}.{key}: expected {wanted!r}; got {actual.get(key)!r}"
            )
    return failures


def _expect_retrieval(actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for key in ("status", "values", "sources"):
        if key in expected and actual.get(key) != expected[key]:
            failures.append(
                f"retrieval.{key}: expected {expected[key]!r}; got {actual.get(key)!r}"
            )
    for key, actual_key in (("values_include", "values"), ("sources_include", "sources")):
        if key in expected:
            missing = [item for item in expected[key] if item not in actual.get(actual_key, [])]
            if missing:
                failures.append(f"retrieval.{actual_key}: missing {missing!r}")
    return failures


def _expect_answer(actual: str, expected: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for phrase in expected.get("contains", []):
        if phrase not in actual:
            failures.append(f"answer: missing required fact/source {phrase!r}")
    for phrase in expected.get("not_contains", []):
        if phrase in actual:
            failures.append(f"answer: contains forbidden claim {phrase!r}")
    return failures


def evaluate_case(assistant: Any, case: GoldCase) -> CaseResult:
    """Run one turn and evaluate only the assertions expressed by its oracle."""

    try:
        response = assistant.ask(case.query)
    except Exception as exc:  # Keep pipeline errors in the evaluation denominator.
        expected_layers = {
            layer: False
            for layer in ("parser", "semantic", "retrieval", "answer")
            if layer in case.expected
        }
        return CaseResult(
            case,
            False,
            expected_layers,
            (f"pipeline: {type(exc).__name__}: {exc}",),
            {"error": f"{type(exc).__name__}: {exc}"},
        )
    failures: list[str] = []
    layer_ok: dict[str, bool] = {}
    expectations = case.expected
    layers = (
        ("parser", "person_1_parser_result", _expect_mapping),
        ("semantic", "person_2_semantic_query", _expect_mapping),
        ("retrieval", "person_3_retrieval_result", _expect_retrieval),
    )
    for layer, response_key, assertion in layers:
        if layer not in expectations:
            continue
        layer_failures = assertion(layer, response[response_key], expectations[layer]) if layer != "retrieval" else assertion(response[response_key], expectations[layer])
        failures.extend(layer_failures)
        layer_ok[layer] = not layer_failures
    if "answer" in expectations:
        layer_failures = _expect_answer(response["answer"], expectations["answer"])
        failures.extend(layer_failures)
        layer_ok["answer"] = not layer_failures
    return CaseResult(case, not failures, layer_ok, tuple(failures), response)


def evaluate_cases(cases: list[GoldCase], assistant_factory: Any) -> list[CaseResult]:
    """Evaluate independent cases in isolation and context cases by dialogue."""

    results: list[CaseResult] = []
    for case in cases:
        if case.group == "independent":
            results.append(evaluate_case(assistant_factory(), case))

    conversations: dict[str, list[GoldCase]] = defaultdict(list)
    for case in cases:
        if case.group == "context":
            conversations[case.conversation_id].append(case)
    for conversation_id in sorted(conversations):
        assistant = assistant_factory()
        for case in sorted(conversations[conversation_id], key=lambda item: item.turn):
            results.append(evaluate_case(assistant, case))
    return results


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    """Create denominator-preserving metrics for report export."""

    total = len(results)
    strict_passed = sum(result.passed for result in results)
    layer_counts: dict[str, dict[str, int]] = {}
    for layer in ("parser", "semantic", "retrieval", "answer"):
        applicable = [result for result in results if layer in result.layer_ok]
        layer_counts[layer] = {
            "passed": sum(result.layer_ok[layer] for result in applicable),
            "total": len(applicable),
        }
    observed_known = [result for result in results if result.case.known_failure and not result.passed]
    stale_known = [result for result in results if result.case.known_failure and result.passed]
    return {
        "total": total,
        "strict_passed": strict_passed,
        "layers": layer_counts,
        "by_split": {
            split: {
                "passed": sum(result.passed for result in results if result.case.split == split),
                "total": sum(1 for result in results if result.case.split == split),
            }
            for split in ("development", "held_out")
        },
        "observed_known_failures": observed_known,
        "stale_known_failures": stale_known,
    }


def percentage(passed: int, total: int) -> str:
    return f"{100 * passed / total:.1f}%" if total else "n/a"


def render_report(metadata: dict[str, Any], results: list[CaseResult]) -> str:
    summary = summarize(results)
    lines = [
        "NLP COURSE ASSISTANT — GOLD EVALUATION v1",
        "",
        "Method",
        "- Gold cases assert parser, semantic, retrieval and answer facts/sources.",
        "- Every case remains in the denominator; known failures are reported, not hidden.",
        f"- Fixture target: {metadata.get('target_turns', 'unspecified')} turns; current fixture: {summary['total']} turns.",
        "",
        "Strict end-to-end accuracy",
        f"- Overall: {summary['strict_passed']}/{summary['total']} ({percentage(summary['strict_passed'], summary['total'])})",
    ]
    for split, row in summary["by_split"].items():
        lines.append(f"- {split}: {row['passed']}/{row['total']} ({percentage(row['passed'], row['total'])})")
    lines.extend(["", "Layer metrics"])
    for layer, row in summary["layers"].items():
        lines.append(f"- {layer}: {row['passed']}/{row['total']} ({percentage(row['passed'], row['total'])})")

    failures = [result for result in results if not result.passed]
    lines.extend(["", "Observed failures"])
    if not failures:
        lines.append("- None.")
    else:
        for result in failures:
            owner = result.case.known_failure.get("owner") if result.case.known_failure else "untriaged"
            lines.append(f"- {result.case.case_id} [{owner}]: " + " | ".join(result.failures))
    if summary["stale_known_failures"]:
        lines.extend(["", "Known-failure cases now passing (triage and remove marker)"])
        lines.extend(f"- {result.case.case_id}" for result in summary["stale_known_failures"])
    lines.extend(["", "Provenance", "- Factual expectations are traced in each case to data/raw or a versioned annotation."])
    return "\n".join(lines) + "\n"
