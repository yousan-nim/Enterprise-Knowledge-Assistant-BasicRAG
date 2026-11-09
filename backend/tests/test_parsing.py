import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from app.services.parsing import DocumentParseError, parse_document


def make_pdf(texts, encrypted=False):
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(width=300, height=300)
        if text:
            font = DictionaryObject({
                NameObject('/Type'): NameObject('/Font'),
                NameObject('/Subtype'): NameObject('/Type1'),
                NameObject('/BaseFont'): NameObject('/Helvetica'),
            })
            page[NameObject('/Resources')] = DictionaryObject({
                NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})
            })
            stream = DecodedStreamObject()
            stream.set_data(f'BT /F1 12 Tf 20 250 Td ({text}) Tj ET'.encode('ascii'))
            page[NameObject('/Contents')] = writer._add_object(stream)
    if encrypted:
        writer.encrypt('demo-password')
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class ParsingTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('app.services.parsing.extract_page_text', return_value='')
        self.ocr = patcher.start()
        self.addCleanup(patcher.stop)

    def test_reads_utf8_text_with_bom(self):
        pages = parse_document('\ufeffสวัสดี'.encode('utf-8'), 'handbook.MD')
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].page, 1)
        self.assertEqual(pages[0].text, 'สวัสดี')
        self.assertEqual(pages[0].extraction_method, 'direct')

    def test_reads_real_pdf_and_preserves_blank_page_numbers(self):
        pages = parse_document(make_pdf(['First page', '', 'Third page']), 'policy.pdf')
        self.assertEqual([page.page for page in pages], [1, 2, 3])
        self.assertIn('First page', pages[0].text)
        self.assertEqual(pages[1].text.strip(), '')
        self.assertIn('Third page', pages[2].text)
        self.assertEqual([page.extraction_method for page in pages], ['direct', 'ocr', 'direct'])
        self.ocr.assert_called_once()

    def test_rejects_pdf_without_text(self):
        with self.assertRaisesRegex(DocumentParseError, 'OCR'):
            parse_document(make_pdf(['']), 'blank.pdf')

    def test_rejects_encrypted_pdf(self):
        with self.assertRaisesRegex(DocumentParseError, 'Encrypted'):
            parse_document(make_pdf(['Secret'], encrypted=True), 'locked.pdf')

    def test_rejects_invalid_inputs(self):
        cases = [('empty.txt', b'   '), ('invalid.txt', b'\xff'),
                 ('null.md', b'Hello\x00world'), ('image.png', b'image'),
                 ('broken.pdf', b'not a PDF'), ('long.txt', b'a' * 50_001)]
        for filename, data in cases:
            with self.subTest(filename=filename):
                with self.assertRaises(DocumentParseError):
                    parse_document(data, filename)

    def test_rejects_too_many_pdf_pages(self):
        reader = SimpleNamespace(is_encrypted=False, pages=[Mock() for _ in range(51)])
        with patch('app.services.parsing.PdfReader', return_value=reader):
            with self.assertRaisesRegex(DocumentParseError, '50 pages'):
                parse_document(b'mock', 'large.pdf')

    def test_rejects_pdf_text_over_limit(self):
        reader = SimpleNamespace(is_encrypted=False, pages=[Mock(extract_text=Mock(return_value='a' * 50_001))])
        with patch('app.services.parsing.PdfReader', return_value=reader):
            with self.assertRaisesRegex(DocumentParseError, '50,000'):
                parse_document(b'mock', 'long.pdf')

    def test_accepts_exact_text_limit(self):
        pages = parse_document(b'a' * 50_000, 'limit.txt')
        self.assertEqual(len(pages[0].text), 50_000)

    def test_text_only_pdf_never_calls_ocr(self):
        parse_document(make_pdf(['Text page']), 'direct.pdf')
        self.ocr.assert_not_called()

    def test_mixed_pdf_uses_ocr_on_only_the_empty_page(self):
        self.ocr.return_value = 'ข้อความจากภาพ 500 บาท'
        data = make_pdf(['Text page', ''])
        pages = parse_document(data, 'mixed.pdf')
        self.ocr.assert_called_once_with(data, 2)
        self.assertEqual(pages[1].text, 'ข้อความจากภาพ 500 บาท')
        self.assertEqual(pages[1].page, 2)
        self.assertEqual(pages[1].extraction_method, 'ocr')
        self.assertEqual(pages[0].extraction_method, 'direct')

    def test_ocr_failure_is_a_document_error(self):
        from app.services.ocr import OcrError
        self.ocr.side_effect = OcrError('Text recognition exceeded its time limit.')
        with self.assertRaisesRegex(DocumentParseError, 'page 1.*time limit'):
            parse_document(make_pdf(['']), 'scan.pdf')

    def test_ocr_page_limit(self):
        self.ocr.return_value = 'Recognized text'
        with self.assertRaisesRegex(DocumentParseError, 'limited to 5 pages'):
            parse_document(make_pdf([''] * 6), 'scan.pdf')
        self.assertEqual(self.ocr.call_count, 5)

    def test_ocr_budget_is_checked_before_next_page(self):
        self.ocr.return_value = 'Recognized text'
        with patch('app.services.parsing.monotonic', side_effect=[0., 0., 120.]):
            with self.assertRaisesRegex(DocumentParseError, 'processing budget'):
                parse_document(make_pdf(['', '']), 'scan.pdf')
        self.assertEqual(self.ocr.call_count, 1)

    def test_ocr_text_is_subject_to_character_and_null_limits(self):
        for text, message in [('a' * 50_001, '50,000'), ('hello\x00world', 'null')]:
            with self.subTest(message=message):
                self.ocr.return_value = text
                with self.assertRaisesRegex(DocumentParseError, message):
                    parse_document(make_pdf(['']), 'scan.pdf')
