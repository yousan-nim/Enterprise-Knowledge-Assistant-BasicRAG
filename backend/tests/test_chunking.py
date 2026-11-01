import unittest

from app.services.chunking import chunk_text


class ChunkingTests(unittest.TestCase):
    def test_chunks_overlap_and_cover_the_text(self):
        chunks = chunk_text(
            "ABCDEFGHIJKLMNOP",
            chunk_size=8,
            overlap=2,
        )

        self.assertEqual(
            chunks,
            ["ABCDEFGH", "GHIJKLMN", "MNOP"],
        )

    def test_empty_text_returns_no_chunks(self):
        self.assertEqual(chunk_text("   "), [])

    def test_short_text_returns_one_chunk(self):
        self.assertEqual(
            chunk_text("สวัสดี", chunk_size=10, overlap=2),
            ["สวัสดี"],
        )

    def test_exact_size_does_not_create_an_extra_chunk(self):
        self.assertEqual(
            chunk_text("ABCDEFGH", chunk_size=8, overlap=2),
            ["ABCDEFGH"],
        )

    def test_invalid_settings_raise_an_error(self):
        for chunk_size, overlap in [(0, 0), (8, -1), (8, 8)]:
            with self.subTest(chunk_size=chunk_size, overlap=overlap):
                with self.assertRaises(ValueError):
                    chunk_text(
                        "Example",
                        chunk_size=chunk_size,
                        overlap=overlap,
                    )