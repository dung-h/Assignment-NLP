from src.answer.export import answer_to_line


def test_multiline_answer_exports_as_one_readable_line():
    answer = "Nội dung tuần 3:\n\n- CFG\n- Parsing\n\nNguồn: schedule:WEEK_03."
    assert answer_to_line(answer) == "Nội dung tuần 3: CFG; Parsing. Nguồn: schedule:WEEK_03."


def test_export_preserves_single_line_answer():
    answer = "Môn CO3085 có 3 tín chỉ. Nguồn: course_info:CO3085."
    assert answer_to_line(answer) == answer


def test_export_list_ending_in_punctuation_does_not_duplicate_it():
    assert answer_to_line("Các yêu cầu:\n\n- Nội dung A.\n- Nội dung B.") == "Các yêu cầu: Nội dung A.; Nội dung B."
