"""Unit tests for partial review redaction.

These need no database and no mail server.  They pin down the two contracts the
feature rests on:

* ``html_to_text`` produces exactly what a browser ``TreeWalker(SHOW_TEXT)``
  produces, because the offsets stored with a redaction are measured in that
  coordinate system on the server and re-measured there in the browser; and
* ``remap`` tells "the author deleted the offending words" apart from "the
  author disguised them", which is the whole reason diff-match-patch is here.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import redaction as R  # noqa: E402

JS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'app', 'static', 'js', 'review-redact.js')


class TestHtmlToText(unittest.TestCase):
    def test_tags_do_not_break_a_word(self):
        # The point of matching on text rather than on the HTML source: an
        # author bolding one character must not shake the mask loose.
        self.assertEqual(R.html_to_text('<p>史<strong>中</strong>史</p>'), '史中史')

    def test_no_separator_is_inserted_between_nodes(self):
        # A browser TreeWalker concatenates text nodes with nothing in between,
        # so neither may this -- an extra space would shift every later offset.
        self.assertEqual(R.html_to_text('<p>abc</p><p>def</p>'), 'abcdef')

    def test_entities_are_decoded(self):
        self.assertEqual(R.html_to_text('<p>a&amp;b&nbsp;c</p>'), 'a&b\xa0c')

    def test_script_and_style_contribute_nothing(self):
        self.assertEqual(
            R.html_to_text('<p>a</p><script>var x = 1;</script><style>p{}</style><p>b</p>'),
            'ab')

    def test_comments_contribute_nothing(self):
        self.assertEqual(R.html_to_text('<p>a<!-- hidden -->b</p>'), 'ab')

    def test_empty_content(self):
        self.assertEqual(R.html_to_text(''), '')
        self.assertEqual(R.html_to_text(None), '')


class TestOccurrences(unittest.TestCase):
    def test_every_occurrence_is_found(self):
        self.assertEqual(R.find_occurrences('史中史很水，史中史', '史中史'), [0, 6])

    def test_overlapping_matches_are_kept(self):
        # Masking "aa" in "aaa" has to cover all three characters; stepping by
        # the quote length would leave a bare one behind.
        self.assertEqual(R.find_occurrences('aaa', 'aa'), [0, 1])

    def test_nearest_occurrence_picks_by_distance(self):
        text = '史中史很水，后面又提了一次史中史'
        self.assertEqual(R.nearest_occurrence(text, '史中史', 0), 0)
        self.assertEqual(R.nearest_occurrence(text, '史中史', 13), 13)

    def test_nearest_occurrence_when_absent(self):
        self.assertIsNone(R.nearest_occurrence('这门课很好', '史中史', 0))


class TestNormalizeQuote(unittest.TestCase):
    def test_a_dragged_selection_loses_its_stray_whitespace(self):
        self.assertEqual(R.normalize_quote('  史中史 '), '史中史')

    def test_whitespace_only_selection_is_rejected(self):
        self.assertIsNone(R.normalize_quote('   '))
        self.assertIsNone(R.normalize_quote(''))
        self.assertIsNone(R.normalize_quote(None))

    def test_an_overlong_selection_is_rejected(self):
        # Past this length the admin means to block the review, not mask a word.
        self.assertIsNone(R.normalize_quote('长' * (R.MAX_QUOTE_LENGTH + 1)))
        self.assertIsNotNone(R.normalize_quote('长' * R.MAX_QUOTE_LENGTH))


class TestRemap(unittest.TestCase):
    """The three verdicts, which are what the alert mail reports."""

    def test_an_edit_elsewhere_leaves_the_span_intact(self):
        old = '史中史真的很水'
        new = '补充一句：史中史真的很水'
        start, end, verdict = R.remap(old, new, 0, 3)
        self.assertEqual(verdict, R.INTACT)
        self.assertEqual(new[start:end], '史中史')

    def test_deleting_the_words_reads_as_deleted(self):
        # The author took the offending text out -- nothing left to cover.
        _start, _end, verdict = R.remap('史中史真的很水', '真的很水', 0, 3)
        self.assertEqual(verdict, R.DELETED)

    def test_splicing_characters_in_reads_as_tampered(self):
        # The evasion shape: the words survive in pieces with symbols wedged
        # between them.  A plain "is the string still there?" check sees only
        # that the quote is gone, exactly as it would for a clean deletion.
        old = '史中史真的很水'
        new = '史*中*史真的很水'
        start, end, verdict = R.remap(old, new, 0, 3)
        self.assertEqual(verdict, R.TAMPERED)
        # The reported span covers the inserted characters too, so the mail
        # quotes what is actually on screen now.
        self.assertEqual(new[start:end], '史*中*史')

    def test_partial_deletion_reads_as_tampered(self):
        _start, _end, verdict = R.remap('史中史真的很水', '史史真的很水', 0, 3)
        self.assertEqual(verdict, R.TAMPERED)

    def test_text_inserted_against_a_boundary_is_not_tampering(self):
        # Writing immediately before or after the span is ordinary editing.
        _start, _end, verdict = R.remap('史中史很水', '很史中史很水', 2, 5)
        self.assertEqual(verdict, R.INTACT)

    def test_replacing_the_whole_review_reads_as_deleted(self):
        # diff-match-patch cannot distinguish this from an honest deletion, and
        # neither can anything else -- which is why every edit mails the admins.
        _start, _end, verdict = R.remap('史中史真的很水', '这门课其实还行', 0, 3)
        self.assertEqual(verdict, R.DELETED)

    def test_a_degenerate_span_is_treated_as_gone(self):
        self.assertEqual(R.remap('abc', 'abc', 2, 2)[2], R.DELETED)
        self.assertEqual(R.remap('abc', 'abc', None, None)[2], R.DELETED)


class TestMaskText(unittest.TestCase):
    def test_every_occurrence_is_covered(self):
        self.assertEqual(R.mask_text('史中史很水，史中史', ['史中史']),
                         '███很水，███')

    def test_a_truncated_quote_does_not_leave_its_head_readable(self):
        # The list pages and the RSS feed cut an abstract to a fixed length,
        # which can slice a quote in half.
        self.assertEqual(R.mask_text('这门课就是史中', ['史中史']), '这门课就是██')

    def test_a_one_character_tail_is_left_alone(self):
        # Too short to tell a truncated quote from a coincidence.
        self.assertEqual(R.mask_text('这门课就是史', ['史中史']), '这门课就是史')

    def test_nothing_to_do(self):
        self.assertEqual(R.mask_text('这门课很好', ['史中史']), '这门课很好')
        self.assertEqual(R.mask_text('', ['史中史']), '')
        self.assertEqual(R.mask_text('abc', []), 'abc')


class TestEndToEnd(unittest.TestCase):
    """The scenario the feature exists for, from the admin's click onward."""

    ORIGINAL = '<p>这门课就是史中史，老师完全在混</p>'

    def redact(self, html, selection):
        """What the API does when an admin drags across `selection`."""
        quote = R.normalize_quote(selection)
        text = R.html_to_text(html)
        occurrences = R.find_occurrences(text, quote)
        self.assertTrue(occurrences, 'the selection must exist in the review')
        return quote, occurrences[0]

    def test_the_mask_survives_an_edit_that_moves_the_text(self):
        quote, _pos = self.redact(self.ORIGINAL, '史中史')
        edited = '<p>先说结论：这门课就是史中史，老师完全在混</p>'
        # Nothing was re-anchored and no diff was consulted: the string is
        # simply still there, which is the whole point of matching on text.
        self.assertTrue(R.find_occurrences(R.html_to_text(edited), quote))

    def test_the_mask_survives_the_author_bolding_a_character(self):
        quote, _pos = self.redact(self.ORIGINAL, '史中史')
        edited = '<p>这门课就是史<strong>中</strong>史，老师完全在混</p>'
        self.assertTrue(R.find_occurrences(R.html_to_text(edited), quote))

    def test_disguising_the_words_is_reported_as_tampering(self):
        quote, pos = self.redact(self.ORIGINAL, '史中史')
        edited = '<p>这门课就是史*中*史，老师完全在混</p>'
        new_text = R.html_to_text(edited)
        self.assertFalse(R.find_occurrences(new_text, quote))
        _s, _e, verdict = R.remap(R.html_to_text(self.ORIGINAL), new_text,
                                  pos, pos + len(quote))
        self.assertEqual(verdict, R.TAMPERED)

    def test_removing_the_words_resolves_the_redaction(self):
        quote, pos = self.redact(self.ORIGINAL, '史中史')
        edited = '<p>这门课一般，老师完全在混</p>'
        new_text = R.html_to_text(edited)
        self.assertFalse(R.find_occurrences(new_text, quote))
        _s, _e, verdict = R.remap(R.html_to_text(self.ORIGINAL), new_text,
                                  pos, pos + len(quote))
        self.assertEqual(verdict, R.DELETED)


class TestFrontendAgreement(unittest.TestCase):
    """The browser re-implements the matching rules; keep the constants in step.

    Running the real JS would mean adding node to CI for two numbers, so this
    reads them out of the file instead.  It catches the drift that would matter:
    a rule changed on one side only.
    """

    def setUp(self):
        with open(JS_PATH, encoding='utf-8') as handle:
            self.js = handle.read()

    def test_partial_tail_threshold_matches(self):
        found = re.search(r'MIN_PARTIAL_TAIL\s*=\s*(\d+)', self.js)
        self.assertIsNotNone(found, 'MIN_PARTIAL_TAIL missing from review-redact.js')
        self.assertEqual(int(found.group(1)), R.MIN_PARTIAL_TAIL)

    def test_mask_character_matches(self):
        found = re.search(r"MASK_CHAR\s*=\s*'(.)'", self.js)
        self.assertIsNotNone(found, 'MASK_CHAR missing from review-redact.js')
        self.assertEqual(found.group(1), R.MASK_CHAR)

    def test_the_same_tags_are_skipped_on_both_sides(self):
        for tag in R._SKIPPED_TAGS:
            self.assertIn(tag.upper(), self.js,
                          '%s is skipped on the server but not in the browser' % tag)


if __name__ == '__main__':
    unittest.main(verbosity=2)
