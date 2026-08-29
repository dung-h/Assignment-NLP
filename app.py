import argparse, json, sys
from src.assistant import CourseAssistant


def _configure_console_encoding():
    """Keep Vietnamese CLI/demo output usable on Windows consoles and pipes."""

    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

def build_ui(bot=None):
    import gradio as gr
    bot = bot or CourseAssistant()
    def run(q):
        out=bot.ask(q)
        return out['answer'], out['person_1_parser_result'], out['person_2_semantic_query'], out['context_state'], out['person_3_retrieval_result']
    def reset():
        bot.reset_context(); return 'Đã reset context.', {}, {}, {}, {}
    with gr.Blocks(title='NLP Course Assistant v0') as demo:
        gr.Markdown('# NLP Course Assistant v0\n**Person 1 → Person 2 → Person 3**. UI này cố ý expose toàn bộ contract trung gian.')
        q=gr.Textbox(label='User question',value='Chương nào nói về CFG?')
        with gr.Row(): ask=gr.Button('Ask',variant='primary'); rst=gr.Button('Reset context')
        ans=gr.Textbox(label='Final answer')
        with gr.Row():
            p=gr.JSON(label='Person 1 — ParserResult'); s=gr.JSON(label='Person 2 — SemanticQuery')
        with gr.Row():
            c=gr.JSON(label='ContextState'); r=gr.JSON(label='Person 3 — RetrievalResult')
        ask.click(run,q,[ans,p,s,c,r]); q.submit(run,q,[ans,p,s,c,r]); rst.click(reset,None,[ans,p,s,c,r])
    return demo

def main():
    _configure_console_encoding()
    ap=argparse.ArgumentParser(); ap.add_argument('--cli'); ap.add_argument('--demo',action='store_true'); args=ap.parse_args()
    bot=CourseAssistant()
    if args.cli:
        print(json.dumps(bot.ask(args.cli),ensure_ascii=False,indent=2)); return
    if args.demo:
        for q in ['Môn NLP có bao nhiêu tín chỉ?','Tuần 3 học gì?','Chương nào nói về CFG?','Có được dùng LLM/RAG không?','Ai dạy môn NLP?']:
            print('\n###',q); print(json.dumps(bot.ask(q),ensure_ascii=False,indent=2))
        return
    build_ui(bot).launch(server_name='127.0.0.1')
if __name__=='__main__': main()
