import argparse, json, sys, os
import copy
import html
from src.assistant import CourseAssistant
from src.syntax.generator import generate


def _configure_console_encoding():
    """Keep Vietnamese CLI/demo output usable on Windows consoles and pipes."""

    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

UI_CSS = """
html, body {background:#fff !important; color-scheme:light;}
.gradio-container {max-width: 1600px !important; margin: 0 auto !important;
 background: #fff !important; color: #222a33 !important;
 --body-text-color: #222a33; --body-text-color-subdued: #697585;
 --background-fill-primary: #fff; --background-fill-secondary: #f6f7f8;
 --block-background-fill: #fff; --input-background-fill: #fff;
 --block-label-text-color: #485868; --block-label-background-fill: #fff;
 --border-color-primary: #e4e7eb; --button-primary-background-fill: #143f69;
 --button-primary-background-fill-hover: #0c3153;}
.gradio-container .prose, .gradio-container .prose h2,
.gradio-container .prose p, .gradio-container label,
.gradio-container label span {color: #28323c !important;}
#sidebar {background: #f4f6f7; border-right: 1px solid #e7eaed;
          border-radius: 12px; padding: 24px 18px; min-height: 720px;
          max-height: calc(100vh - 32px); overflow-y: auto;
          overflow-x: hidden; flex-wrap: nowrap !important;}
#sidebar > * {flex-shrink: 0;}
#sidebar .brand-mark {display:inline-flex; align-items:center; justify-content:center;
 background:#183e60; color:#fff; width:34px; height:34px; border-radius:10px;
 font-weight:700; font-size:14px; margin-right:9px;}
#sidebar .brand {display:flex; align-items:center; color:#1d2c3a; font-size:15px; font-weight:700;}
#sidebar .caption {margin: 32px 0 8px; color:#72808e; font-size:11px;
 text-transform:uppercase; letter-spacing:.08em; font-weight:700;}
#sidebar .course {padding:12px; background:#e9eef1; border-radius:9px; color:#253f50; font-size:13px;}
#sidebar .course strong {display:block; margin-bottom:4px;}
#sidebar .hint {margin-top:24px; color:#687987; font-size:12px; line-height:1.5;}
#conversation {padding: 12px 28px 24px;}
#topbar {display:flex; justify-content:space-between; align-items:center;
 padding:11px 0 17px; border-bottom:1px solid #edf0f2; color:#253544;}
#topbar strong {font-size:15px;}
#topbar .scope {font-size:11px; padding:5px 9px; background:#f1f5f6;
 border:1px solid #e2eaec; border-radius:20px; color:#526a70;}
#chat-history {border:0 !important; box-shadow:none !important; background:white !important;}
#chat-history .placeholder {color:#506273 !important;}
#chat-history .panel.user-row, #chat-history .panel .user {
 background:#edf3f7 !important; color:#222a33 !important;
}
#chat-history .panel.bot-row, #chat-history .panel .bot {
 background:#f7f8f9 !important; color:#222a33 !important;
}
#chat-history .message .prose, #chat-history .message .prose p {
 color:#222a33 !important; opacity:1 !important;
}
#question-input {border:1px solid #dfe4e7 !important; border-radius:16px !important;
 box-shadow:0 4px 20px rgba(28,45,60,.05);}
#question-input textarea,
#question-input textarea:hover,
#question-input textarea:focus {
 background:#fff !important; color:#222a33 !important;
 caret-color:#143f69; font-size:15px !important; color-scheme:light;
}
#question-input textarea::placeholder {color:#697585 !important; opacity:1;}
#raw-details button, #raw-details button span, #analysis-details button,
#analysis-details button span {color:#304150 !important;}
.pipeline-card {background:#f7f9fa; border:1px solid #e8edef; border-radius:10px;
 padding:12px 15px; margin-bottom:8px; color:#293b48;}
.pipeline-card .step {font-size:11px; color:#58768a; font-weight:700; letter-spacing:.06em;}
.pipeline-card h3 {margin:4px 0 7px; font-size:14px; color:#293b48 !important;}
.pipeline-card p {margin:4px 0; overflow-wrap:anywhere; font-size:13px; color:#293b48 !important;}
.pipeline-card pre {white-space:pre; overflow-x:auto; font-size:12px; line-height:1.5;
 padding:10px; background:#fff; border-radius:6px; color:#293b48;}
.badge {display:inline-block; border-radius:999px; padding:3px 9px; font-size:11px; font-weight:700;}
.found {background:#e6f3ed; color:#21624c;}
.not-found {background:#fff2d7; color:#87560f;}
.unknown {background:#f1e8ff; color:#643a95;}
.idle {background:#edf2f8; color:#526475;}
@media(max-width: 700px) {
 .gradio-container {padding:0 !important;}
 #app-shell {flex-direction:column !important;}
 #sidebar, #conversation {width:100% !important; flex:1 1 100% !important;}
 #sidebar {min-width:0 !important; min-height:auto; max-height:none; padding:14px;}
 #sidebar .hint {display:none;} #sidebar .caption {margin-top:14px;}
 #conversation {min-width:0 !important; padding:8px 10px;}
 #chat-history, #question-input {min-width:0 !important;}
 #topbar {gap:8px; flex-wrap:wrap;}
}
"""


def presentation_state(result):
    """Return a display model for an assistant output, or the idle model for None.

    UNKNOWN is semantic, so its placeholder retrieval is never presented as a
    real lookup. The original result is not changed.
    """
    if result is None:
        return {"status": "IDLE", "label": "Chưa có câu hỏi", "detail": "Kết quả tra cứu sẽ xuất hiện ở đây."}
    semantic = result.get("person_2_semantic_query") or {}
    retrieval = result.get("person_3_retrieval_result") or {}
    if semantic.get("intent") == "UNKNOWN":
        return {"status": "UNKNOWN", "label": "Chưa diễn giải được", "detail": "Chưa tra cứu cơ sở tri thức."}
    if retrieval.get("status") == "FOUND":
        return {"status": "FOUND", "label": "Đã tìm thấy", "detail": "Đã tìm thấy dữ liệu trong cơ sở tri thức."}
    if retrieval.get("status") == "NOT_FOUND":
        return {"status": "NOT_FOUND", "label": "Không tìm thấy", "detail": "Đã tra cứu nhưng dữ liệu mẫu không có thông tin phù hợp."}
    return {"status": "IDLE", "label": "Chưa tra cứu", "detail": "Chưa có kết quả tra cứu."}


def pipeline_html(result):
    """Render escaped, deterministic pipeline explanation HTML for result or None."""
    state = presentation_state(result)
    result = result or {}
    parser = result.get("person_1_parser_result") or {}
    semantic = result.get("person_2_semantic_query") or {}
    retrieval = result.get("person_3_retrieval_result") or {}
    esc = lambda value: html.escape(str(value), quote=True)
    intent = esc(semantic.get("intent") or "Chưa có")
    entities = esc(json.dumps(semantic.get("entities", {}), ensure_ascii=False, sort_keys=True))
    attribute = esc(semantic.get("attribute") or "—")
    frame = esc(parser.get("query_frame") or "—")
    slots = esc(json.dumps(parser.get("slots", {}), ensure_ascii=False, sort_keys=True))
    sentence_type = esc(parser.get("sentence_type") or "—")
    tree = esc(parser.get("tree") or "Chưa có cây cú pháp.")
    parser_status = "Đã nhận diện" if parser.get("valid") else ("Chưa nhận diện" if parser else "Chưa có câu hỏi")
    classes = {"IDLE": "idle", "UNKNOWN": "unknown", "FOUND": "found", "NOT_FOUND": "not-found"}
    sources = retrieval.get("sources", []) if state["status"] == "FOUND" else []
    source_text = esc(", ".join(map(str, sources))) if sources else "—"
    values = retrieval.get("values", []) if state["status"] == "FOUND" else []
    value_text = esc(json.dumps(values, ensure_ascii=False)) if values else "—"
    return (
        '<div class="pipeline-card"><div class="step">01 · PARSER</div>'
        f'<h3>Phân tích cú pháp</h3><p>{esc(parser_status)} · Khung: {frame}</p>'
        f'<p>Loại câu: {sentence_type}</p><p>Thông tin trích xuất: {slots}</p>'
        f'<p>Cây cú pháp:</p><pre>{tree}</pre></div>'
        '<div class="pipeline-card"><div class="step">02 · NGỮ NGHĨA</div>'
        f'<h3>Diễn giải yêu cầu</h3><p>Ý định: <strong>{intent}</strong></p>'
        f'<p>Thực thể: {entities}</p><p>Thuộc tính: {attribute}</p></div>'
        '<div class="pipeline-card"><div class="step">03 · KNOWLEDGE BASE</div>'
        f'<h3>Tra cứu &amp; trả lời</h3><span class="badge {classes[state["status"]]}">{esc(state["label"])}</span>'
        f'<p>{esc(state["detail"])}</p><p>Giá trị: {value_text}</p><p>Nguồn: {source_text}</p></div>'
    )


def append_turn(history, question, result):
    """Return a new Gradio messages history with this question and answer appended."""
    return list(history or []) + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": result["answer"]},
    ]


def new_session(bot=None):
    """Create an isolated assistant; an optional bot is copied as a template."""
    session = copy.deepcopy(bot) if bot is not None else CourseAssistant()
    if bot is not None and callable(getattr(session, "reset_context", None)):
        session.reset_context()
    return session


def suggested_questions():
    """Select reviewed, standalone prompts from the current grammar output."""
    examples = set(generate())
    selected = (
        'Môn NLP có bao nhiêu tín chỉ?',
        'Tuần 3 học gì?',
        'Chương nào nói về CFG?',
        'Phần I của bài tập lớn yêu cầu gì?',
        'Bài tập lớn là gì?',
        'Có được dùng LLM/RAG không?',
        'Tài liệu nào nói về statistical NLP?',
        'Giảng viên NLP là ai?',
    )
    return [question for question in selected if question in examples]


def build_ui(bot=None):
    """Build the Gradio UI; a supplied bot is a per-session template."""
    import gradio as gr

    def run(question, history, session):
        if not question or not question.strip():
            return (history, question, gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), session)
        session = session if session is not None else new_session(bot)
        result = session.ask(question.strip())
        return (append_turn(history, question.strip(), result), "", pipeline_html(result),
                result['person_1_parser_result'], result['person_2_semantic_query'],
                result['context_state'], result['person_3_retrieval_result'], session)

    def reset():
        return [], "", pipeline_html(None), {}, {}, {}, {}, None

    with gr.Blocks(title='CO3085 · Trợ lý môn học', analytics_enabled=False) as demo:
        session = gr.State(None)
        with gr.Row(elem_id='app-shell'):
            with gr.Column(scale=3, min_width=280, elem_id='sidebar'):
                gr.HTML('<div class="brand"><span class="brand-mark">N</span><span>Course Assistant</span></div>'
                        '<div class="caption">Môn học</div><div class="course"><strong>CO3085</strong>'
                        'Xử lý ngôn ngữ tự nhiên</div>')
                rst = gr.Button('＋  Hội thoại mới')
                with gr.Accordion('Các bước xử lý câu hỏi gần nhất', open=True, elem_id='analysis-details'):
                    explanation = gr.HTML(pipeline_html(None))
                    gr.Markdown('Dữ liệu đầy đủ của câu hỏi gần nhất:')
                    parser = gr.JSON(label='Kết quả phân tích cú pháp')
                    semantic = gr.JSON(label='Truy vấn ngữ nghĩa')
                    context = gr.JSON(label='Ngữ cảnh hội thoại')
                    retrieval = gr.JSON(label='Kết quả truy xuất')
                    gr.Markdown('Nếu chưa diễn giải được câu hỏi, kết quả truy xuất rỗng chỉ giữ cấu trúc; hệ thống chưa tra cứu KB.')
                gr.HTML('<div class="hint">Dữ liệu môn học là dữ liệu mẫu phục vụ bài tập lớn, '
                        'không phải thông báo hành chính.</div>')
            with gr.Column(scale=7, min_width=280, elem_id='conversation'):
                gr.HTML('<div id="topbar"><strong>Trợ lý môn học</strong><span class="scope">CO3085 · Dữ liệu mẫu</span></div>')
                history = gr.Chatbot(label='Hội thoại', show_label=False, height=470, layout='panel',
                                     buttons=['copy'], elem_id='chat-history',
                                     placeholder='<h2>Hỏi về môn học</h2><p>Ví dụ: Chương nào nói về CFG?</p>')
                with gr.Row():
                    question = gr.Textbox(label='Câu hỏi', show_label=False, placeholder='Nhập câu hỏi về môn học…',
                                          lines=1, scale=8, elem_id='question-input')
                    ask = gr.Button('Gửi', variant='primary', scale=1, min_width=75)
                gr.Examples(examples=[[item] for item in suggested_questions()],
                            inputs=question, label='Câu hỏi gợi ý')
        outputs = [history, question, explanation, parser, semantic, context, retrieval, session]
        ask.click(run, [question, history, session], outputs)
        question.submit(run, [question, history, session], outputs)
        rst.click(reset, None, outputs)
    return demo

def main():
    _configure_console_encoding()
    ap=argparse.ArgumentParser(); ap.add_argument('--cli'); ap.add_argument('--demo',action='store_true'); ap.add_argument('--export-outputs', action='store_true'); args=ap.parse_args()
    if args.export_outputs:
        from src.output_export import export_outputs
        print(f'Đã xuất kết quả cho {export_outputs()} câu hỏi.')
        return
    bot=CourseAssistant()
    if args.cli:
        print(json.dumps(bot.ask(args.cli),ensure_ascii=False,indent=2)); return
    if args.demo:
        for q in ['Môn NLP có bao nhiêu tín chỉ?','Tuần 3 học gì?','Chương nào nói về CFG?','Có được dùng LLM/RAG không?','Ai dạy môn NLP?']:
            print('\n###',q); print(json.dumps(bot.ask(q),ensure_ascii=False,indent=2))
        return
    build_ui().launch(server_name=os.environ.get('GRADIO_SERVER_NAME', '127.0.0.1'), css=UI_CSS)
if __name__=='__main__': main()
