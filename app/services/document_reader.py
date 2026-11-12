from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

import fitz
import mammoth


class _HTMLTextExtractor(HTMLParser):
    """Convert Mammoth's HTML output into readable plain text."""

    BLOCK_TAGS = {
        "p", "div", "br", "h1", "h2", "h3",
        "h4", "h5", "h6", "li", "tr",
    }

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self) -> str:
        return "\n".join(
            line.strip()
            for line in "".join(self.parts).splitlines()
            if line.strip()
        )


class DocumentReader:
    SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

    def read(self, path: str) -> str:
        file_path = Path(path)
        suffix = file_path.suffix.lower()

        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                "Unsupported document type. Upload a PDF or DOCX file."
            )

        return self.read_bytes(
            file_bytes=file_path.read_bytes(),
            suffix=suffix,
        )

    def read_bytes(self, file_bytes: bytes, suffix: str) -> str:
        suffix = suffix.lower()

        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                "Unsupported document type. Upload a PDF or DOCX file."
            )

        if not file_bytes:
            raise ValueError("The uploaded document is empty.")

        if suffix == ".pdf":
            extracted_text = self._read_pdf(file_bytes)
        else:
            extracted_text = self._read_docx(file_bytes)

        extracted_text = self._clean_text(extracted_text)

        if not extracted_text:
            raise ValueError(
                "No readable text was found in this document. "
                "If this is a scanned PDF, it may require OCR."
            )

        return extracted_text

    def _read_pdf(self, file_bytes: bytes) -> str:
        try:
            with fitz.open(
                stream=file_bytes,
                filetype="pdf",
            ) as document:
                return "\n\n".join(
                    page.get_text("text")
                    for page in document
                )
        except Exception as exc:
            raise ValueError(
                "The PDF document could not be read."
            ) from exc

    def _read_docx(self, file_bytes: bytes) -> str:
        try:
            result = mammoth.convert_to_html(
                BytesIO(file_bytes)
            )

            extractor = _HTMLTextExtractor()
            extractor.feed(result.value)

            return extractor.get_text()
        except Exception as exc:
            raise ValueError(
                "The DOCX document could not be read."
            ) from exc

    @staticmethod
    def _clean_text(value: str) -> str:
        return "\n".join(
            line.strip()
            for line in value.replace("\x00", "").splitlines()
            if line.strip()
        )