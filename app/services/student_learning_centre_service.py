from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.repositories.student_learning_centre_repository import (
    student_learning_centre_repo,
)


class StudentLearningCentreService:
    def __init__(self):
        self.repo = student_learning_centre_repo

    # ==========================================================
    # COMMON HELPERS
    # ==========================================================

    async def _get_context(self, db, user):
        context = await self.repo.get_student_context(
            db=db,
            user=user,
        )

        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Your current class enrollment or active "
                    "academic period could not be found."
                ),
            )

        return context

    async def _get_content(self, db, user, content_id: UUID):
        context = await self._get_context(db, user)

        if context["custom_class"] or not context["class_template_id"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning content is not available for this class.",
            )

        content = await self.repo.get_published_content(
            db,
            content_id=content_id,
            class_template_id=context["class_template_id"],
            session_id=context["session_id"],
            term_id=context["term_id"],
            school_id=context["school_id"],
        )

        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Published learning content was not found.",
            )

        return context, content

    @staticmethod
    def _student_safe_content(content_data: dict):
        """
        Remove answer keys and explanations from questions.
        The server retains the original content for checking answers.
        """

        safe_content = dict(content_data)

        safe_questions = []

        for question in content_data.get("practice_questions", []):
            safe_questions.append(
                {
                    "question_id": question["question_id"],
                    "question": question["question"],
                    "question_type": question["question_type"],
                    "options": question.get("options", []),
                    "hint": question.get("hint"),
                    "marks": question.get("marks", 1),
                }
            )

        safe_content["practice_questions"] = safe_questions

        return safe_content

    @staticmethod
    def _normalize_answer(value: str):
        return " ".join(value.strip().casefold().split())

    async def _save_progress(self, db, progress):
        await db.commit()
        await db.refresh(progress)
        return progress

    # ==========================================================
    # STUDENT LEARNING CENTRE DASHBOARD
    # ==========================================================

    async def get_learning_centre(
        self,
        db,
        user,
        week_number: int | None = None,
    ):
        context = await self._get_context(db, user)

        if context["custom_class"] or not context["class_template_id"]:
            return {
                "class_name": context["class_name"],
                "session_id": context["session_id"],
                "term_id": context["term_id"],
                "custom_class": True,
                "lessons": [],
                "message": (
                    "Learning Centre content has not been configured for this class."
                ),
            }

        contents = await self.repo.get_published_contents(
            db,
            class_template_id=context["class_template_id"],
            session_id=context["session_id"],
            term_id=context["term_id"],
            school_id=context["school_id"],
            week_number=week_number,
        )

        content_ids = [item.id for item in contents]

        progress_by_content = {}

        if content_ids:
            from sqlalchemy import select

            from app.models.student_learning_progress import (
                StudentLearningProgress,
            )

            result = await db.execute(
                select(StudentLearningProgress).where(
                    StudentLearningProgress.learning_content_id.in_(content_ids),
                    StudentLearningProgress.student_id == user.id,
                    StudentLearningProgress.school_id == user.school_id,
                )
            )

            progress_by_content = {
                item.learning_content_id: item for item in result.scalars().all()
            }

        lessons = []

        for item in contents:
            lesson = item.lesson
            progress = progress_by_content.get(item.id)

            lessons.append(
                {
                    "content_id": item.id,
                    "lesson_id": lesson.id,
                    "title": item.content.get("title") or lesson.title,
                    "topic": lesson.topic,
                    "week_number": lesson.week_number,
                    "introduction": item.content.get("introduction", ""),
                    "source_coverage": item.content.get("source_coverage"),
                    "sections_count": len(item.content.get("sections", [])),
                    "examples_count": len(item.content.get("solved_examples", [])),
                    "questions_count": len(item.content.get("practice_questions", [])),
                    "activities_count": len(item.content.get("activities", [])),
                    "progress": {
                        "status": (progress.status if progress else "NOT_STARTED"),
                        "score": (progress.score if progress else None),
                        "attempts_count": (progress.attempts_count if progress else 0),
                    },
                }
            )

        return {
            "class_name": context["class_name"],
            "session_id": context["session_id"],
            "term_id": context["term_id"],
            "custom_class": False,
            "lessons": lessons,
        }

    # ==========================================================
    # GET ONE LESSON
    # ==========================================================

    async def get_lesson_content(
        self,
        db,
        user,
        content_id: UUID,
    ):
        context, content = await self._get_content(
            db,
            user,
            content_id,
        )

        progress = await self.repo.get_or_create_progress(
            db,
            content_id=content.id,
            student_id=user.id,
            school_id=context["school_id"],
        )

        await db.commit()

        return {
            "id": content.id,
            "lesson_id": content.lesson_id,
            "version": content.version,
            "status": content.status,
            "lesson": {
                "title": content.lesson.title,
                "topic": content.lesson.topic,
                "week_number": content.lesson.week_number,
                "file_url": content.lesson.file_url,
            },
            "content": self._student_safe_content(content.content),
            "progress": {
                "status": progress.status,
                "score": progress.score,
                "attempts_count": progress.attempts_count,
                "activity_progress": progress.activity_progress or {},
            },
        }

    # ==========================================================
    # SAVE SECTION / ACTIVITY PROGRESS
    # ==========================================================

    async def update_progress(
        self,
        db,
        user,
        content_id: UUID,
        completed_sections: list[str],
        completed_activities: list[str],
    ):
        context, content = await self._get_content(
            db,
            user,
            content_id,
        )

        content_data = content.content

        valid_sections = {item["heading"] for item in content_data.get("sections", [])}

        valid_activities = {
            item["title"] for item in content_data.get("activities", [])
        }

        if not set(completed_sections).issubset(valid_sections):
            raise HTTPException(
                status_code=422,
                detail="One or more section names are invalid.",
            )

        if not set(completed_activities).issubset(valid_activities):
            raise HTTPException(
                status_code=422,
                detail="One or more activity names are invalid.",
            )

        progress = await self.repo.get_or_create_progress(
            db,
            content_id=content.id,
            student_id=user.id,
            school_id=context["school_id"],
        )

        activity_progress = dict(progress.activity_progress or {})

        existing_sections = set(activity_progress.get("completed_sections", []))
        existing_activities = set(activity_progress.get("completed_activities", []))

        existing_sections.update(completed_sections)
        existing_activities.update(completed_activities)

        activity_progress["completed_sections"] = sorted(existing_sections)
        activity_progress["completed_activities"] = sorted(existing_activities)

        progress.activity_progress = activity_progress
        progress.status = "IN_PROGRESS"

        total_sections = len(content_data.get("sections", []))
        total_activities = len(content_data.get("activities", []))
        total_questions = len(content_data.get("practice_questions", []))

        answered_questions = activity_progress.get("question_attempts", {})

        all_sections_completed = len(existing_sections) >= total_sections
        all_activities_completed = len(existing_activities) >= total_activities
        all_questions_answered = len(answered_questions) >= total_questions

        if (
            all_sections_completed
            and all_activities_completed
            and all_questions_answered
        ):
            progress.status = "COMPLETED"

        await self._save_progress(db, progress)

        return {
            "status": progress.status,
            "activity_progress": progress.activity_progress,
            "score": progress.score,
        }

    # ==========================================================
    # CHECK PRACTICE ANSWER
    # ==========================================================

    async def submit_practice_answer(
        self,
        db,
        user,
        content_id: UUID,
        question_id: str,
        answer: str,
    ):
        context, content = await self._get_content(
            db,
            user,
            content_id,
        )

        question = next(
            (
                item
                for item in content.content.get("practice_questions", [])
                if item.get("question_id") == question_id
            ),
            None,
        )

        if not question:
            raise HTTPException(
                status_code=404,
                detail="Practice question not found.",
            )

        question_type = question["question_type"]

        if question_type == "multiple_choice":
            if answer not in question.get("options", []):
                raise HTTPException(
                    status_code=422,
                    detail="Select one of the available options.",
                )

        elif question_type == "true_false":
            if answer not in ("True", "False"):
                raise HTTPException(
                    status_code=422,
                    detail="Answer must be True or False.",
                )

        progress = await self.repo.get_or_create_progress(
            db,
            content_id=content.id,
            student_id=user.id,
            school_id=context["school_id"],
        )

        # Lock the student's progress record before updating attempts.
        locked_progress = await self.repo.get_progress_for_update(
            db,
            content_id=content.id,
            student_id=user.id,
            school_id=context["school_id"],
        )

        if locked_progress:
            progress = locked_progress

        activity_progress = dict(progress.activity_progress or {})
        question_attempts = dict(activity_progress.get("question_attempts", {}))

        previous = dict(question_attempts.get(question_id, {}))

        expected_answer = str(question["correct_answer"])

        if question_type == "short_answer":
            is_correct = self._normalize_answer(answer) == self._normalize_answer(
                expected_answer
            )
        else:
            is_correct = answer == expected_answer

        attempts = int(previous.get("attempts", 0)) + 1

        question_attempts[question_id] = {
            "attempts": attempts,
            "is_correct": is_correct,
            "last_answer": answer,
        }

        activity_progress["question_attempts"] = question_attempts

        progress.activity_progress = activity_progress
        progress.attempts_count = (progress.attempts_count or 0) + 1
        progress.status = "IN_PROGRESS"

        questions = content.content.get("practice_questions", [])
        total_questions = len(questions)

        answered_count = len(question_attempts)
        correct_count = sum(
            1 for item in question_attempts.values() if item.get("is_correct")
        )

        progress.score = (
            round((correct_count / total_questions) * 100) if total_questions else None
        )

        if total_questions and answered_count >= total_questions:
            sections = content.content.get("sections", [])
            activities = content.content.get("activities", [])

            completed_sections = set(activity_progress.get("completed_sections", []))
            completed_activities = set(
                activity_progress.get("completed_activities", [])
            )

            if len(completed_sections) >= len(sections) and len(
                completed_activities
            ) >= len(activities):
                progress.status = "COMPLETED"

        await self._save_progress(db, progress)

        # The correct answer and explanation are only returned
        # after the student has submitted an answer.
        return {
            "question_id": question_id,
            "is_correct": is_correct,
            "submitted_answer": answer,
            "correct_answer": expected_answer,
            "explanation": question.get("explanation", ""),
            "hint": question.get("hint"),
            "attempts": attempts,
            "score": progress.score,
            "progress_status": progress.status,
        }

    # ==========================================================
    # GET PRIVATE PROGRESS
    # ==========================================================

    async def get_lesson_progress(
        self,
        db,
        user,
        content_id: UUID,
    ):
        context, content = await self._get_content(
            db,
            user,
            content_id,
        )

        progress = await self.repo.get_progress(
            db,
            content_id=content.id,
            student_id=user.id,
            school_id=context["school_id"],
        )

        if not progress:
            return {
                "status": "NOT_STARTED",
                "score": None,
                "attempts_count": 0,
                "activity_progress": {},
            }

        return {
            "status": progress.status,
            "score": progress.score,
            "attempts_count": progress.attempts_count,
            "activity_progress": progress.activity_progress or {},
        }


student_learning_centre_service = StudentLearningCentreService()
