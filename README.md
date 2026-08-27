# NLP Course Assistant v0 — End-to-End Runnable Prototype

Prototype đầu tiên cho BTL CO3085. Repo cố ý giữ code đơn giản để **nhìn rõ ranh giới giữa 3 thành viên**.

## Pipeline

```text
User sentence
  ↓
[Person 1] Grammar + Parser
  ↓ ParserResult
[Person 2] Semantic Mapper + Entity Normalizer + Context Resolver
  ↓ SemanticQuery
[Person 3] Knowledge Base + Query Engine + Answer Generator
  ↓ RetrievalResult + Answer
```

## Chạy nhanh

```bash
python -m pip install -r requirements.txt
python app.py --cli "Chương nào nói về CFG?"
python app.py --demo
pytest -q
```

UI Gradio:

```bash
python app.py
```

Sau đó mở địa chỉ local Gradio in ra terminal. UI hiển thị đồng thời **ParserResult → SemanticQuery → RetrievalResult → Answer**.

## Scope v0

- Rule-based grammar/parser cho một subset đại diện của QueryFrame v1.
- NLTK `Tree` để xuất parse tree dễ quan sát.
- Semantic mapping theo controlled contracts.
- Canonical entity normalization.
- Local context cho `nó`, `chương này`, `phần này`, `chương sau`.
- KB load trực tiếp từ sample dataset được cung cấp.
- Không hallucinate khi dữ liệu không có.
- `GET_INSTRUCTOR` tồn tại trong schema nhưng sample KB chưa populate → `NOT_FOUND`.

Đây **không phải implementation cuối**. Sau khi integration v1 ổn mới augment data và xây evaluation đầy đủ.

## Tree repo

```text
contracts/              # shared contract: enums/schema/mock
src/syntax/             # PERSON 1
src/semantics/          # PERSON 2
src/knowledge/          # PERSON 3
src/answer/             # PERSON 3
app.py                   # integration + Gradio UI
scripts/run_samples.py   # chạy sample thật
output/                  # kết quả đã chạy
```

## Ownership

### Person 1 — Syntax
Own: `src/syntax/*`, `data/grammar/grammar_v1.yaml`, `ParserResult` output.

### Person 2 — Semantics & Context
Own: `src/semantics/*`, normalization/reference resolution, `SemanticQuery` output.

### Person 3 — KB / Retrieval / Answer
Own: `src/knowledge/*`, `src/answer/*`, loader/query handlers/source tracking, `RetrievalResult` và answer.

Shared contracts trong `contracts/` chỉ đổi khi cả nhóm đồng ý.
