import json
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from app.schemas.learning_centre import LessonLearningDocument
from app.services.document_reader import DocumentReader


class LearningContentGenerationError(Exception):
    pass


class LearningContentGenerator:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
    ):
        if not api_key:
            raise ValueError(
                "An OpenAI API key is required for learning content generation."
            )

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def get_source_text(self, lesson) -> str:
        # New uploads already have extracted text saved.
        source_text = getattr(lesson, "source_text", None)

        if source_text and source_text.strip():
            return source_text.strip()

        # Older uploads need to be downloaded and extracted.
        if not lesson.file_url:
            raise LearningContentGenerationError(
                "This lesson has no uploaded document."
            )

        parsed_url = urlparse(lesson.file_url)
        suffix = PurePosixPath(unquote(parsed_url.path)).suffix.lower()

        if suffix not in {".pdf", ".docx"}:
            raise LearningContentGenerationError(
                "The original lesson file must be a PDF or DOCX."
            )

        try:
            async with httpx.AsyncClient(
                timeout=60,
                follow_redirects=True,
            ) as client:
                response = await client.get(lesson.file_url)
                response.raise_for_status()

            reader = DocumentReader()
            source_text = reader.read_bytes(
                file_bytes=response.content,
                suffix=suffix,
            )

            # Retain the extracted text for subsequent generation.
            lesson.source_text = source_text

            return source_text

        except LearningContentGenerationError:
            raise
        except Exception as exc:
            raise LearningContentGenerationError(
                "Could not extract text from the original lesson file. "
                "Check that the Cloudinary file is accessible."
            ) from exc

    async def generate(
        self,
        *,
        source_text: str,
        title: str,
        topic: str,
        objectives: str,
        class_name: str,
        subject_name: str,
    ) -> dict:
        source_text = source_text.strip()

        if not source_text:
            raise LearningContentGenerationError(
                "The lesson document contains no extractable text."
            )

        # Avoid silently truncating lesson notes.
        if len(source_text) > 80_000:
            raise LearningContentGenerationError(
                "This lesson document is too large for the current "
                "generation workflow. Please split it into smaller "
                "documents before generating learning content."
            )

        system_prompt = """
You are an experienced school learning-content designer.

Your task is to transform an uploaded school lesson note into
clear, age-appropriate learning material for students.

STRICT SOURCE-GROUNDING RULES:

1. Use the supplied lesson note as your primary and authoritative source.
2. Do not invent facts, definitions, formulas, dates, historical events,
   scientific claims, or curriculum requirements.
3. Do not introduce a topic that is unrelated to the uploaded lesson.
4. You may simplify explanations and provide examples that help students
   understand the supplied material.
5. Any example that requires information not contained in the source
   must be a straightforward illustration of a concept explicitly taught
   in the source. Do not present unsupported facts as source material.
6. If the source does not contain enough information to support a section,
   keep that section limited and explain the limitation in
   generation_warnings.
7. If the source is incomplete, set source_coverage to PARTIAL.
8. If the source is too incomplete to create reliable learning material,
   set source_coverage to INSUFFICIENT and explain why.
9. Do not fabricate learning objectives. Use the supplied objectives
   and derive simple learning outcomes only when directly supported
   by the lesson.
10. Ensure every practice question has one unambiguous correct answer.
11. Check arithmetic and calculations in solved examples.
12. Use language suitable for the specified class level.
13. Do not include markdown code fences around the JSON response.

CONTENT REQUIREMENTS:

- A student-friendly introduction.
- Clear lesson sections with explanations and key points.
- Solved examples with step-by-step solutions where appropriate.
- Practice questions with correct answers and explanations.
- Useful learning activities.
- A glossary of important terms.
- A concise summary.

PRACTICE QUESTION RULES:

- Multiple choice questions must have at least two options.
- The correct answer must exactly match one of the options.
- True/false questions must use boolean answers: true or false.
- Short-answer questions must have a clear expected answer.
- Avoid ambiguous questions.
- Do not create questions that cannot be answered from the lesson.

Return valid JSON matching the requested document structure.
"""

        user_prompt = f"""
Create a complete learning document using the information below.

CLASS LEVEL:
{class_name}

SUBJECT:
{subject_name}

LESSON TITLE:
{title}

TOPIC:
{topic}

EXISTING LEARNING OBJECTIVES:
{objectives}

UPLOADED LESSON NOTE:
---
{source_text}
---

Return a JSON object with these fields:

{{
  "title": "string",
  "introduction": "string",
  "learning_objectives": ["string"],
  "sections": [
    {{
      "heading": "string",
      "explanation": "string",
      "key_points": ["string"]
    }}
  ],
  "solved_examples": [
    {{
      "question": "string",
      "steps": ["string"],
      "answer": "string",
      "explanation": "string"
    }}
  ],
  "practice_questions": [
    {{
      "question_id": "unique string",
      "question": "string",
      "question_type": "multiple_choice",
      "options": ["string"],
      "correct_answer": "string",
      "explanation": "string",
      "hint": "string or null",
      "marks": 1
    }}
  ],
  "activities": [
    {{
      "title": "string",
      "activity_type": "reflection",
      "instructions": "string",
      "expected_outcome": "string"
    }}
  ],
  "glossary": [
    {{
      "term": "string",
      "meaning": "string"
    }}
  ],
  "summary": "string",
  "source_coverage": "COMPLETE",
  "generation_warnings": []
}}

Use only the allowed question types:
multiple_choice, short_answer, true_false.

Use only the allowed activity types:
reflection, matching, fill_in_the_blank, practical, discussion.

If the uploaded lesson is insufficient, do not pretend it is complete.
"""

        try:
            response = await self.client.chat.completions.create(
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
                    "The AI provider returned an empty response."
                )

            data = json.loads(response_text)

            validated = LessonLearningDocument.model_validate(data)

            return validated.model_dump(mode="json")

        except LearningContentGenerationError:
            raise

        except AuthenticationError as exc:
            raise LearningContentGenerationError(
                "OpenAI authentication failed. Check your API key."
            ) from exc

        except RateLimitError as exc:
            raise LearningContentGenerationError(
                "The OpenAI rate limit or available quota was exceeded. "
                "Please try again later."
            ) from exc

        except APITimeoutError as exc:
            raise LearningContentGenerationError(
                "The AI generation request timed out. Please try again."
            ) from exc

        except APIConnectionError as exc:
            raise LearningContentGenerationError(
                "Could not connect to the AI provider."
            ) from exc

        except APIStatusError as exc:
            raise LearningContentGenerationError(
                "The AI provider could not complete the request."
            ) from exc

        except json.JSONDecodeError as exc:
            raise LearningContentGenerationError(
                "The AI provider returned invalid JSON."
            ) from exc

        except Exception as exc:
            raise LearningContentGenerationError(
                "Learning content could not be generated or validated."
            ) from exc

    async def close(self):
        await self.client.close()
