from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

# ==========================================================
# LEARNING SECTIONS
# ==========================================================


class LearningSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str
    explanation: str
    key_points: list[str] = Field(default_factory=list)


# ==========================================================
# SOLVED EXAMPLES
# ==========================================================


class SolvedExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    steps: list[str] = Field(default_factory=list)
    answer: str
    explanation: str


# ==========================================================
# PRACTICE QUESTIONS
# ==========================================================


class PracticeQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    question: str

    question_type: Literal[
        "multiple_choice",
        "short_answer",
        "true_false",
    ]

    options: list[str] = Field(default_factory=list)
    correct_answer: str
    explanation: str
    hint: str | None = None
    marks: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_answer(self):
        if not self.question.strip():
            raise ValueError("Question cannot be empty.")

        if not self.correct_answer.strip():
            raise ValueError("Correct answer cannot be empty.")

        if self.question_type == "multiple_choice":
            if len(self.options) < 2:
                raise ValueError("Multiple-choice questions need at least two options.")

            if len(set(self.options)) != len(self.options):
                raise ValueError("Multiple-choice options must be unique.")

            if self.correct_answer not in self.options:
                raise ValueError("The correct answer must match one of the options.")

        elif self.question_type == "true_false":
            if self.options and set(self.options) != {"True", "False"}:
                raise ValueError("True/false options must be True and False.")

            if self.correct_answer not in {"True", "False"}:
                raise ValueError("True/false answers must be True or False.")

        elif self.question_type == "short_answer":
            if self.options:
                raise ValueError("Short-answer questions should not have options.")

        return self


# ==========================================================
# LEARNING ACTIVITIES
# ==========================================================


class LearningActivity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str

    activity_type: Literal[
        "reflection",
        "matching",
        "fill_in_the_blank",
        "practical",
        "discussion",
    ]

    instructions: str
    expected_outcome: str


# ==========================================================
# GLOSSARY
# ==========================================================


class GlossaryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term: str
    meaning: str


# ==========================================================
# COMPLETE AI-GENERATED LEARNING DOCUMENT
# ==========================================================


class LessonLearningDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    introduction: str

    learning_objectives: list[str] = Field(default_factory=list)

    sections: list[LearningSection] = Field(default_factory=list)

    solved_examples: list[SolvedExample] = Field(default_factory=list)

    practice_questions: list[PracticeQuestion] = Field(default_factory=list)

    activities: list[LearningActivity] = Field(default_factory=list)

    glossary: list[GlossaryItem] = Field(default_factory=list)

    summary: str

    source_coverage: Literal[
        "COMPLETE",
        "PARTIAL",
        "INSUFFICIENT",
    ]

    generation_warnings: list[str] = Field(default_factory=list)


class StudentPracticeAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=5000)


class StudentLearningProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    completed_sections: list[str] = Field(default_factory=list)
    completed_activities: list[str] = Field(default_factory=list)
