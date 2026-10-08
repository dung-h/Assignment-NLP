from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.assistant import CourseAssistant
bot = CourseAssistant()
rows = [
    bot.ask(line.strip())
    for line in (ROOT / "input" / "sentences.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    if line.strip()
]
(ROOT / "output" / "end_to_end_results.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=2),
    encoding="utf-8",
    newline="\n",
)
print(f'wrote {len(rows)} results')
