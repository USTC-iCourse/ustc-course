"""End-to-end tests against a real index.

The important one is :class:`TestSubstringRecall`.  The engine this replaced
lost 17% of substrings taken from real review text -- ``班风``, ``程学``,
``末考`` and hundreds more existed in reviews and could not be found -- and no
test caught it, because every test asked for a whole word that jieba happened
to segment the same way on both sides.  The only test that finds that class of
bug is one that draws its queries from the corpus itself and checks recall
against an independent oracle (here, SQL ``LIKE``).

Requires a built index::

    PYTHONPATH=. python3 -m app.search.builder
    PYTHONPATH=. python3 tests/test_search_engine.py
"""

import os
import random
import re
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlalchemy as sa  # noqa: E402

from app import app, db  # noqa: E402
from app.search import (  # noqa: E402
    IndexUnavailable,
    MatchQuality,
    ranked_review_ids,
    search_courses,
    search_reviews,
)
from app.search.service import _registry  # noqa: E402

CJK_RUN = re.compile(r"[一-鿿]{2,}")
TAGS = re.compile(r"<[^>]+>")

#: p95 budget for a search, index lookup through to hydrated ORM objects.
LATENCY_BUDGET_MS = 120.0


class AnonymousUser(object):
    is_authenticated = False
    identity = None
    id = None


class SearchTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = app.app_context()
        cls.ctx.push()
        try:
            _registry.get(app, "reviews")
            _registry.get(app, "courses")
        except IndexUnavailable as exc:
            raise unittest.SkipTest(str(exc))
        cls.anon = AnonymousUser()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()


class TestSubstringRecall(SearchTestCase):
    """Any substring of a visible review must find that review."""

    SAMPLE_REVIEWS = 300
    PROBES = 120

    @classmethod
    def setUpClass(cls):
        super(TestSubstringRecall, cls).setUpClass()
        rows = db.session.execute(
            sa.text(
                "SELECT id, content FROM reviews "
                "WHERE is_blocked = 0 AND is_hidden = 0 AND only_visible_to_student = 0 "
                "ORDER BY id DESC LIMIT :n"
            ),
            {"n": cls.SAMPLE_REVIEWS},
        ).fetchall()
        rng = random.Random(20260814)
        probes = []
        for rid, content in rows:
            plain = TAGS.sub(" ", content or "")
            runs = [m for m in CJK_RUN.findall(plain) if len(m) >= 3]
            if not runs:
                continue
            run = rng.choice(runs)
            width = min(len(run), rng.choice([2, 2, 3, 4]))
            start = rng.randrange(0, len(run) - width + 1)
            probes.append((rid, run[start : start + width]))
        rng.shuffle(probes)
        cls.probes = probes[: cls.PROBES]

    def test_every_substring_finds_its_review(self):
        self.assertGreater(len(self.probes), 50, "not enough sample data")
        misses = []
        for review_id, probe in self.probes:
            # The whole result set, not the first page: recall is a property of
            # what matched, and must not be confused with where ranking put it.
            ids, _quality, tier = ranked_review_ids(probe, self.anon)[:3]
            if review_id not in set(ids.tolist()):
                # Confirm against the oracle before calling it a miss: the
                # probe must really occur in that review.
                present = db.session.execute(
                    sa.text("SELECT COUNT(*) FROM reviews WHERE id = :i AND content LIKE :w"),
                    {"i": review_id, "w": "%" + probe + "%"},
                ).scalar()
                if present:
                    misses.append((probe, review_id, int(ids.size), tier))
        self.assertEqual(
            misses,
            [],
            "%d of %d substrings were unfindable: %s"
            % (len(misses), len(self.probes), misses[:10]),
        )

    def test_substring_matches_are_reported_as_exact(self):
        for review_id, probe in self.probes[:25]:
            results = search_reviews(probe, 1, 10, self.anon)
            self.assertEqual(
                results.quality,
                MatchQuality.EXACT,
                "%r matched at %s, not EXACT" % (probe, results.quality.name),
            )
            self.assertIsNone(results.note, "an exact match should carry no caveat")


class TestKnownQueries(SearchTestCase):
    """Queries that the previous engine got wrong."""

    def test_two_character_words_are_findable(self):
        # Present in reviews, returned zero results before.
        for probe in ("自杀", "紫砂", "班风", "程学", "末考"):
            results = search_reviews(probe, 1, 10, self.anon)
            self.assertGreater(results.total, 0, "%r found nothing" % probe)
            self.assertEqual(results.quality, MatchQuality.EXACT)

    def test_homophones_reach_the_original(self):
        """A homophone of 自杀 must find something, and say how it found it.

        Which rung fires depends on the corpus, so the expectation is derived
        from it rather than hardcoded: students really do write 自鲨, and on a
        database where they have, an exact match is the *right* answer, not a
        failure of the homophone tier.  An earlier version of this test assumed
        the word was absent and failed against production for being correct.
        """
        for probe in ("紫砂", "自鲨", "自沙"):
            occurs = db.session.execute(
                sa.text(
                    "SELECT COUNT(*) FROM reviews WHERE is_blocked = 0 AND is_hidden = 0 "
                    "AND only_visible_to_student = 0 AND content LIKE :w"
                ),
                {"w": "%" + probe + "%"},
            ).scalar()
            results = search_reviews(probe, 1, 10, self.anon)
            self.assertGreater(results.total, 0, "%r found nothing at all" % probe)
            if occurs:
                self.assertEqual(
                    results.quality,
                    MatchQuality.EXACT,
                    "%r occurs verbatim and should match exactly" % probe,
                )
                self.assertIsNone(results.note)
            else:
                self.assertLess(
                    results.quality,
                    MatchQuality.EXACT,
                    "%r does not occur, so it can only have been reached by "
                    "relaxing the query" % probe,
                )
                self.assertIsNotNone(results.note, "a relaxed match must say so")

    def test_a_homophone_absent_from_the_corpus_still_reaches_it(self):
        """The pinyin tier proper: a spelling nobody used, reaching one they did.

        This is what replaces the hand-maintained variant list in app/utils.py.
        """
        made_up = "自杀".replace("杀", "煞")  # 自煞: same pinyin, not a real word
        occurs = db.session.execute(
            sa.text("SELECT COUNT(*) FROM reviews WHERE content LIKE :w"),
            {"w": "%" + made_up + "%"},
        ).scalar()
        if occurs:
            self.skipTest("%r unexpectedly occurs in this database" % made_up)
        results = search_reviews(made_up, 1, 10, self.anon)
        self.assertGreater(results.total, 0, "%r reached nothing" % made_up)
        self.assertLess(results.quality, MatchQuality.EXACT)
        self.assertIsNotNone(results.note)

    def test_course_abbreviations(self):
        for probe, expected in (("数分", "数学分析"), ("线代", "线性代数")):
            results = search_courses(probe, 1, 5)
            self.assertGreater(results.total, 0, "%r found no course" % probe)
            self.assertTrue(
                any(expected in c.name for c in results.items),
                "%r did not surface %s (got %s)"
                % (probe, expected, [c.name for c in results.items]),
            )

    def test_mixed_script_query(self):
        # "微积分B" must reach 微积分(B1); the latin run is a one-character
        # prefix with no bigram of its own.
        results = search_courses("微积分B", 1, 10)
        self.assertGreater(results.total, 0)
        self.assertTrue(all("微积分" in c.name for c in results.items))

    def test_typo_falls_back_not_out(self):
        results = search_courses("数学分忻", 1, 5)  # 析 mistyped as 忻
        self.assertGreater(results.total, 0)
        self.assertLess(results.quality, MatchQuality.EXACT)

    def test_single_character_query(self):
        results = search_courses("数", 1, 5)
        self.assertGreater(results.total, 0)
        self.assertTrue(all("数" in c.name for c in results.items))

    def test_surname_plus_honorific_searches_teachers(self):
        # 张老师 reduces to 张, which alone would match a thousand course names.
        # The honorific says the user named a person, so it is answered against
        # teacher names instead.
        results = search_courses("张老师", 1, 10)
        if results.total == 0:
            self.skipTest("no teacher with this surname")
        for course in results.items:
            self.assertTrue(
                any("张" in t.name for t in course.teachers),
                "%r has no 张 teacher, so it should not match 张老师" % course.name,
            )

    def test_filler_suffix_is_not_treated_as_a_person(self):
        # 怎么样 is filler, not an honorific.  Treating it as one aimed the
        # remaining 数 at teacher names and returned nothing.
        plain = search_courses("数", 1, 5)
        with_filler = search_courses("数怎么样", 1, 5)
        self.assertEqual(with_filler.total, plain.total)
        self.assertEqual(with_filler.quality, plain.quality)

    def test_repeated_characters_do_not_break_the_last_resort_tier(self):
        # A duplicate character used to demand more distinct matches than the
        # query had, turning the final rung into a silent no-op.
        for probe in ("数学数", "线线代"):
            search_courses(probe, 1, 5)  # must not raise
        self.assertGreater(search_courses("数学数", 1, 5).total, 0)

    def test_overlong_query_says_it_was_truncated(self):
        results = search_courses("数学分析 " * 60, 1, 5)
        if results.total:
            self.assertTrue(results.truncated)
            self.assertIn("过长", results.note or "")

    def test_nonsense_returns_nothing_rather_than_noise(self):
        results = search_reviews("zzzqqqxxxjjj", 1, 10, self.anon)
        self.assertEqual(results.total, 0)

    def test_empty_query(self):
        self.assertEqual(search_reviews("", 1, 10, self.anon).total, 0)
        self.assertEqual(search_courses("   ", 1, 10).total, 0)

    def test_hostile_input_does_not_raise(self):
        for probe in (
            "!!!???",
            "%%%",
            "a" * 5000,
            "数" * 400,
            "\x00\x01",
            "🎉🎉🎉",
            "＋＋＋",
            "'; DROP TABLE reviews;--",
            "*",
            "+++",
            "​​",
            "数据结构 " * 60,
        ):
            search_courses(probe, 1, 10)
            search_reviews(probe, 1, 10, self.anon)


class TestVisibility(SearchTestCase):
    """Hidden, blocked and student-only reviews must not leak."""

    def test_blocked_and_hidden_never_appear(self):
        forbidden = {
            row[0]
            for row in db.session.execute(
                sa.text("SELECT id FROM reviews WHERE is_blocked = 1 OR is_hidden = 1")
            )
        }
        if not forbidden:
            self.skipTest("no blocked or hidden reviews in this database")
        for probe in ("老师", "课程", "考试"):
            results = search_reviews(probe, 1, 100, self.anon)
            leaked = forbidden & {r.id for r in results.items}
            self.assertEqual(leaked, set(), "%r leaked hidden reviews %s" % (probe, leaked))

    def test_student_only_hidden_from_anonymous(self):
        restricted = {
            row[0]
            for row in db.session.execute(
                sa.text(
                    "SELECT id FROM reviews WHERE only_visible_to_student = 1 "
                    "AND is_blocked = 0 AND is_hidden = 0"
                )
            )
        }
        if not restricted:
            self.skipTest("no student-only reviews in this database")
        for probe in ("老师", "课程"):
            results = search_reviews(probe, 1, 100, self.anon)
            leaked = restricted & {r.id for r in results.items}
            self.assertEqual(leaked, set(), "%r leaked student-only reviews" % probe)

    def test_teacher_identity_does_not_raise(self):
        # The previous engine compared a relationship to an integer here and
        # raised ArgumentError for every non-Student account -- 667 of them.
        from app.models import User

        teacher = User.query.filter(User.identity == "Teacher").first()
        if teacher is None:
            self.skipTest("no Teacher account in this database")
        results = search_reviews("老师", 1, 10, teacher)
        self.assertGreaterEqual(results.total, 0)

    def test_all_identities_agree_on_unrestricted_results(self):
        from app.models import User

        student = User.query.filter(User.identity == "Student").first()
        if student is None:
            self.skipTest("no Student account in this database")
        as_student = search_reviews("自杀", 1, 20, student)
        as_anon = search_reviews("自杀", 1, 20, self.anon)
        # A student sees at least what an anonymous visitor sees.
        self.assertTrue({r.id for r in as_anon.items} <= {r.id for r in as_student.items})


class TestPagination(SearchTestCase):
    def test_pages_do_not_overlap_or_skip(self):
        first = search_reviews("老师", 1, 10, self.anon)
        second = search_reviews("老师", 2, 10, self.anon)
        self.assertEqual(first.total, second.total)
        ids_a = [r.id for r in first.items]
        ids_b = [r.id for r in second.items]
        self.assertEqual(len(ids_a), 10)
        self.assertEqual(set(ids_a) & set(ids_b), set(), "pages overlap")

    def test_ordering_is_stable_across_calls(self):
        a = [r.id for r in search_reviews("考试", 1, 20, self.anon).items]
        b = [r.id for r in search_reviews("考试", 1, 20, self.anon).items]
        self.assertEqual(a, b)

    def test_page_beyond_the_end_is_empty_not_an_error(self):
        results = search_reviews("自杀", 500, 10, self.anon)
        self.assertEqual(results.items, [])

    def test_total_is_the_same_on_every_page(self):
        """Pages of one search must agree about how many results there are.

        Discounting deleted rows only when they fell inside the current window
        made total, pages and has_next differ per page, which could put the
        last page out of reach.
        """
        pages = [search_reviews("老师", n, 10, self.anon) for n in (1, 2, 3)]
        self.assertEqual(len({p.total for p in pages}), 1, "total differs between pages")
        self.assertEqual(len({p.pages for p in pages}), 1, "page count differs")

    def test_pager_links_have_neighbour_page_numbers(self):
        """review-list.html builds its «/» links from these; a missing
        attribute renders as an empty string and sends both arrows to page 1."""
        results = search_reviews("老师", 3, 10, self.anon)
        self.assertEqual(results.prev_num, 2)
        self.assertEqual(results.next_num, 4)
        self.assertEqual(search_reviews("老师", 1, 10, self.anon).prev_num, 1)


class TestRanking(SearchTestCase):
    def test_exact_course_name_ranks_first(self):
        for name in ("数据结构", "编译原理和技术", "概率论与数理统计"):
            results = search_courses(name, 1, 5)
            self.assertGreater(results.total, 0, name)
            self.assertEqual(
                results.items[0].name.strip(),
                name,
                "%r did not rank its exact match first (got %r)"
                % (name, results.items[0].name),
            )

    def test_verbatim_review_match_outranks_scattered_characters(self):
        results = search_reviews("给分很好", 1, 10, self.anon)
        if results.total == 0:
            self.skipTest("phrase absent from this database")
        top = TAGS.sub("", results.items[0].content or "")
        self.assertIn("给分很好", top.replace(" ", ""))


class TestLatency(SearchTestCase):
    QUERIES = ["自杀", "数分", "数据结构", "老师", "微积分B", "概率论与数理统计", "程学"]

    def test_p95_within_budget(self):
        timings = []
        for probe in self.QUERIES:
            search_reviews(probe, 1, 10, self.anon)  # warm
            for _ in range(5):
                start = time.perf_counter()
                search_reviews(probe, 1, 10, self.anon)
                search_courses(probe, 1, 10)
                timings.append((time.perf_counter() - start) * 1000.0)
        timings.sort()
        p95 = timings[int(len(timings) * 0.95) - 1]
        self.assertLess(
            p95,
            LATENCY_BUDGET_MS,
            "p95 %.1f ms exceeds the %.0f ms budget (max %.1f ms)"
            % (p95, LATENCY_BUDGET_MS, timings[-1]),
        )


class TestPopularQueryReplay(SearchTestCase):
    """Replay real queries; none should return nothing while a plain LIKE would
    have matched.  Guards the head of the distribution against regressions."""

    LIMIT = 200

    def test_no_popular_query_returns_a_false_empty(self):
        try:
            rows = db.session.execute(
                sa.text(
                    "SELECT keyword, COUNT(*) n FROM search_log "
                    "WHERE keyword IS NOT NULL AND CHAR_LENGTH(keyword) BETWEEN 2 AND 20 "
                    "GROUP BY keyword ORDER BY n DESC LIMIT :n"
                ),
                {"n": self.LIMIT},
            ).fetchall()
        except Exception:
            self.skipTest("no search_log table in this database")
        if not rows:
            self.skipTest("search_log is empty")

        false_empties = []
        for keyword, _count in rows:
            courses = search_courses(keyword, 1, 1)
            reviews = search_reviews(keyword, 1, 1, self.anon)
            if courses.total or reviews.total:
                continue
            like = "%" + keyword.strip() + "%"
            oracle = db.session.execute(
                sa.text(
                    "SELECT (SELECT COUNT(*) FROM reviews WHERE is_blocked = 0 AND "
                    "is_hidden = 0 AND only_visible_to_student = 0 AND content LIKE :w) + "
                    "(SELECT COUNT(*) FROM courses WHERE name LIKE :w)"
                ),
                {"w": like},
            ).scalar()
            if oracle:
                false_empties.append((keyword, oracle))
        self.assertEqual(
            false_empties, [], "queries that found nothing but should have: %s" % false_empties[:10]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
