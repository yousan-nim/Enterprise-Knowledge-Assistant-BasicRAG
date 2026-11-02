import unittest

from app.services.retrieval import cosine_similarity


class CosineSimilarityTests(unittest.TestCase):
    def test_same_direction_returns_one(self):
        score = cosine_similarity([1, 2], [2, 4])
        self.assertAlmostEqual(score, 1.0)

    def test_perpendicular_vectors_return_zero(self):
        score = cosine_similarity([1, 0], [0, 1])
        self.assertAlmostEqual(score, 0.0)

    def test_opposite_direction_returns_negative_one(self):
        score = cosine_similarity([1, 0], [-1, 0])
        self.assertAlmostEqual(score, -1.0)

    def test_known_angle(self):
        score = cosine_similarity([1, 0], [1, 1])
        self.assertAlmostEqual(score, 0.70710678)

    def test_invalid_vectors_raise_an_error(self):
        cases = [
            ([], []),
            ([1, 2], [1]),
            ([0, 0], [1, 2]),
            ([float("nan"), 1], [1, 2]),
            ([float("inf"), 1], [1, 2]),
            ([True, 1], [1, 2]),
            (["invalid", 1], [1, 2]),
        ]

        for a, b in cases:
            with self.subTest(a=a, b=b):
                with self.assertRaises(ValueError):
                    cosine_similarity(a, b)