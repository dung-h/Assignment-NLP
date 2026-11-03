"""Generate the denominator-preserving gold evaluation report."""

from __future__ import annotations

from pathlib import Path
import sys

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


def main() -> None:
    metadata, cases = load_gold_cases(DEFAULT_GOLD_PATH)
    results = evaluate_cases(cases, CourseAssistant)
    OUTPUT.write_text(render_report(metadata, results), encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)} from {len(cases)} gold turns")


if __name__ == "__main__":
    main()
