from io import BytesIO
from pathlib import Path
from time import monotonic

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.services.ocr import OcrError, extract_page_text

from app.schemas.documents import DocumentPage

MAX_PDF_PAGES = 50
MAX_TEXT_CHARACTERS = 50_000

MAX_OCR_PAGES = 5
OCR_BUDGET_SECONDS = 120

class DocumentParseError(ValueError):
    pass

def parse_document(
    data: bytes,
    filename: str,
) -> list[DocumentPage]:
    extension = Path(filename).suffix.lower()

    if extension in {".txt", ".md"}:
        pages = parse_text(data)
    elif extension == ".pdf":
        pages = parse_pdf(data)
    else:
        raise DocumentParseError(
            "Supported formats are TXT, Markdown and PDF."
        )

    if not any(page.text.strip() for page in pages):
        raise DocumentParseError(
            "No readable text found after text extraction and OCR."
        )

    if any("\x00" in page.text for page in pages):
        raise DocumentParseError(
            "The document contains unsupported null characters."
        )

    if sum(len(page.text) for page in pages) > MAX_TEXT_CHARACTERS:
        raise DocumentParseError(
            "The document exceeds 50,000 extracted characters."
        )

    return pages


def parse_text(data: bytes) -> list[DocumentPage]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DocumentParseError(
            "Text files must use UTF-8."
        ) from error

    return [DocumentPage(page=1, text=text)]


def parse_pdf(data: bytes) -> list[DocumentPage]:
    try:
        reader = PdfReader(BytesIO(data))

        if reader.is_encrypted:
            raise DocumentParseError(
                "Encrypted PDFs are not supported."
            )

        if len(reader.pages) > MAX_PDF_PAGES:
            raise DocumentParseError(
                f"PDFs must contain at most {MAX_PDF_PAGES} pages."
            )

        pages = []
        total_characters = 0
        ocr_pages = 0
        ocr_started = None

        for number, pdf_page in enumerate(reader.pages, start=1):
            text = pdf_page.extract_text() or ""
            extraction_method = "direct"

            if not text.strip():
                if ocr_pages >= MAX_OCR_PAGES:
                    raise DocumentParseError(
                        f"OCR is limited to {MAX_OCR_PAGES} pages per file."
                    )

                if ocr_started is None:
                    ocr_started = monotonic()

                if monotonic() - ocr_started >= OCR_BUDGET_SECONDS:
                    raise DocumentParseError(
                        "The document exceeded its OCR processing budget."
                    )

                try:
                    text = extract_page_text(data, number)
                except OcrError as error:
                    raise DocumentParseError(
                        f"Cannot read PDF page {number}: {error}"
                    ) from error

                extraction_method = "ocr"
                ocr_pages += 1

            total_characters += len(text)

            if total_characters > MAX_TEXT_CHARACTERS:
                raise DocumentParseError(
                    "The PDF exceeds 50,000 extracted characters."
                )

            pages.append(
                DocumentPage(
                    page=number,
                    text=text,
                    extraction_method=extraction_method,
                )
            )

        return pages

    except DocumentParseError:
        raise
    except (
        PyPdfError,
        ValueError,
        TypeError,
        KeyError,
        IndexError,
    ) as error:
        raise DocumentParseError(
            "Cannot read this PDF. It may be damaged or invalid."
        ) from error
