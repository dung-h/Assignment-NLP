# PROPOSAL KIẾN TRÚC & PHÂN CÔNG TRIỂN KHAI

## NLP Course Assistant --- Nhóm 3 người

> **Trạng thái tài liệu:** Architecture/Contract Proposal v1\
> **Mục tiêu:** Chốt kiến trúc, ontology, taxonomy, API contract, mock
> I/O và phạm vi công việc để 3 thành viên có thể phát triển song song.\
> **Chưa thuộc phạm vi giai đoạn này:** data augmentation chi tiết và
> evaluation framework chi tiết. Hai phần này thực hiện sau khi pipeline
> v1 đã tích hợp chạy end-to-end.

------------------------------------------------------------------------

# 1. Mục tiêu của proposal

BTL yêu cầu xây dựng một **Course Assistant trong miền hẹp**, nhưng mục
tiêu học thuật không chỉ là tạo một chatbot trả lời được câu hỏi. Hệ
thống cuối cùng phải thể hiện được pipeline NLP:

``` text
Natural Language Input
→ Grammar / Parser
→ Syntactic Representation
→ Semantic Interpretation
→ Intent / Entity
→ Knowledge Base / Retrieval
→ Answer
```

LLM/RAG có thể được bổ sung về sau, nhưng không thay thế các thành phần
NLP cốt lõi phía trên.

Proposal này chốt trước các điểm mà cả ba thành viên cần dùng chung:

1.  Domain ontology và Knowledge Base schema.
2.  Intent taxonomy.
3.  QueryFrame taxonomy.
4.  Shared vocabulary: SentenceType, SlotType, EntityType, Attribute,
    AnswerMode, Status.
5.  Contract `ParserResult` giữa Người 1 → Người 2.
6.  Contract `SemanticQuery` giữa Người 2 → Người 3.
7.  Contract context/reference resolution.
8.  Contract `RetrievalResult`.
9.  Canonical entity IDs và alias normalization.
10. Mock input / expected output cho từng thành viên.
11. Phân công và Definition of Done.
12. Quy trình integration.

Nguyên tắc quan trọng:

> Một field chỉ được đưa vào contract nếu downstream module thực sự cần
> nó.

Proposal tránh thêm các field như confidence, timestamp, trace ID,
metadata... nếu phiên bản v1 chưa có use case rõ ràng.

------------------------------------------------------------------------

# 2. Audit tài nguyên được cung cấp

## 2.1 Sample code

Sample code hiện chủ yếu là project bootstrap:

-   Python package skeleton;
-   Java Maven skeleton;
-   Dockerfile;
-   requirements/config cơ bản;
-   Python `utils.py` chỉ có hàm test rất sơ khai.

Hiện chưa có implementation đáng kể cho:

-   grammar;
-   parser;
-   semantic mapper;
-   intent/entity recognizer;
-   context resolver;
-   knowledge-base loader;
-   query engine;
-   answer generator;
-   evaluation framework.

**Quyết định:** không cố gắng bám kiến trúc vào sample code. Nhóm dùng
sample code như bộ khung môi trường và tự xây các module NLP.

------------------------------------------------------------------------

## 2.2 Sample data

Sample dataset hiện có:

``` text
00_README.txt
course_info.txt
schedule.txt
topics.txt
assignments.txt
resources.txt
regulations.txt
faq.txt
dialogues.txt
sample_queries.txt
entities.txt
```

Dataset được thiết kế để hỗ trợ:

-   Grammar / Parser;
-   Semantic representation;
-   Intent / Entity recognition;
-   Knowledge-base QA;
-   local discourse context/reference;
-   retrieval/RAG mở rộng.

Một điểm quan trọng trong README của sample dataset là các file kiến
thức là **nguồn dữ liệu để Course Assistant truy vấn**, không phải
grammar được cung cấp sẵn. Các intent/entity trong sample cũng chỉ là
gợi ý, nhóm được phép thiết kế schema phù hợp hơn.

### Dữ liệu hiện có tương đối tốt cho prototype

Có dữ liệu về:

-   course information;
-   15-week schedule;
-   12 chapters/topics;
-   learning outcomes;
-   assignment;
-   resources;
-   regulations;
-   FAQ;
-   local dialogue/context;
-   entity aliases;
-   labeled sample queries.

### Nhưng cần phân biệt hai khái niệm

``` text
DOMAIN SCHEMA CAPABILITY
≠
CURRENT SAMPLE KB COVERAGE
```

Ví dụ:

``` text
INSTRUCTOR
Schema capability: SUPPORTED
Current sample KB: NOT POPULATED
```

Do đó việc sample data chưa có instructor **không phải lý do để xóa
`INSTRUCTOR` hay `GET_INSTRUCTOR` khỏi thiết kế**.

Nếu người dùng hỏi:

``` text
Giảng viên môn NLP là ai?
```

hệ thống vẫn hiểu intent/entity đúng, nhưng Knowledge Base trả:

``` text
NOT_FOUND
```

Đây là hành vi đúng và còn giúp kiểm tra yêu cầu "hiểu câu hỏi nhưng KB
không có dữ liệu".

------------------------------------------------------------------------

# 3. Kiến trúc tổng thể

``` text
                       USER UTTERANCE
                              │
                              ▼
                  ┌─────────────────────┐
                  │  Grammar + Parser   │
                  │      Người 1        │
                  └──────────┬──────────┘
                             │
                        ParserResult
                             │
                             ▼
             ┌───────────────────────────────┐
             │ Semantic Interpretation       │
             │ Intent / Entity Normalization │
             │ Context / Reference Resolver  │
             │            Người 2            │
             └──────────────┬────────────────┘
                            │
                       SemanticQuery
                            │
                            ▼
                ┌─────────────────────────┐
                │ KB + Query Engine       │
                │ Retrieval + Answer      │
                │       Người 3           │
                └───────────┬─────────────┘
                            │
                      RetrievalResult
                            │
                            ▼
                         ANSWER
```

Ba module phụ thuộc nhau về mặt logic nhưng **không cần phát triển tuần
tự**.

Người 2 dùng mock `ParserResult` trong lúc Người 1 code parser.\
Người 3 dùng mock `SemanticQuery` trong lúc Người 2 code semantic layer.

------------------------------------------------------------------------

# 4. Shared artifacts phải freeze trước khi code

Repository nên có thư mục:

``` text
contracts/
├── ontology.md
├── intents.yaml
├── query_frames.yaml
├── attributes.yaml
├── entity_ids.yaml
├── parser_result.schema.json
├── semantic_query.schema.json
├── retrieval_result.schema.json
└── mock_cases/
```

Các file này là **shared contract**.

Không thành viên nào được tự ý đổi enum hoặc ý nghĩa field trên branch
cá nhân. Thay đổi contract phải được cả nhóm đồng ý vì nó ảnh hưởng
module downstream.

------------------------------------------------------------------------

# 5. Domain Ontology

Ontology mô tả **những object nào tồn tại trong miền Course Assistant,
chúng có thuộc tính gì và quan hệ với nhau như thế nào**.

Ontology không đồng nghĩa với NER labels và cũng không đồng nghĩa với dữ
liệu sample hiện đang populate.

------------------------------------------------------------------------

## 5.1 COURSE

### Mục đích

Đại diện cho môn học.

### Canonical ID

``` text
CO3085
```

### Attributes

  Attribute                  Type       Cardinality Sample hiện có
  -------------------------- -------- ------------- ----------------
  `id`                       string               1 Có
  `name`                     string               1 Có
  `name_en`                  string            0..1 Có
  `semester`                 string            0..1 Có
  `credits`                  number            0..1 Có
  `ects`                     number            0..1 Có
  `course_type`              string            0..1 Có
  `department`               string            0..1 Có
  `format`                   string            0..1 Có
  `total_course_hours`       number            0..1 Có
  `lecture_hours`            number            0..1 Có
  `major_assignment_hours`   number            0..1 Có
  `self_study_hours`         number            0..1 Có
  `description`              text              0..1 Có

### Relations

``` text
COURSE HAS_PART COURSE_PART
COURSE HAS_CHAPTER CHAPTER
COURSE HAS_WEEK WEEK
COURSE HAS_ASSIGNMENT ASSIGNMENT
COURSE HAS_RESOURCE RESOURCE
COURSE HAS_REGULATION REGULATION
COURSE HAS_LEARNING_OUTCOME LEARNING_OUTCOME
COURSE HAS_INSTRUCTOR INSTRUCTOR
COURSE HAS_EXAM EXAM
```

------------------------------------------------------------------------

## 5.2 COURSE_PART

Ví dụ:

``` text
COURSE_PART_INTRO
COURSE_PART_SYNTACTIC
COURSE_PART_SEMANTIC
COURSE_PART_CONTEXT
```

### Attributes

``` text
id
name
name_en
```

### Relations

``` text
COURSE_PART BELONGS_TO COURSE
COURSE_PART HAS_CHAPTER CHAPTER
```

### Lý do tồn tại

Sample course chia nội dung thành các phần lớn. `COURSE_PART` không nên
bị trộn với `ASSIGNMENT_PART`; "Part I - Syntactic Processing" của
course và "Part I - Grammar and Parser" của BTL là hai domain object
khác nhau.

------------------------------------------------------------------------

## 5.3 WEEK

### Canonical IDs

``` text
WEEK_01 ... WEEK_15
```

### Attributes

``` text
id
week_number
activity
milestone
```

### Relations

``` text
WEEK COVERS_CHAPTER CHAPTER
WEEK COVERS_TOPIC TOPIC
WEEK BELONGS_TO_PART COURSE_PART
```

### Cardinality quan trọng

Một tuần có thể có nhiều chapter/topic và một chapter có thể xuất hiện ở
nhiều tuần.

Sample đã có ví dụ Chapter 4 xuất hiện ở Week 4 và Week 5, Chapter 6
xuất hiện ở Week 7 và Week 8.

Vì vậy không được model quan hệ này theo kiểu one-to-one.

------------------------------------------------------------------------

## 5.4 CHAPTER

### Canonical IDs

``` text
CH01 ... CH12
```

### Attributes

``` text
id
title
summary
keywords[]
subtopics[]
```

### Relations

``` text
CHAPTER BELONGS_TO_PART COURSE_PART
CHAPTER HAS_TOPIC TOPIC
CHAPTER TAUGHT_IN WEEK
CHAPTER RELATED_TO_LO LEARNING_OUTCOME
CHAPTER SUPPORTED_BY RESOURCE
```

------------------------------------------------------------------------

## 5.5 TOPIC

### Mục đích

`TOPIC` biểu diễn nội dung/khái niệm được học, ví dụ:

``` text
CFG
PCFG
PARSING
DEPENDENCY_GRAMMAR
SEMANTIC_GRAMMAR
QUESTION_ANSWERING
REFERENCE
ANAPHORA
CENTERING
SELECTIONAL_RESTRICTION
...
```

### Attributes

``` text
id
canonical_name
aliases[]
```

### Relations

``` text
TOPIC COVERED_BY CHAPTER
TOPIC TAUGHT_IN WEEK
TOPIC SUPPORTED_BY RESOURCE
TOPIC RELATED_TO_LO LEARNING_OUTCOME
```

### Vì sao cần TOPIC?

Câu:

``` text
Chương nào nói về CFG?
```

không hỏi một attribute đơn giản của course. Nó hỏi quan hệ:

``` text
TOPIC(CFG) --COVERED_BY--> CHAPTER(?)
```

Ngược lại:

``` text
Chương 3 học gì?
```

hỏi:

``` text
CHAPTER(CH03) --HAS_TOPIC--> TOPIC[]
```

------------------------------------------------------------------------

## 5.6 ASSIGNMENT

### Canonical ID

``` text
BTL01
```

### Attributes

``` text
id
title
team_size
domain
goal
```

### Relations

``` text
ASSIGNMENT HAS_PART ASSIGNMENT_PART
ASSIGNMENT HAS_DEADLINE DEADLINE
```

------------------------------------------------------------------------

## 5.7 ASSIGNMENT_PART

### Canonical IDs

``` text
PART_I
PART_II
PART_III
PART_IV
```

Trong implementation nên namespace rõ nếu cần tránh nhầm với Course
Part:

``` text
BTL_PART_I
BTL_PART_II
BTL_PART_III
BTL_PART_IV
```

### Attributes

``` text
id
title
requirements[]
outputs[]
status
description
```

### Relations

``` text
ASSIGNMENT_PART BELONGS_TO ASSIGNMENT
ASSIGNMENT_PART HAS_DEADLINE DEADLINE
```

------------------------------------------------------------------------

## 5.8 DEADLINE

### Mục đích

Schema cần support deadline/milestone dù sample hiện chỉ có các
milestone mẫu và chưa có deadline hành chính chính thức.

### Attributes

``` text
id
name
date
time
description
official
```

### Relations

``` text
DEADLINE FOR_ASSIGNMENT ASSIGNMENT
DEADLINE FOR_ASSIGNMENT_PART ASSIGNMENT_PART
```

### Lưu ý

`DEADLINE` là domain object trong ontology. Tuy nhiên trong câu:

``` text
Deadline BTL là khi nào?
```

từ "deadline" không nhất thiết phải được NER thành một entity riêng.
Intent `GET_DEADLINE` + assignment entity đã đủ để xây semantic query.

------------------------------------------------------------------------

## 5.9 RESOURCE

### Canonical IDs

Sample chưa có ID ổn định nên implementation nên cấp:

``` text
RES01
RES02
...
```

### Attributes

``` text
id
resource_type
title
authors[]
publisher
year
usage
```

### Relations

``` text
RESOURCE SUPPORTS_TOPIC TOPIC
RESOURCE SUPPORTS_CHAPTER CHAPTER
RESOURCE SUPPORTS_COURSE COURSE
```

### Lý do dùng ID

Title dài và không ổn định để làm join key. Stable ID giúp normalization
và query đơn giản hơn.

------------------------------------------------------------------------

## 5.10 REGULATION

### Canonical IDs ban đầu từ sample

``` text
ATTENDANCE
ACADEMIC_INTEGRITY
AI_USAGE
SOURCE_CODE
ASSIGNMENT_SHARING
EXTERNAL_LIBRARIES
LLM_RAG
OUT_OF_SCOPE
```

### Attributes

``` text
id
text
```

### Relations

``` text
REGULATION APPLIES_TO COURSE
REGULATION APPLIES_TO ASSIGNMENT       # nếu phù hợp
```

### `AI_USAGE`, `LLM_RAG` là gì?

Đây **không phải intent**.

Chúng là canonical IDs của các regulation/policy object.

Ví dụ:

``` text
Có được dùng LLM/RAG không?
```

→ entity:

``` text
REGULATION = LLM_RAG
```

→ query KB:

``` text
regulations["LLM_RAG"]
```

------------------------------------------------------------------------

## 5.11 LEARNING_OUTCOME

### Canonical IDs

``` text
LO1
LO2
LO2.1
...
LO4.2
```

### Attributes

``` text
id
description
```

### Relations

``` text
LEARNING_OUTCOME RELATED_TO_TOPIC TOPIC
LEARNING_OUTCOME RELATED_TO_CHAPTER CHAPTER
LEARNING_OUTCOME BELONGS_TO COURSE
```

------------------------------------------------------------------------

## 5.12 EXAM

### Canonical IDs

``` text
MIDTERM
FINAL
```

### Attributes

``` text
id
duration_minutes
format
weight
```

### Relations

``` text
EXAM BELONGS_TO COURSE
```

------------------------------------------------------------------------

## 5.13 INSTRUCTOR

### Canonical IDs

Khi có dữ liệu thật:

``` text
INS01
INS02
...
```

### Attributes

``` text
id
name
email
office
```

### Relations

``` text
INSTRUCTOR TEACHES COURSE
```

### Current sample coverage

``` text
Schema: SUPPORTED
Current sample KB: NOT POPULATED
```

Do đó `GET_INSTRUCTOR` vẫn tồn tại.

------------------------------------------------------------------------

# 6. Canonical ID & Alias Normalization

Raw text từ parser **không được dùng trực tiếp làm key của KB**.

Ví dụ:

``` text
"Chương 3"
"chương ba"
"CH3"
```

đều normalize:

``` text
CH03
```

Tương tự:

``` text
"NLP"
"CO3085"
"Natural Language Processing"
"Xử lý Ngôn ngữ Tự nhiên"
```

→

``` text
CO3085
```

Và:

``` text
"context free grammar"
"context-free grammar"
"CFG"
```

→

``` text
CFG
```

Shared alias dictionary là dependency của cả Người 2 và Người 3.

Người 2 dùng dictionary để normalize.\
Người 3 xây KB bằng chính canonical IDs đó.

------------------------------------------------------------------------

# 7. Intent Taxonomy v1

Intent trả lời câu hỏi:

> **Người dùng muốn hệ thống thực hiện loại truy vấn nghiệp vụ nào?**

Intent không mô tả hình thức cú pháp. Ví dụ `WH_QUESTION` không phải
intent.

Intent cũng không mô tả việc câu có phụ thuộc context hay không.
`CONTEXT_DEPENDENT` không phải business intent.

## 7.1 Danh sách intent freeze cho v1

``` text
GET_COURSE_INFO
GET_SCHEDULE
GET_TOPIC
GET_ASSIGNMENT
GET_DEADLINE
GET_RESOURCE
GET_RULE
GET_INSTRUCTOR
GET_LO
UNKNOWN
```

------------------------------------------------------------------------

## 7.2 GET_COURSE_INFO

### Ý nghĩa

Lấy attribute trực tiếp của course hoặc exam thuộc course.

### Ví dụ

``` text
Môn NLP có bao nhiêu tín chỉ?
CO3085 thuộc khoa nào?
Môn học gồm những phần nào?
Midterm bao nhiêu phút?
Final chiếm bao nhiêu phần trăm?
```

### Không dùng khi

Câu hỏi chủ yếu về:

-   schedule;
-   chapter/topic;
-   assignment;
-   resource;
-   regulation;
-   instructor;
-   LO.

### Entity thường dùng

``` text
COURSE
EXAM
```

### Attributes thường dùng

``` text
name
name_en
semester
credits
ects
course_type
department
format
total_course_hours
lecture_hours
major_assignment_hours
self_study_hours
description
parts
assessment
duration
weight
```

------------------------------------------------------------------------

## 7.3 GET_SCHEDULE

### Ý nghĩa

Truy vấn quan hệ thời gian học:

``` text
week ↔ chapter
week ↔ topic
week ↔ activity
week ↔ milestone
```

### Ví dụ

``` text
Tuần 3 học gì?
Chương 4 học tuần nào?
CFG học tuần mấy?
Tuần 8 có hoạt động gì?
Checkpoint 1 nằm ở tuần nào?
```

### Entities

``` text
WEEK
CHAPTER
TOPIC
ASSIGNMENT / ASSIGNMENT_PART nếu milestone liên quan
```

------------------------------------------------------------------------

## 7.4 GET_TOPIC

### Ý nghĩa

Truy vấn nội dung chapter/topic hoặc quan hệ chapter ↔ topic.

### Ví dụ

``` text
Chương 12 nói về gì?
Chương nào nói về CFG?
PCFG nằm ở chương nào?
Chương 11 có question answering không?
Chương 10 có những phương pháp gì?
```

### Entities

``` text
CHAPTER
TOPIC
```

------------------------------------------------------------------------

## 7.5 GET_ASSIGNMENT

### Ý nghĩa

Lấy cấu trúc, requirement, output hoặc thông tin chung của
assignment/assignment part.

### Ví dụ

``` text
BTL yêu cầu xây dựng gì?
Phần I là gì?
Phần II yêu cầu gì?
Phần I phải xuất file nào?
BTL có phần parser không?
```

### Entities

``` text
ASSIGNMENT
ASSIGNMENT_PART
TOPIC        # khi hỏi assignment có chứa một capability/topic không
```

### Không dùng cho deadline

Deadline dùng `GET_DEADLINE`.

------------------------------------------------------------------------

## 7.6 GET_DEADLINE

### Ý nghĩa

Truy vấn deadline/mốc thời gian nộp của assignment hoặc assignment part.

### Ví dụ

``` text
Deadline BTL là khi nào?
Phần I nộp khi nào?
Checkpoint 1 khi nào?
```

### Entities

``` text
ASSIGNMENT
ASSIGNMENT_PART
DEADLINE
```

Nếu KB chưa có ngày chính thức, intent vẫn đúng nhưng retrieval trả
`NOT_FOUND`.

------------------------------------------------------------------------

## 7.7 GET_RESOURCE

### Ý nghĩa

Tìm resource hoặc attribute của resource.

### Ví dụ

``` text
Tài liệu nào nói về statistical NLP?
Có tài liệu Python NLP không?
Ai viết Natural Language Processing with Python?
Tài liệu về CFG là gì?
```

### Entities

``` text
RESOURCE
TOPIC
CHAPTER
```

------------------------------------------------------------------------

## 7.8 GET_RULE

### Ý nghĩa

Truy vấn regulation/policy hoặc permission/prohibition.

### Ví dụ

``` text
Quy định về AI là gì?
Có được dùng LLM/RAG không?
Có được chia sẻ code giữa các nhóm không?
Có được dùng thư viện ngoài không?
```

### Entities

``` text
REGULATION
```

------------------------------------------------------------------------

## 7.9 GET_INSTRUCTOR

### Ý nghĩa

Truy vấn instructor của course hoặc attribute của instructor.

### Ví dụ

``` text
Ai dạy môn NLP?
Giảng viên CO3085 là ai?
Email giảng viên là gì?
```

### Current data

Sample hiện chưa populate instructor.

Đây là **supported intent with potentially NOT_FOUND data**, không phải
unsupported intent.

------------------------------------------------------------------------

## 7.10 GET_LO

### Ý nghĩa

Truy vấn learning outcome hoặc quan hệ LO ↔ topic/chapter.

### Ví dụ

``` text
LO2.5 là gì?
LO4.2 liên quan nội dung nào?
LO2.5 nằm ở chương nào?
```

### Entities

``` text
LEARNING_OUTCOME
TOPIC
CHAPTER
```

------------------------------------------------------------------------

## 7.11 UNKNOWN

### Ý nghĩa

Câu không thuộc miền Course Assistant hoặc không map được sang một
intent được hỗ trợ.

### Ví dụ

``` text
Hôm nay có mưa không?
Ai là tổng thống Pháp?
Giải bài xác suất này giúp tôi.
```

### Phân biệt với NOT_FOUND

``` text
UNKNOWN
= không thuộc intent/domain mà hệ thống support.

NOT_FOUND
= semantic query hợp lệ nhưng KB không có dữ liệu.
```

Ví dụ:

``` text
Ai dạy NLP?
→ GET_INSTRUCTOR
→ KB không có instructor
→ NOT_FOUND
```

không phải `UNKNOWN`.

------------------------------------------------------------------------

# 8. SentenceType v1

Controlled vocabulary:

``` text
WH_QUESTION
YES_NO_QUESTION
IMPERATIVE_REQUEST
```

## WH_QUESTION

``` text
Chương nào nói về CFG?
Tuần 3 học gì?
Deadline BTL là khi nào?
```

## YES_NO_QUESTION

``` text
Chương 11 có question answering không?
Có được dùng LLM/RAG không?
BTL có phần parser không?
```

## IMPERATIVE_REQUEST

``` text
Cho tôi tài liệu về CFG.
Cho biết nội dung chương 3.
Liệt kê các phần của BTL.
```

V1 không cần thêm nhiều sentence types nếu downstream chưa dùng.

------------------------------------------------------------------------

# 9. SlotType v1

Parser chỉ extract **raw surface values**.

Controlled slot keys:

``` text
course
course_part
week
chapter
topic
assignment
assignment_part
deadline
resource
regulation
learning_outcome
exam
instructor
reference
```

Tất cả slot values có cardinality:

``` text
0..N
```

Ví dụ:

``` json
{
  "chapter": ["Chương 3", "Chương 4"],
  "topic": ["CFG", "Parsing"]
}
```

`reference` dành cho biểu thức như:

``` text
nó
chương này
phần này
nội dung này
chương sau
```

Parser nhận diện đây là reference expression nhưng **không resolve nó
thành CH04/PART_I**. Việc resolve thuộc Người 2.

------------------------------------------------------------------------

# 10. QueryFrame Taxonomy v1

QueryFrame trả lời câu hỏi:

> **Cấu trúc cú pháp này đang hỏi quan hệ/thuộc tính nào?**

Nó là cầu nối giữa parse tree và semantic interpretation.

QueryFrame không phải intent. Nhiều QueryFrame có thể map vào cùng một
intent.

Ví dụ:

``` text
ASK_CHAPTER_CONTENT
ASK_CHAPTER_BY_TOPIC
ASK_TOPIC_EXISTENCE_IN_CHAPTER
```

đều có thể map sang:

``` text
GET_TOPIC
```

------------------------------------------------------------------------

## 10.1 Course / Exam frames

### ASK_COURSE_ATTRIBUTE

``` text
Required slots: course [0..N]
Optional slots: none
Examples:
- Môn NLP có bao nhiêu tín chỉ?
- CO3085 thuộc khoa nào?
- Môn này có bao nhiêu giờ tự học?
```

`course` có thể thiếu nếu course mặc định của assistant là CO3085.

------------------------------------------------------------------------

### ASK_COURSE_PARTS

``` text
Required: none
Optional: course
Examples:
- Môn học gồm những phần nào?
- NLP có mấy phần chính?
```

------------------------------------------------------------------------

### ASK_EXAM_ATTRIBUTE

``` text
Required: exam [1..N]
Optional: course
Examples:
- Midterm bao nhiêu phút?
- Final chiếm bao nhiêu phần trăm?
- Hình thức thi midterm là gì?
```

------------------------------------------------------------------------

### ASK_INSTRUCTOR

``` text
Required: none
Optional: course, instructor
Examples:
- Ai dạy môn NLP?
- Giảng viên CO3085 là ai?
```

------------------------------------------------------------------------

### ASK_INSTRUCTOR_ATTRIBUTE

``` text
Required: instructor [0..N]
Optional: course
Examples:
- Email giảng viên NLP là gì?
- Văn phòng giảng viên ở đâu?
```

------------------------------------------------------------------------

## 10.2 Schedule frames

### ASK_WEEK_CONTENT

``` text
Required: week [1..N]
Optional: none
Examples:
- Tuần 3 học gì?
- Tuần 3 và tuần 4 học nội dung gì?
```

------------------------------------------------------------------------

### ASK_WEEK_OF_CHAPTER

``` text
Required: chapter [1..N]
Examples:
- Chương 4 học tuần nào?
- Chương 3 và chương 4 học tuần nào?
```

------------------------------------------------------------------------

### ASK_WEEK_OF_TOPIC

``` text
Required: topic [1..N]
Examples:
- CFG học tuần mấy?
- Reference được học khi nào?
```

------------------------------------------------------------------------

### ASK_WEEK_ACTIVITY

``` text
Required: week [1..N]
Examples:
- Tuần 8 có hoạt động gì?
```

------------------------------------------------------------------------

### ASK_WEEK_MILESTONE

``` text
Required: week [1..N]
Examples:
- Tuần 12 có milestone gì?
```

------------------------------------------------------------------------

### ASK_MILESTONE_WEEK

``` text
Required: assignment/assignment_part/deadline [0..N]
Examples:
- Checkpoint 1 nằm ở tuần nào?
- BTL final submission ở tuần mấy?
```

------------------------------------------------------------------------

## 10.3 Chapter / Topic frames

### ASK_CHAPTER_CONTENT

``` text
Required: chapter [1..N]
Examples:
- Chương 12 nói về gì?
- Nội dung chương 10 là gì?
```

------------------------------------------------------------------------

### ASK_CHAPTER_TITLE

``` text
Required: chapter [1..N]
Examples:
- Chương 3 tên gì?
```

------------------------------------------------------------------------

### ASK_CHAPTER_BY_TOPIC

``` text
Required: topic [1..N]
Examples:
- Chương nào nói về CFG?
- PCFG nằm ở chương nào?
```

------------------------------------------------------------------------

### ASK_TOPIC_OF_CHAPTER

``` text
Required: chapter [1..N]
Examples:
- Chương 10 có những chủ đề nào?
- Chương 3 học những gì?
```

------------------------------------------------------------------------

### ASK_TOPIC_EXISTENCE_IN_CHAPTER

``` text
Required: chapter/reference [1..N], topic [1..N]
Examples:
- Chương 11 có question answering không?
- Nó có liên quan đến parsing không?
```

Reference có thể thay chapter ở ParserResult và được Người 2 resolve
sau.

------------------------------------------------------------------------

### ASK_PART_OF_CHAPTER

``` text
Required: chapter [1..N]
Examples:
- Chương 8 thuộc phần nào?
```

------------------------------------------------------------------------

### ASK_CHAPTERS_OF_PART

``` text
Required: course_part [1..N]
Examples:
- Phần Semantic Interpretation gồm chương nào?
```

------------------------------------------------------------------------

## 10.4 Assignment frames

### ASK_ASSIGNMENT_INFO

``` text
Required: assignment [0..N]
Examples:
- BTL là gì?
- Mục tiêu bài tập lớn là gì?
```

------------------------------------------------------------------------

### ASK_ASSIGNMENT_PARTS

``` text
Required: assignment [0..N]
Examples:
- BTL gồm những phần nào?
```

------------------------------------------------------------------------

### ASK_ASSIGNMENT_PART_INFO

``` text
Required: assignment_part [1..N]
Optional: assignment
Examples:
- Phần I của BTL là gì?
```

------------------------------------------------------------------------

### ASK_ASSIGNMENT_REQUIREMENTS

``` text
Required: assignment hoặc assignment_part [1..N]
Examples:
- BTL yêu cầu xây dựng những gì?
- Phần II yêu cầu gì?
```

------------------------------------------------------------------------

### ASK_ASSIGNMENT_OUTPUTS

``` text
Required: assignment_part [1..N] hoặc reference [1..N]
Examples:
- Phần I phải xuất file gì?
- Phần này cần output gì?
```

------------------------------------------------------------------------

### ASK_ASSIGNMENT_COMPONENT_EXISTENCE

``` text
Required: assignment/assignment_part/reference [1..N]
Required: topic [1..N]
Examples:
- BTL có phần parser không?
- Phần II có hỏi đáp không?
```

------------------------------------------------------------------------

### ASK_ASSIGNMENT_TEAM_SIZE

``` text
Required: assignment [0..N]
Examples:
- BTL làm nhóm mấy người?
```

------------------------------------------------------------------------

## 10.5 Deadline frames

### ASK_ASSIGNMENT_DEADLINE

``` text
Required: assignment [0..N]
Examples:
- Deadline BTL là khi nào?
```

------------------------------------------------------------------------

### ASK_ASSIGNMENT_PART_DEADLINE

``` text
Required: assignment_part [1..N]
Examples:
- Phần I nộp khi nào?
```

------------------------------------------------------------------------

### ASK_DEADLINE_INFO

``` text
Required: deadline [1..N]
Examples:
- Checkpoint 1 diễn ra khi nào?
```

------------------------------------------------------------------------

## 10.6 Resource frames

### ASK_RESOURCE_BY_TOPIC

``` text
Required: topic [1..N]
Examples:
- Tài liệu nào nói về statistical NLP?
- Cho tôi tài liệu về CFG.
```

------------------------------------------------------------------------

### ASK_RESOURCE_BY_CHAPTER

``` text
Required: chapter/reference [1..N]
Examples:
- Tài liệu của chương 3 là gì?
- Tài liệu của chương này là gì?
```

------------------------------------------------------------------------

### ASK_RESOURCE_ATTRIBUTE

``` text
Required: resource [1..N]
Examples:
- Ai viết Natural Language Processing with Python?
- Tài liệu này xuất bản năm nào?
```

------------------------------------------------------------------------

## 10.7 Regulation frames

### ASK_REGULATION

``` text
Required: regulation [1..N]
Examples:
- Quy định sử dụng AI là gì?
- Quy định về source code như thế nào?
```

------------------------------------------------------------------------

### ASK_PERMISSION

``` text
Required: regulation [1..N]
Examples:
- Có được dùng LLM/RAG không?
- Có được dùng thư viện ngoài không?
- Có được chia sẻ bài giữa các nhóm không?
```

------------------------------------------------------------------------

## 10.8 Learning Outcome frames

### ASK_LO_DESCRIPTION

``` text
Required: learning_outcome [1..N]
Examples:
- LO2.5 là gì?
- LO4.2 nói về gì?
```

------------------------------------------------------------------------

### ASK_LO_RELATED_CONTENT

``` text
Required: learning_outcome [1..N]
Examples:
- LO4.2 liên quan nội dung nào?
```

------------------------------------------------------------------------

### ASK_CHAPTER_BY_LO

``` text
Required: learning_outcome/reference [1..N]
Examples:
- LO2.5 nằm ở chương nào?
- Nội dung này nằm ở chương nào?
```

------------------------------------------------------------------------

## 10.9 QueryFrame extensibility rule

Danh sách trên là **v1 controlled vocabulary**, không phải tuyên bố rằng
mọi câu Course Assistant trong tương lai chỉ có thể thuộc các frame này.

Nếu khi triển khai xuất hiện một cấu trúc query mới mà:

1.  không thể biểu diễn chính xác bằng frame hiện có;
2.  có use case trong domain;
3.  có semantic mapping và KB handler rõ ràng;

thì nhóm thêm frame mới vào `query_frames.yaml` qua một contract change
chung.

Không được tự tạo frame ad-hoc trong code.

------------------------------------------------------------------------

# 11. Attribute Vocabulary v1

`attribute` trong `SemanticQuery` phải là controlled value, không phải
free text.

## COURSE attributes

``` text
name
name_en
semester
credits
ects
course_type
department
format
total_course_hours
lecture_hours
major_assignment_hours
self_study_hours
description
parts
assessment
```

## EXAM

``` text
duration
format
weight
```

## WEEK

``` text
topics
chapters
activity
milestone
```

## CHAPTER/TOPIC

``` text
title
summary
topics
chapter
week
part
contains_topic
```

## ASSIGNMENT

``` text
title
team_size
domain
goal
parts
requirements
outputs
contains_component
```

## DEADLINE

``` text
date
time
description
week
```

## RESOURCE

``` text
title
authors
publisher
year
usage
resource
```

## REGULATION

``` text
policy_text
permission
```

## LEARNING_OUTCOME

``` text
description
related_content
chapter
```

## INSTRUCTOR

``` text
name
email
office
```

------------------------------------------------------------------------

# 12. AnswerMode v1

``` text
VALUE
LIST
BOOLEAN
```

## VALUE

Một giá trị/text chính:

``` text
Môn NLP có 3 tín chỉ.
```

## LIST

Nhiều giá trị:

``` text
Chương 3 gồm CFG, parsing, PCFG, dependency grammar...
```

## BOOLEAN

Câu yes/no:

``` text
Có. Chương 11 có nội dung Question Answering.
```

Answer generator có thể thêm explanation sau boolean nhưng mode chính
vẫn là `BOOLEAN`.

------------------------------------------------------------------------

# 13. Contract 1 --- ParserResult

Đây là API contract **Người 1 → Người 2**.

``` json
{
  "valid": true,
  "sentence_type": "WH_QUESTION",
  "query_frame": "ASK_CHAPTER_BY_TOPIC",
  "slots": {
    "topic": ["CFG"]
  },
  "tree": "(S ...)"
}
```

## Schema

  ----------------------------------------------------------------------------------
  Field             Type                                Cardinality Ý nghĩa
  ----------------- ------------------------- --------------------- ----------------
  `valid`           boolean                                       1 Câu có parse
                                                                    được theo
                                                                    grammar/domain
                                                                    không

  `sentence_type`   SentenceType/null                          0..1 Kiểu câu cú pháp

  `query_frame`     QueryFrame/null                            0..1 Cấu trúc truy
                                                                    vấn cú pháp

  `slots`           map\<SlotType,                                1 Raw constituents
                    list`<string>`{=html}\>                         quan trọng

  `tree`            string/null                                0..1 Parse tree
  ----------------------------------------------------------------------------------

### Khi invalid

``` json
{
  "valid": false,
  "sentence_type": null,
  "query_frame": null,
  "slots": {},
  "tree": null
}
```

Output file theo đề vẫn có thể serialize invalid tree thành:

``` text
()
```

------------------------------------------------------------------------

## 13.1 Vì sao cần `valid`?

Semantic layer không nên tự kiểm tra string tree `()`.

`valid` là machine-readable signal rõ ràng.

------------------------------------------------------------------------

## 13.2 Vì sao cần `sentence_type`?

Hai câu có cùng entity nhưng semantics/answer khác:

``` text
Chương 11 có question answering không?
→ YES_NO_QUESTION

Chương nào có question answering?
→ WH_QUESTION
```

------------------------------------------------------------------------

## 13.3 Vì sao cần `query_frame`?

Nếu chỉ truyền parse tree, Người 2 phải tự traverse mọi production để
đoán cấu trúc semantic.

`query_frame` là kết quả structural interpretation trực tiếp từ
grammar/parser và là cầu nối ổn định sang semantic mapper.

------------------------------------------------------------------------

## 13.4 Vì sao `slots` là list?

Một câu có thể có nhiều entity cùng loại:

``` text
Chương 3 và chương 4 học tuần nào?
```

→

``` json
{
  "chapter": ["Chương 3", "Chương 4"]
}
```

Do đó value không được fix thành scalar.

------------------------------------------------------------------------

## 13.5 Parser không được output gì?

Không output:

``` text
intent
canonical entity IDs
KB objects
answer
retrieval source
confidence
```

Vì đây không thuộc responsibility của parser.

------------------------------------------------------------------------

# 14. Contract 2 --- SemanticQuery

Đây là API contract **Người 2 → Người 3**.

``` json
{
  "intent": "GET_TOPIC",
  "entities": {
    "topic": ["CFG"]
  },
  "attribute": "chapter",
  "answer_mode": "LIST"
}
```

## Schema

  Field           Type                                              Cardinality
  --------------- ----------------------------------------------- -------------
  `intent`        Intent                                                      1
  `entities`      map\<EntityType, list`<CanonicalID>`{=html}\>               1
  `attribute`     Attribute/null                                           0..1
  `answer_mode`   AnswerMode                                                  1

------------------------------------------------------------------------

## 14.1 `intent`

Chọn query handler cấp cao.

Ví dụ:

``` text
GET_TOPIC
GET_SCHEDULE
GET_RULE
```

------------------------------------------------------------------------

## 14.2 `entities`

Khác Parser slots ở chỗ values đã được:

1.  normalized;
2.  context-resolved nếu cần;
3.  chuyển sang canonical IDs.

Ví dụ:

``` text
"Chương bốn"
```

→

``` text
CH04
```

------------------------------------------------------------------------

## 14.3 `attribute`

Cho Query Engine biết property/relation cần truy vấn.

Ví dụ:

``` text
Môn NLP có bao nhiêu tín chỉ?
```

→

``` json
{
  "intent": "GET_COURSE_INFO",
  "entities": {"course": ["CO3085"]},
  "attribute": "credits",
  "answer_mode": "VALUE"
}
```

Nếu không có `attribute`, `GET_COURSE_INFO + CO3085` không đủ để biết
user đang hỏi credits, department hay description.

------------------------------------------------------------------------

## 14.4 `answer_mode`

Cho downstream biết hình dạng câu trả lời mong muốn.

Ví dụ:

``` text
Chương 11 có hỏi đáp không?
```

→ `BOOLEAN`

khác với:

``` text
Chương 11 có những nội dung gì?
```

→ `LIST`.

------------------------------------------------------------------------

# 15. QueryFrame → Semantic mapping

Một số mapping chuẩn để cả Người 1 và Người 2 thống nhất:

  -----------------------------------------------------------------------------------------------------
  QueryFrame                             Intent              Attribute                AnswerMode
  -------------------------------------- ------------------- ------------------------ -----------------
  `ASK_COURSE_ATTRIBUTE`                 `GET_COURSE_INFO`   phụ thuộc lexical target VALUE

  `ASK_COURSE_PARTS`                     `GET_COURSE_INFO`   parts                    LIST

  `ASK_EXAM_ATTRIBUTE`                   `GET_COURSE_INFO`   duration/format/weight   VALUE

  `ASK_INSTRUCTOR`                       `GET_INSTRUCTOR`    name                     LIST

  `ASK_INSTRUCTOR_ATTRIBUTE`             `GET_INSTRUCTOR`    email/office/name        VALUE

  `ASK_WEEK_CONTENT`                     `GET_SCHEDULE`      topics                   LIST

  `ASK_WEEK_OF_CHAPTER`                  `GET_SCHEDULE`      week                     LIST

  `ASK_WEEK_OF_TOPIC`                    `GET_SCHEDULE`      week                     LIST

  `ASK_WEEK_ACTIVITY`                    `GET_SCHEDULE`      activity                 VALUE

  `ASK_WEEK_MILESTONE`                   `GET_SCHEDULE`      milestone                VALUE/LIST

  `ASK_MILESTONE_WEEK`                   `GET_SCHEDULE`      week                     VALUE/LIST

  `ASK_CHAPTER_CONTENT`                  `GET_TOPIC`         summary                  VALUE

  `ASK_CHAPTER_TITLE`                    `GET_TOPIC`         title                    VALUE

  `ASK_CHAPTER_BY_TOPIC`                 `GET_TOPIC`         chapter                  LIST

  `ASK_TOPIC_OF_CHAPTER`                 `GET_TOPIC`         topics                   LIST

  `ASK_TOPIC_EXISTENCE_IN_CHAPTER`       `GET_TOPIC`         contains_topic           BOOLEAN

  `ASK_PART_OF_CHAPTER`                  `GET_TOPIC`         part                     VALUE

  `ASK_CHAPTERS_OF_PART`                 `GET_TOPIC`         chapter                  LIST

  `ASK_ASSIGNMENT_INFO`                  `GET_ASSIGNMENT`    goal/title/domain        VALUE

  `ASK_ASSIGNMENT_PARTS`                 `GET_ASSIGNMENT`    parts                    LIST

  `ASK_ASSIGNMENT_PART_INFO`             `GET_ASSIGNMENT`    title/description        VALUE

  `ASK_ASSIGNMENT_REQUIREMENTS`          `GET_ASSIGNMENT`    requirements             LIST

  `ASK_ASSIGNMENT_OUTPUTS`               `GET_ASSIGNMENT`    outputs                  LIST

  `ASK_ASSIGNMENT_COMPONENT_EXISTENCE`   `GET_ASSIGNMENT`    contains_component       BOOLEAN

  `ASK_ASSIGNMENT_TEAM_SIZE`             `GET_ASSIGNMENT`    team_size                VALUE

  `ASK_ASSIGNMENT_DEADLINE`              `GET_DEADLINE`      date                     VALUE

  `ASK_ASSIGNMENT_PART_DEADLINE`         `GET_DEADLINE`      date                     VALUE

  `ASK_DEADLINE_INFO`                    `GET_DEADLINE`      date                     VALUE

  `ASK_RESOURCE_BY_TOPIC`                `GET_RESOURCE`      resource                 LIST

  `ASK_RESOURCE_BY_CHAPTER`              `GET_RESOURCE`      resource                 LIST

  `ASK_RESOURCE_ATTRIBUTE`               `GET_RESOURCE`      authors/year/etc.        VALUE/LIST

  `ASK_REGULATION`                       `GET_RULE`          policy_text              VALUE

  `ASK_PERMISSION`                       `GET_RULE`          permission               BOOLEAN

  `ASK_LO_DESCRIPTION`                   `GET_LO`            description              VALUE

  `ASK_LO_RELATED_CONTENT`               `GET_LO`            related_content          LIST/VALUE

  `ASK_CHAPTER_BY_LO`                    `GET_LO`            chapter                  LIST
  -----------------------------------------------------------------------------------------------------

`phụ thuộc lexical target` nghĩa là semantic mapper phải đọc lexical cue
đã parse, ví dụ "tín chỉ" → `credits`, "khoa" → `department`.

------------------------------------------------------------------------

# 16. Context / Reference Contract

Context resolution thuộc **Người 2**.

Parser chỉ nhận diện reference expression.

## ContextState v1

``` json
{
  "focus_entities": [
    {
      "type": "chapter",
      "id": "CH04"
    }
  ]
}
```

### Vì sao chỉ lưu focus entities?

Đề chỉ yêu cầu local discourse context đơn giản, không cần Dialogue
Manager phức tạp.

V1 chưa cần:

``` text
conversation_id
timestamp
user profile
long-term memory
full dialogue graph
```

------------------------------------------------------------------------

## 16.1 Example: pronoun

Turn 1:

``` text
Chương 4 nói về gì?
```

Semantic:

``` json
{
  "intent": "GET_TOPIC",
  "entities": {"chapter": ["CH04"]},
  "attribute": "summary",
  "answer_mode": "VALUE"
}
```

Context:

``` json
{
  "focus_entities": [
    {"type": "chapter", "id": "CH04"}
  ]
}
```

Turn 2:

``` text
Nó có liên quan đến parsing không?
```

ParserResult:

``` json
{
  "valid": true,
  "sentence_type": "YES_NO_QUESTION",
  "query_frame": "ASK_TOPIC_EXISTENCE_IN_CHAPTER",
  "slots": {
    "reference": ["nó"],
    "topic": ["parsing"]
  },
  "tree": "..."
}
```

Người 2 resolve:

``` text
"nó" → current focus chapter → CH04
"parsing" → PARSING
```

SemanticQuery:

``` json
{
  "intent": "GET_TOPIC",
  "entities": {
    "chapter": ["CH04"],
    "topic": ["PARSING"]
  },
  "attribute": "contains_topic",
  "answer_mode": "BOOLEAN"
}
```

------------------------------------------------------------------------

## 16.2 Example: definite description

``` text
Phần này cần xuất file gì?
```

Nếu focus trước đó là `BTL_PART_I`:

``` text
"phần này" → BTL_PART_I
```

------------------------------------------------------------------------

## 16.3 Example: relative reference

``` text
Còn chương sau?
```

Nếu current focus:

``` text
CH11
```

resolver áp dụng relation:

``` text
NEXT(CH11) → CH12
```

Đây là logic của Context Resolver, không phải Parser và không phải KB
Query Engine.

------------------------------------------------------------------------

# 17. Knowledge Base Schema & Ownership

Ontology là shared design artifact.

**Người 3 chịu trách nhiệm implement Knowledge Base thực tế.**

Công việc bao gồm:

1.  đọc sample `.txt`;
2.  parse/normalize thành internal structured representation;
3.  dùng canonical IDs;
4.  xây indexes/relations;
5.  expose query API cho semantic layer;
6.  trả `RetrievalResult`;
7.  generate grounded answer.

Internal KB có thể tổ chức:

``` python
kb.courses
kb.course_parts
kb.weeks
kb.chapters
kb.topics
kb.assignments
kb.assignment_parts
kb.deadlines
kb.resources
kb.regulations
kb.learning_outcomes
kb.exams
kb.instructors
```

`kb.instructors` có thể là `{}` ở sample v1.

------------------------------------------------------------------------

## 17.1 Không duplicate source of truth

Ví dụ quan hệ week ↔ chapter nên có một representation canonical.

Không nên lưu:

``` text
week.CH03 = ...
```

và một bản hoàn toàn độc lập:

``` text
chapter.week = ...
```

rồi cập nhật bằng tay hai nơi.

Có thể tạo reverse index programmatically.

------------------------------------------------------------------------

# 18. Contract 3 --- RetrievalResult

Đây là output chuẩn của Query Engine trước khi answer generator render
câu tự nhiên.

``` json
{
  "status": "FOUND",
  "values": ["CH03"],
  "sources": ["topics:CH03"]
}
```

## Status enum

``` text
FOUND
NOT_FOUND
```

### FOUND

Semantic query hợp lệ và KB tìm được dữ liệu.

### NOT_FOUND

Semantic query hợp lệ nhưng current KB không có dữ liệu.

`UNKNOWN` không nằm ở retrieval status vì UNKNOWN đã được semantic layer
xác định.

------------------------------------------------------------------------

## 18.1 `values`

Luôn dùng list:

``` json
"values": ["CH03"]
```

hoặc:

``` json
"values": ["CH03", "CH06"]
```

để tránh scalar/list inconsistency.

------------------------------------------------------------------------

## 18.2 `sources`

Ví dụ:

``` text
course_info:CO3085
topics:CH03
schedule:WEEK_03
assignments:BTL01
regulations:LLM_RAG
resources:RES05
```

Lý do cần source:

-   debug retrieval;
-   report/demo;
-   grounded answer;
-   chuẩn bị sẵn cho RAG extension sau này.

------------------------------------------------------------------------

# 19. Mock fixtures cho phát triển song song

Mock fixtures là **bắt buộc**, không phải tài liệu tham khảo tùy chọn.

------------------------------------------------------------------------

## 19.1 Người 1 --- Parser fixtures

### P01

Input:

``` text
Chương nào nói về CFG?
```

Expected:

``` json
{
  "valid": true,
  "sentence_type": "WH_QUESTION",
  "query_frame": "ASK_CHAPTER_BY_TOPIC",
  "slots": {
    "topic": ["CFG"]
  }
}
```

### P02

Input:

``` text
Chương 3 và chương 4 học tuần nào?
```

Expected nếu v1 support coordination:

``` json
{
  "valid": true,
  "sentence_type": "WH_QUESTION",
  "query_frame": "ASK_WEEK_OF_CHAPTER",
  "slots": {
    "chapter": ["Chương 3", "Chương 4"]
  }
}
```

### P03

``` text
Có được dùng LLM/RAG không?
```

Expected:

``` json
{
  "valid": true,
  "sentence_type": "YES_NO_QUESTION",
  "query_frame": "ASK_PERMISSION",
  "slots": {
    "regulation": ["LLM/RAG"]
  }
}
```

### P04

``` text
Hôm nay ở TP.HCM có mưa không?
```

Expected:

``` json
{
  "valid": false,
  "sentence_type": null,
  "query_frame": null,
  "slots": {},
  "tree": null
}
```

------------------------------------------------------------------------

# 20. Người 2 --- Semantic fixtures

## S01

Input ParserResult:

``` json
{
  "valid": true,
  "sentence_type": "WH_QUESTION",
  "query_frame": "ASK_CHAPTER_BY_TOPIC",
  "slots": {
    "topic": ["CFG"]
  }
}
```

Expected:

``` json
{
  "intent": "GET_TOPIC",
  "entities": {
    "topic": ["CFG"]
  },
  "attribute": "chapter",
  "answer_mode": "LIST"
}
```

------------------------------------------------------------------------

## S02

Input:

``` json
{
  "valid": true,
  "sentence_type": "WH_QUESTION",
  "query_frame": "ASK_COURSE_ATTRIBUTE",
  "slots": {
    "course": ["NLP"]
  }
}
```

Lexical target:

``` text
tín chỉ
```

Expected:

``` json
{
  "intent": "GET_COURSE_INFO",
  "entities": {
    "course": ["CO3085"]
  },
  "attribute": "credits",
  "answer_mode": "VALUE"
}
```

> Implementation của ParserResult cần đảm bảo lexical cue cần cho
> attribute mapping không bị mất trong parse/tree. Có thể semantic
> mapper đọc parse tree hoặc lexical terminal tương ứng; không thêm một
> field contract mới nếu tree đã cung cấp đủ thông tin.

------------------------------------------------------------------------

## S03 --- Context

Context:

``` json
{
  "focus_entities": [
    {"type": "chapter", "id": "CH04"}
  ]
}
```

ParserResult:

``` json
{
  "valid": true,
  "sentence_type": "YES_NO_QUESTION",
  "query_frame": "ASK_TOPIC_EXISTENCE_IN_CHAPTER",
  "slots": {
    "reference": ["nó"],
    "topic": ["parsing"]
  }
}
```

Expected:

``` json
{
  "intent": "GET_TOPIC",
  "entities": {
    "chapter": ["CH04"],
    "topic": ["PARSING"]
  },
  "attribute": "contains_topic",
  "answer_mode": "BOOLEAN"
}
```

------------------------------------------------------------------------

# 21. Người 3 --- KB/Query fixtures

## K01

Input:

``` json
{
  "intent": "GET_TOPIC",
  "entities": {
    "topic": ["CFG"]
  },
  "attribute": "chapter",
  "answer_mode": "LIST"
}
```

Expected retrieval:

``` json
{
  "status": "FOUND",
  "values": ["CH03"],
  "sources": ["topics:CH03"]
}
```

Expected answer:

``` text
CFG được trình bày trong Chương 3 – Grammar and Parsing.
```

------------------------------------------------------------------------

## K02 --- Multi-value result

Input:

``` json
{
  "intent": "GET_TOPIC",
  "entities": {
    "topic": ["PCFG"]
  },
  "attribute": "chapter",
  "answer_mode": "LIST"
}
```

Sample FAQ/topics cho thấy PCFG xuất hiện ở Chapter 3 và tiếp tục được
dùng ở Chapter 6.

Expected:

``` json
{
  "status": "FOUND",
  "values": ["CH03", "CH06"],
  "sources": ["topics:CH03", "topics:CH06"]
}
```

------------------------------------------------------------------------

## K03 --- Missing data

Input:

``` json
{
  "intent": "GET_INSTRUCTOR",
  "entities": {
    "course": ["CO3085"]
  },
  "attribute": "name",
  "answer_mode": "LIST"
}
```

Expected:

``` json
{
  "status": "NOT_FOUND",
  "values": [],
  "sources": []
}
```

Expected answer:

``` text
Tôi không tìm thấy thông tin giảng viên trong dữ liệu môn học hiện tại.
```

------------------------------------------------------------------------

# 22. Phân công nhóm 3 người

# 22.1 Người 1 --- Syntax / Grammar / Parser

## Own

``` text
Grammar
Lexicon phục vụ grammar
Sentence generator
Parser
Parse tree
ParserResult
Parser unit tests
```

## Công việc cụ thể

1.  Xây grammar bao phủ các QueryFrame v1 đã freeze.
2.  Xây lexical productions cho các dạng diễn đạt.
3.  Sinh câu hợp lệ từ grammar.
4.  Xây parser.
5.  Extract `sentence_type`.
6.  Extract `query_frame`.
7.  Extract raw `slots`.
8.  Serialize parse tree.
9.  Reject câu ngoài grammar/domain theo behavior đã thống nhất.
10. Viết unit test theo parser mock fixtures.

## Input

``` text
raw sentence
```

## Output

``` text
ParserResult
```

## Không chịu trách nhiệm

``` text
canonicalization
intent
context resolution
KB querying
answer generation
```

## Definition of Done

-   Các QueryFrame v1 trong scope có grammar production tương ứng.
-   ParserResult đúng schema.
-   Multi-value slot không làm vỡ contract.
-   Parse tree được xuất.
-   Invalid input trả đúng contract.
-   Mock fixtures của Người 1 pass.

------------------------------------------------------------------------

# 22.2 Người 2 --- Semantic / Intent / Entity / Context

## Own

``` text
Semantic mapper
Intent mapping
Entity normalization
Alias resolution
Attribute mapping
AnswerMode mapping
ContextState
Reference Resolver
SemanticQuery
Semantic unit tests
```

## Công việc cụ thể

1.  Nhận `ParserResult`.
2.  Map `QueryFrame → Intent`.
3.  Normalize raw slots → canonical entity IDs.
4.  Map lexical target → `attribute`.
5.  Xác định `answer_mode`.
6.  Quản lý local context.
7.  Resolve:
    -   nó;
    -   chương này;
    -   phần này;
    -   nội dung này;
    -   chương sau;
    -   các reference patterns v1 khác nếu được thêm vào contract.
8.  Output `SemanticQuery`.
9.  Xử lý semantic `UNKNOWN` khi cần.
10. Viết unit test bằng mock ParserResult.

## Input

``` text
ParserResult
ContextState
```

## Output

``` text
SemanticQuery
updated ContextState
```

## Không chịu trách nhiệm

``` text
actual KB lookup
resource retrieval
answer text generation
```

## Definition of Done

-   Tất cả QueryFrame v1 có semantic mapping.
-   Entity aliases normalize thống nhất.
-   Không truyền raw alias xuống Người 3.
-   Context fixtures resolve đúng.
-   `SemanticQuery` đúng schema.
-   Mock fixtures của Người 2 pass.

------------------------------------------------------------------------

# 22.3 Người 3 --- Knowledge Base / Retrieval / Answer / Integration Shell

## Own

``` text
KB implementation
Sample-data loader
Canonical object model
Indexes / relations
Query handlers
RetrievalResult
Answer templates
Integration entry point
KB/query unit tests
```

## Công việc cụ thể

1.  Parse các sample `.txt`.
2.  Map chúng vào ontology đã freeze.
3.  Tạo canonical KB.
4.  Tạo reverse indexes cần thiết.
5.  Implement handler cho từng Intent + Attribute combination.
6.  Trả `FOUND`/`NOT_FOUND`.
7.  Track source.
8.  Render câu trả lời theo `answer_mode`.
9.  Xây CLI/entry point để sau này nối cả pipeline.
10. Viết unit test bằng mock SemanticQuery.

## Input

``` text
SemanticQuery
```

## Output

``` text
RetrievalResult
Answer
```

## Không chịu trách nhiệm

``` text
grammar
parse tree
intent recognition
reference resolution
```

## Definition of Done

-   Sample files load thành công.
-   Canonical IDs đúng shared vocabulary.
-   Query handler không phụ thuộc raw wording của user.
-   Multi-value query/result không vỡ.
-   Missing data trả `NOT_FOUND`, không hallucinate.
-   Source được track.
-   Mock fixtures của Người 3 pass.

------------------------------------------------------------------------

# 23. Shared work trước khi tách branch

Ba người cần làm chung một buổi để freeze:

``` text
ontology
intent taxonomy
query frames
slot/entity vocabulary
attribute vocabulary
canonical IDs
contracts
mock fixtures
```

Sau đó:

``` text
Person 1 → feature/parser
Person 2 → feature/semantics
Person 3 → feature/kb-retrieval
```

Không cần chờ nhau.

------------------------------------------------------------------------

# 24. Parallel development workflow

``` text
                    CONTRACT FREEZE
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
    PERSON 1          PERSON 2         PERSON 3
 Grammar/Parser     Semantics/Context    KB/Query
        │                │                │
 test bằng          test bằng          test bằng
 raw sentences      mock ParserResult  mock SemanticQuery
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                     INTEGRATION
                         ▼
                 END-TO-END TESTING
                         ▼
              AUGMENTATION + EVALUATION
```

------------------------------------------------------------------------

# 25. Integration sequence

Không đợi cả ba module "hoàn hảo" mới ghép.

## Integration 1

``` text
Parser thật
→ Semantic mock/adapter
```

Kiểm tra `ParserResult`.

## Integration 2

``` text
Parser thật
→ Semantic thật
→ Query Engine mock
```

Kiểm tra `SemanticQuery`.

## Integration 3

``` text
Parser thật
→ Semantic thật
→ KB thật
→ Answer
```

## Integration 4

Thêm ContextState:

``` text
Turn 1
→ Answer
→ update context

Turn 2
→ reference resolution
→ SemanticQuery
→ Answer
```

------------------------------------------------------------------------

# 26. Repository structure đề xuất

``` text
course-assistant/
│
├── contracts/
│   ├── ontology.md
│   ├── intents.yaml
│   ├── query_frames.yaml
│   ├── attributes.yaml
│   ├── entity_ids.yaml
│   ├── parser_result.schema.json
│   ├── semantic_query.schema.json
│   ├── retrieval_result.schema.json
│   └── mock_cases/
│
├── src/
│   ├── syntax/
│   │   ├── grammar.py
│   │   ├── generator.py
│   │   └── parser.py
│   │
│   ├── semantics/
│   │   ├── semantic_mapper.py
│   │   ├── normalizer.py
│   │   ├── intent_mapper.py
│   │   └── context_resolver.py
│   │
│   ├── knowledge/
│   │   ├── loader.py
│   │   ├── models.py
│   │   ├── indexes.py
│   │   └── query_engine.py
│   │
│   ├── answer/
│   │   └── generator.py
│   │
│   └── assistant.py
│
├── data/
│   ├── raw/
│   ├── normalized/
│   └── grammar/
│
├── input/
│   └── sentences.txt
│
├── output/
│   ├── grammar.txt
│   ├── samples.txt
│   ├── parse-results.txt
│   ├── semantic.txt
│   ├── intent-entity.txt
│   ├── query.txt
│   ├── retrieval.txt
│   ├── answer.txt
│   ├── dialogue.txt
│   └── evaluation.txt
│
├── tests/
│   ├── syntax/
│   ├── semantics/
│   ├── knowledge/
│   └── integration/
│
├── requirements.txt
├── Dockerfile
└── README.md
```

------------------------------------------------------------------------

# 27. Một end-to-end example hoàn chỉnh

Input:

``` text
Chương nào nói về CFG?
```

## Người 1

``` json
{
  "valid": true,
  "sentence_type": "WH_QUESTION",
  "query_frame": "ASK_CHAPTER_BY_TOPIC",
  "slots": {
    "topic": ["CFG"]
  },
  "tree": "(S ...)"
}
```

## Người 2

``` text
CFG
→ canonical ID CFG
```

``` json
{
  "intent": "GET_TOPIC",
  "entities": {
    "topic": ["CFG"]
  },
  "attribute": "chapter",
  "answer_mode": "LIST"
}
```

## Người 3

Query relation:

``` text
TOPIC(CFG)
→ COVERED_BY
→ CHAPTER[]
```

Retrieval:

``` json
{
  "status": "FOUND",
  "values": ["CH03"],
  "sources": ["topics:CH03"]
}
```

Answer:

``` text
CFG được trình bày trong Chương 3 – Grammar and Parsing.
```

------------------------------------------------------------------------

# 28. End-to-end example có context

## Turn 1

``` text
Chương 4 nói về gì?
```

Parser:

``` json
{
  "valid": true,
  "sentence_type": "WH_QUESTION",
  "query_frame": "ASK_CHAPTER_CONTENT",
  "slots": {
    "chapter": ["Chương 4"]
  }
}
```

Semantic:

``` json
{
  "intent": "GET_TOPIC",
  "entities": {
    "chapter": ["CH04"]
  },
  "attribute": "summary",
  "answer_mode": "VALUE"
}
```

Context update:

``` json
{
  "focus_entities": [
    {"type": "chapter", "id": "CH04"}
  ]
}
```

## Turn 2

``` text
Nó có liên quan đến parsing không?
```

Parser:

``` json
{
  "valid": true,
  "sentence_type": "YES_NO_QUESTION",
  "query_frame": "ASK_TOPIC_EXISTENCE_IN_CHAPTER",
  "slots": {
    "reference": ["nó"],
    "topic": ["parsing"]
  }
}
```

Context Resolver:

``` text
nó → CH04
parsing → PARSING
```

Semantic:

``` json
{
  "intent": "GET_TOPIC",
  "entities": {
    "chapter": ["CH04"],
    "topic": ["PARSING"]
  },
  "attribute": "contains_topic",
  "answer_mode": "BOOLEAN"
}
```

Retrieval:

``` json
{
  "status": "FOUND",
  "values": [true],
  "sources": ["topics:CH04"]
}
```

Answer:

``` text
Có. Chương 4 có nội dung parsing với features.
```

------------------------------------------------------------------------

# 29. End-to-end example: schema support nhưng sample thiếu dữ liệu

Input:

``` text
Ai dạy môn NLP?
```

Parser:

``` json
{
  "valid": true,
  "sentence_type": "WH_QUESTION",
  "query_frame": "ASK_INSTRUCTOR",
  "slots": {
    "course": ["NLP"]
  }
}
```

Semantic:

``` json
{
  "intent": "GET_INSTRUCTOR",
  "entities": {
    "course": ["CO3085"]
  },
  "attribute": "name",
  "answer_mode": "LIST"
}
```

KB:

``` text
INSTRUCTOR schema exists
but current instructor collection = empty
```

Retrieval:

``` json
{
  "status": "NOT_FOUND",
  "values": [],
  "sources": []
}
```

Answer:

``` text
Tôi không tìm thấy thông tin giảng viên trong dữ liệu môn học hiện tại.
```

Điều này minh họa rõ:

``` text
Schema capability
≠
Current data coverage
```

------------------------------------------------------------------------

# 30. Phạm vi sau integration: Data Augmentation & Evaluation

Hai phần này **chưa triển khai chi tiết trong phase hiện tại**.

Lý do:

Trước khi augment/evaluate cần biết pipeline thực tế support:

-   những QueryFrame nào;
-   những intent nào;
-   những entity/relation nào;
-   grammar coverage thực tế;
-   failure modes sau integration.

Nếu augment trước khi contract ổn định, nhóm có nguy cơ tạo nhiều dữ
liệu không phục vụ đúng architecture.

Sau khi end-to-end v1 chạy ổn, nhóm mới thực hiện phase:

``` text
1. Audit coverage thực tế
2. Bổ sung KB nếu có coverage hole hợp lý
3. Augment/paraphrase query set
4. Tạo negative/OOD/not-found/context cases
5. Freeze gold test set
6. Evaluation
7. Error analysis
8. Iterative improvement
```

Chi tiết metric và augmentation strategy sẽ được thiết kế ở phase đó.

------------------------------------------------------------------------

# 31. Checklist để nhóm bắt đầu code

Trước khi tách branch, cả nhóm phải hoàn thành:

-   [ ] Freeze ontology v1.
-   [ ] Freeze canonical entity IDs.
-   [ ] Freeze Intent enum.
-   [ ] Freeze SentenceType enum.
-   [ ] Freeze SlotType enum.
-   [ ] Freeze QueryFrame enum.
-   [ ] Freeze Attribute enum.
-   [ ] Freeze AnswerMode enum.
-   [ ] Freeze ParserResult schema.
-   [ ] Freeze SemanticQuery schema.
-   [ ] Freeze ContextState schema.
-   [ ] Freeze RetrievalResult schema.
-   [ ] Viết mock fixtures cho cả 3 roles.
-   [ ] Xác nhận QueryFrame → Intent/Attribute/AnswerMode mapping.
-   [ ] Tạo 3 development branches.
-   [ ] Mỗi người chạy unit test bằng mock input trước khi integration.

------------------------------------------------------------------------

# 32. Chốt kiến trúc v1

Ba người có thể làm song song vì dependency được thay bằng contract:

``` text
Người 1
Raw Sentence
→ ParserResult
```

``` text
Người 2
ParserResult + ContextState
→ SemanticQuery
```

``` text
Người 3
SemanticQuery
→ RetrievalResult
→ Answer
```

Shared domain model:

``` text
COURSE
COURSE_PART
WEEK
CHAPTER
TOPIC
ASSIGNMENT
ASSIGNMENT_PART
DEADLINE
RESOURCE
REGULATION
LEARNING_OUTCOME
EXAM
INSTRUCTOR
```

Intent v1:

``` text
GET_COURSE_INFO
GET_SCHEDULE
GET_TOPIC
GET_ASSIGNMENT
GET_DEADLINE
GET_RESOURCE
GET_RULE
GET_INSTRUCTOR
GET_LO
UNKNOWN
```

Điểm quan trọng nhất của proposal là mọi thành viên cùng code trên **một
vocabulary và một contract đã freeze**, thay vì ba module chạy riêng rồi
đến cuối mới cố nối với nhau.

Sau khi ba module v1 tích hợp end-to-end thành công, nhóm mới chuyển
sang **data augmentation và evaluation**.
