"""Deterministic, grounded rendering for Person 3 retrieval results."""

from __future__ import annotations

import re


OUT_OF_SCOPE_ANSWER = "Xin lỗi, câu hỏi này nằm ngoài phạm vi Course Assistant hiện tại."


class AnswerGenerationError(ValueError):
    """The answer input violates the Person 3 rendering contract."""


class AnswerGenerator:
    """Render a validated retrieval result without performing retrieval.

    ``kb`` is optional for compatibility with the original two-argument v0
    API.  When supplied, it is read only for display labels of IDs already
    present in ``retrieval.values``; it is never used to discover more facts.
    """

    def generate(self, query, retrieval, kb=None):
        if query.intent == "UNKNOWN":
            raise AnswerGenerationError(
                "UNKNOWN must be rendered by the orchestration layer"
            )
        self._validate_retrieval(retrieval)

        if retrieval.status == "NOT_FOUND":
            return self._not_found_message(query)

        if query.answer_mode == "BOOLEAN":
            if not isinstance(retrieval.values[0], bool):
                raise AnswerGenerationError(
                    "BOOLEAN answers require a boolean retrieval value"
                )
            answer = "Có." if retrieval.values[0] is True else "Không."
            return self._with_sources(answer, retrieval.sources)

        display_values = [
            self._display_value(query, value, kb) for value in retrieval.values
        ]
        answer = self._render_found(query, display_values)
        return self._with_sources(answer, retrieval.sources)

    @staticmethod
    def _validate_retrieval(retrieval):
        if retrieval.status not in {"FOUND", "NOT_FOUND"}:
            raise AnswerGenerationError(
                f"Unsupported retrieval status: {retrieval.status!r}"
            )
        if not isinstance(retrieval.values, list) or not isinstance(
            retrieval.sources, list
        ):
            raise AnswerGenerationError("Retrieval values and sources must be lists")
        if retrieval.status == "FOUND" and not retrieval.values:
            raise AnswerGenerationError("FOUND retrieval must contain values")
        if retrieval.status == "NOT_FOUND" and (
            retrieval.values or retrieval.sources
        ):
            raise AnswerGenerationError("NOT_FOUND retrieval must be empty")
        if any(value is None or value == "" for value in retrieval.values):
            raise AnswerGenerationError("Retrieval cannot contain missing values")

    @staticmethod
    def _not_found_message(query):
        if query.intent == "GET_INSTRUCTOR":
            return "Tôi không tìm thấy thông tin giảng viên trong dữ liệu môn học hiện tại."
        if query.intent == "GET_DEADLINE":
            return (
                "Tôi hiểu đây là câu hỏi về deadline, nhưng dữ liệu mẫu hiện tại "
                "không có deadline chính thức tương ứng."
            )
        return "Xin lỗi, tôi không tìm thấy thông tin này trong dữ liệu môn học hiện tại."

    def _render_found(self, query, values):
        key = (query.intent, query.attribute, query.answer_mode)
        if key == ("GET_COURSE_INFO", "credits", "VALUE"):
            return f"Môn CO3085 có {values[0]} tín chỉ."
        if key == ("GET_COURSE_INFO", "duration", "VALUE") and "exam" in query.entities:
            return f"{query.entities['exam'][0]} có thời lượng {values[0]} phút."
        if key == ("GET_TOPIC", "chapter", "LIST"):
            return "Nội dung này được tìm thấy ở: " + ", ".join(values) + "."
        if key == ("GET_SCHEDULE", "week", "LIST"):
            return "Được học ở: " + ", ".join(values) + "."
        if key == ("GET_RESOURCE", "resource", "LIST"):
            return "Tài liệu phù hợp: " + "; ".join(values) + "."
        if key == ("GET_TOPIC", "summary", "VALUE"):
            subject = self._query_subject(query)
            return f"Tóm tắt {subject}: {self._sentence(values[0])}"
        if key == ("GET_TOPIC", "title", "VALUE"):
            subject = self._query_subject(query)
            return f"Tên của {subject} là {self._sentence(values[0])}"
        if key == ("GET_LO", "description", "VALUE"):
            outcome_id = (query.entities.get("learning_outcome") or ["LO"])[0]
            return f"Mô tả {outcome_id}: {self._sentence(values[0])}"
        if query.answer_mode == "LIST":
            return "; ".join(values) + "."
        return str(values[0])

    @staticmethod
    def _sentence(value):
        text = str(value).strip()
        return text if text.endswith((".", "!", "?")) else f"{text}."

    @staticmethod
    def _query_subject(query):
        chapter_id = (query.entities.get("chapter") or [None])[0]
        return chapter_id or "nội dung được hỏi"

    def _display_value(self, query, value, kb):
        """Resolve presentation metadata for this value only.

        No index or relation is traversed here.  If the value is not a known
        displayable ID, its retrieved representation is returned unchanged.
        """

        rendered = str(value)
        if kb is None:
            return rendered

        if query.intent == "GET_TOPIC" and query.attribute == "chapter":
            chapter = kb.chapters.get(rendered)
            if chapter:
                number = self._numeric_suffix(rendered)
                return f"{rendered} (Chương {number} – {chapter['title']})"

        if query.intent == "GET_SCHEDULE" and query.attribute == "week":
            week = kb.weeks.get(rendered)
            if week:
                return f"{rendered} (Tuần {week['week_number']})"

        if query.intent == "GET_ASSIGNMENT" and query.attribute == "parts":
            part = kb.assignment_parts.get(rendered)
            if part:
                return f"{rendered} ({part['title']})"

        return rendered

    @staticmethod
    def _numeric_suffix(identifier):
        match = re.search(r"(\d+)$", identifier)
        return str(int(match.group(1))) if match else identifier

    @staticmethod
    def _with_sources(answer, sources):
        if not sources:
            return answer
        return f"{answer} Nguồn: {', '.join(sources)}."
