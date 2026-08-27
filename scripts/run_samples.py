from pathlib import Path
import json
from src.assistant import CourseAssistant
ROOT=Path(__file__).resolve().parents[1]
b=CourseAssistant(); rows=[]
for line in (ROOT/'input/sentences.txt').read_text(encoding='utf-8').splitlines():
    if line.strip(): rows.append(b.ask(line.strip()))
(ROOT/'output/end_to_end_results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'wrote {len(rows)} results')
