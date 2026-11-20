import json
import logging
import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

import cloudinary
import cloudinary.utils
import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)
from pydantic import ValidationError

from app.core.config import settings

from app.schemas.learning_centre import LearningActivity, LessonLearningDocument
from app.services.document_reader import DocumentReader

logger = logging.getLogger(__name__)


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

    @staticmethod
    def _build_signed_cloudinary_url(file_url: str, suffix: str) -> str:
        """Build a signed URL for a stored Cloudinary raw asset.

        The URL is accepted only when it belongs to this application's
        configured Cloudinary cloud. The API secret remains server-side.
        """
        parsed = urlparse(file_url)

        if parsed.scheme != "https" or parsed.hostname != "res.cloudinary.com":
            raise LearningContentGenerationError(
                "The lesson document URL is not a valid Cloudinary HTTPS URL."
            )

        parts = [unquote(part) for part in parsed.path.split("/") if part]

        if len(parts) < 5:
            raise LearningContentGenerationError(
                "The Cloudinary lesson document URL has an invalid format."
            )

        cloud_name, resource_type, delivery_type = parts[:3]

        if cloud_name != settings.cloudinary_cloud_name:
            raise LearningContentGenerationError(
                "The lesson document does not belong to the configured Cloudinary account."
            )

        if resource_type != "raw":
            raise LearningContentGenerationError(
                "The lesson document is not stored as a Cloudinary raw asset."
            )

        if delivery_type not in {"upload", "private", "authenticated"}:
            raise LearningContentGenerationError(
                "The Cloudinary lesson document has an unsupported delivery type."
            )

        asset_parts = parts[3:]
        version = None

        if asset_parts and re.fullmatch(r"v\d+", asset_parts[0]):
            version = int(asset_parts.pop(0)[1:])

        public_id = "/".join(asset_parts)

        if not public_id or not public_id.lower().endswith(suffix):
            raise LearningContentGenerationError(
                "The Cloudinary public ID does not match the lesson document format."
            )

        if not all((
            settings.cloudinary_cloud_name,
            settings.cloudinary_api_key,
            settings.cloudinary_api_secret,
        )):
            raise LearningContentGenerationError(
                "Cloudinary credentials are not fully configured."
            )

        # Configure the official SDK from the same settings used by uploads.
        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True,
        )

        try:
            signed_url, _ = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type="raw",
                type=delivery_type,
                version=version,
                secure=True,
                sign_url=True,
            )
        except Exception as exc:
            logger.exception("Could not create a signed Cloudinary URL.")
            raise LearningContentGenerationError(
                "Could not create an authenticated download URL for the lesson document."
            ) from exc

        return signed_url

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
            signed_url = self._build_signed_cloudinary_url(
                lesson.file_url,
                suffix,
            )

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=15.0),
                follow_redirects=True,
            ) as client:
                response = await client.get(signed_url)

                if response.status_code == 401:
                    cloudinary_error = response.headers.get("x-cld-error")
                    logger.error(
                        "Cloudinary denied signed raw-file delivery. "
                        "Status: %s; Cloudinary error: %s",
                        response.status_code,
                        cloudinary_error,
                    )
                    raise LearningContentGenerationError(
                        "Cloudinary rejected the signed document download. "
                        "Verify the asset delivery type and Cloudinary API credentials."
                    )

                response.raise_for_status()
                file_bytes = response.content

            reader = DocumentReader()
            source_text = reader.read_bytes(
                file_bytes=file_bytes,
                suffix=suffix,
            )

            # Keep extracted text on the ORM lesson. The service commits it
            # with the generated content; future runs will not download again.
            lesson.source_text = source_text

            logger.info(
                "Extracted and populated source_text for legacy lesson %s.",
                getattr(lesson, "id", "unknown"),
            )

            return source_text

        except LearningContentGenerationError:
            raise

        except httpx.HTTPStatusError as exc:
            logger.exception(
                "Cloudinary document download failed with HTTP %s.",
                exc.response.status_code,
            )
            raise LearningContentGenerationError(
                "Could not download the original lesson document from Cloudinary. "
                f"Cloudinary returned HTTP {exc.response.status_code}."
            ) from exc

        except Exception as exc:
            logger.exception("Failed to extract text from lesson document.")
            raise LearningContentGenerationError(
                "Could not extract text from the original lesson file. "
                "Check the Cloudinary asset and document format."
            ) from exc

    @staticmethod
    def _normalize_practice_answers(data: dict) -> dict:
        """
        Ensure every practice question has a string correct_answer.

        The database/schema expects correct_answer to be a string,
        including for true/false questions.
        """

        practice_questions = data.get("practice_questions", [])

        if not isinstance(practice_questions, list):
            raise LearningContentGenerationError(
                "The AI generated an invalid practice questions structure."
            )

        for index, question in enumerate(practice_questions):
            if not isinstance(question, dict):
                raise LearningContentGenerationError(
                    f"Practice question {index + 1} has an invalid structure."
                )

            answer = question.get("correct_answer")

            if answer is None:
                raise LearningContentGenerationError(
                    f"Practice question {index + 1} has no correct answer."
                )

            # Convert boolean answers to the exact string representation.
            if isinstance(answer, bool):
                question["correct_answer"] = "True" if answer else "False"

            # Convert numeric answers to strings.
            elif isinstance(answer, (int, float)):
                question["correct_answer"] = str(answer)

            # Reject structures that cannot safely represent an answer.
            elif isinstance(answer, (list, dict)):
                raise LearningContentGenerationError(
                    f"Practice question {index + 1} has an invalid "
                    "correct answer format."
                )

            elif not isinstance(answer, str):
                raise LearningContentGenerationError(
                    f"Practice question {index + 1} has an unsupported "
                    "correct answer format."
                )

            # Reject empty answers.
            elif not answer.strip():
                raise LearningContentGenerationError(
                    f"Practice question {index + 1} has an empty correct answer."
                )

            # Validate question-type-specific answer formats.
            question_type = question.get("question_type")

            if question_type == "true_false":
                normalized_answer = question["correct_answer"].strip().lower()

                if normalized_answer not in {"true", "false"}:
                    raise LearningContentGenerationError(
                        f"True/false question {index + 1} must have "
                        "a correct answer of 'True' or 'False'."
                    )

                question["correct_answer"] = (
                    "True" if normalized_answer == "true" else "False"
                )

                # Ensure the options conform to the Pydantic schema.
                options = question.get("options", [])

                if options not in ([], ["True", "False"]):
                    raise LearningContentGenerationError(
                        f"True/false question {index + 1} must have "
                        "either no options or exactly ['True', 'False']."
                    )

            elif question_type == "multiple_choice":
                options = question.get("options")

                if not isinstance(options, list) or len(options) < 2:
                    raise LearningContentGenerationError(
                        f"Multiple-choice question {index + 1} "
                        "must have at least two options."
                    )

                answer = question["correct_answer"].strip()

                # The correct answer must match one of the supplied options.
                if not any(
                    isinstance(option, str) and option.strip() == answer
                    for option in options
                ):
                    raise LearningContentGenerationError(
                        f"Multiple-choice question {index + 1} has a "
                        "correct answer that does not match any option."
                    )

                question["correct_answer"] = answer

            else:
                question["correct_answer"] = question["correct_answer"].strip()

        return data

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

        # The Pydantic schema remains authoritative. These values are also
        # included in the prompt so the model receives the exact allowed set.
        activity_literal = LearningActivity.model_fields["activity_type"].annotation
        allowed_activity_types = list(activity_literal.__args__)
        activity_types_text = "\n".join(
            f"- {activity_type}" for activity_type in allowed_activity_types
        )

        system_prompt = f"""
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
        - True/false questions must use the strings "True" or "False"
          as correct_answer. NEVER return boolean values true or false.
        - Short-answer questions must have a clear expected answer.
        - The correct_answer field MUST ALWAYS be a string.
        - Never return correct_answer as a number, boolean, array, object, or null.
        - Never omit correct_answer.
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
                    "options": [
                        "Option A",
                        "Option B",
                        "Option C",
                        "Option D"
                    ],
                    "correct_answer": "Option B",
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

        - multiple_choice
        - short_answer
        - true_false

        IMPORTANT CORRECT ANSWER FORMATS:

        Multiple choice:
        - correct_answer must be a string.
        - It must exactly match one of the options.

        Example:
        "correct_answer": "Photosynthesis"

        True/false:
        - correct_answer must be the string "True" or "False".
        - Never return true or false as JSON boolean values.

        Example:
        "correct_answer": "True"

        Short answer:
        - correct_answer must be a string containing the expected answer.

        Example:
        "correct_answer": "The process by which plants make their food."

        Never return correct_answer as a boolean, number, array, object, or null.

        Use only the allowed activity types:

        {activity_types_text}

        If the uploaded lesson is insufficient, do not pretend it is complete.
        """

        validation_feedback = None
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            current_user_prompt = user_prompt

            if validation_feedback:
                current_user_prompt += f"""

                VALIDATION RETRY — ATTEMPT {attempt}/{max_attempts}

                Your previous response failed backend validation.
                Correct every issue listed below and return the COMPLETE
                learning document. Do not omit sections, weaken the schema,
                or introduce information unsupported by the source lesson.

                VALIDATION ERRORS:
                {validation_feedback}

                The activity_type field must exactly match one of the allowed
                values in the original instructions. Do not invent synonyms.
                Return valid JSON only.
                """

            logger.info(
                "Generating learning content. Attempt %s/%s. Lesson: %s",
                attempt,
                max_attempts,
                title,
            )

            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": current_user_prompt},
                    ],
                )

                response_text = response.choices[0].message.content
                if not response_text:
                    raise LearningContentGenerationError(
                        "The AI provider returned an empty response."
                    )

                data = json.loads(response_text)
                if not isinstance(data, dict):
                    raise LearningContentGenerationError(
                        "The AI provider returned an invalid document structure."
                    )

                data = self._normalize_practice_answers(data)
                validated = LessonLearningDocument.model_validate(data)

                logger.info(
                    "Learning content generated and validated successfully. "
                    "Lesson: %s. Attempt: %s",
                    title,
                    attempt,
                )
                return validated.model_dump(mode="json")

            except ValidationError as exc:
                errors = exc.errors(include_input=False)
                validation_feedback = "\n".join(
                    f"- Field: {'.'.join(str(part) for part in error.get('loc', ())) }\n"
                    f"  Error: {error.get('msg', 'Invalid value')}\n"
                    f"  Type: {error.get('type', 'validation_error')}"
                    for error in errors
                )

                logger.warning(
                    "Learning content failed Pydantic validation. "
                    "Lesson: %s. Attempt: %s/%s. Errors: %s",
                    title,
                    attempt,
                    max_attempts,
                    validation_feedback,
                )

                if attempt < max_attempts:
                    logger.info(
                        "Retrying learning content generation after validation failure."
                    )
                    continue

                raise LearningContentGenerationError(
                    "The AI generated learning content that does not match "
                    "the required document structure after "
                    f"{max_attempts} attempts. Check backend logs for details."
                ) from exc

            except json.JSONDecodeError as exc:
                validation_feedback = (
                    "The previous response was not valid JSON. Return a complete, "
                    "syntactically valid JSON object matching the requested structure."
                )
                logger.warning(
                    "AI returned invalid JSON. Lesson: %s. Attempt: %s/%s",
                    title,
                    attempt,
                    max_attempts,
                )
                if attempt < max_attempts:
                    continue
                raise LearningContentGenerationError(
                    f"The AI provider returned invalid JSON after {max_attempts} attempts."
                ) from exc

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

            except Exception as exc:
                logger.exception(
                    "Unexpected learning content generation failure. "
                    "Error type: %s. Error: %s",
                    type(exc).__name__,
                    str(exc),
                )
                raise LearningContentGenerationError(
                    "Learning content could not be generated or validated. "
                    "Check the backend logs for details."
                ) from exc

        raise LearningContentGenerationError(
            "Learning content generation failed after all attempts."
        )

    async def close(self):
        await self.client.close()
