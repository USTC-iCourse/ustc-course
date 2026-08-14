"""The on-disk segment format, checked against an independent recomputation.

Everything else in the engine trusts these arrays.  A silent misalignment here
would not crash -- it would quietly return the wrong documents -- so the format
is tested by building a segment from known input and verifying every postings
list against a plain Python dict built the obvious way.

    PYTHONPATH=. python3 tests/test_search_segment.py
"""

import os
import random
import shutil
import sys
import tempfile
import unittest
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.search.segment import MAX_TF, Segment, SegmentWriter  # noqa: E402


def _corpus(count, rng):
    alphabet = "数学分析线性代数物理实验编译原理与技术自杀紫砂abc123"
    docs = []
    for i in range(count):
        length = rng.randrange(0, 40)
        text = "".join(rng.choice(alphabet) for _ in range(length))
        docs.append((1000 + i * 7, text))
    return docs


class SegmentRoundTrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="segtest")
        rng = random.Random(4242)
        cls.docs = _corpus(400, rng)

        writer = SegmentWriter("t", ["gram", "char"], meta={"built_at_utc": "2020-01-01T00:00:00"})
        cls.expected = {"gram": defaultdict(dict), "char": defaultdict(dict)}
        for index, (doc_id, text) in enumerate(cls.docs):
            grams = [text[i : i + 2] for i in range(len(text) - 1)]
            chars = list(text)
            for field, tokens in (("gram", grams), ("char", chars)):
                for term, freq in Counter(tokens).items():
                    cls.expected[field][term][index] = min(freq, MAX_TF)
            writer.add_doc(
                doc_id, text, {"gram": grams, "char": chars}, {"weight": float(index)}
            )
        cls.path = os.path.join(cls.dir, "t.seg")
        writer.write(cls.path)
        cls.seg = Segment(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.seg.close()
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_document_identity_and_count(self):
        self.assertEqual(self.seg.doc_count, len(self.docs))
        self.assertEqual(list(self.seg.doc_ids), [doc_id for doc_id, _ in self.docs])

    def test_every_postings_list_matches_a_recomputation(self):
        for field, terms in self.expected.items():
            for term, expected_docs in terms.items():
                docs, tf = self.seg.postings(field, term)
                self.assertEqual(
                    list(docs),
                    sorted(expected_docs),
                    "%s postings for %r are wrong" % (field, term),
                )
                self.assertEqual(
                    [int(x) for x in tf],
                    [expected_docs[d] for d in sorted(expected_docs)],
                    "%s term frequencies for %r are wrong" % (field, term),
                )

    def test_postings_are_ascending(self):
        # Intersection uses searchsorted, which silently returns nonsense on an
        # unsorted list rather than failing.
        for field, terms in self.expected.items():
            for term in terms:
                docs, _tf = self.seg.postings(field, term)
                self.assertTrue(all(docs[i] < docs[i + 1] for i in range(docs.size - 1)))

    def test_unknown_term_returns_empty(self):
        docs, tf = self.seg.postings("gram", "龘龘")
        self.assertEqual(docs.size, 0)
        self.assertEqual(tf.size, 0)
        self.assertEqual(self.seg.doc_freq("gram", "龘龘"), 0)

    def test_doc_freq_agrees_with_postings(self):
        for term in list(self.expected["gram"])[:50]:
            self.assertEqual(
                self.seg.doc_freq("gram", term), self.seg.postings("gram", term)[0].size
            )

    def test_text_round_trips(self):
        for index, (_doc_id, text) in enumerate(self.docs):
            self.assertEqual(self.seg.text(index), text)

    def test_find_locates_substrings_within_the_right_document(self):
        for index, (_doc_id, text) in enumerate(self.docs):
            if len(text) < 3:
                continue
            needle = text[1:3].encode("utf-8")
            found = self.seg.find(index, needle)
            self.assertGreaterEqual(found, 0)
            self.assertEqual(
                self.seg.text(index).encode("utf-8")[found : found + len(needle)], needle
            )

    def test_find_does_not_leak_across_documents(self):
        """A needle present only in a *different* document must not be found."""
        rng = random.Random(7)
        for _ in range(200):
            a, b = rng.randrange(len(self.docs)), rng.randrange(len(self.docs))
            text_a, text_b = self.docs[a][1], self.docs[b][1]
            if len(text_b) < 2 or text_b[:2] in text_a:
                continue
            self.assertEqual(self.seg.find(a, text_b[:2].encode("utf-8")), -1)

    def test_priors_stay_parallel_with_documents(self):
        weights = self.seg.prior("weight")
        self.assertEqual(weights.size, self.seg.doc_count)
        self.assertEqual(list(weights), [float(i) for i in range(len(self.docs))])

    def test_index_of_maps_ids_back_to_rows(self):
        for index, (doc_id, _text) in enumerate(self.docs):
            self.assertEqual(self.seg.index_of(doc_id), index)
        self.assertEqual(self.seg.index_of(999999), -1)

    def test_mask_ids_selects_only_present_ids(self):
        wanted = [self.docs[3][0], self.docs[100][0], 999999]
        got = sorted(int(i) for i in self.seg.mask_ids(wanted))
        self.assertEqual(got, sorted([3, 100]))

    def test_header_survives_reopening(self):
        again = Segment(self.path)
        try:
            self.assertEqual(again.doc_count, self.seg.doc_count)
            self.assertEqual(again.fields, self.seg.fields)
            self.assertEqual(again.built_at, self.seg.built_at)
        finally:
            again.close()


class EmptySegment(unittest.TestCase):
    """A collection with no documents must not be a special case anywhere."""

    def test_empty_segment_round_trips(self):
        path = os.path.join(tempfile.mkdtemp(prefix="segempty"), "e.seg")
        writer = SegmentWriter("t", ["gram"], meta={"built_at_utc": "2020-01-01T00:00:00"})
        writer.write(path)
        seg = Segment(path)
        try:
            self.assertEqual(seg.doc_count, 0)
            self.assertEqual(seg.postings("gram", "xx")[0].size, 0)
            self.assertEqual(seg.mask_ids([1, 2, 3]).size, 0)
            self.assertEqual(seg.index_of(1), -1)
        finally:
            seg.close()
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)


class TermFrequencySaturation(unittest.TestCase):
    def test_frequency_is_capped_not_wrapped(self):
        """tf is a byte; a document repeating a term 300 times must saturate
        rather than overflow to a small number."""
        path = os.path.join(tempfile.mkdtemp(prefix="segtf"), "tf.seg")
        writer = SegmentWriter("t", ["gram"], meta={"built_at_utc": "2020-01-01T00:00:00"})
        writer.add_doc(1, "x", {"gram": ["ab"] * 300}, {})
        writer.write(path)
        seg = Segment(path)
        try:
            _docs, tf = seg.postings("gram", "ab")
            self.assertEqual(int(tf[0]), MAX_TF)
        finally:
            seg.close()
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
