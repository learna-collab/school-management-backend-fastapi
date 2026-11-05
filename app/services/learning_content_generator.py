import json

from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
)

from app.schemas.learning_centre import LessonLearningDocument


class LearningContentGenerationError(Exception):
    """Raised when AI learning content cannot be generated."""


class LearningContentGenerator:
    def __init__(
        self,
        api_key: str | None,
        model: str = "gpt-4.1-mini",
    ):
        if not api_key:
            raise LearningContentGenerationError(
                "OpenAI API key is not configured. "
                "Set OPENAI_API_KEY in your backend environment."
            )

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(
        self,
        *,
        source_text: str,
        lesson_title: str,
        topic: str,
        objectives: str,
        class_name: str,
        subject_name: str,
        academic_level: str,
    ) -> dict:
        if not source_text or not source_text.strip():
            raise LearningContentGenerationError(
                "The original lesson document contains no readable text."
            )

        system_prompt = """
You are an educational content assistant for a school Learning Centre.

Your task is to transform an uploaded lesson note into clear,
age-appropriate learning material for students.

STRICT SOURCE-GROUNDING RULES:

1. Treat the supplied lesson document as the primary and authoritative source.
2. Do not invent facts, definitions, formulas, dates, examples, or claims
   that are not supported by the document.
3. Do not silently fill gaps in the source using your general knowledge.
4. You may simplify wording and explain concepts in student-friendly language,
   but preserve the meaning of the source.
5. If an important concept is mentioned but not explained adequately,
   identify that limitation in generation_warnings.
6. If the source is insufficient to create reliable learning content,
   set source_coverage to INSUFFICIENT.
7. If only some sections are adequately supported,
   set source_coverage to PARTIAL.
8. Set source_coverage to COMPLETE only when the source adequately supports
   the generated learning material.
9. Do not invent numerical examples. Any numerical example you create
   must be directly supported by the source and its calculations must be correct.
10. Every practice question must have an answer supported by the source.
11. Every multiple-choice correct_answer must exactly match one of its options.
12. Make the explanation for every correct answer understandable to the
    intended student age and academic level.
13. Avoid questions whose answers are not available in the source.
14. Do not include teacher-only notes or administrative instructions
    in student-facing content.
15. Do not mention that you are an AI.

CONTENT REQUIREMENTS:

- Write a student-friendly introduction.
- Organize explanations into meaningful sections.
- Include key points where supported by the source.
- Include solved examples only where the source supports them.
- Create practice questions where sufficient information exists.
- Include hints and explanations for questions.
- Create age-appropriate activities where supported by the lesson.
- Include a glossary for important terms where appropriate.
- Keep the language appropriate for the specified academic level.
- Do not pad the response with generic or unrelated content.

Return valid JSON matching the requested schema.
"""

        user_prompt = f"""
Prepare a student Learning Centre lesson using the following information.

LESSON METADATA

Title: {lesson_title}
Topic: {topic}
Subject: {subject_name}
Class: {class_name}
Academic level: {academic_level}
Learning objectives: {objectives}

ORIGINAL UPLOADED LESSON DOCUMENT

The content below is the actual extracted content of the uploaded document.
It may contain HTML markup from a DOCX file.

<lesson_source>
{source_text}
</lesson_source>

Generate structured student learning content.

The content must remain grounded in the uploaded document.
If the document does not support a section, return an empty list for that
section rather than inventing material.

For insufficient source material, explain the limitation in
generation_warnings and set source_coverage accordingly.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            )

            response_text = response.choices[0].message.content

            if not response_text:
                raise LearningContentGenerationError(
                    "OpenAI returned an empty response."
                )

            generated_data = json.loads(response_text)

            validated_content = LessonLearningDocument.model_validate(generated_data)

            return validated_content.model_dump(mode="json")

        except AuthenticationError as exc:
            raise LearningContentGenerationError(
                "OpenAI authentication failed. Check OPENAI_API_KEY."
            ) from exc

        except APIConnectionError as exc:
            raise LearningContentGenerationError(
                "Could not connect to the OpenAI API. Please try again."
            ) from exc

        except APIStatusError as exc:
            raise LearningContentGenerationError(
                f"OpenAI API returned an error: {exc.status_code}."
            ) from exc

        except json.JSONDecodeError as exc:
            raise LearningContentGenerationError(
                "The AI returned an invalid JSON response."
            ) from exc

        except Exception as exc:
            if isinstance(
                exc,
                LearningContentGenerationError,
            ):
                raise

            raise LearningContentGenerationError(
                f"Could not validate generated lesson content: {exc}"
            ) from exc
