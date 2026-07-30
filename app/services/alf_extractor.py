import re

from app.schemas.parser import ParsedALF


class ALFExtractor:
    def build(
        self,
        *,
        independent_reading=None,
        mini_lesson=None,
        case_study=None,
        project_based_learning=None,
        evaluation=None,
    ) -> ParsedALF:
        return ParsedALF(
            independent_reading=independent_reading,
            mini_lesson=mini_lesson,
            case_study=case_study,
            project_based_learning=project_based_learning,
            evaluation=evaluation,
        )

    def extract(self, text: str) -> ParsedALF:
        def grab(patterns: list[str]):
            for pattern in patterns:
                match = re.search(
                    pattern,
                    text,
                    re.IGNORECASE | re.DOTALL,
                )
                if match:
                    return " ".join(match.group(1).split()).strip()
            return None

        independent_reading = grab(
            [
                r"Independent Reading[:\s]+(.*?)(?=\n[A-Z][A-Za-z ]{2,}|\Z)",
            ]
        )

        mini_lesson = grab(
            [
                r"Mini Lesson[:\s]+(.*?)(?=\n\d+\s*mins|\n[A-Z][A-Za-z ]{2,}|\Z)",
            ]
        )

        case_study = grab(
            [
                r"CASE STUDY\s*(.*?)(?=EVALUATION|\Z)",
                r"Case Study[:\s]+(.*?)(?=EVALUATION|\Z)",
            ]
        )

        project_based_learning = grab(
            [
                r"Project[- ]Based Learning[:\s]+(.*?)(?=\n[A-Z][A-Za-z ]{2,}|\Z)",
            ]
        )

        evaluation = grab(
            [
                r"EVALUATION\s*(.*?)(?=COMPREHENSIVE TEACHER'S NOTE|\Z)",
            ]
        )

        return ParsedALF(
            independent_reading=independent_reading,
            mini_lesson=mini_lesson,
            case_study=case_study,
            project_based_learning=project_based_learning,
            evaluation=evaluation,
        )
