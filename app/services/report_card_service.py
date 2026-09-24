from __future__ import annotations

import html
from io import BytesIO
from typing import Any

import requests
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ============================================================================
# PROFESSIONAL IMAGE BOX
# ============================================================================


class ProfessionalImageBox(Flowable):
    """
    Formal image container for:
        - School logo
        - Student passport photograph

    Images are preserved at their original aspect ratio.
    No circular avatars or decorative illustrations are used.
    """

    def __init__(
        self,
        image_data: bytes | None,
        width: float,
        height: float,
        placeholder_title: str,
        placeholder_subtitle: str | None = None,
        border_color=colors.HexColor("#8A8A8A"),
        background_color=colors.white,
    ):
        super().__init__()

        self.image_data = image_data
        self.box_width = width
        self.box_height = height
        self.placeholder_title = placeholder_title
        self.placeholder_subtitle = placeholder_subtitle
        self.border_color = border_color
        self.background_color = background_color

        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.box_width, self.box_height

    def draw(self):
        canvas = self.canv

        canvas.saveState()

        # --------------------------------------------------------------
        # Main image box
        # --------------------------------------------------------------

        canvas.setFillColor(self.background_color)

        canvas.setStrokeColor(self.border_color)

        canvas.setLineWidth(0.55)

        canvas.rect(
            0,
            0,
            self.box_width,
            self.box_height,
            stroke=1,
            fill=1,
        )

        # --------------------------------------------------------------
        # Draw actual image
        # --------------------------------------------------------------

        if self.image_data:
            try:
                image = ImageReader(BytesIO(self.image_data))

                image_width, image_height = image.getSize()

                if image_width > 0 and image_height > 0:
                    padding = 1.5 * mm

                    available_width = self.box_width - (padding * 2)

                    available_height = self.box_height - (padding * 2)

                    scale = min(
                        available_width / image_width,
                        available_height / image_height,
                    )

                    draw_width = image_width * scale

                    draw_height = image_height * scale

                    x = (self.box_width - draw_width) / 2

                    y = (self.box_height - draw_height) / 2

                    canvas.drawImage(
                        image,
                        x,
                        y,
                        width=draw_width,
                        height=draw_height,
                        preserveAspectRatio=True,
                        mask="auto",
                    )

                else:
                    self._draw_placeholder(canvas)

            except Exception:
                self._draw_placeholder(canvas)

        else:
            self._draw_placeholder(canvas)

        canvas.restoreState()

    def _draw_placeholder(self, canvas):
        """
        Simple formal placeholder.
        """

        canvas.setFillColor(colors.HexColor("#F7F7F7"))

        canvas.setStrokeColor(colors.HexColor("#C4C4C4"))

        canvas.setLineWidth(0.4)

        canvas.rect(
            1.5 * mm,
            1.5 * mm,
            self.box_width - 3 * mm,
            self.box_height - 3 * mm,
            stroke=1,
            fill=1,
        )

        center_x = self.box_width / 2

        center_y = self.box_height / 2

        canvas.setFillColor(colors.HexColor("#666666"))

        canvas.setFont(
            "Helvetica-Bold",
            5.8,
        )

        canvas.drawCentredString(
            center_x,
            center_y + 1.5 * mm,
            self.placeholder_title,
        )

        if self.placeholder_subtitle:
            canvas.setFont(
                "Helvetica",
                4.8,
            )

            canvas.setFillColor(colors.HexColor("#888888"))

            canvas.drawCentredString(
                center_x,
                center_y - 2.5 * mm,
                self.placeholder_subtitle,
            )


# ============================================================================
# REPORT CARD SERVICE
# ============================================================================


class ReportCardService:
    """
    Professional school report-card PDF.

    Design:
        - A4 portrait
        - Formal academic document
        - Black outer frame
        - Light grey internal borders
        - Clear spacing between major sections
        - Actual school logo
        - Actual student passport photograph
        - No dashboard/avatar styling
        - Uses only fields available from the result backend
    """

    # =========================================================================
    # PAGE
    # =========================================================================

    PAGE_WIDTH, PAGE_HEIGHT = A4

    MARGIN_LEFT = 5 * mm
    MARGIN_RIGHT = 5 * mm
    MARGIN_TOP = 5 * mm
    MARGIN_BOTTOM = 5 * mm

    CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT

    # =========================================================================
    # PROFESSIONAL SPACING
    # =========================================================================

    # Main gap between major sections.
    #
    # This is intentionally larger than the previous version.
    # The document should breathe without looking wasteful.
    SECTION_SPACING = 3.0 * mm

    # Smaller gap between a section heading and its table.
    INNER_SPACING = 1.0 * mm

    # =========================================================================
    # COLORS
    # =========================================================================

    BLACK = colors.black
    WHITE = colors.white

    GRID = colors.HexColor("#C9C9C9")
    GRID_DARK = colors.HexColor("#7F7F7F")

    TEXT = colors.HexColor("#414141")
    TEXT_DARK = colors.HexColor("#2F2F2F")

    HEADING = colors.HexColor("#5D5D5D")

    LIGHT_GREY = colors.HexColor("#F4F4F4")
    MEDIUM_GREY = colors.HexColor("#E6E6E6")

    # =========================================================================
    # FONTS
    # =========================================================================

    FONT = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"

    def __init__(self):
        # --------------------------------------------------------------
        # Main body
        # --------------------------------------------------------------

        self.body_style = ParagraphStyle(
            "ReportBody",
            fontName=self.FONT,
            fontSize=7.2,
            leading=8.4,
            textColor=self.TEXT,
            alignment=TA_LEFT,
            spaceBefore=0,
            spaceAfter=0,
        )

        # --------------------------------------------------------------
        # Small text
        # --------------------------------------------------------------

        self.small_style = ParagraphStyle(
            "ReportSmall",
            fontName=self.FONT,
            fontSize=6.7,
            leading=7.7,
            textColor=self.TEXT,
            alignment=TA_LEFT,
            spaceBefore=0,
            spaceAfter=0,
        )

        # --------------------------------------------------------------
        # Centered text
        # --------------------------------------------------------------

        self.center_style = ParagraphStyle(
            "ReportCenter",
            fontName=self.FONT,
            fontSize=7,
            leading=8,
            textColor=self.TEXT,
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=0,
        )

        # --------------------------------------------------------------
        # School name
        # --------------------------------------------------------------

        self.school_name_style = ParagraphStyle(
            "SchoolName",
            fontName=self.FONT_BOLD,
            fontSize=13,
            leading=14.5,
            textColor=self.TEXT_DARK,
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=0,
        )

        # --------------------------------------------------------------
        # School contact information
        # --------------------------------------------------------------

        self.school_detail_style = ParagraphStyle(
            "SchoolDetail",
            fontName=self.FONT,
            fontSize=6.5,
            leading=7.5,
            textColor=self.TEXT,
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=0,
        )

        # --------------------------------------------------------------
        # Report title
        # --------------------------------------------------------------

        self.report_title_style = ParagraphStyle(
            "ReportTitle",
            fontName=self.FONT_BOLD,
            fontSize=8.7,
            leading=9.8,
            textColor=self.HEADING,
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=0,
        )

        # --------------------------------------------------------------
        # Section title
        # --------------------------------------------------------------

        self.section_style = ParagraphStyle(
            "SectionTitle",
            fontName=self.FONT_BOLD,
            fontSize=7.3,
            leading=8.2,
            textColor=self.TEXT_DARK,
            alignment=TA_LEFT,
            spaceBefore=0,
            spaceAfter=0,
        )

        # --------------------------------------------------------------
        # Table header
        # --------------------------------------------------------------

        self.table_header_style = ParagraphStyle(
            "TableHeader",
            fontName=self.FONT_BOLD,
            fontSize=6.2,
            leading=7,
            textColor=self.TEXT_DARK,
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=0,
        )

        # --------------------------------------------------------------
        # Table body
        # --------------------------------------------------------------

        self.table_body_style = ParagraphStyle(
            "TableBody",
            fontName=self.FONT,
            fontSize=6.5,
            leading=7.4,
            textColor=self.TEXT,
            alignment=TA_LEFT,
            spaceBefore=0,
            spaceAfter=0,
        )

        # --------------------------------------------------------------
        # Center table body
        # --------------------------------------------------------------

        self.table_body_center_style = ParagraphStyle(
            "TableBodyCenter",
            fontName=self.FONT,
            fontSize=6.5,
            leading=7.4,
            textColor=self.TEXT,
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=0,
        )

    # =========================================================================
    # GENERATE
    # =========================================================================

    def generate(
        self,
        student: Any,
        result: Any,
        attendance: Any,
    ) -> BytesIO:
        result_data = self._normalise_mapping(result)

        student_data = self._normalise_mapping(student)

        school = self._normalise_mapping(
            result_data.get("school")
            or getattr(
                student,
                "school",
                None,
            )
            or {}
        )

        student_info = self._normalise_mapping(
            result_data.get("student") or student_data or {}
        )

        session = self._normalise_mapping(result_data.get("session") or {})

        term = self._normalise_mapping(result_data.get("term") or {})

        summary = self._normalise_mapping(result_data.get("summary") or {})

        class_statistics = self._normalise_mapping(
            result_data.get("class_statistics") or {}
        )

        staff = self._normalise_mapping(result_data.get("staff") or {})

        subjects = result_data.get("subjects") or []

        # =====================================================================
        # PDF
        # =====================================================================

        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=self.MARGIN_LEFT,
            rightMargin=self.MARGIN_RIGHT,
            topMargin=self.MARGIN_TOP,
            bottomMargin=self.MARGIN_BOTTOM,
            title="Student Report Card",
            author="School Management System",
        )

        story: list[Any] = []

        # =====================================================================
        # SCHOOL HEADER
        # =====================================================================

        story.append(
            self._build_header(
                school=school,
                student=student_info,
            )
        )

        # Clear separation after header.
        story.append(
            Spacer(
                1,
                self.SECTION_SPACING,
            )
        )

        # =====================================================================
        # REPORT TITLE
        # =====================================================================

        story.append(
            self._build_report_title(
                session=session,
                term=term,
            )
        )

        story.append(
            Spacer(
                1,
                self.SECTION_SPACING,
            )
        )

        # =====================================================================
        # STUDENT INFORMATION
        # =====================================================================

        story.append(
            self._build_student_information(
                student=student_info,
                summary=summary,
                class_statistics=class_statistics,
            )
        )

        story.append(
            Spacer(
                1,
                self.SECTION_SPACING,
            )
        )

        # =====================================================================
        # COGNITIVE DOMAIN
        # =====================================================================

        story.append(self._section_heading("COGNITIVE DOMAIN"))

        story.append(
            Spacer(
                1,
                self.INNER_SPACING,
            )
        )

        story.append(self._build_subject_table(subjects))

        # More breathing room after the large results table.
        story.append(
            Spacer(
                1,
                self.SECTION_SPACING,
            )
        )

        # =====================================================================
        # ATTENDANCE
        # =====================================================================

        story.append(self._section_heading("ATTENDANCE"))

        story.append(
            Spacer(
                1,
                self.INNER_SPACING,
            )
        )

        story.append(self._build_attendance_section(attendance))

        story.append(
            Spacer(
                1,
                self.SECTION_SPACING,
            )
        )

        # =====================================================================
        # STAFF / CLASS SUMMARY
        # =====================================================================

        story.append(self._section_heading("CLASS / RESULT SUMMARY"))

        story.append(
            Spacer(
                1,
                self.INNER_SPACING,
            )
        )

        story.append(
            self._build_staff_section(
                staff=staff,
                summary=summary,
                class_statistics=class_statistics,
            )
        )

        story.append(
            Spacer(
                1,
                self.SECTION_SPACING,
            )
        )

        # =====================================================================
        # GRADING KEY
        # =====================================================================

        story.append(self._section_heading("KEY TO SUBJECT GRADING"))

        story.append(
            Spacer(
                1,
                self.INNER_SPACING,
            )
        )

        story.append(self._build_grading_key())

        # =====================================================================
        # BUILD PDF
        # =====================================================================

        doc.build(
            story,
            onFirstPage=self._draw_outer_frame,
            onLaterPages=self._draw_outer_frame,
        )

        buffer.seek(0)

        return buffer

    # =========================================================================
    # OUTER FRAME
    # =========================================================================

    def _draw_outer_frame(
        self,
        canvas,
        doc,
    ):
        canvas.saveState()

        canvas.setStrokeColor(self.BLACK)

        canvas.setLineWidth(0.7)

        canvas.rect(
            self.MARGIN_LEFT - 1.5 * mm,
            self.MARGIN_BOTTOM - 1.5 * mm,
            (self.PAGE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT + 3 * mm),
            (self.PAGE_HEIGHT - self.MARGIN_TOP - self.MARGIN_BOTTOM + 3 * mm),
            stroke=1,
            fill=0,
        )

        canvas.restoreState()

    # =========================================================================
    # SCHOOL HEADER
    # =========================================================================

    def _build_header(
        self,
        school: dict[str, Any],
        student: dict[str, Any],
    ) -> Table:
        school_name = school.get("name") or school.get("school_name") or "SCHOOL NAME"

        address = school.get("address") or ""

        phone = school.get("phone") or school.get("phone_number") or ""

        email = school.get("email") or ""

        website = school.get("website") or ""

        # =====================================================================
        # SCHOOL LOGO
        # =====================================================================

        logo_url = school.get("logo_url") or school.get("logo")

        logo_data = self._download_image_data(logo_url) if logo_url else None

        logo = ProfessionalImageBox(
            image_data=logo_data,
            width=25 * mm,
            height=25 * mm,
            placeholder_title="SCHOOL LOGO",
            placeholder_subtitle="Official Logo",
        )

        # =====================================================================
        # STUDENT PASSPORT
        # =====================================================================

        photo_url = (
            student.get("passport")
            or student.get("passport_url")
            or student.get("avatar_url")
            or student.get("photo_url")
        )

        photo_data = self._download_image_data(photo_url) if photo_url else None

        passport = ProfessionalImageBox(
            image_data=photo_data,
            width=23 * mm,
            height=27 * mm,
            placeholder_title="PASSPORT",
            placeholder_subtitle="Photograph",
        )

        # =====================================================================
        # SCHOOL DETAILS
        # =====================================================================

        details: list[Any] = []

        details.append(
            Paragraph(
                html.escape(str(school_name)),
                self.school_name_style,
            )
        )

        if address:
            details.append(
                Paragraph(
                    html.escape(str(address)),
                    self.school_detail_style,
                )
            )

        if email:
            details.append(
                Paragraph(
                    html.escape(f"Email: {email}"),
                    self.school_detail_style,
                )
            )

        if website:
            details.append(
                Paragraph(
                    html.escape(f"Website: {website}"),
                    self.school_detail_style,
                )
            )

        if phone:
            details.append(
                Paragraph(
                    html.escape(f"Phone: {phone}"),
                    self.school_detail_style,
                )
            )

        center_width = self.CONTENT_WIDTH - 58 * mm

        center_cell = Table(
            [[item] for item in details],
            colWidths=[center_width],
        )

        center_cell.setStyle(
            TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        0.5 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        0.5 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        0.25 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        0.25 * mm,
                    ),
                ]
            )
        )

        # =====================================================================
        # HEADER TABLE
        # =====================================================================

        table = Table(
            [
                [
                    logo,
                    center_cell,
                    passport,
                ]
            ],
            colWidths=[
                29 * mm,
                self.CONTENT_WIDTH - 58 * mm,
                29 * mm,
            ],
            rowHeights=[30 * mm],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.6,
                        self.GRID_DARK,
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        self.GRID,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (0, 0),
                        "CENTER",
                    ),
                    (
                        "ALIGN",
                        (2, 0),
                        (2, 0),
                        "CENTER",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.2 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.2 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        1 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        1 * mm,
                    ),
                ]
            )
        )

        return table

    # =========================================================================
    # REPORT TITLE
    # =========================================================================

    def _build_report_title(
        self,
        session: dict[str, Any],
        term: dict[str, Any],
    ) -> Table:
        session_name = session.get("name") or session.get("session_name") or ""

        term_name = term.get("name") or term.get("term_name") or ""

        session_name = str(session_name).strip()

        term_name = str(term_name).strip()

        if session_name and term_name:
            title = f"{session_name} - {term_name}"

        elif session_name:
            title = session_name

        elif term_name:
            title = term_name

        else:
            title = "STUDENT REPORT"

        if not title.upper().endswith("REPORT"):
            title = f"{title} REPORT"

        table = Table(
            [
                [
                    Paragraph(
                        html.escape(title.upper()),
                        self.report_title_style,
                    )
                ]
            ],
            colWidths=[self.CONTENT_WIDTH],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        self.GRID_DARK,
                    ),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        self.LIGHT_GREY,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.5 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.5 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        1.5 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        1.5 * mm,
                    ),
                ]
            )
        )

        return table

    # =========================================================================
    # STUDENT INFORMATION
    # =========================================================================

    def _build_student_information(
        self,
        student: dict[str, Any],
        summary: dict[str, Any],
        class_statistics: dict[str, Any],
    ) -> Table:
        first_name = student.get("first_name") or ""

        last_name = student.get("last_name") or ""

        full_name = student.get("name")

        if not full_name:
            full_name = (f"{first_name} {last_name}").strip()

        if not full_name:
            full_name = "—"

        admission_number = (
            student.get("admission_number") or student.get("student_id") or "—"
        )

        class_name = student.get("class_name") or student.get("class") or "—"

        average = self._number(summary.get("average_score"))

        position = summary.get("position") or "—"

        subjects_offered = summary.get("subjects_offered") or 0

        total_score = self._number(summary.get("total_score"))

        class_average = self._number(class_statistics.get("class_average"))

        class_size = class_statistics.get("class_size") or 0

        rows = [
            [
                self._label_value(
                    "PUPIL NAME",
                    full_name,
                ),
                self._label_value(
                    "STUDENT ID",
                    admission_number,
                ),
            ],
            [
                self._label_value(
                    "CLASS",
                    class_name,
                ),
                self._label_value(
                    "NO. OF SUBJECTS",
                    subjects_offered,
                ),
            ],
            [
                self._label_value(
                    "TERM AVERAGE",
                    self._format_number(average),
                ),
                self._label_value(
                    "FINAL AVERAGE",
                    self._format_number(average),
                ),
            ],
            [
                self._label_value(
                    "POSITION",
                    position,
                ),
                self._label_value(
                    "CLASS AVERAGE",
                    self._format_number(class_average),
                ),
            ],
            [
                self._label_value(
                    "TOTAL SCORE",
                    self._format_number(total_score),
                ),
                self._label_value(
                    "CLASS SIZE",
                    class_size,
                ),
            ],
        ]

        table = Table(
            rows,
            colWidths=[
                self.CONTENT_WIDTH / 2,
                self.CONTENT_WIDTH / 2,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.55,
                        self.GRID_DARK,
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        self.GRID,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.7 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.7 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        1.15 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        1.15 * mm,
                    ),
                ]
            )
        )

        return table

    # =========================================================================
    # LABEL / VALUE
    # =========================================================================

    def _label_value(
        self,
        label: str,
        value: Any,
    ) -> Paragraph:
        safe_label = html.escape(str(label))

        safe_value = html.escape(self._display(value))

        return Paragraph(
            (f"<b>{safe_label}:</b> {safe_value}"),
            self.small_style,
        )

    # =========================================================================
    # SECTION HEADING
    # =========================================================================

    def _section_heading(
        self,
        title: str,
    ) -> Table:
        table = Table(
            [
                [
                    Paragraph(
                        html.escape(title),
                        self.section_style,
                    )
                ]
            ],
            colWidths=[self.CONTENT_WIDTH],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.55,
                        self.GRID_DARK,
                    ),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        self.MEDIUM_GREY,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.7 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.7 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        1.1 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        1.1 * mm,
                    ),
                ]
            )
        )

        return table

    # =========================================================================
    # SUBJECT TABLE
    # =========================================================================

    def _build_subject_table(
        self,
        subjects: list[Any],
    ) -> Table:
        header = [
            Paragraph(
                "SUBJECT",
                self.table_header_style,
            ),
            Paragraph(
                "CA",
                self.table_header_style,
            ),
            Paragraph(
                "EXAM",
                self.table_header_style,
            ),
            Paragraph(
                "TOTAL",
                self.table_header_style,
            ),
            Paragraph(
                "GRADE",
                self.table_header_style,
            ),
            Paragraph(
                "REMARKS",
                self.table_header_style,
            ),
        ]

        rows = [header]

        if not subjects:
            rows.append(
                [
                    Paragraph(
                        "No subject results available",
                        self.table_body_style,
                    ),
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )

        else:
            for item in subjects:
                subject = self._normalise_mapping(item)

                subject_name = subject.get("subject_name") or subject.get("name") or "—"

                ca = self._number(subject.get("ca_score"))

                exam = self._number(subject.get("exam_score"))

                total = self._number(subject.get("total_score"))

                grade = subject.get("grade") or self._grade_from_score(total) or "—"

                remark = subject.get("remark") or "—"

                teacher_comment = subject.get("teacher_comment") or ""

                if teacher_comment:
                    remark_text = f"{remark} - {teacher_comment}"

                else:
                    remark_text = remark

                rows.append(
                    [
                        Paragraph(
                            html.escape(str(subject_name)),
                            self.table_body_style,
                        ),
                        Paragraph(
                            self._format_number(ca),
                            self.table_body_center_style,
                        ),
                        Paragraph(
                            self._format_number(exam),
                            self.table_body_center_style,
                        ),
                        Paragraph(
                            self._format_number(total),
                            self.table_body_center_style,
                        ),
                        Paragraph(
                            html.escape(str(grade)),
                            self.table_body_center_style,
                        ),
                        Paragraph(
                            html.escape(str(remark_text)),
                            self.table_body_style,
                        ),
                    ]
                )

        # Full available width.
        widths = [
            self.CONTENT_WIDTH * 0.29,
            self.CONTENT_WIDTH * 0.10,
            self.CONTENT_WIDTH * 0.10,
            self.CONTENT_WIDTH * 0.13,
            self.CONTENT_WIDTH * 0.09,
            self.CONTENT_WIDTH * 0.29,
        ]

        table = Table(
            rows,
            colWidths=widths,
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.6,
                        self.GRID_DARK,
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        self.GRID,
                    ),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        self.MEDIUM_GREY,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.25 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.25 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        0.95 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        0.95 * mm,
                    ),
                    (
                        "ALIGN",
                        (1, 1),
                        (4, -1),
                        "CENTER",
                    ),
                ]
            )
        )

        return table

    # =========================================================================
    # ATTENDANCE
    # =========================================================================

    def _build_attendance_section(
        self,
        attendance: Any,
    ) -> Table:
        data = self._normalise_attendance(attendance)

        present = data["present"]
        absent = data["absent"]
        late = data["late"]
        total = data["total"]

        cells = [
            [
                Paragraph(
                    "<b>TOTAL DAYS</b>",
                    self.table_header_style,
                ),
                Paragraph(
                    "<b>PRESENT</b>",
                    self.table_header_style,
                ),
                Paragraph(
                    "<b>ABSENT</b>",
                    self.table_header_style,
                ),
                Paragraph(
                    "<b>LATE</b>",
                    self.table_header_style,
                ),
            ],
            [
                Paragraph(
                    str(total),
                    self.table_body_center_style,
                ),
                Paragraph(
                    str(present),
                    self.table_body_center_style,
                ),
                Paragraph(
                    str(absent),
                    self.table_body_center_style,
                ),
                Paragraph(
                    str(late),
                    self.table_body_center_style,
                ),
            ],
        ]

        table = Table(
            cells,
            colWidths=[
                self.CONTENT_WIDTH * 0.25,
                self.CONTENT_WIDTH * 0.25,
                self.CONTENT_WIDTH * 0.25,
                self.CONTENT_WIDTH * 0.25,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.55,
                        self.GRID_DARK,
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        self.GRID,
                    ),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        self.LIGHT_GREY,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.2 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.2 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        0.85 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        0.85 * mm,
                    ),
                ]
            )
        )

        return table

    # =========================================================================
    # STAFF / CLASS SUMMARY
    # =========================================================================

    def _build_staff_section(
        self,
        staff: dict[str, Any],
        summary: dict[str, Any],
        class_statistics: dict[str, Any],
    ) -> Table:
        class_teacher = staff.get("class_teacher") or "—"

        principal = staff.get("principal") or "—"

        highest = self._number(class_statistics.get("highest_average"))

        lowest = self._number(class_statistics.get("lowest_average"))

        class_average = self._number(class_statistics.get("class_average"))

        rows = [
            [
                self._label_value(
                    "CLASS TEACHER",
                    class_teacher,
                ),
                self._label_value(
                    "HEAD TEACHER / PRINCIPAL",
                    principal,
                ),
            ],
            [
                self._label_value(
                    "HIGHEST CLASS AVERAGE",
                    self._format_number(highest),
                ),
                self._label_value(
                    "LOWEST CLASS AVERAGE",
                    self._format_number(lowest),
                ),
            ],
            [
                self._label_value(
                    "CLASS AVERAGE",
                    self._format_number(class_average),
                ),
                self._label_value(
                    "RESULT STATUS",
                    "PUBLISHED",
                ),
            ],
        ]

        table = Table(
            rows,
            colWidths=[
                self.CONTENT_WIDTH / 2,
                self.CONTENT_WIDTH / 2,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.55,
                        self.GRID_DARK,
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        self.GRID,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.7 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.7 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        1.05 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        1.05 * mm,
                    ),
                ]
            )
        )

        return table

    # =========================================================================
    # GRADING KEY
    # =========================================================================

    def _build_grading_key(
        self,
    ) -> Table:
        rows = [
            [
                Paragraph(
                    "SCORE",
                    self.table_header_style,
                ),
                Paragraph(
                    "GRADE",
                    self.table_header_style,
                ),
                Paragraph(
                    "REMARK",
                    self.table_header_style,
                ),
            ],
            [
                Paragraph(
                    "70 - 100",
                    self.table_body_center_style,
                ),
                Paragraph(
                    "A",
                    self.table_body_center_style,
                ),
                Paragraph(
                    "Excellent",
                    self.table_body_style,
                ),
            ],
            [
                Paragraph(
                    "60 - 69",
                    self.table_body_center_style,
                ),
                Paragraph(
                    "B",
                    self.table_body_center_style,
                ),
                Paragraph(
                    "Very Good",
                    self.table_body_style,
                ),
            ],
            [
                Paragraph(
                    "50 - 59",
                    self.table_body_center_style,
                ),
                Paragraph(
                    "C",
                    self.table_body_center_style,
                ),
                Paragraph(
                    "Good",
                    self.table_body_style,
                ),
            ],
            [
                Paragraph(
                    "45 - 49",
                    self.table_body_center_style,
                ),
                Paragraph(
                    "D",
                    self.table_body_center_style,
                ),
                Paragraph(
                    "Fair",
                    self.table_body_style,
                ),
            ],
            [
                Paragraph(
                    "40 - 44",
                    self.table_body_center_style,
                ),
                Paragraph(
                    "E",
                    self.table_body_center_style,
                ),
                Paragraph(
                    "Pass",
                    self.table_body_style,
                ),
            ],
            [
                Paragraph(
                    "0 - 39",
                    self.table_body_center_style,
                ),
                Paragraph(
                    "F",
                    self.table_body_center_style,
                ),
                Paragraph(
                    "Fail",
                    self.table_body_style,
                ),
            ],
        ]

        table = Table(
            rows,
            colWidths=[
                self.CONTENT_WIDTH * 0.34,
                self.CONTENT_WIDTH * 0.16,
                self.CONTENT_WIDTH * 0.50,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.55,
                        self.GRID_DARK,
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        self.GRID,
                    ),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        self.LIGHT_GREY,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.2 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        1.2 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        0.7 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        0.7 * mm,
                    ),
                ]
            )
        )

        return table

    # =========================================================================
    # IMAGE DOWNLOAD
    # =========================================================================

    def _download_image_data(
        self,
        url: str | None,
    ) -> bytes | None:
        if not url:
            return None

        try:
            response = requests.get(
                str(url),
                timeout=8,
                headers={"User-Agent": ("Mozilla/5.0 (Student Report Card)")},
            )

            response.raise_for_status()

            if not response.content:
                return None

            content_type = response.headers.get(
                "content-type",
                "",
            ).lower()

            if content_type and not content_type.startswith("image/"):
                return None

            return response.content

        except Exception:
            return None

    # =========================================================================
    # ATTENDANCE NORMALISER
    # =========================================================================

    def _normalise_attendance(
        self,
        attendance: Any,
    ) -> dict[str, int]:
        result = {
            "total": 0,
            "present": 0,
            "absent": 0,
            "late": 0,
        }

        if attendance is None:
            return result

        # ---------------------------------------------------------------------
        # Dictionary
        # ---------------------------------------------------------------------

        if isinstance(
            attendance,
            dict,
        ):
            result["present"] = self._safe_int(
                attendance.get("present") or attendance.get("present_count")
            )

            result["absent"] = self._safe_int(
                attendance.get("absent") or attendance.get("absent_count")
            )

            result["late"] = self._safe_int(
                attendance.get("late") or attendance.get("late_count")
            )

            result["total"] = self._safe_int(
                attendance.get("total") or attendance.get("total_days")
            )

            if not result["total"]:
                result["total"] = result["present"] + result["absent"] + result["late"]

            return result

        # ---------------------------------------------------------------------
        # List of attendance records
        # ---------------------------------------------------------------------

        if isinstance(
            attendance,
            (list, tuple),
        ):
            for record in attendance:
                record_data = self._normalise_mapping(record)

                status = record_data.get("status") or ""

                status = str(status).upper().strip()

                if status == "PRESENT":
                    result["present"] += 1

                elif status == "ABSENT":
                    result["absent"] += 1

                elif status == "LATE":
                    result["late"] += 1

            result["total"] = result["present"] + result["absent"] + result["late"]

            return result

        # ---------------------------------------------------------------------
        # Pydantic / object
        # ---------------------------------------------------------------------

        data = self._normalise_mapping(attendance)

        if data:
            return self._normalise_attendance(data)

        return result

    # =========================================================================
    # GRADE
    # =========================================================================

    def _grade_from_score(
        self,
        score: float,
    ) -> str:
        if score >= 70:
            return "A"

        if score >= 60:
            return "B"

        if score >= 50:
            return "C"

        if score >= 45:
            return "D"

        if score >= 40:
            return "E"

        return "F"

    # =========================================================================
    # NORMALISE OBJECT
    # =========================================================================

    def _normalise_mapping(
        self,
        value: Any,
    ) -> dict[str, Any]:
        if value is None:
            return {}

        if isinstance(
            value,
            dict,
        ):
            return value

        # ---------------------------------------------------------------------
        # Pydantic v2
        # ---------------------------------------------------------------------

        model_dump = getattr(
            value,
            "model_dump",
            None,
        )

        if callable(model_dump):
            try:
                return model_dump()

            except Exception:
                pass

        # ---------------------------------------------------------------------
        # Pydantic v1
        # ---------------------------------------------------------------------

        dict_method = getattr(
            value,
            "dict",
            None,
        )

        if callable(dict_method):
            try:
                return dict_method()

            except Exception:
                pass

        # ---------------------------------------------------------------------
        # Generic object
        # ---------------------------------------------------------------------

        try:
            result = {}

            for key in dir(value):
                if key.startswith("_"):
                    continue

                try:
                    item = getattr(
                        value,
                        key,
                    )

                except Exception:
                    continue

                if callable(item):
                    continue

                result[key] = item

            return result

        except Exception:
            return {}

    # =========================================================================
    # NUMBER
    # =========================================================================

    def _number(
        self,
        value: Any,
    ) -> float:
        if value is None:
            return 0.0

        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return 0.0

    # =========================================================================
    # SAFE INTEGER
    # =========================================================================

    def _safe_int(
        self,
        value: Any,
    ) -> int:
        if value is None:
            return 0

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            return 0

    # =========================================================================
    # FORMAT NUMBER
    # =========================================================================

    def _format_number(
        self,
        value: Any,
    ) -> str:
        if value is None:
            return "0"

        try:
            number = float(value)

            if number.is_integer():
                return str(int(number))

            return f"{number:.2f}"

        except (
            TypeError,
            ValueError,
        ):
            return str(value)

    # =========================================================================
    # DISPLAY
    # =========================================================================

    def _display(
        self,
        value: Any,
    ) -> str:
        if value is None:
            return "—"

        if isinstance(
            value,
            str,
        ):
            value = value.strip()

            if not value:
                return "—"

            return value

        return str(value)


# ============================================================================
# SERVICE INSTANCE
# ============================================================================


report_card_service = ReportCardService()
