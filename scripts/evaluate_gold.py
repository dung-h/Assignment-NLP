"""Generate the denominator-preserving gold evaluation report."""

from __future__ import annotations

from pathlib import Path
import sys
import argparse
import json

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.assistant import CourseAssistant
from src.evaluation.gold import (
    DEFAULT_GOLD_PATH,
    evaluate_cases,
    load_gold_cases,
    render_report,
)


OUTPUT = ROOT / "output" / "evaluation.txt"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strict', action='store_true', help='Return nonzero when any evaluated case fails')
    args = parser.parse_args()
    metadata, cases = load_gold_cases(DEFAULT_GOLD_PATH)
    results = evaluate_cases(cases, CourseAssistant)
    OUTPUT.write_text(render_report(metadata, results), encoding="utf-8", newline="\n")
    traces = [{
        'id': row.case.case_id, 'query': row.case.query, 'split': row.case.split,
        'conversation_id': row.case.conversation_id, 'turn': row.case.turn,
        'passed': row.passed, 'layers': row.layer_ok, 'failures': row.failures,
        'expected': row.case.expected, 'actual': row.response,
        'provenance': row.case.provenance,
    } for row in results]
    (OUTPUT.parent / 'gold_results.json').write_text(
        json.dumps(traces, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n',
    )
    print(f"wrote {OUTPUT.relative_to(ROOT)} from {len(cases)} gold turns")
    return int(args.strict and any(not row.passed for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
