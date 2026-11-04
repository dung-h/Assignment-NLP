"""Deterministic, fact-level evaluation of end-to-end gold cases.

The evaluator deliberately reports failed expectations instead of treating a
successful process exit as evidence that the assistant answered correctly.
It is used by both the report exporter and regression tests.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from copy import deepcopy

import yaml
from nltk.tree import Tree


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
    layer_ok: dict[str, bool | None]
    failures: tuple[str, ...]
    response: dict[str, Any]


def _as_sources(value: Any) -> list[str]:
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, list) and value and all(isinstance(item, str) and item for item in value):
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
    # Reuse reviewed oracles for explicit paraphrases; never derive gold from
    # the assistant's current output. Each extension supplies its raw query.
    originals = {item['id']: item for item in raw_cases if isinstance(item, dict) and 'id' in item}
    expanded = list(raw_cases)
    for extension in raw.get('additional_cases', []):
        base_id = extension.get('oracle_case')
        if base_id not in originals or not {'id', 'query'} <= extension.keys():
            raise ValueError('additional case needs id, query and a baseline oracle_case')
        item = deepcopy(originals[base_id])
        item.pop('known_failure', None)
        for key, value in extension.items():
            if key not in {'oracle_case', 'expected'}:
                item[key] = value
        for layer, override in extension.get('expected', {}).items():
            item['expected'][layer] = {**item['expected'].get(layer, {}), **override}
        expanded.append(item)
    raw_cases = expanded

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
        if item["split"] not in {"development", "held_out", "regression"}:
            raise ValueError(f"{case_id}: unsupported split")
        if not isinstance(item['query'], str) or not item['query'].strip():
            raise ValueError(f'{case_id}: query must be non-empty')
        if item["group"] not in {"independent", "context"}:
            raise ValueError(f"{case_id}: unsupported group")
        if not isinstance(item["expected"], dict):
            raise ValueError(f"{case_id}: expected must be a mapping")
        _validate_oracle(case_id, item['expected'])
        for source in _as_sources(item['provenance']):
            resolved = (ROOT / source).resolve()
            if not resolved.is_relative_to(ROOT.resolve()) or not resolved.is_file():
                raise ValueError(f'{case_id}: invalid provenance {source!r}')
        if item["group"] == "context" and (
            not item.get("conversation_id") or type(item.get("turn")) is not int
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
    dialogues = defaultdict(list)
    for case in cases:
        if case.group == 'context':
            dialogues[case.conversation_id].append(case)
    for conversation_id, turns in dialogues.items():
        if sorted(case.turn for case in turns) != list(range(1, len(turns) + 1)):
            raise ValueError(f'{conversation_id}: turns must be unique and contiguous from 1')
        if len({case.split for case in turns}) != 1:
            raise ValueError(f'{conversation_id}: a dialogue must stay within one split')
    return raw, cases


def _validate_oracle(case_id, expected):
    required = {
        'parser': {'valid', 'sentence_type', 'query_frame', 'slots', 'tree'},
        'semantic': {'intent', 'entities', 'attribute', 'answer_mode'},
        'retrieval': {'status', 'values', 'sources'},
        'answer': {'contains'},
    }
    for layer, fields in required.items():
        if not isinstance(expected.get(layer), dict) or not fields <= expected[layer].keys():
            raise ValueError(f'{case_id}: incomplete {layer} oracle')
    retrieval = expected['retrieval']
    if not isinstance(retrieval['values'], list) or not isinstance(retrieval['sources'], list):
        raise ValueError(f'{case_id}: retrieval oracle requires lists')
    if retrieval['status'] == 'FOUND':
        if not retrieval['values'] or not retrieval['sources']:
            raise ValueError(f'{case_id}: FOUND oracle must have values and sources')
    elif retrieval['status'] != 'NOT_FOUND' or retrieval['values'] or retrieval['sources']:
        raise ValueError(f'{case_id}: invalid missing-data oracle')
    if not expected['answer']['contains']:
        raise ValueError(f'{case_id}: answer oracle needs at least one required fact')
    if expected['parser']['tree'] not in {'non_empty', 'empty'}:
        raise ValueError(f'{case_id}: unsupported tree oracle')


def _same(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_same(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(_same(left, right) for left, right in zip(actual, expected))
    return actual == expected


def _expect_mapping(
    layer: str, actual: dict[str, Any], expected: dict[str, Any]
) -> list[str]:
    failures: list[str] = []
    for key, wanted in expected.items():
        if key == "tree":
            tree = actual.get("tree")
            ok = tree is None
            if wanted == 'non_empty':
                try:
                    parsed_tree = Tree.fromstring(tree)
                    ok = parsed_tree.label() == 'S' and bool(parsed_tree.leaves())
                    for slot, values in actual.get('slots', {}).items():
                        observed = [leaf for node in parsed_tree.subtrees() if node.label() == slot.upper() for leaf in node.leaves()]
                        wanted_leaves = [token for value in values for token in value.split()]
                        ok = ok and observed == wanted_leaves
                except (ValueError, TypeError, AttributeError):
                    ok = False
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
        if key in expected and not _same(actual.get(key), expected[key]):
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
    if not isinstance(actual, str):
        return ['answer: must be a string']
    if 'exact' in expected and actual != expected['exact']:
        failures.append('answer: does not match the frozen complete answer')
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
            layer: None
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
            "passed": sum(result.layer_ok[layer] is True for result in applicable),
            "total": sum(result.layer_ok[layer] is not None for result in applicable),
            "unobserved": sum(result.layer_ok[layer] is None for result in applicable),
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
            for split in ("regression", "development", "held_out")
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
        "- Current cases are regression cases already used during development; no independent held-out claim.",
        "- Answer scores below measure frozen-template/fact assertions, not independent human review.",
        f"- Fixture target: {metadata.get('target_turns', 'unspecified')} turns; current fixture: {summary['total']} turns.",
        "",
        "Regression end-to-end assertion accuracy",
        f"- Overall: {summary['strict_passed']}/{summary['total']} ({percentage(summary['strict_passed'], summary['total'])})",
    ]
    for split, row in summary["by_split"].items():
        lines.append(f"- {split}: {row['passed']}/{row['total']} ({percentage(row['passed'], row['total'])})")
    lines.extend(["", "Layer metrics"])
    for layer, row in summary["layers"].items():
        lines.append(f"- {layer}: {row['passed']}/{row['total']} ({percentage(row['passed'], row['total'])}); unobserved={row['unobserved']}")
    lines.extend(['', 'Expected outcome breakdown'])
    for outcome in ('FOUND', 'NOT_FOUND', 'UNKNOWN'):
        rows = [row for row in results if (
            'UNKNOWN' if row.case.expected['semantic']['intent'] == 'UNKNOWN'
            else row.case.expected['retrieval']['status']) == outcome]
        count = sum(row.passed for row in rows)
        lines.append(f'- {outcome}: {count}/{len(rows)} ({percentage(count, len(rows))})')
    followups = [row for row in results if row.case.group == 'context' and row.case.turn > 1]
    count = sum(row.passed for row in followups)
    lines.extend(['', f'Context follow-ups: {count}/{len(followups)} ({percentage(count, len(followups))})'])

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
