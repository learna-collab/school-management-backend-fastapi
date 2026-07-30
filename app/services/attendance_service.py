from collections import Counter

from fastapi import HTTPException, status

from app.mappers.attendance_mapper import AttendanceMapper
from app.models.attendance_record import (
    AttendanceRecord,
    AttendanceStatus,
)
from app.models.attendance_sheet import AttendanceSheet
from app.repositories.attendance_repository import (
    attendance_repository,
)
from app.repositories.school_admin_dashboard_repository import (
    SchoolAdminDashboardRepository,
)
from app.repositories.teacher_assignment_repository import (
    teacher_assignment_repository,
)
from app.schemas.attendance import (
    AttendanceAnalyticsResponse,
    ClassAttendanceSummaryResponse,
)


class AttendanceService:
    def __init__(self):
        self.repo = attendance_repository
        self.assignment_repo = teacher_assignment_repository
        self.period_repo = SchoolAdminDashboardRepository()

    async def submit_attendance(
        self,
        db,
        payload,
        teacher,
    ):
        can_manage = await self.assignment_repo.teacher_has_class_access(
            db=db,
            teacher_id=teacher.id,
            class_id=payload.class_id,
        )

        if not can_manage:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this class.",
            )
        active_session = await self.period_repo.get_active_session(
            db,
            teacher.school_id,
        )

        active_term = await self.period_repo.get_active_term(
            db,
            teacher.school_id,
        )
        sheet = await self.repo.get_sheet_by_scope(
            db=db,
            school_id=teacher.school_id,
            class_id=payload.class_id,
            session_id=active_session.id,
            term_id=active_term.id,
            attendance_date=payload.attendance_date,
        )
        if not sheet:
            sheet = AttendanceSheet(
                school_id=teacher.school_id,
                class_id=payload.class_id,
                session_id=active_session.id,
                term_id=active_term.id,
                attendance_date=payload.attendance_date,
                marked_by=teacher.id,
            )

            await self.repo.create_sheet(
                db,
                sheet,
            )
        else:
            await self.repo.delete_sheet_records(
                db,
                sheet.id,
            )
        records = []

        for row in payload.students:
            records.append(
                AttendanceRecord(
                    school_id=teacher.school_id,
                    sheet_id=sheet.id,
                    student_id=row.student_id,
                    status=row.status,
                    note=row.note,
                )
            )
        await self.repo.create_records(
            db,
            records,
        )

        await self.repo.commit(db)

        present_count = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)

        absent_count = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)

        late_count = sum(1 for r in records if r.status == AttendanceStatus.LATE)

        return {
            "sheet_id": sheet.id,
            "created": True,
            "total_students": len(records),
            "present_count": present_count,
            "absent_count": absent_count,
            "late_count": late_count,
            "message": "Attendance submitted successfully",
        }

    async def get_student_term_history(
        self,
        db,
        student,
        session_id,
        term_id,
    ):
        rows = await self.repo.get_student_attendance_history(
            db=db,
            school_id=student.school_id,
            student_id=student.id,
            session_id=session_id,
            term_id=term_id,
        )

        return [
            {
                "attendance_date": str(date),
                "status": status,
                "created_at": created_at.isoformat() if created_at else None,
            }
            for date, status, created_at in rows
        ]

    async def get_class_attendance(
        self,
        db,
        teacher,
        class_id,
        attendance_date,
    ):
        active_session = await self.period_repo.get_active_session(
            db,
            teacher.school_id,
        )

        active_term = await self.period_repo.get_active_term(
            db,
            teacher.school_id,
        )

        sheet = await self.repo.get_class_attendance(
            db=db,
            school_id=teacher.school_id,
            class_id=class_id,
            session_id=active_session.id,
            term_id=active_term.id,
            attendance_date=attendance_date,
        )

        if sheet:
            return AttendanceMapper.class_sheet(sheet)

        return {
            "sheet_id": None,
            "class_id": class_id,
            "session_id": active_session.id,
            "term_id": active_term.id,
            "attendance_date": attendance_date,
            "total_students": 0,
            "present_count": 0,
            "absent_count": 0,
            "late_count": 0,
            "records": [],
        }

    async def get_student_attendance(
        self,
        db,
        student,
        session_id,
        term_id,
    ):
        records = await self.repo.get_student_attendance(
            db=db,
            school_id=student.school_id,
            student_id=student.id,
            session_id=session_id,
            term_id=term_id,
        )

        return AttendanceMapper.student_history(
            records,
        )

    async def get_analytics(
        self,
        db,
        school_id,
        session_id,
        term_id,
    ):
        rows = await self.repo.get_attendance_analytics(
            db=db,
            school_id=school_id,
            session_id=session_id,
            term_id=term_id,
        )

        classes = []

        for row in rows:
            total = row.total or 0

            attendance_rate = (
                round(
                    ((row.present + row.late) / total) * 100,
                    2,
                )
                if total
                else 0
            )

            classes.append(
                ClassAttendanceSummaryResponse(
                    class_id=row.class_id,
                    class_name=row.name,
                    total_students=total,
                    present_count=row.present or 0,
                    absent_count=row.absent or 0,
                    late_count=row.late or 0,
                    attendance_rate=attendance_rate,
                )
            )

        return AttendanceAnalyticsResponse(
            classes=classes,
        )

    async def get_student_term_summary(
        self,
        db,
        student,
        session_id,
        term_id,
    ):
        rows = await self.repo.get_student_term_summary(
            db=db,
            school_id=student.school_id,
            student_id=student.id,
            session_id=session_id,
            term_id=term_id,
        )

        stats = {
            AttendanceStatus.PRESENT: 0,
            AttendanceStatus.ABSENT: 0,
            AttendanceStatus.LATE: 0,
        }

        history = []

        total_present = 0
        total_absent = 0
        total_late = 0

        for row in rows:
            date, present, absent, late = row

            present = present or 0
            absent = absent or 0
            late = late or 0

            total_present += present
            total_absent += absent
            total_late += late

            history.append(
                {
                    "date": date,
                    "present": present,
                    "absent": absent,
                    "late": late,
                }
            )

        total_days = len(history)

        attendance_rate = 0
        if total_days:
            attendance_rate = round(
                (
                    (total_present + total_late)
                    / (total_present + total_absent + total_late)
                )
                * 100,
                2,
            )

        return {
            "total_days": total_days,
            "present": total_present,
            "absent": total_absent,
            "late": total_late,
            "attendance_rate": attendance_rate,
            "history": history,
        }

    async def get_dashboard(
        self,
        db,
        school_id,
        attendance_date,
    ):
        rows = await self.repo.get_dashboard(
            db,
            school_id,
            attendance_date,
        )

        rankings = await self.repo.get_dashboard_class_rankings(
            db,
            school_id,
            attendance_date,
        )

        total_students = await self.repo.get_total_students(
            db,
            school_id,
        )

        counter = Counter()

        for status, count in rows:
            counter[status] = count

        present = counter[AttendanceStatus.PRESENT]
        absent = counter[AttendanceStatus.ABSENT]
        late = counter[AttendanceStatus.LATE]

        attendance_rate = 0

        if total_students:
            attendance_rate = round(
                ((present + late) / total_students) * 100,
                2,
            )

        class_rankings = []

        for row in rankings:
            total = row.total or 0

            percentage = (
                round(((row.present + row.late) / total) * 100, 2) if total else 0
            )

            class_rankings.append(
                {
                    "class_id": str(row.class_id),
                    "class_name": row.class_name,
                    "present": row.present,
                    "absent": row.absent,
                    "late": row.late,
                    "attendance_percentage": percentage,
                }
            )

        class_rankings.sort(
            key=lambda x: x["attendance_percentage"],
            reverse=True,
        )

        return {
            "date": attendance_date,
            "total_students": total_students,
            "present": present,
            "absent": absent,
            "late": late,
            "attendance_rate": attendance_rate,
            "class_rankings": class_rankings,
        }


attendance_service = AttendanceService()
