import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


MAX_PDF_BYTES = 1024 * 1024
RENDER_TIMEOUT_SECONDS = 30
OCR_TIMEOUT_SECONDS = 30
MAX_IMAGE_SIDE = 2000


class OcrError(ValueError):
    pass


def _run_command(
    command: list[str],
    *,
    timeout: int,
    operation: str,
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except FileNotFoundError as error:
        raise OcrError(
            "OCR tools are unavailable. Rebuild the backend Docker image."
        ) from error
    except subprocess.TimeoutExpired as error:
        raise OcrError(
            f"{operation} exceeded its time limit."
        ) from error
    except subprocess.CalledProcessError as error:
        raise OcrError(
            f"{operation} failed."
        ) from error


def extract_page_text(
    pdf_data: bytes,
    page_number: int,
) -> str:
    """Read one PDF page using Thai and English OCR."""
    if not pdf_data:
        raise OcrError("The PDF is empty.")

    if len(pdf_data) > MAX_PDF_BYTES:
        raise OcrError("The PDF must be 1 MiB or smaller.")

    if type(page_number) is not int or page_number < 1:
        raise OcrError("page_number must be a positive integer.")

    with TemporaryDirectory(prefix="rag-ocr-") as directory:
        working_directory = Path(directory)
        pdf_path = working_directory / "document.pdf"
        image_prefix = working_directory / "page"
        image_path = working_directory / "page.png"

        pdf_path.write_bytes(pdf_data)

        _run_command(
            [
                "pdftoppm",
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                "-singlefile",
                "-scale-to",
                str(MAX_IMAGE_SIDE),
                "-png",
                str(pdf_path),
                str(image_prefix),
            ],
            timeout=RENDER_TIMEOUT_SECONDS,
            operation="PDF page rendering",
        )

        if not image_path.is_file():
            raise OcrError("PDF page rendering produced no image.")

        result = _run_command(
            [
                "tesseract",
                str(image_path),
                "stdout",
                "-l",
                "tha+eng",
                "--psm",
                "3",
            ],
            timeout=OCR_TIMEOUT_SECONDS,
            operation="Text recognition",
        )

        return result.stdout.strip()
