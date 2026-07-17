from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.result_approval import ResultApproval
from app.models.result_batch import ResultBatch
from app.models.result_record import ResultRecord
from app.models.result_summary import ResultSummary


class ResultRepository:
    # =====================================================
    # WRITE OPERATIONS
    # =====================================================

    async def create_batch(
        self,
        db: AsyncSession,
        batch: ResultBatch,
    ) -> ResultBatch:
        db.add(batch)
        await db.flush()
        return batch

    async def create_records(
        self,
        db: AsyncSession,
        records: list[ResultRecord],
    ) -> list[ResultRecord]:
        db.add_all(records)
        await db.flush()
        return records

    async def create_summaries(
        self,
        db: AsyncSession,
        summaries: list[ResultSummary],
    ) -> list[ResultSummary]:
        db.add_all(summaries)
        await db.flush()
        return summaries

    async def create_approval_log(
        self,
        db: AsyncSession,
        approval: ResultApproval,
    ) -> ResultApproval:
        db.add(approval)
        await db.flush()
        return approval

    async def commit(
        self,
        db: AsyncSession,
    ):
        await db.commit()

    async def rollback(
        self,
        db: AsyncSession,
    ):
        await db.rollback()

    # =====================================================
    # BATCH
    # =====================================================

    async def get_batch(
        self,
        db: AsyncSession,
        batch_id: UUID,
        school_id: UUID,
    ) -> ResultBatch | None:
        result = await db.execute(
            select(ResultBatch).where(
                and_(
                    ResultBatch.id == batch_id,
                    ResultBatch.school_id == school_id,
                )
            )
        )

        return result.scalar_one_or_none()

    async def get_batch_with_records(
        self,
        db: AsyncSession,
        batch_id: UUID,
        school_id: UUID,
    ) -> ResultBatch | None:
        result = await db.execute(
            select(ResultBatch)
            .options(
                selectinload(ResultBatch.records),
                selectinload(ResultBatch.summaries),
                selectinload(ResultBatch.approvals),
            )
            .where(
                and_(
                    ResultBatch.id == batch_id,
                    ResultBatch.school_id == school_id,
                )
            )
        )

        return result.scalar_one_or_none()

    async def get_class_batch(
        self,
        db: AsyncSession,
        school_id: UUID,
        class_id: UUID,
        session_id: UUID,
        term_id: UUID,
    ) -> ResultBatch | None:
        result = await db.execute(
            select(ResultBatch)
            .where(
                and_(
                    ResultBatch.school_id == school_id,
                    ResultBatch.class_id == class_id,
                    ResultBatch.session_id == session_id,
                    ResultBatch.term_id == term_id,
                )
            )
            .order_by(ResultBatch.created_at.desc())
        )

        return result.scalars().first()

    # =====================================================
    # RECORDS
    # =====================================================

    async def get_batch_records(
        self,
        db: AsyncSession,
        batch_id: UUID,
    ) -> list[ResultRecord]:
        result = await db.execute(
            select(ResultRecord)
            .options(
                selectinload(ResultRecord.subject),
                selectinload(ResultRecord.student),
            )
            .where(
                ResultRecord.batch_id == batch_id,
            )
        )

        return list(result.scalars().all())

    async def get_record(
        self,
        db: AsyncSession,
        record_id: UUID,
    ) -> ResultRecord | None:
        result = await db.execute(
            select(ResultRecord).where(ResultRecord.id == record_id)
        )

        return result.scalar_one_or_none()

    async def update_record(
        self,
        db: AsyncSession,
        record: ResultRecord,
    ) -> ResultRecord:
        db.add(record)
        await db.flush()

        return record

    # =====================================================
    # SUMMARYS
    # =====================================================

    async def get_batch_summaries(
        self,
        db: AsyncSession,
        batch_id: UUID,
    ) -> list[ResultSummary]:
        result = await db.execute(
            select(ResultSummary)
            .options(
                selectinload(ResultSummary.student),
            )
            .where(
                ResultSummary.batch_id == batch_id,
            )
            .order_by(ResultSummary.position.asc())
        )

        return list(result.scalars().all())

    async def get_student_summary(
        self,
        db: AsyncSession,
        batch_id: UUID,
        student_id: UUID,
    ) -> ResultSummary | None:
        result = await db.execute(
            select(ResultSummary).where(
                and_(
                    ResultSummary.batch_id == batch_id,
                    ResultSummary.student_id == student_id,
                )
            )
        )

        return result.scalar_one_or_none()

    # =====================================================
    # STUDENT REPORT CARD
    # =====================================================

    async def get_student_records(
        self,
        db: AsyncSession,
        batch_id: UUID,
        student_id: UUID,
    ) -> list[ResultRecord]:
        result = await db.execute(
            select(ResultRecord)
            .options(
                selectinload(ResultRecord.subject),
            )
            .where(
                and_(
                    ResultRecord.batch_id == batch_id,
                    ResultRecord.student_id == student_id,
                )
            )
            .order_by(ResultRecord.subject_id)
        )

        return list(result.scalars().all())

    async def get_student_batch(
        self,
        db: AsyncSession,
        school_id: UUID,
        student_id: UUID,
        session_id: UUID,
        term_id: UUID,
    ) -> ResultBatch | None:
        result = await db.execute(
            select(ResultBatch)
            .join(
                ResultSummary,
                ResultSummary.batch_id == ResultBatch.id,
            )
            .where(
                and_(
                    ResultBatch.school_id == school_id,
                    ResultBatch.session_id == session_id,
                    ResultBatch.term_id == term_id,
                    ResultBatch.status == "PUBLISHED",
                    ResultSummary.student_id == student_id,
                )
            )
        )

        return result.scalar_one_or_none()

    # =====================================================
    # APPROVAL HISTORY
    # =====================================================

    async def get_approval_history(
        self,
        db: AsyncSession,
        batch_id: UUID,
    ) -> list[ResultApproval]:
        result = await db.execute(
            select(ResultApproval)
            .options(
                selectinload(ResultApproval.actor),
            )
            .where(
                ResultApproval.batch_id == batch_id,
            )
            .order_by(ResultApproval.action_at.desc())
        )

        return list(result.scalars().all())

    # =====================================================
    # STATUS
    # =====================================================

    async def save_batch(
        self,
        db: AsyncSession,
        batch: ResultBatch,
    ) -> ResultBatch:
        db.add(batch)
        await db.flush()

        return batch

    # =====================================================
    # EXISTENCE CHECKS
    # =====================================================
    async def get_teacher_editable_batch(
        self,
        db: AsyncSession,
        school_id,
        class_id,
        session_id,
        term_id,
    ):
        result = await db.execute(
            select(ResultBatch)
            .options(
                # ✅ records + nested subject/student
                selectinload(ResultBatch.records).selectinload(ResultRecord.student),
                selectinload(ResultBatch.records).selectinload(ResultRecord.subject),
                # 🔥 MISSING PIECE (this is your crash)
                selectinload(ResultBatch.summaries).selectinload(ResultSummary.student),
            )
            .where(
                ResultBatch.school_id == school_id,
                ResultBatch.class_id == class_id,
                ResultBatch.session_id == session_id,
                ResultBatch.term_id == term_id,
            )
        )

        return result.scalar_one_or_none()

    async def result_exists(
        self,
        db: AsyncSession,
        school_id: UUID,
        class_id: UUID,
        session_id: UUID,
        term_id: UUID,
    ) -> ResultBatch | None:
        result = await db.execute(
            select(ResultBatch).where(
                and_(
                    ResultBatch.school_id == school_id,
                    ResultBatch.class_id == class_id,
                    ResultBatch.session_id == session_id,
                    ResultBatch.term_id == term_id,
                )
            )
        )

        return result.scalar_one_or_none()

    async def get_class_result_batch(
        self,
        db: AsyncSession,
        school_id: UUID,
        class_id: UUID,
        session_id: UUID,
        term_id: UUID,
    ):
        result = await db.execute(
            select(ResultBatch)
            .options(
                selectinload(ResultBatch.records).selectinload(ResultRecord.student),
                selectinload(ResultBatch.records).selectinload(ResultRecord.subject),
                selectinload(ResultBatch.summaries).selectinload(ResultSummary.student),
            )
            .where(
                and_(
                    ResultBatch.school_id == school_id,
                    ResultBatch.class_id == class_id,
                    ResultBatch.session_id == session_id,
                    ResultBatch.term_id == term_id,
                )
            )
        )

        return result.scalar_one_or_none()

    async def get_student_published_result(
        self,
        db: AsyncSession,
        school_id: UUID,
        student_id: UUID,
        session_id: UUID,
        term_id: UUID,
    ):
        result = await db.execute(
            select(ResultBatch)
            .join(ResultSummary)
            .options(
                selectinload(ResultBatch.session),
                selectinload(ResultBatch.term),
                selectinload(ResultBatch.school_class),
                selectinload(ResultBatch.school),
            )
            .where(
                and_(
                    ResultBatch.school_id == school_id,
                    ResultBatch.session_id == session_id,
                    ResultBatch.term_id == term_id,
                    ResultBatch.status == "PUBLISHED",
                    ResultSummary.student_id == student_id,
                )
            )
        )

        batch = result.scalar_one_or_none()

        if batch is None:
            return None

        return {
            "batch": batch,
            "summary": await self.get_student_summary(
                db,
                batch.id,
                student_id,
            ),
            "records": await self.get_student_records(
                db,
                batch.id,
                student_id,
            ),
        }

    async def update_comment(
        self,
        db: AsyncSession,
        record: ResultRecord,
    ):
        db.add(record)
        await db.flush()
        return record

    async def delete_batch(
        self,
        db: AsyncSession,
        batch: ResultBatch,
    ):
        await db.delete(batch)
        await db.flush()

    async def get_batch_statistics(
        self,
        db: AsyncSession,
        batch_id: UUID,
    ):
        result = await db.execute(
            select(ResultSummary).where(ResultSummary.batch_id == batch_id)
        )

        return result.scalars().all()

    async def get_class_batches(
        self,
        db: AsyncSession,
        school_id: UUID,
        class_id: UUID,
    ):
        result = await db.execute(
            select(ResultBatch)
            .options(
                selectinload(ResultBatch.session),
                selectinload(ResultBatch.term),
                selectinload(ResultBatch.school_class),
            )
            .where(
                and_(
                    ResultBatch.school_id == school_id,
                    ResultBatch.class_id == class_id,
                )
            )
            .order_by(ResultBatch.updated_at.desc())
        )

        return result.scalars().all()

    async def get_student_result_in_batch(
        self,
        db: AsyncSession,
        batch_id: UUID,
        student_id: UUID,
    ):
        result = await db.execute(
            select(ResultRecord)
            .options(selectinload(ResultRecord.subject))
            .where(
                and_(
                    ResultRecord.batch_id == batch_id,
                    ResultRecord.student_id == student_id,
                )
            )
        )

        return result.scalars().all()

    async def save_summary(
        self,
        db: AsyncSession,
        summary: ResultSummary,
    ):
        db.add(summary)
        await db.flush()

        return summary

    async def save_record(
        self,
        db: AsyncSession,
        record: ResultRecord,
    ):
        db.add(record)
        await db.flush()

        return record

    async def update_batch(
        self,
        db: AsyncSession,
        batch: ResultBatch,
    ) -> ResultBatch:
        """Persist changes made to an existing result batch."""
        db.add(batch)
        await db.flush()

        return batch

    async def delete_batch_approvals(
        self,
        db: AsyncSession,
        batch_id: UUID,
    ):
        result = await db.execute(
            select(ResultApproval).where(ResultApproval.batch_id == batch_id)
        )

        for approval in result.scalars():
            await db.delete(approval)

        await db.flush()

    async def delete_batch_summaries(
        self,
        db: AsyncSession,
        batch_id: UUID,
    ):
        result = await db.execute(
            select(ResultSummary).where(ResultSummary.batch_id == batch_id)
        )

        for summary in result.scalars():
            await db.delete(summary)

        await db.flush()

    async def delete_batch_records(
        self,
        db: AsyncSession,
        batch_id: UUID,
    ):
        result = await db.execute(
            select(ResultRecord).where(ResultRecord.batch_id == batch_id)
        )

        for record in result.scalars():
            await db.delete(record)

        await db.flush()

    async def get_existing_record(
        self,
        db: AsyncSession,
        batch_id: UUID,
        student_id: UUID,
        subject_id: UUID,
    ):
        result = await db.execute(
            select(ResultRecord).where(
                and_(
                    ResultRecord.batch_id == batch_id,
                    ResultRecord.student_id == student_id,
                    ResultRecord.subject_id == subject_id,
                )
            )
        )

        return result.scalar_one_or_none()

    async def upsert_record(
        self,
        db: AsyncSession,
        *,
        batch_id: UUID,
        school_id: UUID,
        student_id: UUID,
        subject_id: UUID,
        ca_score: int,
        exam_score: int,
        total_score: int,
        grade: str,
        remark: str,
        teacher_comment: str | None,
    ):
        record = await self.get_existing_record(
            db=db,
            batch_id=batch_id,
            student_id=student_id,
            subject_id=subject_id,
        )

        if record:
            record.ca_score = ca_score
            record.exam_score = exam_score
            record.total_score = total_score
            record.grade = grade
            record.remark = remark
            record.teacher_comment = teacher_comment

        else:
            record = ResultRecord(
                school_id=school_id,
                batch_id=batch_id,
                student_id=student_id,
                subject_id=subject_id,
                ca_score=ca_score,
                exam_score=exam_score,
                total_score=total_score,
                grade=grade,
                remark=remark,
                teacher_comment=teacher_comment,
            )

            db.add(record)

        await db.flush()

        return record

    async def get_batch_details(
        self,
        db: AsyncSession,
        batch_id: UUID,
    ):
        result = await db.execute(
            select(ResultBatch)
            .options(
                selectinload(ResultBatch.records).selectinload(ResultRecord.subject),
                selectinload(ResultBatch.records).selectinload(ResultRecord.student),
                selectinload(ResultBatch.summaries),
                selectinload(ResultBatch.approvals).selectinload(ResultApproval.actor),
            )
            .where(ResultBatch.id == batch_id)
        )

        return result.scalar_one_or_none()

    async def get_current_batch(
        self,
        db: AsyncSession,
        school_id: UUID,
        class_id: UUID,
        session_id: UUID,
        term_id: UUID,
    ):
        result = await db.execute(
            select(ResultBatch)
            .options(
                selectinload(ResultBatch.records).selectinload(ResultRecord.subject),
                selectinload(ResultBatch.records).selectinload(ResultRecord.student),
                selectinload(ResultBatch.summaries),
            )
            .where(
                and_(
                    ResultBatch.school_id == school_id,
                    ResultBatch.class_id == class_id,
                    ResultBatch.session_id == session_id,
                    ResultBatch.term_id == term_id,
                )
            )
        )

        return result.scalar_one_or_none()

    async def get_school_batches(
        self,
        db: AsyncSession,
        school_id: UUID,
    ):
        result = await db.execute(
            select(ResultBatch)
            .options(
                selectinload(ResultBatch.school_class),
                selectinload(ResultBatch.session),
                selectinload(ResultBatch.term),
            )
            .where(ResultBatch.school_id == school_id)
            .order_by(ResultBatch.updated_at.desc())
        )

        return result.scalars().all()


result_repository = ResultRepository()
