"""Checks the isolated handbook evaluator without calling Ollama or a database."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("handbook_evaluator", ROOT / "evaluation/run.py")
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)


class HandbookEvaluationTests(unittest.IsolatedAsyncioTestCase):
    def test_fixture_evidence_is_present(self):
        dataset, _, text = evaluator.load_dataset(ROOT / "evaluation/datasets/handbook.json")
        self.assertEqual(len(dataset["cases"]), 4)
        self.assertIn("Receipts are required.", text)

    def test_coverage_combines_spans_but_not_gaps_or_wrong_pages(self):
        gold = [{"page": 1, "text": "abcdef"}]
        chunks = [
            {"id": "a", "page": 1, "start": 0, "end": 3},
            {"id": "b", "page": 1, "start": 3, "end": 6},
        ]
        both = [{"id": "a"}, {"id": "b"}]
        self.assertEqual(evaluator.evidence_coverage(gold, both, chunks, "abcdef"), 1)
        chunks[1]["start"] = 4
        self.assertEqual(evaluator.evidence_coverage(gold, both, chunks, "abcdef"), 0)
        chunks[1].update(start=3, page=2)
        self.assertEqual(evaluator.evidence_coverage(gold, both, chunks, "abcdef"), 0)
        self.assertIsNone(evaluator.evidence_coverage([], [], [], "abcdef"))

    def test_repeated_quote_can_match_a_later_retrieved_occurrence(self):
        chunks = [{"id": "a", "page": 1, "start": 4, "end": 7}]
        self.assertEqual(evaluator.evidence_coverage(
            [{"page": 1, "text": "abc"}], [{"id": "a"}], chunks, "abc abc"
        ), 1)

    async def test_generation_error_retains_evidence_and_is_not_a_pass(self):
        dataset, _, document = evaluator.load_dataset(ROOT / "evaluation/datasets/handbook.json")
        chunks = [{"id": "chunk-1", "text": document, "source": "handbook.md",
                   "page": 1, "start": 0, "end": len(document), "embedding": [1., 0.]}]
        with patch.object(evaluator, "embed_texts", new_callable=AsyncMock, return_value=[[1., 0.]]), \
             patch.object(evaluator, "answer_with_sources", new_callable=AsyncMock, side_effect=ValueError("Invalid answer")):
            row = await evaluator.evaluate_case(dataset["cases"][0], chunks, document, 3)
        self.assertEqual(row["error"]["stage"], "generation_and_validation")
        self.assertTrue(row["retrieved"])
        self.assertFalse(row["metrics"]["schema_and_ids_valid"])
        self.assertIsNone(row["metrics"]["found_matches_expected"])
        self.assertIsNone(row["manual_review"]["answer_correct"])
        self.assertEqual(evaluator.summarize([row])["errors"], 1)
