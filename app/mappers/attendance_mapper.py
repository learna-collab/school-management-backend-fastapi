from app.models.attendance_record import AttendanceStatus
from app.schemas.attendance import (
    AttendanceSheetResponse,
    AttendanceStudentResponse,
    StudentAttendanceRecordResponse,
    StudentAttendanceResponse,
)


class AttendanceMapper:
    @staticmethod
    def class_sheet(sheet):
        present_count = sum(
            1 for record in sheet.records if record.status == AttendanceStatus.PRESENT
        )
        absent_count = sum(
            1 for record in sheet.records if record.status == AttendanceStatus.ABSENT
        )
        late_count = sum(
            1 for record in sheet.records if record.status == AttendanceStatus.LATE
        )

        return AttendanceSheetResponse(
            sheet_id=sheet.id,
            class_id=sheet.class_id,
            session_id=sheet.session_id,
            term_id=sheet.term_id,
            attendance_date=sheet.attendance_date,
            total_students=len(sheet.records),
            present_count=present_count,
            absent_count=absent_count,
            late_count=late_count,
            records=[
                AttendanceStudentResponse(
                    student_id=record.student_id,
                    student_name=f"{record.student.first_name} {record.student.last_name}",
                    status=record.status,
                    note=record.note,
                )
                for record in sheet.records
            ],
        )

    @staticmethod
    def student_history(records):
        present_count = sum(
            1 for record in records if record.status == AttendanceStatus.PRESENT
        )
        absent_count = sum(
            1 for record in records if record.status == AttendanceStatus.ABSENT
        )
        late_count = sum(
            1 for record in records if record.status == AttendanceStatus.LATE
        )

        total_school_days = len(records)

        attendance_rate = (
            round(((present_count + late_count) / total_school_days) * 100, 2)
            if total_school_days
            else 0
        )

        return StudentAttendanceResponse(
            total_school_days=total_school_days,
            present_count=present_count,
            absent_count=absent_count,
            late_count=late_count,
            attendance_rate=attendance_rate,
            records=[
                StudentAttendanceRecordResponse(
                    date=record.sheet.attendance_date,
                    status=record.status,
                    note=record.note,
                )
                for record in records
            ],
        )
