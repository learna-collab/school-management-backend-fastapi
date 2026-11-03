"""cbt assessment allocation and legacy exam migration

Revision ID: 19fe0d19df69
Revises: 6d38d9654a63
Create Date: 2026-11-01 06:21:54.801855
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "19fe0d19df69"
down_revision: Union[str, None] = "6d38d9654a63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


assessment_type_enum = postgresql.ENUM(
    "CA",
    "EXAM",
    name="cbt_assessment_type",
    create_type=False,
)


# These are the four existing exams confirmed for CA1.
CA1_EXAM_IDS = (
    "3419171c-340a-4ff9-9094-36ab5fb4a236",
    "a288d9a4-af27-4706-ad39-1c8ba58008e8",
    "45eaf89b-d019-4610-bd7d-30386acf662f",
    "21f4d8a9-ca74-4854-8c75-530443c95cd6",
)


def upgrade() -> None:
    # ---------------------------------------------------------
    # 1. Create the assessment enum.
    # ---------------------------------------------------------
    assessment_type_enum.create(op.get_bind(), checkfirst=True)

    # ---------------------------------------------------------
    # 2. Add attempt columns.
    # ---------------------------------------------------------
    op.add_column(
        "cbt_attempts",
        sa.Column(
            "attempt_number",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "cbt_attempts",
        sa.Column(
            "contribution_score",
            sa.Numeric(7, 2),
            nullable=True,
        ),
    )

    # Assign attempt numbers independently for each student/exam.
    op.execute(
        sa.text(
            """
            WITH ranked_attempts AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY exam_id, student_id
                        ORDER BY started_at ASC NULLS LAST, id ASC
                    ) AS attempt_number
                FROM cbt_attempts
            )
            UPDATE cbt_attempts AS attempt
            SET attempt_number = ranked_attempts.attempt_number
            FROM ranked_attempts
            WHERE attempt.id = ranked_attempts.id
            """
        )
    )

    # ---------------------------------------------------------
    # 3. Add assessment columns to CBT exams.
    # ---------------------------------------------------------
    op.add_column(
        "cbt_exams",
        sa.Column(
            "assessment_type",
            assessment_type_enum,
            nullable=False,
            server_default="CA",
        ),
    )

    op.add_column(
        "cbt_exams",
        sa.Column(
            "assessment_number",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "cbt_exams",
        sa.Column(
            "assessment_label",
            sa.String(length=100),
            nullable=False,
            server_default="Legacy CBT",
        ),
    )

    op.add_column(
        "cbt_exams",
        sa.Column(
            "contribution_marks",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.add_column(
        "cbt_exams",
        sa.Column(
            "is_result_assessment",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # ---------------------------------------------------------
    # 4. Mark all existing exams as legacy/non-contributing.
    # ---------------------------------------------------------
    op.execute(
        sa.text(
            """
            UPDATE cbt_exams
            SET
                assessment_type = 'CA',
                assessment_number = NULL,
                assessment_label = 'Legacy CBT',
                contribution_marks = 0,
                is_result_assessment = FALSE
            """
        )
    )

    # ---------------------------------------------------------
    # 5. Promote only the four confirmed exams to CA1.
    # ---------------------------------------------------------
    op.execute(
        sa.text(
            """
            UPDATE cbt_exams
            SET
                assessment_type = 'CA',
                assessment_number = 1,
                assessment_label = 'CA1',
                contribution_marks = 20,
                is_result_assessment = TRUE
            WHERE id IN (
                '3419171c-340a-4ff9-9094-36ab5fb4a236',
                'a288d9a4-af27-4706-ad39-1c8ba58008e8',
                '45eaf89b-d019-4610-bd7d-30386acf662f',
                '21f4d8a9-ca74-4854-8c75-530443c95cd6'
            )
            """
        )
    )

    # ---------------------------------------------------------
    # 6. Backfill attempt contribution scores.
    #
    # CA1 attempts are normalized to 20 marks.
    # Legacy attempts receive zero contribution.
    # ---------------------------------------------------------
    op.execute(
        sa.text(
            """
            UPDATE cbt_attempts AS attempt
            SET contribution_score =
                CASE
                    WHEN exam.is_result_assessment = TRUE
                         AND exam.contribution_marks > 0
                         AND attempt.total_marks > 0
                    THEN ROUND(
                        LEAST(
                            GREATEST(COALESCE(attempt.score, 0), 0)
                            / attempt.total_marks
                            * exam.contribution_marks,
                            exam.contribution_marks
                        ),
                        2
                    )
                    ELSE 0
                END
            FROM cbt_exams AS exam
            WHERE attempt.exam_id = exam.id
            """
        )
    )

    # ---------------------------------------------------------
    # 7. Make the new attempt columns non-null.
    # ---------------------------------------------------------
    op.alter_column(
        "cbt_attempts",
        "attempt_number",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="1",
    )

    op.alter_column(
        "cbt_attempts",
        "contribution_score",
        existing_type=sa.Numeric(7, 2),
        nullable=False,
        server_default="0",
    )

    # Remove temporary defaults from exam columns.
    op.alter_column(
        "cbt_exams",
        "assessment_type",
        existing_type=assessment_type_enum,
        server_default=None,
    )

    op.alter_column(
        "cbt_exams",
        "assessment_label",
        existing_type=sa.String(length=100),
        server_default=None,
    )

    op.alter_column(
        "cbt_exams",
        "contribution_marks",
        existing_type=sa.Integer(),
        server_default=None,
    )

    op.alter_column(
        "cbt_exams",
        "is_result_assessment",
        existing_type=sa.Boolean(),
        server_default=None,
    )

    # ---------------------------------------------------------
    # 8. Replace the old attempt uniqueness constraint.
    # ---------------------------------------------------------
    op.drop_constraint(
        "uq_exam_student_attempt",
        "cbt_attempts",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_exam_student_attempt_number",
        "cbt_attempts",
        ["exam_id", "student_id", "attempt_number"],
    )

    # ---------------------------------------------------------
    # 9. Replace assessment indexes.
    #
    # Only official result assessments participate in these
    # uniqueness rules. Legacy exams remain unrestricted.
    # ---------------------------------------------------------
    op.execute("DROP INDEX IF EXISTS uq_cbt_ca_assessment_number")
    op.execute("DROP INDEX IF EXISTS uq_cbt_main_exam")

    op.create_index(
        "uq_cbt_ca_assessment_number",
        "cbt_exams",
        [
            "school_id",
            "session_id",
            "term_id",
            "class_id",
            "subject_id",
            "assessment_number",
        ],
        unique=True,
        postgresql_where=sa.text(
            "is_result_assessment = TRUE AND assessment_type = 'CA'"
        ),
    )

    op.create_index(
        "uq_cbt_main_exam",
        "cbt_exams",
        [
            "school_id",
            "session_id",
            "term_id",
            "class_id",
            "subject_id",
        ],
        unique=True,
        postgresql_where=sa.text(
            "is_result_assessment = TRUE AND assessment_type = 'EXAM'"
        ),
    )

    # ---------------------------------------------------------
    # 10. Allow result batches without a creator.
    # ---------------------------------------------------------
    op.alter_column(
        "result_batches",
        "created_by",
        existing_type=sa.Uuid(),
        nullable=True,
    )


def downgrade() -> None:
    # Remove assessment indexes.
    op.execute("DROP INDEX IF EXISTS uq_cbt_ca_assessment_number")
    op.execute("DROP INDEX IF EXISTS uq_cbt_main_exam")

    # Restore the old attempt uniqueness constraint.
    op.drop_constraint(
        "uq_exam_student_attempt_number",
        "cbt_attempts",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_exam_student_attempt",
        "cbt_attempts",
        ["exam_id", "student_id"],
    )

    # Restore result batch creator requirement.
    op.alter_column(
        "result_batches",
        "created_by",
        existing_type=sa.Uuid(),
        nullable=False,
    )

    # Remove newly added exam columns.
    op.drop_column("cbt_exams", "is_result_assessment")
    op.drop_column("cbt_exams", "contribution_marks")
    op.drop_column("cbt_exams", "assessment_label")
    op.drop_column("cbt_exams", "assessment_number")
    op.drop_column("cbt_exams", "assessment_type")

    # Remove newly added attempt columns.
    op.drop_column("cbt_attempts", "contribution_score")
    op.drop_column("cbt_attempts", "attempt_number")

    # Drop enum.
    assessment_type_enum.drop(op.get_bind(), checkfirst=True)
