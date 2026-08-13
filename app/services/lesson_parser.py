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
        # EXTRACT BASIC FIELDS (TABLE FORMAT OR LABEL FORMAT)
        # -------------------------------------------------
        subject = self._extract_field(text, "Subject")
        topic = self._extract_field(text, "Topic")

        objectives = self._extract_field(
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
        teacher_notes = self._extract_section(
            text,
            start_keywords=["Key Points"],
            end_keywords=[
                "CLASS ACTIVITY",
                "Practical Classroom Activities",
                "CASE STUDY",
                "EVALUATION",
            ],
        )

        # -------------------------------------------------
        # MINI LESSON / COMPREHENSIVE NOTE
        # -------------------------------------------------

        # First priority: extract the full COMPREHENSIVE TEACHER'S NOTE section
        comprehensive_note = self._extract_section(
            text,
            start_keywords=[
                "COMPREHENSIVE TEACHER’S NOTE",
                "COMPREHENSIVE TEACHER'S NOTE",
                "COMPREHENSIVE NOTE",
            ],
            end_keywords=[],  # capture until the end of the document
        )

        # Fallback: instructional table format only if no comprehensive note exists
        if not comprehensive_note:
            comprehensive_note = self._extract_table_phase(
                text, phase_name="Mini Lesson"
            ) or self._extract_table_phase(text, phase_name="Mini-Lesson")

        # -------------------------------------------------
        # CASE STUDY
        # -------------------------------------------------

        case_study = self._extract_heading_section(
            text,
            heading="CASE STUDY",
            end_keywords=[
                "EVALUATION",
                "COMPREHENSIVE TEACHER’S NOTE",
                "COMPREHENSIVE TEACHER'S NOTE",
                "Practical Classroom Activities",
                "CLASS ACTIVITY",
            ],
        )

        # -------------------------------------------------
        # EVALUATION
        # -------------------------------------------------
        evaluation = self._extract_section(
            text,
            start_keywords=["EVALUATION"],
            end_keywords=[
                "COMPREHENSIVE TEACHER’S NOTE",
                "COMPREHENSIVE TEACHER'S NOTE",
                "MINI LESSON",
            ],
        )

        if not evaluation:
            evaluation = self._extract_section(
                text,
                start_keywords=["EVALUATION"],
                end_keywords=[],
            )

        # -------------------------------------------------
        # PROJECT BASED LEARNING / CLASS ACTIVITY
        # -------------------------------------------------

        # Preferred headings (Format 1)
        project_based_learning = self._extract_section(
            text,
            start_keywords=[
                "Practical Classroom Activities",
                "CLASS ACTIVITY",
            ],
            end_keywords=[
                "Item | Details",
                "CASE STUDY",
                "EVALUATION",
                "COMPREHENSIVE TEACHER’S NOTE",
                "COMPREHENSIVE TEACHER'S NOTE",
            ],
        )

        # Fallback headings (Format 1 variants)
        if not project_based_learning:
            project_based_learning = self._extract_section(
                text,
                start_keywords=[
                    "Practical Classroom Activities",
                    "CLASS ACTIVITY",
                ],
                end_keywords=["CASE STUDY"],
            )

        # Final heading fallback
        if not project_based_learning:
            project_based_learning = self._extract_section(
                text,
                start_keywords=[
                    "Practical Classroom Activities",
                    "CLASS ACTIVITY",
                ],
                end_keywords=[],
            )

        # -------------------------------------------------
        # DEFAULT TO TABLE EXTRACTION IF NO HEADING SECTION
        # -------------------------------------------------
        if not project_based_learning:
            project_based_learning = self._extract_table_project_based_learning(text)
        # -------------------------------------------------
        # INDEPENDENT READING
        # Preserve full formatted HTML document
        # -------------------------------------------------
        independent_reading = "Pupils should consult the school-approved textbook and read the relevant topic for further understanding."

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
    # UNIVERSAL FIELD EXTRACTOR
    # =====================================================

    def _extract_field(self, text: str, label: str):
        # Try table extraction first
        value = self._extract_table_value(text, label)
        if value:
            return value

        normalized = text.replace("’", "'")
        label_normalized = label.replace("’", "'")

        pattern = (
            rf"{re.escape(label_normalized)}\s*[:\-]\s*(.+?)"
            rf"(?=<br|</p>|</div>|\n|<h[1-6]|$)"
        )

        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE | re.DOTALL,
        )

        if not match:
            return None

        value = match.group(1)

        value = re.sub(r"<[^>]+>", " ", value)

        value = (
            value.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )

        value = re.sub(r"\s+", " ", value).strip()

        return value or None

    # =====================================================
    # TABLE VALUE EXTRACTOR
    # =====================================================

    def _extract_table_value(self, text: str, label: str):
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

        value = re.sub(r"<[^>]+>", " ", value)

        value = (
            value.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )

        value = re.sub(r"\s+", " ", value).strip()

        return value or None

    # =====================================================
    # UNIVERSAL SECTION EXTRACTOR
    # =====================================================

    def _extract_section(
        self,
        text: str,
        start_keywords: list[str],
        end_keywords: list[str],
    ):
        normalized = text.replace("’", "'")

        start_parts = []
        for keyword in start_keywords:
            keyword = keyword.replace("’", "'")
            start_parts.append(
                rf"(?:<h[1-6][^>]*>\s*{re.escape(keyword)}\s*</h[1-6]>|{re.escape(keyword)})"
            )

        start_pattern = "|".join(start_parts)

        if end_keywords:
            end_parts = []
            for keyword in end_keywords:
                keyword = keyword.replace("’", "'")
                end_parts.append(
                    rf"(?:<h[1-6][^>]*>\s*{re.escape(keyword)}\s*</h[1-6]>|{re.escape(keyword)})"
                )

            end_pattern = "|".join(end_parts)

            pattern = rf"(?:{start_pattern})\s*(.*?)(?=(?:{end_pattern}))"
        else:
            pattern = rf"(?:{start_pattern})\s*(.*)$"

        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE | re.DOTALL,
        )

        if not match:
            return None

        return match.group(1).strip()

    # =====================================================
    # EXTRACT CONTENT FROM INSTRUCTIONAL TABLE PHASE
    # =====================================================

    def _extract_table_phase(self, text: str, phase_name: str):
        pattern = (
            rf"{re.escape(phase_name)}\s*</p>.*?"
            rf"Guided Instruction\s*</p>.*?"
            rf"(.*?)</p>"
        )

        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.DOTALL,
        )

        if not match:
            return None

        value = match.group(1)

        value = re.sub(r"<[^>]+>", " ", value)
        value = value.replace("&nbsp;", " ")
        value = re.sub(r"\s+", " ", value).strip()

        return value or None

    # =====================================================
    # HEADING-ONLY SECTION EXTRACTOR
    # Works for BOTH:
    #   <h2>CASE STUDY</h2>
    #   CASE STUDY
    # Prevents extracting table labels such as:
    #   <td>Case Study</td>
    # =====================================================

    # =====================================================
    # CASE STUDY EXTRACTOR
    # Extracts only the real CASE STUDY section and ignores
    # table rows such as "Case Study / Analysis"
    # =====================================================

    def _extract_heading_section(
        self,
        text: str,
        heading: str,
        end_keywords: list[str],
    ):
        normalized = text.replace("’", "'")

        # Remove table rows that contain "Case Study"
        normalized = re.sub(
            r"<tr[^>]*>.*?Case Study.*?</tr>",
            "",
            normalized,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Match either:
        #   CASE STUDY
        #   <h1>CASE STUDY</h1>
        start_pattern = (
            rf"(?:<h[1-6][^>]*>\s*{re.escape(heading)}\s*</h[1-6]>"
            rf"|{re.escape(heading)})"
        )

        end_parts = []
        for k in end_keywords:
            k = k.replace("’", "'")
            end_parts.append(
                rf"(?:<h[1-6][^>]*>\s*{re.escape(k)}\s*</h[1-6]>|{re.escape(k)})"
            )

        end_pattern = "|".join(end_parts)

        pattern = rf"{start_pattern}\s*(.*?)(?=(?:{end_pattern})|$)"

        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE | re.DOTALL,
        )

        if not match:
            return None

        value = match.group(1).strip()

        return value or None
        # =====================================================

    # EXTRACT PROJECT-BASED LEARNING FROM INSTRUCTIONAL TABLE
    # =====================================================

    def _extract_table_project_based_learning(self, text: str):
        pattern = (
            r"Project(?:￾|-)?Based\s+Learning.*?"
            r"(?:Practical Activity|Project|Group / Individual\s+Project)\s*</p>.*?"
            r"(.*?)</p>"
        )

        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.DOTALL,
        )

        if not match:
            return None

        value = match.group(1)

        # Remove HTML tags
        value = re.sub(r"<[^>]+>", " ", value)

        # Decode entities
        value = (
            value.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )

        value = re.sub(r"\s+", " ", value).strip()

        return value or None
