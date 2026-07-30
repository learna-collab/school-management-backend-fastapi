import re

from app.schemas.parser import ParsedLesson
from app.services.alf_extractor import ALFExtractor
from app.services.document_reader import DocumentReader


class LessonParser:
    def __init__(self):
        self.reader = DocumentReader()
        self.alf = ALFExtractor()

    async def parse(
        self,
        file_path: str,
        week_number: int,
        lesson_day: str,
    ) -> ParsedLesson:
        raw_text = self.reader.read(file_path)

        text = raw_text.replace("\r", "")

        # -------------------------------------------------
        # EXTRACT TABLE VALUES
        # -------------------------------------------------
        subject = self._extract_table_value(text, "Subject")
        topic = self._extract_table_value(text, "Topic")

        objectives = self._extract_table_value(
            text,
            "Performance Objectives",
        )

        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------
        if subject and topic:
            title = f"{subject} – {topic}"
        else:
            title = topic or "Untitled Lesson"

        # -------------------------------------------------
        # TEACHER NOTES (KEY POINTS ONLY)
        # -------------------------------------------------
        teacher_notes = self._extract_between(
            text,
            "Key Points",
            "CLASS ACTIVITY",
        )

        if teacher_notes:
            teacher_notes = teacher_notes.strip()

        # -------------------------------------------------
        # COMPREHENSIVE NOTE
        # -------------------------------------------------
        comprehensive_note = self._extract_between(
            text,
            "COMPREHENSIVE TEACHER’S NOTE",
            "Key Points",
        )

        # -------------------------------------------------
        # CASE STUDY
        # -------------------------------------------------
        case_study = self._extract_between(
            text,
            "CASE STUDY",
            "Reflective Questions",
        )

        # -------------------------------------------------
        # EVALUATION
        # -------------------------------------------------
        evaluation = self._extract_between(
            text,
            "EVALUATION",
            "COMPREHENSIVE TEACHER’S NOTE",
        )

        # -------------------------------------------------
        # CLASS ACTIVITY
        # -------------------------------------------------
        project_based_learning = self._extract_between(
            text,
            "CLASS ACTIVITY",
            "Item | Details",
        )

        # -------------------------------------------------
        # INDEPENDENT READING
        # -------------------------------------------------
        independent_reading = text.strip()

        # -------------------------------------------------
        # BUILD ALF
        # -------------------------------------------------
        alf = self.alf.build(
            independent_reading=independent_reading,
            mini_lesson=comprehensive_note,
            case_study=case_study,
            project_based_learning=project_based_learning,
            evaluation=evaluation,
        )

        return ParsedLesson(
            week_number=week_number,
            lesson_day=lesson_day,
            title=title,
            topic=topic or "Untitled Lesson",
            objectives=objectives or "Performance objectives not extracted.",
            teacher_notes=teacher_notes,
            alf=alf,
        )

    # =====================================================
    # TABLE VALUE EXTRACTOR
    # Example:
    # Subject | Digital Literacy
    # =====================================================

    def _extract_table_value(self, text: str, label: str):
        pattern = rf"{re.escape(label)}\s*\|\s*(.+)"

        match = re.search(pattern, text, re.IGNORECASE)

        if not match:
            return None

        value = match.group(1).strip()

        return re.sub(r"\s+", " ", value)

    # =====================================================
    # GENERIC SECTION EXTRACTOR
    # =====================================================

    def _extract_between(
        self,
        text: str,
        start: str,
        end: str | None,
    ):
        # Normalize smart apostrophes for matching
        normalized = text.replace("’", "'")

        start = start.replace("’", "'")
        end = end.replace("’", "'") if end else None

        if end:
            pattern = (
                rf"{re.escape(start)}\s*"
                rf"(.*?)(?={re.escape(end)})"
            )
        else:
            pattern = rf"{re.escape(start)}\s*(.*)$"

        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE | re.DOTALL,
        )

        if not match:
            return None

        value = match.group(1).strip()

        # Keep line breaks instead of collapsing everything
        value = re.sub(r"\n\s*", "\n", value)

        return value.strip()
