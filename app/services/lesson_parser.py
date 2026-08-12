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

        # Keep HTML intact
        text = raw_text

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
        # TEACHER NOTES
        # -------------------------------------------------
        teacher_notes = self._extract_between(
            text,
            "Key Points",
            "CLASS ACTIVITY",
        )

        # -------------------------------------------------
        # MINI LESSON / COMPREHENSIVE NOTE
        # -------------------------------------------------
        comprehensive_note = self._extract_between(
            text,
            "COMPREHENSIVE TEACHER’S NOTE",
            "Key Points",
        )

        # -------------------------------------------------
        # CASE STUDY
        # Everything from CASE STUDY until EVALUATION
        # -------------------------------------------------
        case_study = self._extract_between(
            text,
            "CASE STUDY",
            "EVALUATION",
        )

        # Remove any leaked content before the CASE STUDY heading
        if case_study:
            match = re.search(
                r"((?:<h[1-6][^>]*>\s*)?CASE STUDY.*)",
                case_study,
                re.IGNORECASE | re.DOTALL,
            )
            if match:
                case_study = match.group(1).strip()

        # -------------------------------------------------
        # EVALUATION
        # Only the evaluation section
        # -------------------------------------------------
        evaluation = self._extract_between(
            text,
            "EVALUATION",
            "COMPREHENSIVE TEACHER’S NOTE",
        )

        if not evaluation:
            evaluation = self._extract_between(
                text,
                "EVALUATION",
                None,
            )

        # -------------------------------------------------
        # PROJECT BASED LEARNING / CLASS ACTIVITY
        # Only the CLASS ACTIVITY section
        # Exclude the table beginning with "Item | Details"
        # -------------------------------------------------
        project_based_learning = self._extract_between(
            text,
            "CLASS ACTIVITY",
            "Item | Details",
        )

        # Fallback if table heading is not present
        if not project_based_learning:
            project_based_learning = self._extract_between(
                text,
                "CLASS ACTIVITY",
                "CASE STUDY",
            )

        # Final fallback
        if not project_based_learning:
            project_based_learning = self._extract_between(
                text,
                "CLASS ACTIVITY",
                None,
            )

        # -------------------------------------------------
        # INDEPENDENT READING
        # Preserve full formatted HTML document
        # -------------------------------------------------
        independent_reading = raw_text.strip()

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
    # =====================================================

    def _extract_table_value(self, text: str, label: str):
        """
        Extract values from Mammoth-generated HTML tables.

        Handles nested tags such as:
        <tr>
            <td><p>Subject</p></td>
            <td><p>Digital Literacy</p></td>
        </tr>
        """
        pattern = (
            rf"<tr[^>]*>\s*"
            rf"<t[dh][^>]*>.*?{re.escape(label)}.*?</t[dh]>\s*"
            rf"<t[dh][^>]*>(.*?)</t[dh]>\s*"
            rf"</tr>"
        )

        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        if not match:
            return None

        value = match.group(1)

        # Remove all HTML tags inside the cell
        value = re.sub(r"<[^>]+>", " ", value)

        # Decode common HTML entities
        value = (
            value.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )

        # Normalize whitespace
        value = re.sub(r"\s+", " ", value).strip()

        return value or None

    # =====================================================
    # GENERIC SECTION EXTRACTOR
    # =====================================================

    def _extract_between(
        self,
        text: str,
        start: str,
        end: str | None,
    ):
        normalized = text.replace("’", "'")

        start = start.replace("’", "'")
        end = end.replace("’", "'") if end else None

        # Match HTML headings OR plain text headings
        start_pattern = (
            rf"(?:<h[1-6][^>]*>\s*{re.escape(start)}\s*</h[1-6]>|{re.escape(start)})"
        )

        if end:
            end_pattern = (
                rf"(?:<h[1-6][^>]*>\s*{re.escape(end)}\s*</h[1-6]>|{re.escape(end)})"
            )
            pattern = rf"{start_pattern}\s*(.*?)(?={end_pattern})"
        else:
            pattern = rf"{start_pattern}\s*(.*)$"

        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE | re.DOTALL,
        )

        if not match:
            return None

        value = match.group(1).strip()

        return value
