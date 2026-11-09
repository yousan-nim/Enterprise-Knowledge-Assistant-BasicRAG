"""Real Poppler/Tesseract checks; enable inside the backend image with RUN_OCR_TESTS=1."""
from io import BytesIO
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, NumberObject, DecodedStreamObject

from app.services.ocr import OcrError, extract_page_text
from test_parsing import make_pdf


def scanned_pdf(text):
    # Rasterize a fixture and embed only its pixels, with no searchable text layer.
    with TemporaryDirectory() as directory:
        source = Path(directory) / 'source.pdf'
        image = Path(directory) / 'scan'
        source.write_bytes(make_pdf([text]))
        subprocess.run(['pdftoppm', '-singlefile', '-r', '150', '-gray', str(source), str(image)], check=True, capture_output=True, timeout=30)
        header, dimensions, maximum, pixels = image.with_suffix('.pgm').read_bytes().split(b'\n', 3)
    assert header == b'P5' and maximum == b'255'
    width, height = map(int, dimensions.split())
    assert len(pixels) == width * height
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    bitmap = DecodedStreamObject()
    bitmap.set_data(pixels)
    bitmap.update({
        NameObject('/Type'): NameObject('/XObject'),
        NameObject('/Subtype'): NameObject('/Image'),
        NameObject('/Width'): NumberObject(width),
        NameObject('/Height'): NumberObject(height),
        NameObject('/ColorSpace'): NameObject('/DeviceGray'),
        NameObject('/BitsPerComponent'): NumberObject(8),
    })
    page[NameObject('/Resources')] = DictionaryObject({
        NameObject('/XObject'): DictionaryObject({NameObject('/Scan'): writer._add_object(bitmap.flate_encode())}),
    })
    drawing = DecodedStreamObject()
    drawing.set_data(b'q 300 0 0 300 0 0 cm /Scan Do Q')
    page[NameObject('/Contents')] = writer._add_object(drawing)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@unittest.skipUnless(os.getenv('RUN_OCR_TESTS') == '1', 'Set RUN_OCR_TESTS=1 with Poppler and Tesseract installed')
class OcrIntegrationTests(unittest.TestCase):
    def test_reads_image_only_pdf(self):
        data = scanned_pdf('TRAVEL LIMIT 500')
        self.assertEqual(PdfReader(BytesIO(data)).pages[0].extract_text(), '')
        text = extract_page_text(data, 1)
        self.assertIn('TRAVEL', text.upper())
        self.assertIn('500', text)

    def test_blank_scan_returns_empty_text(self):
        self.assertEqual(extract_page_text(scanned_pdf(''), 1), '')

    def test_languages_and_invalid_pdf(self):
        result = subprocess.run(['tesseract', '--list-langs'], check=True, capture_output=True, text=True, timeout=10)
        languages = result.stdout.splitlines()
        self.assertIn('tha', languages)
        self.assertIn('eng', languages)
        with self.assertRaisesRegex(OcrError, 'PDF page rendering failed'):
            extract_page_text(b'invalid PDF', 1)

    def test_parser_reads_mixed_pdf_with_real_ocr(self):
        from app.services.parsing import parse_document
        writer = PdfWriter()
        for data in [make_pdf(['DIRECT PAGE']), scanned_pdf('TRAVEL LIMIT 500')]:
            reader = PdfReader(BytesIO(data))
            for page in reader.pages:
                writer.add_page(page)
        buffer = BytesIO()
        writer.write(buffer)
        pages = parse_document(buffer.getvalue(), 'mixed.pdf')
        self.assertEqual([page.page for page in pages], [1, 2])
        self.assertEqual([page.extraction_method for page in pages], ['direct', 'ocr'])
        self.assertIn('DIRECT PAGE', pages[0].text)
        self.assertIn('500', pages[1].text)

    def test_thai_policy_scan_preserves_key_facts(self):
        import unicodedata
        from app.services.parsing import parse_document
        root = Path(__file__).resolve().parents[2] / 'samples/ocr'
        data = (root / 'thai-policy-scan.pdf').read_bytes()
        self.assertEqual(PdfReader(BytesIO(data)).pages[0].extract_text(), '')
        pages = parse_document(data, 'thai-policy-scan.pdf')
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].extraction_method, 'ocr')
        self.assertEqual(pages[0].page, 1)
        text = pages[0].text
        compact = lambda value: ''.join(unicodedata.normalize('NFC', value).split())
        actual = compact(text)
        expected = compact((root / 'thai-policy-scan.txt').read_text())
        for phrase in ['นโยบายการเดินทาง', '500 บาทต่อวัน', 'ต้องแนบใบเสร็จทุกครั้ง', 'THB 500 per day']:
            self.assertIn(compact(phrase), actual)
        # Levenshtein CER on a fixed clean fixture; not a general accuracy claim.
        previous = list(range(len(actual) + 1))
        for i, left in enumerate(expected, 1):
            current = [i]
            for j, right in enumerate(actual, 1):
                current.append(min(current[-1] + 1, previous[j] + 1, previous[j-1] + (left != right)))
            previous = current
        self.assertLessEqual(previous[-1] / len(expected), 0.08)
