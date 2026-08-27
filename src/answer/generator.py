class AnswerGenerator:
    def generate(self,q,r):
        if q.intent=='UNKNOWN': return 'Xin lỗi, câu hỏi này nằm ngoài phạm vi Course Assistant hiện tại.'
        if r.status=='NOT_FOUND':
            if q.intent=='GET_INSTRUCTOR': return 'Tôi không tìm thấy thông tin giảng viên trong dữ liệu môn học hiện tại.'
            if q.intent=='GET_DEADLINE': return 'Tôi hiểu đây là câu hỏi về deadline, nhưng dữ liệu mẫu hiện tại không có deadline chính thức tương ứng.'
            return 'Xin lỗi, tôi không tìm thấy thông tin này trong dữ liệu môn học hiện tại.'
        v=r.values
        if q.answer_mode=='BOOLEAN': return ('Có.' if bool(v[0]) else 'Không.') + (f' Nguồn: {", ".join(r.sources)}.' if r.sources else '')
        if q.intent=='GET_TOPIC' and q.attribute=='chapter': return 'Nội dung này được tìm thấy ở: ' + ', '.join(v) + '.'
        if q.intent=='GET_SCHEDULE' and q.attribute=='week': return 'Được học ở: ' + ', '.join(v) + '.'
        if q.intent=='GET_COURSE_INFO' and q.attribute=='credits': return f'Môn CO3085 có {v[0]} tín chỉ.'
        if q.intent=='GET_COURSE_INFO' and 'exam' in q.entities and q.attribute=='duration': return f"{q.entities['exam'][0]} có thời lượng {v[0]} phút."
        if q.intent=='GET_RESOURCE': return 'Tài liệu phù hợp: ' + '; '.join(map(str,v)) + '.'
        if q.answer_mode=='LIST': return '; '.join(map(str,v))
        return str(v[0])
