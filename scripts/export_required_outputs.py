from pathlib import Path
import json, yaml
from src.assistant import CourseAssistant
from src.syntax.generator import generate
ROOT=Path(__file__).resolve().parents[1]
b=CourseAssistant()
qs=[x.strip() for x in (ROOT/'input/sentences.txt').read_text(encoding='utf-8').splitlines() if x.strip()]
rows=[b.ask(q) for q in qs]
(ROOT/'output/grammar.txt').write_text((ROOT/'data/grammar/grammar_v1.yaml').read_text(encoding='utf-8'),encoding='utf-8')
(ROOT/'output/samples.txt').write_text('\n'.join(generate())+'\n',encoding='utf-8')
(ROOT/'output/parse-results.txt').write_text('\n\n'.join((r['person_1_parser_result']['tree'] or '()') for r in rows),encoding='utf-8')
(ROOT/'output/semantic.txt').write_text('\n'.join(json.dumps(r['person_2_semantic_query'],ensure_ascii=False) for r in rows),encoding='utf-8')
(ROOT/'output/intent-entity.txt').write_text('\n'.join(f"{r['person_2_semantic_query']['intent']} | {r['person_2_semantic_query']['entities']}" for r in rows),encoding='utf-8')
(ROOT/'output/query.txt').write_text('\n'.join(json.dumps(r['person_2_semantic_query'],ensure_ascii=False) for r in rows),encoding='utf-8')
(ROOT/'output/retrieval.txt').write_text('\n'.join(json.dumps(r['person_3_retrieval_result'],ensure_ascii=False) for r in rows),encoding='utf-8')
(ROOT/'output/answer.txt').write_text('\n'.join(r['answer'] for r in rows)+'\n',encoding='utf-8')
print('exported required v0 outputs')
