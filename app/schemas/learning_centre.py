from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LearningSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str
    explanation: str
    key_points: list[str] = Field(default_factory=list)


class SolvedExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    steps: list[str] = Field(default_factory=list)
    answer: str
    explanation: str


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
        if self.question_type == "multiple_choice":
            if len(self.options) < 2:
                raise ValueError("Multiple-choice questions need at least two options.")

            if self.correct_answer not in self.options:
                raise ValueError("The correct answer must match one of the options.")

        if self.question_type == "true_false":
            if self.correct_answer not in ["True", "False"]:
                raise ValueError("True/false answers must be True or False.")

        return self


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


class GlossaryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term: str
    meaning: str


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
