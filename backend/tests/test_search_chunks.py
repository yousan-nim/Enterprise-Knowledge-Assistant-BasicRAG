import unittest
from app.services.retrieval import search_chunks


class SearchChunksTests(unittest.TestCase):
    def setUp(self):
        self.chunks = [
            {'id': 'a', 'text': 'Travel policy', 'source': 'travel.md', 'embedding': [1.0, 0.0]},
            {'id': 'b', 'text': 'Working hours', 'source': 'handbook.md', 'embedding': [0.0, 1.0]},
            {'id': 'c', 'text': 'Expense receipts', 'source': 'expenses.md', 'embedding': [1.0, 1.0]},
        ]

    def test_returns_top_k_in_descending_order(self):
        results = search_chunks(query_vector=[1.0, 0.0], chunks=self.chunks, top_k=2)
        self.assertEqual([item['id'] for item in results], ['a', 'c'])
        self.assertAlmostEqual(results[0]['score'], 1.0)
        self.assertAlmostEqual(results[1]['score'], 0.70710678)
        self.assertEqual(results[0]['source'], 'travel.md')
        self.assertNotIn('embedding', results[0])

    def test_empty_chunks_returns_empty_list(self):
        self.assertEqual(search_chunks([1.0, 0.0], []), [])

    def test_top_k_can_exceed_chunk_count(self):
        self.assertEqual(len(search_chunks([1.0, 0.0], self.chunks, top_k=10)), 3)

    def test_invalid_top_k_is_rejected(self):
        for value in [0, -1, 1.5, True]:
            with self.subTest(top_k=value):
                with self.assertRaises(ValueError):
                    search_chunks([1.0, 0.0], self.chunks, top_k=value)

    def test_invalid_query_is_rejected_even_without_chunks(self):
        with self.assertRaises(ValueError):
            search_chunks([0.0, 0.0], [])

    def test_does_not_change_original_chunks(self):
        import copy
        original = copy.deepcopy(self.chunks)
        search_chunks([1.0, 0.0], self.chunks)
        self.assertEqual(self.chunks, original)
