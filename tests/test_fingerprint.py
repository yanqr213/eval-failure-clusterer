import unittest

from eval_failure_clusterer.fingerprint import simhash
from eval_failure_clusterer.utils import hamming_distance, similarity_from_distance


class FingerprintTests(unittest.TestCase):
    def test_simhash_stable(self):
        first = simhash("missing final answer in output")
        second = simhash("missing final answer in output")
        self.assertEqual(first, second)

    def test_hamming_distance(self):
        self.assertEqual(hamming_distance(0b1010, 0b0011), 2)

    def test_simhash_similarity_for_related_text(self):
        left = simhash("missing final answer after reasoning")
        right = simhash("reasoning is present but final answer is missing")
        self.assertGreater(similarity_from_distance(left, right), 0.45)
