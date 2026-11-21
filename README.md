# NLP Course Assistant — CO3085

Course Assistant hỗ trợ sinh viên tra cứu thông tin về môn Xử lý ngôn ngữ tự
nhiên (CO3085) bằng các câu hỏi tiếng Việt. Hệ thống sử dụng phương pháp xử lý
ngôn ngữ dựa trên luật và trả lời dựa trên dữ liệu môn học mẫu.

## Thành viên

- Quách Trọng Kiên — 2211734: grammar và parser.
- Nguyễn Trần Nhật Châu — 2310335: ngữ nghĩa và ngữ cảnh.
- Hồ Anh Dũng — 2310543: cơ sở tri thức, truy vấn và sinh câu trả lời.

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
.\.venv\Scripts\python.exe app.py --evaluate
.\.venv\Scripts\python.exe -m pytest -q --ignore=experiments
```

`input/sentences.txt` chứa các câu độc lập; `output/dialogue.txt` chứa các
hội thoại hai lượt với trace. Script export ghi cây hoặc `()` theo yêu cầu.
`output/semantic.txt`, `intent-entity.txt`, `query.txt`, `retrieval.txt` và
`answer.txt` giữ cùng thứ tự với input.

Tập đánh giá chính là `data/annotations/evaluation.yaml`. Mỗi trường hợp ghi
câu hỏi, lịch sử hội thoại, các thông tin cần có trong đầu ra và nguồn đối
chiếu. Chương trình dùng cùng tiêu chí cho toàn bộ tập: kiểm tra dữ liệu trả
về, nguồn và các ý bắt buộc trong câu trả lời; không chấm theo nhãn parser
hay cách biểu diễn intent/entity nội bộ. Trường hợp chưa rõ ý có thể có phản
hồi hỏi lại trong danh sách các đầu ra được chấp nhận.
Nhóm trường hợp hỏi lại khảo sát một khả năng sử dụng do nhóm đề xuất; đề
bài không quy định mọi câu nhập nhằng phải được xử lý bằng một câu hỏi lại.

`output/evaluation.txt` ghi cách chấm, kết quả và lỗi từng trường hợp;
`output/evaluation_results.json` lưu kỳ vọng cùng dấu vết chạy thực tế và
mã kiểm tra nội dung tập dữ liệu. `output/pipeline_results.json` là kết quả
chạy các câu đầu vào minh họa. Thêm `--strict` vào lệnh `app.py --evaluate`
để trả mã lỗi khi có trường hợp chưa đạt. Chạy thành công chương trình đánh
giá không có nghĩa mọi câu hỏi đều được trả lời đúng.

Các phép kiểm tra từ ngữ chưa thay thế việc người đánh giá xem xét toàn bộ
ý nghĩa, tính đầy đủ và tính tự nhiên của câu trả lời. Tập có câu đã dùng khi
phát triển, chưa phải đánh giá độc lập. `evaluation_v1.yaml` được giữ để kiểm
tra các hành vi cũ trong pytest, không dùng làm kết quả đánh giá chính.
Chú giải LO4.2–CH12 và tài liệu–CFG do nhóm bổ sung, không phải quan hệ do
giảng viên chỉ định.

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

Lệnh cũ `scripts/evaluate_gold.py` cũng gọi bộ đánh giá chính.
`scripts/evaluate_samples.py` chỉ khảo sát các nhãn trong sample_queries và
ghi riêng `output/sample_query_evaluation.txt`, không ghi đè kết quả chính.

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
docker run --rm nlp python app.py --evaluate
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

Văn phạm có ít nhất một mẫu cho cả 36 QueryFrame, nhưng không hiểu mọi cách
diễn đạt tiếng Việt. Context
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
