# Role Handoff — Ai đưa gì cho ai?

## Person 1 — Syntax / Grammar / Parser

**Nhận:** raw user sentence.  
**Trả:** `ParserResult`.

```json
{
  "valid": true,
  "sentence_type": "WH_QUESTION",
  "query_frame": "ASK_CHAPTER_BY_TOPIC",
  "slots": {"topic": ["CFG"]},
  "tree": "(S ...)"
}
```

Person 1 **dừng ở raw slots**. Không canonicalize, không query KB.

---

## Person 2 — Semantics / Entity / Context

**Nhận:** `ParserResult` + `ContextState`.  
**Làm:** QueryFrame → Intent, raw slot → canonical ID, resolve reference.  
**Trả:** `SemanticQuery` + context mới.

```json
{
  "intent": "GET_TOPIC",
  "entities": {"topic": ["CFG"]},
  "attribute": "chapter",
  "answer_mode": "LIST"
}
```

Person 2 **không đọc/query KB để lấy câu trả lời**.

---

## Person 3 — Knowledge / Retrieval / Answer

**Nhận:** `SemanticQuery`.  
**Làm:** query canonical KB, track source, render answer.  
**Trả:** `RetrievalResult` + final answer.

```json
{
  "status": "FOUND",
  "values": ["CH03"],
  "sources": ["topics:CH03"]
}
```

Nếu semantic query đúng nhưng sample KB không có dữ liệu, trả `NOT_FOUND`; ví dụ instructor.

---

## Shared contract

Không role nào tự ý thêm intent/query frame/attribute/entity key. Thay đổi nằm trong `contracts/` và phải được cả nhóm thống nhất.
