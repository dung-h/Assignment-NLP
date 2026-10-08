import re, unicodedata

def fold(s):
    s=s.lower().strip()
    s=''.join(c for c in unicodedata.normalize('NFD',s) if unicodedata.category(c)!='Mn')
    return re.sub(r'\s+',' ',s)

TOPIC_ALIASES = {
 'cfg':'CFG','context-free grammar':'CFG','context free grammar':'CFG',
 'pcfg':'PCFG','probabilistic context-free grammar':'PCFG',
 'parsing':'PARSING','parser':'PARSING',
 'semantic grammar':'SEMANTIC_GRAMMAR','reference':'REFERENCE',
 'question answering':'QUESTION_ANSWERING','hoi dap':'QUESTION_ANSWERING',
 'hoi đap':'QUESTION_ANSWERING',
 'selectional restriction':'SELECTIONAL_RESTRICTION',
 'statistical nlp':'STATISTICAL_NLP','python nlp':'PYTHON_NLP','rag':'RAG'
}
REG_ALIASES = {
 'llm/rag':'LLM_RAG','dung llm/rag':'LLM_RAG',
 'su dung ai':'AI_USAGE','ai':'AI_USAGE','dung ai':'AI_USAGE',
 'source code':'SOURCE_CODE','thu vien ngoai':'EXTERNAL_LIBRARIES',
 'dung thu vien ngoai':'EXTERNAL_LIBRARIES','chia se giua cac nhom':'ASSIGNMENT_SHARING'
}

def canonical(slot, value):
    f=fold(value)
    if slot=='course': return 'CO3085' if f in {'nlp','co3085','mon nlp'} else value
    if slot=='week':
        m=re.search(r'(\d+)',f); return f'WEEK_{int(m.group(1)):02d}' if m else value
    if slot=='chapter':
        m=re.search(r'(\d+)',f); return f'CH{int(m.group(1)):02d}' if m else value
    if slot=='assignment': return 'BTL01' if ('bai tap lon' in f or 'btl' in f) else value
    if slot=='assignment_part':
        roman={'i':1,'ii':2,'iii':3,'iv':4}
        m=re.search(r'phan\s*(i{1,3}|iv|[1-4])',f)
        if m:
            n=roman.get(m.group(1), int(m.group(1)) if m.group(1).isdigit() else None)
            return f'BTL_PART_{n}'
    if slot=='topic': return TOPIC_ALIASES.get(f, value.upper().replace(' ','_'))
    if slot == 'regulation':
        # Sort alias dài trước để tránh match nhầm alias ngắn
        ordered = sorted(REG_ALIASES.items(), key=lambda x: len(x[0]), reverse=True)
        for k, v in ordered:
            if re.search(rf"(?:^|\s){re.escape(k)}(?:$|\s)", f):
                return v
        return value.upper().replace(' ', '_')
    if slot=='learning_outcome':
        m=re.search(r'(\d+(?:\.\d+)?)',f); return 'LO'+m.group(1) if m else value
    if slot=='exam': return f.upper()
    return value
