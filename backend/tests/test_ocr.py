import subprocess
from pathlib import Path
import unittest
from unittest.mock import patch

from app.services.ocr import (
    MAX_PDF_BYTES, OCR_TIMEOUT_SECONDS, RENDER_TIMEOUT_SECONDS,
    OcrError, extract_page_text,
)


class OcrTests(unittest.TestCase):
    def test_renders_requested_page_and_cleans_temporary_files(self):
        calls = []

        def run(command, **kwargs):
            calls.append((command, kwargs))
            if command[0] == 'pdftoppm':
                pdf_path = Path(command[-2])
                self.assertEqual(pdf_path.read_bytes(), b'%PDF-test')
                Path(command[-1] + '.png').write_bytes(b'image')
                return subprocess.CompletedProcess(command, 0, stdout='', stderr='')
            return subprocess.CompletedProcess(command, 0, stdout='  สวัสดี Hello\n', stderr='')

        with patch('app.services.ocr.subprocess.run', side_effect=run):
            self.assertEqual(extract_page_text(b'%PDF-test', 3), 'สวัสดี Hello')
        render, recognize = calls
        self.assertEqual(render[0][1:6], ['-f', '3', '-l', '3', '-singlefile'])
        self.assertEqual(render[1]['timeout'], RENDER_TIMEOUT_SECONDS)
        self.assertEqual(recognize[0][3:], ['-l', 'tha+eng', '--psm', '3'])
        self.assertEqual(recognize[1]['timeout'], OCR_TIMEOUT_SECONDS)
        self.assertNotIn('shell', render[1])
        self.assertFalse(Path(render[0][-2]).parent.exists())

    def test_rejects_invalid_inputs_before_running_tools(self):
        cases = [(b'', 1), (b'a' * (MAX_PDF_BYTES + 1), 1),
                 (b'pdf', 0), (b'pdf', -1), (b'pdf', True), (b'pdf', '1')]
        with patch('app.services.ocr.subprocess.run') as run:
            for data, page in cases:
                with self.subTest(page=page, size=len(data)):
                    with self.assertRaises(OcrError):
                        extract_page_text(data, page)
            run.assert_not_called()

    def test_missing_output_image_stops_before_recognition(self):
        with patch('app.services.ocr.subprocess.run', return_value=subprocess.CompletedProcess([], 0, stdout='', stderr='')) as run:
            with self.assertRaisesRegex(OcrError, 'no image'):
                extract_page_text(b'pdf', 1)
        self.assertEqual(run.call_count, 1)

    def test_translates_tool_failures_and_cleans_up(self):
        cases = [(FileNotFoundError(), 'unavailable'),
                 (subprocess.TimeoutExpired('pdftoppm', 30), 'time limit'),
                 (subprocess.CalledProcessError(1, 'pdftoppm', stderr='private path'), 'failed')]
        for failure, message in cases:
            paths = []

            def fail(command, **kwargs):
                paths.append(Path(command[-2]).parent)
                raise failure

            with self.subTest(failure=type(failure).__name__):
                with patch('app.services.ocr.subprocess.run', side_effect=fail):
                    with self.assertRaisesRegex(OcrError, message) as raised:
                        extract_page_text(b'pdf', 1)
                self.assertNotIn('private path', str(raised.exception))
                self.assertFalse(paths[0].exists())

    def test_recognition_timeout_is_reported(self):
        def run(command, **kwargs):
            if command[0] == 'pdftoppm':
                Path(command[-1] + '.png').write_bytes(b'image')
                return subprocess.CompletedProcess(command, 0, stdout='', stderr='')
            raise subprocess.TimeoutExpired(command, OCR_TIMEOUT_SECONDS)

        with patch('app.services.ocr.subprocess.run', side_effect=run):
            with self.assertRaisesRegex(OcrError, 'Text recognition exceeded'):
                extract_page_text(b'pdf', 1)
