from pathlib import Path
import re
from src.semantics.normalizer import fold

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/raw'

def _section_value(text,key):
    m=re.search(rf'(?mi)^{re.escape(key)}:\s*(.+)$',text)
    return m.group(1).strip() if m else None

def _multiline(text,key,next_keys):
    pat=rf'(?ms)^{re.escape(key)}:\s*\n?(.*?)(?=^(?:{"|".join(map(re.escape,next_keys))}):|\Z)'
    m=re.search(pat,text); return ' '.join(m.group(1).split()) if m else None

class KnowledgeBase:
    def __init__(self):
        self.course={}; self.weeks={}; self.chapters={}; self.assignments={}; self.assignment_parts={}; self.regulations={}; self.resources={}; self.los={}; self.instructors={}
        self.load()
    def load(self):
        self._course(); self._schedule(); self._topics(); self._assignments(); self._regulations(); self._resources(); self._los()
    def _course(self):
        t=(DATA/'course_info.txt').read_text(encoding='utf-8')
        for k in ['course_id','course_name','course_name_en','semester','credits','ects','course_type','department','format','total_course_hours','lecture_hours','major_assignment_hours','self_study_hours']:
            v=_section_value(t,k)
            if v and k in {'credits','ects','total_course_hours','lecture_hours','major_assignment_hours','self_study_hours'}: v=int(re.search(r'\d+',v).group())
            self.course[k]=v
        self.course['description']=_multiline(t,'course_description',['Mục tiêu','main_parts','learning_outcomes'])
        m=re.search(r'(?ms)^main_parts:\s*(.*?)(?=^learning_outcomes:)',t)
        self.course['parts']=[x.strip() for x in m.group(1).splitlines() if x.strip()] if m else []
        ex=re.search(r'(?ms)^exam_format:\s*(.*)$',t)
        self.course['exams']={}
        if ex:
            for line in ex.group(1).splitlines():
                if ':' in line:
                    k,v=line.split(':',1); dur=re.search(r'(\d+) minutes',v)
                    self.course['exams'][k.strip().upper()]={'duration':int(dur.group(1)) if dur else None,'format':v.strip()}
        ass=re.search(r'(?ms)^assessment:\s*(.*?)(?=^exam_format:)',t)
        self.course['assessment']={}
        if ass:
            for line in ass.group(1).splitlines():
                if ':' in line:
                    k,v=line.split(':',1); self.course['assessment'][k.strip()]=v.strip()
    def _schedule(self):
        t=(DATA/'schedule.txt').read_text(encoding='utf-8')
        chunks=re.split(r'(?m)^WEEK\s+(\d+)\s*$',t)[1:]
        for i in range(0,len(chunks),2):
            n=int(chunks[i]); body=chunks[i+1]; wid=f'WEEK_{n:02d}'
            ch=re.search(r'(?mi)^chapter:\s*Chapter\s*(\d+)',body)
            topics=[]; tm=re.search(r'(?ms)^topics:\s*(.*?)(?=^(?:activity|milestone):|\Z)',body)
            if tm: topics=[x[2:].strip() for x in tm.group(1).splitlines() if x.strip().startswith('- ')]
            self.weeks[wid]={'chapter_ids':[f'CH{int(ch.group(1)):02d}'] if ch else [],'topics':topics,'activity':_section_value(body,'activity'),'milestone':_section_value(body,'milestone')}
    def _topics(self):
        t=(DATA/'topics.txt').read_text(encoding='utf-8')
        chunks=re.split(r'(?m)^CHAPTER\s+(\d+):\s*(.+)$',t)[1:]
        for i in range(0,len(chunks),3):
            num,title,body=chunks[i],chunks[i+1],chunks[i+2]; cid=f'CH{int(num):02d}'
            kw=_section_value(body,'keywords') or ''
            sm=_multiline(body,'summary',['subtopics']) or ''
            subs=[]; m=re.search(r'(?ms)^subtopics:\s*(.*?)(?=^CHAPTER|\Z)',body)
            if m: subs=[x.strip() for x in m.group(1).splitlines() if x.strip()]
            self.chapters[cid]={'title':title.strip(),'keywords':[x.strip() for x in kw.split(',') if x.strip()],'summary':sm,'subtopics':subs}
    def _assignments(self):
        t=(DATA/'assignments.txt').read_text(encoding='utf-8')
        self.assignments['BTL01']={'title':_section_value(t,'title'),'team_size':_section_value(t,'team_size'),'domain':_section_value(t,'domain'),'goal':_multiline(t,'goal',['PART I - Grammar and Parser'])}
        parts=[('BTL_PART_1','PART I - Grammar and Parser'),('BTL_PART_2','PART II - Semantic Interpretation and QA'),('BTL_PART_3','PART III - Local Discourse Context'),('BTL_PART_4','PART IV - Evaluation')]
        for idx,(pid,header) in enumerate(parts):
            start=t.find(header)
            if start<0: continue
            end=min([x for x in [t.find(h,start+1) for _,h in parts[idx+1:]]+[t.find('LLM/RAG EXTENSION',start+1)] if x>=0] or [len(t)])
            body=t[start:end]
            req=[]; outs=[]
            for line in body.splitlines():
                s=line.strip()
                if s.startswith('- '):
                    if 'output/' in s: outs.append(s[2:])
                    else: req.append(s[2:])
                elif s.startswith('output/'): outs.append(s)
            self.assignment_parts[pid]={'title':header,'requirements':req,'outputs':outs}
    def _regulations(self):
        t=(DATA/'regulations.txt').read_text(encoding='utf-8')
        mapping={'attendance':'ATTENDANCE','academic_integrity':'ACADEMIC_INTEGRITY','AI_usage':'AI_USAGE','source_code':'SOURCE_CODE','assignment_sharing':'ASSIGNMENT_SHARING','external_libraries':'EXTERNAL_LIBRARIES','LLM_RAG':'LLM_RAG','OUT_OF_SCOPE':'OUT_OF_SCOPE'}
        keys=list(mapping)
        for i,k in enumerate(keys):
            nexts=keys[i+1:] or ['__never__']; val=_multiline(t,k,nexts)
            if val: self.regulations[mapping[k]]=val
    def _resources(self):
        t=(DATA/'resources.txt').read_text(encoding='utf-8')
        chunks=re.split(r'(?m)^(TEXTBOOK|REFERENCE)\s+(\d+)\s*$',t)[1:]
        n=1
        for i in range(0,len(chunks),3):
            body=chunks[i+2]; rid=f'RES{n:02d}'; n+=1
            self.resources[rid]={'title':_section_value(body,'title'),'author':_section_value(body,'author') or _section_value(body,'authors'),'publisher':_section_value(body,'publisher'),'year':_section_value(body,'year'),'usage':_section_value(body,'usage')}
    def _los(self):
        t=(DATA/'course_info.txt').read_text(encoding='utf-8')
        for m in re.finditer(r'(?m)^(LO\d+(?:\.\d+)?)\s*-\s*(.+(?:\n\s+.+)?)',t): self.los[m.group(1)]=' '.join(m.group(2).split())
