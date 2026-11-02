import unittest
from app.services.generation import validate_citations

class CitationTests(unittest.TestCase):
    def test_valid_citation(self):
        validate_citations('สูงสุด 500 บาท [chunk-2]', {'chunk-2'})

    def test_abstention(self):
        validate_citations(' ไม่พบข้อมูลในเอกสาร ', set())

    def test_missing_citation(self):
        with self.assertRaises(ValueError):
            validate_citations('สูงสุด 500 บาท', {'chunk-2'})

    def test_unknown_citation(self):
        with self.assertRaises(ValueError):
            validate_citations('500 บาท [chunk-2] [chunk-99]', {'chunk-2'})
