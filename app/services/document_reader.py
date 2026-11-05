# app/utils/document_reader.py
# Keep your existing file location if it is different.

from io import BytesIO
from pathlib import Path

import fitz
import mammoth


class DocumentReader:
    SUPPORTED_EXTENSIONS = {".docx", ".pdf"}

    def read(self, path: str) -> str:
        file_path = Path(path)
        suffix = file_path.suffix.lower()

        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported document type: {suffix}. "
                "Only PDF and DOCX files are supported."
            )

        return self.read_bytes(
            file_path.read_bytes(),
            suffix,
        )

    def read_bytes(self, file_bytes: bytes, suffix: str) -> str:
        suffix = suffix.lower()

        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError("Only PDF and DOCX files are supported.")

        if not file_bytes:
            raise ValueError("The uploaded document is empty.")

        if suffix == ".docx":
            return self._read_docx_bytes(file_bytes)

        return self._read_pdf_bytes(file_bytes)

    def _read_docx_bytes(self, file_bytes: bytes) -> str:
        with BytesIO(file_bytes) as document:
            result = mammoth.convert_to_html(document)

        extracted = result.value.strip()

        if not extracted:
            raise ValueError("No readable content was found in the DOCX document.")

        return extracted

    def _read_pdf_bytes(self, file_bytes: bytes) -> str:
        extracted_pages: list[str] = []

        with fitz.open(
            stream=file_bytes,
            filetype="pdf",
        ) as document:
            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text("text").strip()

                if page_text:
                    extracted_pages.append(f"\n--- Page {page_number} ---\n{page_text}")

        extracted = "\n".join(extracted_pages).strip()

        if not extracted:
            raise ValueError(
                "No readable text was found in this PDF. "
                "It may be a scanned document and require OCR."
            )

        return extracted
