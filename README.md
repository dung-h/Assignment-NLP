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

Sau đó mở địa chỉ local Gradio in ra terminal. Khung hội thoại giữ lịch sử hỏi
đáp; mục **Các bước xử lý câu hỏi gần nhất** giải thích phân tích, ngữ nghĩa
và truy xuất. Phần mở rộng bên trong hiển thị dữ liệu chi tiết. Với `UNKNOWN`, giao diện
ghi rõ KB chưa được truy vấn; dữ liệu truy xuất rỗng trong JSON chỉ là phần
giữ cấu trúc phản hồi. Nút **Bắt đầu lại** xóa lịch sử và ngữ cảnh phiên.

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
.\.venv\Scripts\python.exe app.py --export-outputs
.\.venv\Scripts\python.exe scripts/run_samples.py
.\.venv\Scripts\python.exe scripts/evaluate_gold.py --strict
.\.venv\Scripts\python.exe -m pytest -q --ignore=experiments
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
`output/evaluation_results.json` giữ expected/actual/provenance từng case;
`output/pipeline_results.json` lưu kết quả pipeline cho các câu đầu vào mẫu.
`--strict` trả exit code khác 0 khi còn case fail. Evaluator có mutation test
để phát hiện value/source thừa, sai kiểu boolean, cây hỏng và câu trả lời
thêm fact. Số unit test pass không phải số câu trả lời đúng.

Tập này đã được dùng trong phát triển, không phải held-out độc lập. Kết quả
template regression chưa thay thế đánh giá diễn đạt/factual answer bởi người
review trên tập mới. Thiếu instructor, deadline hoặc quan hệ LO–chapter chưa
được đối chiếu được kỳ vọng trả NOT_FOUND; đó là case đúng khi diễn giải và
từ chối đúng. Quan hệ LO4.2–CH12 và tài liệu–CFG là chú giải tham khảo của
nhóm, không phải quan hệ do giảng viên chỉ định.

## Cấu trúc kiểm thử

Bộ test được gom theo mục đích trong `tests/`, không theo thành viên thực hiện:

- `tests/unit/`: kiểm tra từng module và ranh giới contract.
- `tests/integration/`: kiểm tra các module đã nối với nhau, gồm xử lý hội thoại.
- `tests/acceptance/`: kiểm tra câu hỏi hoàn chỉnh, mock KB dùng chung và bộ
  đánh giá hồi quy end-to-end.

Chạy toàn bộ test hoặc chọn riêng một tầng khi cần tìm lỗi:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest tests/unit -q
.\.venv\Scripts\python.exe -m pytest tests/integration -q
.\.venv\Scripts\python.exe -m pytest tests/acceptance -q
```

Trong `tests/acceptance/test_language_coverage.py`, các phép kiểm tra parser,
semantic mapper và toàn pipeline được tách rõ: test semantic mapper nhận một
`ParserResult` hợp lệ làm đầu vào, còn test pipeline chạy câu hỏi từ đầu đến
kết quả truy xuất. Nhờ đó có thể nhận biết lỗi nằm ở bước nào; các case mở rộng
này không bị gộp vào bộ gold regression.

## Docker

Để demo qua Docker, mở PowerShell tại thư mục gốc và bảo đảm Docker Desktop
đang chạy. Build image rồi chạy giao diện:

```powershell
docker build -t nlp .
docker run --rm -p 127.0.0.1:7860:7860 nlp
```

Mở `http://localhost:7860` và giữ terminal đang chạy trong khi demo. Nhấn
`Ctrl+C` ở terminal để dừng container. Để kiểm tra bằng Docker:

```powershell
docker run --rm nlp python -m pytest -q
docker run --rm nlp python app.py --export-outputs
```

UI trong container bind `0.0.0.0`; cổng được công bố riêng trên localhost của
máy host. Phiên bản thư viện trong `requirements.txt` chỉ được giới hạn tối
thiểu, vì vậy các lần build khác nhau có thể cài phiên bản khác nhau.

Kịch bản demo gợi ý: hỏi “Chương nào nói về CFG?”, hỏi tiếp trong một phiên
mới “Tuần 3 học gì?” rồi “Tài liệu của chương này là gì?”, và thử “Ai dạy
môn NLP?” để minh họa trường hợp thiếu dữ liệu. Có thể hỏi “Midterm kéo dài
bao lâu?” để minh họa cách diễn đạt chưa được hỗ trợ. Quan hệ tài liệu và
chương dựa trên chủ đề do nhóm đối chiếu, không khẳng định là tài liệu được
giảng viên chỉ định.

## Tạo gói nộp thử

Nén các thư mục và file theo yêu cầu đề bài; không đưa `.venv`, cache, Git,
hoặc tài liệu làm việc nội bộ vào gói nộp. Báo cáo, thông tin thành viên và
video cần hoàn thiện theo yêu cầu nộp của lớp.

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
