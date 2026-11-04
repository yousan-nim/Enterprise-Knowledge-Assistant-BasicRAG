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
        self.assertTrue(all(page.extraction_method == 'direct' for page in pages))

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
