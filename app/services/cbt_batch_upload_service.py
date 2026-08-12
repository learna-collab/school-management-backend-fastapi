from io import BytesIO
from uuid import UUID

import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cbt_exam import CBTExam
from app.models.cbt_question import CBTQuestion, QuestionType
from app.models.cbt_question_option import CBTQuestionOption


class CBTBatchUploadService:
    REQUIRED_COLUMNS = [
        "question_text",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_option",
        "marks",
    ]

    async def upload_questions(
        self,
        *,
        db: AsyncSession,
        exam_id: UUID,
        file: UploadFile,
    ):
        # Verify exam exists
        result = await db.execute(select(CBTExam).where(CBTExam.id == exam_id))
        exam = result.scalar_one_or_none()

        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        filename = (file.filename or "").lower()
        content = await file.read()

        # Read file
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(BytesIO(content))
            elif filename.endswith(".xlsx"):
                df = pd.read_excel(BytesIO(content))
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Only .xlsx and .csv files are supported",
                )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Unable to read file: {str(e)}",
            )

        # Normalize headers
        df.columns = [str(c).strip().lower() for c in df.columns]

        missing = [c for c in self.REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing columns: {', '.join(missing)}",
            )

        # Determine next question order
        existing_result = await db.execute(
            select(CBTQuestion).where(CBTQuestion.exam_id == exam_id)
        )
        existing_questions = existing_result.scalars().all()
        next_order = len(existing_questions) + 1

        created = 0
        skipped = 0

        for _, row in df.iterrows():
            question_text = str(row.get("question_text", "")).strip()

            if not question_text:
                skipped += 1
                continue

            correct = str(row.get("correct_option", "")).strip().upper()

            if correct not in {"A", "B", "C", "D"}:
                skipped += 1
                continue

            try:
                marks = int(row.get("marks", 1))
            except Exception:
                marks = 1

            # Create question
            question = CBTQuestion(
                exam_id=exam_id,
                question=question_text,
                type=QuestionType.OBJECTIVE,
                marks=marks,
                question_order=next_order,
            )

            db.add(question)
            await db.flush()

            # Create options
            options = [
                ("A", str(row.get("option_a", "")).strip()),
                ("B", str(row.get("option_b", "")).strip()),
                ("C", str(row.get("option_c", "")).strip()),
                ("D", str(row.get("option_d", "")).strip()),
            ]

            for label, text in options:
                option = CBTQuestionOption(
                    question_id=question.id,
                    option_label=label,
                    option_text=text,
                    is_correct=(label == correct),
                )
                db.add(option)

            created += 1
            next_order += 1

        await db.commit()

        return {
            "success": True,
            "message": f"{created} questions uploaded successfully",
            "created": created,
            "skipped": skipped,
        }


cbt_batch_upload_service = CBTBatchUploadService()
