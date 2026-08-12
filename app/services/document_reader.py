from pathlib import Path

import fitz
import mammoth


class DocumentReader:
    def read(self, path: str) -> str:
        suffix = Path(path).suffix.lower()

        if suffix == ".docx":
            return self.read_docx(path)

        if suffix == ".pdf":
            return self.read_pdf(path)

        raise ValueError("Unsupported document type")

    # DOCX → HTML (preserves headings, lists, tables, bold, etc.)
    def read_docx(self, path: str) -> str:
        with open(path, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file)

        return result.value

    # PDF → plain text fallback
    def read_pdf(self, path: str) -> str:
        document = fitz.open(path)
        text = ""

        for page in document:
            text += page.get_text()

        return text
