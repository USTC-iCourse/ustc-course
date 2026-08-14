"""The freshness overlay: writes are visible to search before the next rebuild.

Everything here runs inside a transaction that is rolled back, so the database
is left exactly as it was found.  The overlay reads through the same session,
so it sees the uncommitted rows -- which is precisely the property under test.

    PYTHONPATH=. python3 tests/test_search_freshness.py
"""

import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlalchemy as sa  # noqa: E402

from app import app, db  # noqa: E402
from app.search import IndexUnavailable, MatchQuality, ranked_review_ids  # noqa: E402
from app.search import delta  # noqa: E402
from app.search.service import _registry  # noqa: E402

#: A string that cannot occur in the corpus, so any hit is the row we wrote.
NONCE = "锟斤拷烫烫烫垃圾测试字符串"


class AnonymousUser(object):
    is_authenticated = False
    identity = None
    id = None


class FreshnessTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = app.app_context()
        cls.ctx.push()
        try:
            _registry.get(app, "reviews")
        except IndexUnavailable as exc:
            raise unittest.SkipTest(str(exc))
        cls.anon = AnonymousUser()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def setUp(self):
        delta.invalidate()
        self.written = []

    def tearDown(self):
        db.session.rollback()
        delta.invalidate()

    def _expire_changed_rows_only(self):
        """Age out the changed-rows cache while leaving the visibility snapshot
        as it is -- the state production is in whenever a review is posted
        between two visibility refreshes."""
        delta._cache.docs_at = 0.0
        delta._cache.docs_watermark = None

    def _insert_review(self, content, invalidate=True, **overrides):
        """Insert a review inside the open transaction and return its id."""
        course_id = db.session.execute(
            sa.text("SELECT id FROM courses ORDER BY id LIMIT 1")
        ).scalar()
        author_id = db.session.execute(
            sa.text("SELECT id FROM users ORDER BY id LIMIT 1")
        ).scalar()
        fields = {
            "content": content,
            "course_id": course_id,
            "author_id": author_id,
            "publish_time": datetime.utcnow(),
            "update_time": datetime.utcnow(),
            "upvote_count": 0,
            "comment_count": 0,
            "is_anonymous": 0,
            "only_visible_to_student": 0,
            "is_hidden": 0,
            "is_blocked": 0,
            "rate": 8,
        }
        fields.update(overrides)
        columns = ", ".join(fields)
        params = ", ".join(":" + key for key in fields)
        db.session.execute(
            sa.text("INSERT INTO reviews (%s) VALUES (%s)" % (columns, params)), fields
        )
        review_id = db.session.execute(sa.text("SELECT LAST_INSERT_ID()")).scalar()
        self.written.append(review_id)
        if invalidate:
            delta.invalidate()
        else:
            self._expire_changed_rows_only()
        return review_id

    def _find(self, query):
        ids, quality, tier = ranked_review_ids(query, self.anon)[:3]
        return set(ids.tolist()), quality, tier


class TestNewReviews(FreshnessTestCase):
    def test_a_brand_new_review_is_immediately_findable(self):
        review_id = self._insert_review("<p>这门课的%s非常有意思</p>" % NONCE)
        found, quality, _tier = self._find(NONCE)
        self.assertIn(review_id, found)
        self.assertEqual(quality, MatchQuality.EXACT)

    def test_a_new_review_is_findable_by_a_substring(self):
        review_id = self._insert_review("<p>%s很难</p>" % NONCE)
        found, _quality, _tier = self._find(NONCE[2:6])
        self.assertIn(review_id, found)

    def test_html_is_stripped_before_matching(self):
        review_id = self._insert_review("<p><strong>%s</strong></p>" % NONCE)
        found, _quality, _tier = self._find(NONCE)
        self.assertIn(review_id, found)
        # Markup must not itself be searchable.
        by_markup, _q, _t = self._find("strong")
        self.assertNotIn(review_id, by_markup)


class TestEditedReviews(FreshnessTestCase):
    def test_an_edit_replaces_the_indexed_text(self):
        """The stale copy in the segment must not answer for the new text."""
        existing = db.session.execute(
            sa.text(
                "SELECT id, content FROM reviews WHERE is_blocked = 0 AND is_hidden = 0 "
                "AND only_visible_to_student = 0 AND content LIKE '%考试%' "
                "ORDER BY id DESC LIMIT 1"
            )
        ).fetchone()
        if existing is None:
            self.skipTest("no suitable review to edit")
        review_id = existing[0]

        before, _q, _t = self._find("考试")
        self.assertIn(review_id, before)

        db.session.execute(
            sa.text("UPDATE reviews SET content = :c, update_time = :t WHERE id = :i"),
            {"c": "<p>%s</p>" % NONCE, "t": datetime.utcnow(), "i": review_id},
        )
        delta.invalidate()

        after, _q, _t = self._find("考试")
        self.assertNotIn(
            review_id, after, "the segment's stale text still answered for an edited review"
        )
        by_new_text, _q, _t = self._find(NONCE)
        self.assertIn(review_id, by_new_text)


class TestVisibilityIsLive(FreshnessTestCase):
    def test_hiding_a_review_removes_it_without_a_rebuild(self):
        target = db.session.execute(
            sa.text(
                "SELECT id FROM reviews WHERE is_blocked = 0 AND is_hidden = 0 "
                "AND only_visible_to_student = 0 AND content LIKE '%老师%' "
                "ORDER BY id DESC LIMIT 1"
            )
        ).scalar()
        if target is None:
            self.skipTest("no suitable review")
        self.assertIn(target, self._find("老师")[0])

        db.session.execute(
            sa.text("UPDATE reviews SET is_hidden = 1 WHERE id = :i"), {"i": target}
        )
        delta.invalidate()
        self.assertNotIn(target, self._find("老师")[0])

    def test_clearing_a_flag_restores_the_review(self):
        """The visibility snapshot is the authority, not a correction to the
        index -- so a flag being *cleared* has to work too."""
        target = db.session.execute(
            sa.text(
                "SELECT id FROM reviews WHERE is_hidden = 1 AND is_blocked = 0 "
                "AND only_visible_to_student = 0 ORDER BY id DESC LIMIT 1"
            )
        ).scalar()
        if target is None:
            self.skipTest("no hidden review to restore")
        content = db.session.execute(
            sa.text("SELECT content FROM reviews WHERE id = :i"), {"i": target}
        ).scalar()

        db.session.execute(
            sa.text("UPDATE reviews SET is_hidden = 0 WHERE id = :i"), {"i": target}
        )
        delta.invalidate()

        # Find a phrase that really occurs in it, then check it comes back.
        import re

        plain = re.sub(r"<[^>]+>", "", content or "")
        probe = next((m for m in re.findall(r"[一-鿿]{3,}", plain)), None)
        if not probe:
            self.skipTest("review has no usable probe text")
        self.assertIn(target, self._find(probe[:3])[0])

    def test_student_only_review_is_hidden_from_anonymous_immediately(self):
        review_id = self._insert_review(
            "<p>%s</p>" % NONCE, only_visible_to_student=1
        )
        found, _q, _t = self._find(NONCE)
        self.assertNotIn(review_id, found)

    def test_new_restricted_review_is_hidden_even_with_a_stale_snapshot(self):
        """The two overlay caches expire on different schedules.

        A brand-new row enters the candidate set within seconds, but the
        visibility snapshot refreshes far less often and cannot contain it.
        Judging the row against that snapshot answered "no flags set" and
        published a student-only review to anonymous visitors for as long as
        the snapshot lived.
        """
        delta.visibility(db)  # prime the snapshot *before* the row exists
        snapshot_at = delta._cache.visibility_at
        review_id = self._insert_review(
            "<p>%s</p>" % NONCE, invalidate=False, only_visible_to_student=1
        )
        self.assertEqual(
            delta._cache.visibility_at, snapshot_at, "snapshot should still be stale"
        )
        self.assertNotIn(review_id, self._find(NONCE)[0])

    def test_new_hidden_review_is_never_returned(self):
        delta.visibility(db)
        review_id = self._insert_review("<p>%s</p>" % NONCE, invalidate=False, is_hidden=1)
        self.assertNotIn(review_id, self._find(NONCE)[0])


class TestOverlayBounds(FreshnessTestCase):
    def test_watermark_bounds_the_overlay(self):
        seg = _registry.get(app, "reviews")
        changed = delta.changed_reviews(db, seg)
        self.assertLessEqual(
            len(changed),
            delta.MAX_DELTA_ROWS + 1,
            "the overlay is unbounded; the rebuild timer is probably not running",
        )
        for doc in changed:
            self.assertGreaterEqual(
                doc.updated_at,
                (seg.built_at - timedelta(seconds=2)).timestamp() - 86400,
                "overlay pulled in a row older than the watermark",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
