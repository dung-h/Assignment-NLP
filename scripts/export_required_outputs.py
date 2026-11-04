from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.assistant import CourseAssistant
from src.syntax.generator import generate


def write_output(path, text):
    path.write_text(text, encoding="utf-8", newline="\n")


queries = [
    line.strip()
    for line in (ROOT / "input" / "sentences.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    if line.strip()
]
# input/sentences.txt is a set of independent questions, not one dialogue.
rows = [CourseAssistant().ask(query) for query in queries]

# One supported two-turn dialogue is exported separately for Part III.  The
# full context coverage, including failures, is reported in evaluation.txt.
dialogue_rows = []
for questions in (
    ['Chương 4 nói về gì?', 'Nó có liên quan đến parsing không?'],
    ['Chương 11 có hỏi đáp không?', 'Còn chương sau?'],
    ['Bài tập lớn có phần parser không?', 'Phần này cần xuất file gì?'],
):
    dialogue_bot = CourseAssistant()
    dialogue_rows.append([dialogue_bot.ask(query) for query in questions])
write_output(
    ROOT / "output" / "grammar.txt",
    (ROOT / "data" / "grammar" / "grammar_v1.yaml").read_text(encoding="utf-8"),
)
write_output(ROOT / "output" / "samples.txt", "\n".join(generate()) + "\n")
write_output(
    ROOT / "output" / "parse-results.txt",
    "\n\n".join(row["person_1_parser_result"]["tree"] or "()" for row in rows) + '\n',
)
write_output(
    ROOT / "output" / "semantic.txt",
    "\n".join(
        json.dumps(row["person_2_semantic_query"], ensure_ascii=False)
        for row in rows
    ),
)
write_output(
    ROOT / "output" / "intent-entity.txt",
    "\n".join(
        f"{row['person_2_semantic_query']['intent']} | "
        f"{row['person_2_semantic_query']['entities']}"
        for row in rows
    ),
)
write_output(
    ROOT / "output" / "query.txt",
    "\n".join(
        json.dumps(row["person_2_semantic_query"], ensure_ascii=False)
        for row in rows
    ),
)
write_output(
    ROOT / "output" / "retrieval.txt",
    "\n".join(
        json.dumps(row["person_3_retrieval_result"], ensure_ascii=False)
        for row in rows
    ),
)
write_output(ROOT / "output" / "answer.txt", "\n".join(row["answer"] for row in rows) + "\n")
write_output(
    ROOT / "output" / "dialogue.txt",
    json.dumps(dialogue_rows, ensure_ascii=False, indent=2) + "\n",
)
print('exported required v0 outputs')
