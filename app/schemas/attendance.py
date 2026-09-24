from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.models.attendance_record import AttendanceStatus


class StudentAttendanceItem(BaseModel):
    student_id: UUID
    status: AttendanceStatus
    note: str | None = None


class AttendanceCreate(BaseModel):
    class_id: UUID
    attendance_date: date
    students: list[StudentAttendanceItem]


class AttendanceStudentResponse(BaseModel):
    student_id: UUID
    student_name: str
    status: AttendanceStatus
    note: str | None = None


class AttendanceSheetResponse(BaseModel):
    sheet_id: UUID

    class_id: UUID
    session_id: UUID
    term_id: UUID

    attendance_date: date

    total_students: int
    present_count: int
    absent_count: int
    late_count: int

    records: list[AttendanceStudentResponse]


class AttendanceSubmissionResponse(BaseModel):
    sheet_id: UUID

    created: bool

    total_students: int
    present_count: int
    absent_count: int
    late_count: int

    message: str


class StudentAttendanceRecordResponse(BaseModel):
    date: date
    status: AttendanceStatus
    note: str | None = None


class StudentAttendanceResponse(BaseModel):
    present_count: int
    absent_count: int
    late_count: int
    total_school_days: int

    attendance_rate: float

    records: list[StudentAttendanceRecordResponse]


class AttendanceDashboardResponse(BaseModel):
    total_students: int

    present_today: int
    absent_today: int
    late_today: int

    attendance_rate: float


class ClassAttendanceSummaryResponse(BaseModel):
    class_id: UUID
    class_name: str

    total_students: int

    present_count: int
    absent_count: int
    late_count: int

    attendance_rate: float


class AttendanceAnalyticsResponse(BaseModel):
    classes: list[ClassAttendanceSummaryResponse]


class AttendanceReportCardSummary(BaseModel):
    present_count: int
    absent_count: int
    late_count: int

    attendance_rate: float
