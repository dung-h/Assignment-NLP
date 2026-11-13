"""Export the assignment's parser, semantic, retrieval and answer outputs."""

import json
from pathlib import Path

from src.answer.export import answer_to_line
from src.assistant import CourseAssistant
from src.syntax.generator import generate


ROOT = Path(__file__).resolve().parents[1]


def export_outputs(root=ROOT):
    """Export results for the project's input questions and sample dialogues."""
    root = Path(root)
    output = root / 'output'
    output.mkdir(parents=True, exist_ok=True)

    def write(name, text):
        (output / name).write_text(text, encoding='utf-8', newline='\n')

    queries = [line.strip() for line in
               (root / 'input' / 'sentences.txt').read_text(encoding='utf-8').splitlines()
               if line.strip()]
    # These are independent questions; each starts a fresh conversation.
    rows = [CourseAssistant().ask(query) for query in queries]
    dialogues = []
    for questions in (
        ['Chương 4 nói về gì?', 'Nó có liên quan đến parsing không?'],
        ['Chương 11 có hỏi đáp không?', 'Còn chương sau?'],
        ['Bài tập lớn có phần parser không?', 'Phần này cần xuất file gì?'],
    ):
        bot = CourseAssistant()
        dialogues.append([bot.ask(query) for query in questions])

    write('grammar.txt', (root / 'data' / 'grammar' / 'grammar_v1.yaml').read_text(encoding='utf-8'))
    write('samples.txt', '\n'.join(generate(grammar_path=root / 'data' / 'grammar' / 'grammar_v1.yaml')) + '\n')
    write('parse-results.txt', '\n\n'.join(row['person_1_parser_result']['tree'] or '()' for row in rows) + '\n')
    semantic = [row['person_2_semantic_query'] for row in rows]
    semantic_lines = '\n'.join(json.dumps(item, ensure_ascii=False) for item in semantic)
    write('semantic.txt', semantic_lines)
    write('intent-entity.txt', '\n'.join(f"{item['intent']} | {item['entities']}" for item in semantic))
    write('query.txt', semantic_lines)
    write('retrieval.txt', '\n'.join(json.dumps(row['person_3_retrieval_result'], ensure_ascii=False) for row in rows))
    write('answer.txt', '\n'.join(answer_to_line(row['answer']) for row in rows) + '\n')
    write('dialogue.txt', json.dumps(dialogues, ensure_ascii=False, indent=2) + '\n')
    return len(rows)
