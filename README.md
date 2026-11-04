# NLP Course Assistant — CO3085

Course Assistant cho một môn CO3085, theo lựa chọn Classical/Statistical NLP.
Dữ liệu lịch học, quy định và bài tập là sample data phục vụ BTL, không phải
thông báo hành chính chính thức.

## Thành viên

Nhóm cần điền tên và MSSV thật trước khi nộp. Phân công hiện tại:
Người 1 phụ trách grammar/parser; Người 2 phụ trách semantic/context;
Người 3 phụ trách KB/retrieval/answer và tích hợp.

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

Mở Windows PowerShell tại root project. Môi trường đã kiểm sử dụng Python
3.12; Python 3.11+ là baseline cho source và Dockerfile.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py --cli 'Chương nào nói về CFG?'
.\.venv\Scripts\python.exe app.py --demo
.\.venv\Scripts\python.exe -m pytest -q
```

UI Gradio:

```powershell
.\.venv\Scripts\python.exe app.py
```

Sau đó mở địa chỉ local Gradio in ra terminal. UI hiển thị đồng thời **ParserResult → SemanticQuery → RetrievalResult → Answer**.

## Phương pháp và scope

- Văn phạm hữu hạn gồm lexicon và productions trong `data/grammar/grammar_v1.yaml`.
- Parser mở rộng các production thành mẫu, khớp toàn câu và dựng NLTK `Tree`
  theo dẫn xuất. Regex chỉ nằm ở nhận dạng từ vựng. Grammar không hỗ trợ
  đệ quy tùy ý và không được mô tả như parser CFG tổng quát.
- Generator mở rộng cùng productions với tập ví dụ lexical, loại trùng,
  duyệt luân phiên và giới hạn tối đa 10.000 câu.
- Semantic mapping theo controlled contracts.
- Canonical entity normalization.
- Context cho `nó`, `chương này`, `phần này` và kế thừa câu hỏi gần nhất ở
  `Còn chương sau?`. Reset xóa cả entity focus lẫn truy vấn trước.
- Adapter tích hợp dùng quan hệ KB để đặt focus phần bài tập khi câu hỏi
  về thành phần trả true và chỉ có một phần phù hợp. Trường hợp nhập nhằng
  không tự chọn phần đầu tiên. Trạng thái UI được giữ riêng trong session.
- KB load trực tiếp từ sample dataset được cung cấp.
- Không hallucinate khi dữ liệu không có.
- `GET_INSTRUCTOR` tồn tại trong schema nhưng sample KB chưa populate → `NOT_FOUND`.

SemanticQuery gồm intent, canonical entity lists, attribute và answer mode.
Mapper lấy định nghĩa frame từ shared contracts; Query Engine chỉ nhận query
có cấu trúc. KB dùng dictionary trong bộ nhớ, load từ `data/raw`, có validation
và reverse indexes. `data/annotations/resource_topics.yaml` là quan hệ nhóm
annotate có provenance. Answer Generator dùng template và nguồn retrieval.

`FOUND [false]` là kết quả phủ định có dữ liệu. `NOT_FOUND` là thiếu fact hoặc
quan hệ; `UNKNOWN` là kết quả semantic cho câu ngoài scope/không resolve được.
Không dùng LLM để xử lý NLP hoặc tạo câu trả lời trong bản này.

## Tái sinh output và đánh giá

```powershell
.\.venv\Scripts\python.exe scripts/export_required_outputs.py
.\.venv\Scripts\python.exe scripts/run_samples.py
.\.venv\Scripts\python.exe scripts/evaluate_gold.py --strict
.\.venv\Scripts\python.exe scripts/verify_outputs.py
```

`input/sentences.txt` chứa các câu độc lập; `output/dialogue.txt` chứa các
hội thoại hai lượt với trace. Script export ghi cây hoặc `()` theo yêu cầu.
`output/semantic.txt`, `intent-entity.txt`, `query.txt`, `retrieval.txt` và
`answer.txt` giữ cùng thứ tự với input.

Gold fixture `data/annotations/evaluation_v1.yaml` có 84 lượt regression,
gồm 6 hội thoại hai lượt. Oracle bao gồm parser/slot, full SemanticQuery,
exact retrieval và template answer đã freeze; các paraphrase tái sử dụng
oracle đã review bằng `oracle_case` và override tường minh.

`output/evaluation.txt` báo số đúng/sai theo outcome và context.
`output/gold_results.json` giữ expected/actual/provenance từng case.
`--strict` trả exit code khác 0 khi còn case fail. Evaluator có mutation test
để phát hiện value/source thừa, sai kiểu boolean, cây hỏng và câu trả lời
thêm fact. Số unit test pass không phải số câu trả lời đúng.

Tập này đã được dùng trong phát triển, không phải held-out độc lập. Kết quả
template regression chưa thay thế đánh giá diễn đạt/factual answer bởi người
review trên tập mới. Thiếu instructor, deadline hoặc quan hệ LO–chapter được
kỳ vọng trả NOT_FOUND; đó là case đúng khi diễn giải và từ chối đúng.

## Bàn giao lỗi/cải tiến Người 1 và Người 2

Đọc `output/person12_handoff.txt` để xem các case chưa đạt, ownership và
expected/actual. Bộ 84 case gold không bao phủ hết các câu trong dữ liệu mẫu.
Các acceptance case bổ sung nằm ở `tests/test_person12_improvements.py`,
được thu thập cả trong lượt `pytest` mặc định; không dùng `skip`/`xfail`.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_completion_regressions.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_person12_improvements.py -v --tb=short
.\.venv\Scripts\python.exe -m pytest -q
```

Trong bộ bổ sung, `test_person1_requested_coverage` kiểm grammar/slot;
`test_person2_with_correct_upstream_input` cấp ParserResult trực tiếp để
không quy lỗi parser cho mapper. Case integration cuối tái hiện DIALOGUE 01
trong `data/raw/dialogues.txt`. Ba case grammar là mục tiêu mở rộng coverage,
không phải khẳng định đề bắt buộc hỗ trợ mọi paraphrase; case DIALOGUE 01 là
thiếu coverage so với chính hội thoại mẫu đã cung cấp. Vì vậy, gold 84/84
không đồng nghĩa toàn bộ acceptance test hoặc sample dialogue đều đạt.

Lần kiểm tra gần nhất: **239 test pass, 4 fail trên tổng 243**. Bốn failure
gồm ECTS, department, topic list CFG–PCFG và tham chiếu week–chapter của
DIALOGUE 01. Các testcase giữ assertion bình thường để thành viên tái hiện
và sửa lỗi; kết quả gold regression riêng vẫn là **84/84**.

## Docker

```powershell
docker build -t nlp-course-assistant .
docker run --rm -p 7860:7860 nlp-course-assistant
docker run --rm nlp-course-assistant python -m pytest -q
docker run --rm nlp-course-assistant python scripts/verify_outputs.py --regenerate
```

UI trong container bind `0.0.0.0`; mở `http://localhost:7860` trên máy host.
Docker phải đang chạy. Nếu chưa kiểm build/run thành công, cần ghi môi trường
container chưa được xác minh, không suy ra từ việc có Dockerfile.

## Tạo gói nộp thử

```powershell
.\.venv\Scripts\python.exe scripts/package_submission.py
```

Gói nằm trong `dist`, chứa source, data, contracts, test và output; loại
venv/cache/Git và Markdown nội bộ. Có thể thêm `--include-report` sau khi PDF
đã được cập nhật, hoặc `--name` để đặt tên theo MSSV thật. Script không ghi
đè archive đã tồn tại. Báo cáo, thông tin thành viên và video cần hoàn thiện
theo yêu cầu nộp của lớp.

## Hạn chế

Chỉ hỗ trợ 24 QueryFrame trong phạm vi grammar; contract còn có các frame
chưa có recognition rule. Không hiểu mọi cách diễn đạt tiếng Việt. Context
là cục bộ, không phải dialogue manager tổng quát. Không có căn cứ suy ra
deadline, instructor hay quan hệ LO/resource chưa được annotate. Chưa có
đánh giá người dùng độc lập hoặc cam kết hiệu năng nhiều người dùng.

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
