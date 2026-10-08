"""Evaluate the runnable pipeline against the supplied sample-query labels.

The supplied data labels intent and a focus entity, but does not provide gold
answer strings.  This evaluator therefore reports semantic accuracy and
grounding invariants separately instead of claiming unsupported answer-text
accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.assistant import CourseAssistant


SAMPLE_QUERIES = ROOT / "data" / "raw" / "sample_queries.txt"
OUTPUT = ROOT / "output" / "evaluation.txt"
ROW = re.compile(r"^(Q\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*$")
ENTITY_ALIASES = {
    "PART_I": "BTL_PART_1",
    "PART_II": "BTL_PART_2",
    "PART_III": "BTL_PART_3",
    "PART_IV": "BTL_PART_4",
}


@dataclass(frozen=True)
class SampleCase:
    case_id: str
    question: str
    expected_intent: str
    expected_entity: str
    group: str


def load_cases(path: Path = SAMPLE_QUERIES) -> list[SampleCase]:
    """Load labelled queries while retaining their evaluation group."""

    group = "independent"
    cases: list[SampleCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("OUT-OF-SCOPE"):
            group = "out_of_scope"
            continue
        if line.startswith("REFERENCE / CONTEXT"):
            group = "context"
            continue
        match = ROW.match(line)
        if not match:
            continue
        cases.append(SampleCase(*match.groups(), group))
    return cases


def flatten_entities(entities: dict[str, list[str]]) -> list[str]:
    return [entity_id for values in entities.values() for entity_id in values]


def normalized_expected_entity(case: SampleCase) -> str | None:
    if case.expected_entity == "OUT_OF_SCOPE":
        return None
    return ENTITY_ALIASES.get(case.expected_entity, case.expected_entity)


def retrieval_is_grounded(result: dict) -> bool:
    """Check the public RetrievalResult invariants that answer generation uses."""

    status = result["status"]
    values = result["values"]
    sources = result["sources"]
    if status == "FOUND":
        return bool(values) and bool(sources)
    return status == "NOT_FOUND" and values == [] and sources == []


def evaluate_independent(cases: list[SampleCase]) -> tuple[list[dict], list[dict]]:
    """Evaluate isolated questions, avoiding accidental context carry-over."""

    rows: list[dict] = []
    failures: list[dict] = []
    for case in cases:
        try:
            response = CourseAssistant().ask(case.question)
        except Exception as exc:  # Keep failed pipeline rows in evaluation.
            row = {
                "case": case,
                "actual_intent": "ERROR",
                "actual_entities": [],
                "status": "ERROR",
                "intent_ok": False,
                "entity_ok": False,
                "grounded_ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            rows.append(row)
            failures.append(row)
            continue
        semantic = response["person_2_semantic_query"]
        retrieval = response["person_3_retrieval_result"]
        intent_ok = semantic["intent"] == case.expected_intent
        expected_entity = normalized_expected_entity(case)
        entity_ok = (
            expected_entity is None
            or expected_entity in flatten_entities(semantic["entities"])
        )
        grounded_ok = retrieval_is_grounded(retrieval)
        row = {
            "case": case,
            "actual_intent": semantic["intent"],
            "actual_entities": flatten_entities(semantic["entities"]),
            "status": retrieval["status"],
            "intent_ok": intent_ok,
            "entity_ok": entity_ok,
            "grounded_ok": grounded_ok,
        }
        rows.append(row)
        if not (intent_ok and entity_ok and grounded_ok):
            failures.append(row)
    return rows, failures


def evaluate_context(cases: list[SampleCase]) -> list[dict]:
    """Evaluate supplied context pairs in separate two-turn conversations."""

    by_id = {case.case_id: case for case in cases}
    pairs = [("Q029", "Q030"), ("Q031", "Q032"), ("Q033", "Q034")]
    rows: list[dict] = []
    for seed_id, follow_up_id in pairs:
        bot = CourseAssistant()
        bot.ask(by_id[seed_id].question)
        try:
            response = bot.ask(by_id[follow_up_id].question)
        except Exception as exc:  # A context bug is an evaluation result.
            rows.append(
                {
                    "seed": seed_id,
                    "follow_up": follow_up_id,
                    "expected_entity": normalized_expected_entity(
                        by_id[follow_up_id]
                    ),
                    "actual_intent": "ERROR",
                    "actual_entities": [],
                    "status": "ERROR",
                    "entity_ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        semantic = response["person_2_semantic_query"]
        expected_entity = normalized_expected_entity(by_id[follow_up_id])
        entity_ok = expected_entity in flatten_entities(semantic["entities"])
        rows.append(
            {
                "seed": seed_id,
                "follow_up": follow_up_id,
                "expected_entity": expected_entity,
                "actual_intent": semantic["intent"],
                "actual_entities": flatten_entities(semantic["entities"]),
                "status": response["person_3_retrieval_result"]["status"],
                "entity_ok": entity_ok,
            }
        )
    return rows


def percentage(passed: int, total: int) -> str:
    return f"{(100 * passed / total):.1f}%" if total else "n/a"


def render_report(
    independent_rows: list[dict],
    failures: list[dict],
    context_rows: list[dict],
) -> str:
    intent_passed = sum(row["intent_ok"] for row in independent_rows)
    entity_passed = sum(row["entity_ok"] for row in independent_rows)
    grounded_passed = sum(row["grounded_ok"] for row in independent_rows)
    context_passed = sum(row["entity_ok"] for row in context_rows)
    total = len(independent_rows)

    lines = [
        "NLP COURSE ASSISTANT — EVALUATION v0",
        "",
        "Scope and method",
        "- Q001–Q025: independent in-domain semantic labels.",
        "- Q026–Q028: out-of-domain intent labels.",
        "- Q029–Q034: three isolated two-turn context pairs.",
        "- Intent and focus-entity labels come from sample_queries.txt.",
        "- The supplied dataset has no gold answer strings; this report does not claim answer-text accuracy.",
        "- Grounding invariant: FOUND has values and sources; NOT_FOUND has empty values and sources.",
        "",
        "Independent semantic evaluation (Q001–Q028)",
        f"- Cases: {total}",
        f"- Intent exact match: {intent_passed}/{total} ({percentage(intent_passed, total)})",
        f"- Focus entity inclusion: {entity_passed}/{total} ({percentage(entity_passed, total)})",
        f"- Retrieval grounding invariant: {grounded_passed}/{total} ({percentage(grounded_passed, total)})",
        "",
        "Context-reference evaluation (Q029–Q034)",
        f"- Resolved expected focus entity: {context_passed}/{len(context_rows)} ({percentage(context_passed, len(context_rows))})",
    ]

    for row in context_rows:
        lines.append(
            "- "
            f"{row['seed']} → {row['follow_up']}: "
            f"expected {row['expected_entity']}; actual "
            f"{row['actual_entities']}; intent={row['actual_intent']}; "
            f"status={row['status']}; pass={row['entity_ok']}"
            + (f"; error={row['error']}" if "error" in row else "")
        )

    lines.extend(["", "Observed independent failures"])
    if not failures:
        lines.append("- None.")
    else:
        for row in failures:
            case = row["case"]
            lines.append(
                "- "
                f"{case.case_id}: expected intent={case.expected_intent}, "
                f"entity={normalized_expected_entity(case)}; actual "
                f"intent={row['actual_intent']}, entities={row['actual_entities']}, "
                f"status={row['status']}; intent_ok={row['intent_ok']}, "
                f"entity_ok={row['entity_ok']}, grounded_ok={row['grounded_ok']}"
                + (f"; error={row['error']}" if "error" in row else "")
            )

    lines.extend(
        [
            "",
            "Interpretation and limitations",
            "- A semantic label match does not by itself prove factual answer correctness.",
            "- Intentional NOT_FOUND is valid when the sample KB lacks the requested relation, such as LO-to-content or official deadlines.",
            "- Failed rows are retained as evidence for parser/semantic/context coverage work; they are not silently excluded from the denominator.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    cases = load_cases()
    independent = [case for case in cases if case.group != "context"]
    context = [case for case in cases if case.group == "context"]
    independent_rows, failures = evaluate_independent(independent)
    context_rows = evaluate_context(context)
    OUTPUT.write_text(
        render_report(independent_rows, failures, context_rows),
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
