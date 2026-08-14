"""Public entry points: plan, retrieve, rank, paginate, hydrate.

This is the only module the rest of the application talks to.  Everything above
it -- the ladder, the postings algebra, the segment format -- is an
implementation detail that can change without touching a view.
"""

import calendar
import os
import threading
import time
from typing import Dict, List, Sequence

import numpy as np

from . import delta, rank
from .builder import segment_path
from .results import SearchResults
from .retrieve import (
    Candidates,
    MatchQuality,
    Plan,
    plan_query,
    retrieve_courses,
    retrieve_reviews,
)
from .segment import Segment

#: How often a worker checks whether the builder has replaced a segment.
_RELOAD_INTERVAL = 2.0

_EMPTY_IDX = np.zeros(0, dtype=np.int32)

#: Courses feeding the "reviews of a course you named" tier.  Bounded because
#: a vague query can match thousands of courses, and pulling in every review of
#: all of them would drown the content matches the user actually typed.
_RELATED_COURSE_LIMIT = 40


class IndexUnavailable(RuntimeError):
    """No segment on disk.  Raised rather than silently falling back to a
    different matching strategy: a search that quietly answers a different
    question than the one asked is how the previous engine lost 17% of its
    recall without anyone noticing."""


class _Registry:
    """Per-worker segment cache.

    Segments are replaced by an atomic rename, so a worker holding an open
    mapping keeps reading a consistent -- if briefly outdated -- file until it
    notices the new inode.  There is no locking against the builder, and none
    is needed.
    """

    def __init__(self):
        self._segments: Dict[str, Segment] = {}
        self._checked: Dict[str, float] = {}
        self._lock = threading.Lock()

    def get(self, app, collection: str) -> Segment:
        now = time.time()
        seg = self._segments.get(collection)
        if seg is not None and now - self._checked.get(collection, 0.0) < _RELOAD_INTERVAL:
            return seg
        path = segment_path(app, collection)
        try:
            mtime = os.stat(path).st_mtime
        except OSError:
            if seg is not None:
                return seg
            raise IndexUnavailable(
                "search index %r has not been built; run "
                "`PYTHONPATH=. python3 -m app.search.builder`" % path
            )
        with self._lock:
            self._checked[collection] = now
            current = self._segments.get(collection)
            if current is not None and current.mtime == mtime:
                return current
            fresh = Segment(path)
            self._segments[collection] = fresh
        # The superseded segment is deliberately not closed here.  A request
        # already in flight may still hold it, and closing its mapping out from
        # under that request would raise; dropping the reference is enough,
        # since the mapping is released when the last user lets go of it.
        return fresh

    def loaded(self) -> Dict[str, Segment]:
        return dict(self._segments)


_registry = _Registry()


def _app_db():
    from app import app, db

    return app, db


# --------------------------------------------------------------------------
# Courses
# --------------------------------------------------------------------------


def _rank_courses(seg: Segment, plan: Plan, cand: Candidates) -> np.ndarray:
    scores = rank.score_courses(seg, plan, cand.doc_idx, cand.positions)
    return rank.order(scores, cand.doc_idx, tiebreak=None)


def search_courses(query, page: int = 1, per_page: int = 10) -> SearchResults:
    app, db = _app_db()
    plan = plan_query(_as_text(query))
    if plan.is_empty:
        return SearchResults.empty(page, per_page)

    seg = _registry.get(app, "courses")
    cand = retrieve_courses(seg, plan)
    if cand.doc_idx.size == 0:
        return SearchResults(
            page, per_page, 0, [], cand.quality, cand.tier, cand.dropped,
            truncated=plan.truncated,
        )

    ordered = _rank_courses(seg, plan, cand)
    ids = seg.doc_ids[ordered]
    total = int(ids.size)
    window = ids[(page - 1) * per_page : page * per_page]
    items = _hydrate_courses(db, window)
    return SearchResults(
        page, per_page, total, items, cand.quality, cand.tier, cand.dropped,
        truncated=plan.truncated,
    )


def _hydrate_courses(db, ids: np.ndarray) -> List:
    from app.models import Course

    if ids.size == 0:
        return []
    wanted = [int(i) for i in ids]
    rows = Course.query.filter(Course.id.in_(wanted)).all()
    by_id = {row.id: row for row in rows}
    return [by_id[i] for i in wanted if i in by_id]


def _related_course_ids(seg: Segment, plan: Plan) -> List[int]:
    """Courses the query names, used to pull in their reviews.

    Only strong course matches qualify: a fuzzy or partial course match is too
    thin a thread to hang an entire course's reviews on.
    """
    cand = retrieve_courses(seg, plan)
    if cand.doc_idx.size == 0 or cand.quality < MatchQuality.RELATED:
        return []
    scores = rank.score_courses(seg, plan, cand.doc_idx, cand.positions)
    ordered = rank.order(scores, cand.doc_idx)[:_RELATED_COURSE_LIMIT]
    return [int(i) for i in seg.doc_ids[ordered]]


# --------------------------------------------------------------------------
# Reviews
# --------------------------------------------------------------------------


def _visible_mask(ids: np.ndarray, vis: delta.Visibility, current_user) -> np.ndarray:
    keep = ~np.isin(ids, vis.blocked_arr) & ~np.isin(ids, vis.hidden_arr)
    if _is_student(current_user):
        return keep
    restricted = np.isin(ids, vis.student_only_arr)
    if getattr(current_user, "is_authenticated", False):
        own = np.isin(ids, _own_restricted(vis, int(current_user.id)))
        return keep & (~restricted | own)
    return keep & ~restricted


def _is_student(current_user) -> bool:
    return bool(
        getattr(current_user, "is_authenticated", False)
        and getattr(current_user, "identity", None) == "Student"
    )


def _own_restricted(vis: delta.Visibility, user_id: int) -> np.ndarray:
    mine = vis.own_cache.get(user_id)
    if mine is None:
        mine = np.array(
            sorted(rid for rid, author in vis.author_of.items() if author == user_id),
            dtype=np.int64,
        )
        vis.own_cache[user_id] = mine
    return mine


def _delta_visible(doc: delta.DeltaDoc, vis: delta.Visibility, current_user) -> bool:
    """Visibility for a row the segment does not know about yet.

    Judged on the flags carried by the row itself, ORed with the snapshot.  A
    review posted seconds ago is by definition absent from a snapshot that may
    be half a minute old, and asking that snapshot about it would answer "no
    flags set" -- which for a student-only review means publishing it.
    """
    if doc.blocked or doc.hidden or doc.doc_id in vis.blocked or doc.doc_id in vis.hidden:
        return False
    if not (doc.student_only or doc.doc_id in vis.student_only):
        return True
    if _is_student(current_user):
        return True
    return bool(
        getattr(current_user, "is_authenticated", False)
        and int(current_user.id) == doc.author_id
    )


def search_reviews(query, page: int = 1, per_page: int = 10, current_user=None) -> SearchResults:
    _app, db = _app_db()
    ids, quality, tier, dropped, truncated = ranked_review_ids(query, current_user)
    if ids.size == 0:
        return SearchResults(
            page, per_page, 0, [], quality, tier, dropped, truncated=truncated
        )
    total = int(ids.size)
    window = ids[(page - 1) * per_page : page * per_page].tolist()
    # Rows deleted since the build do not come back from hydration, so a page
    # can be short.  ``total`` is deliberately *not* adjusted for them: it is a
    # property of the result set, and discounting only the deletions that
    # happen to fall in the current window made total, pages and has_next
    # disagree between pages of the same search -- which can put the last page
    # out of reach entirely.  The count is corrected by the next rebuild.
    items = _hydrate_reviews(db, window)
    return SearchResults(
        page, per_page, total, items, quality, tier, dropped,
        stale=delta.overflowed(), truncated=truncated,
    )


def ranked_review_ids(query, current_user=None):
    """Every matching review id, best first, without loading a single row.

    Separated from :func:`search_reviews` because retrieval and ranking are
    cheap while hydration is not: a caller that wants to know *what* matched --
    a recall test, an export, a count -- should not pay to materialize
    twenty thousand ORM objects to find out.
    """
    app, db = _app_db()
    # Review text is prose: an honorific in the query is text that really
    # occurs there, so the content plan keeps it.  The course lookup gets its
    # own plan, where stripping it is what makes 张老师 mean a teacher.
    plan = plan_query(_as_text(query), strip_honorific=False)
    if plan.is_empty:
        return np.zeros(0, dtype=np.int64), MatchQuality.EXACT, "empty", (), plan.truncated

    seg = _registry.get(app, "reviews")
    course_seg = _registry.get(app, "courses")
    related = _related_course_ids(course_seg, plan_query(_as_text(query)))

    changed = delta.changed_reviews(db, seg)
    vis = delta.visibility(db)
    now = time.time()

    cand = retrieve_reviews(seg, plan, related)
    graded = delta.match(changed, plan, related)

    # A row that has changed since the build is judged only by its current
    # text; its copy in the segment is stale by definition.
    stale_ids = np.array(sorted(doc.doc_id for doc in changed), dtype=np.int64)

    doc_idx = cand.doc_idx
    quality = cand.quality
    related_mask = cand.related
    positions = cand.positions
    if doc_idx.size and stale_ids.size:
        ids = seg.doc_ids[doc_idx]
        fresh = ~np.isin(ids, stale_ids)
        doc_idx = doc_idx[fresh]
        if related_mask is not None:
            related_mask = related_mask[fresh]
        if positions is not None:
            positions = positions[fresh]

    # The ladder stops at one rung for the result as a whole, and the rung is
    # the best either source reached.  Both sides are then held to it: raising
    # the reported quality for a fresh row while keeping weaker segment results
    # would label approximations as exact and suppress the caveat the whole
    # design exists to show.
    best_delta = max((q for _, q in graded), default=None)
    if best_delta is not None and best_delta > quality:
        quality, tier = best_delta, "delta"
        doc_idx = _EMPTY_IDX
        related_mask = positions = None
    else:
        tier = cand.tier
    graded = [(doc, q) for doc, q in graded if q >= quality]

    scores = np.zeros(0)
    ids = np.zeros(0, dtype=np.int64)
    if doc_idx.size:
        ids = seg.doc_ids[doc_idx]
        keep = _visible_mask(ids, vis, current_user)
        doc_idx = doc_idx[keep]
        if related_mask is not None:
            related_mask = related_mask[keep]
        if positions is not None:
            positions = positions[keep]
        if doc_idx.size:
            scores = rank.score_reviews(seg, plan, doc_idx, related_mask, positions, now=now)
            ids = seg.doc_ids[doc_idx].astype(np.int64)
        else:
            ids = np.zeros(0, dtype=np.int64)

    fresh = [
        (delta.score(seg, plan, doc, now=now), doc.doc_id)
        for doc, _q in graded
        if _delta_visible(doc, vis, current_user)
    ]
    if fresh:
        # The changed rows are few enough to append and sort with everything
        # else, which keeps a single ordering rather than two merged by hand.
        scores = np.concatenate([scores, np.array([s for s, _ in fresh])])
        ids = np.concatenate([ids, np.array([i for _, i in fresh], dtype=np.int64)])

    # Descending score, then newest first, so pagination is stable across
    # requests.  Sorting in numpy rather than as Python tuples matters here:
    # a common query can leave twenty thousand candidates standing.
    order = np.lexsort((-ids, -scores))
    return ids[order], quality, tier, cand.dropped, plan.truncated


def _hydrate_reviews(db, ids: Sequence[int]) -> List:
    from sqlalchemy.orm import lazyload

    from app.models import Review

    if not ids:
        return []
    rows = (
        Review.query.options(lazyload(Review.comments))
        .filter(Review.id.in_([int(i) for i in ids]))
        .all()
    )
    by_id = {row.id: row for row in rows}
    return [by_id[i] for i in ids if i in by_id]


# --------------------------------------------------------------------------
# Introspection
# --------------------------------------------------------------------------


def _as_text(query) -> str:
    """Accept a raw query string or a pre-split keyword list."""
    if isinstance(query, (list, tuple)):
        return " ".join(str(part) for part in query)
    return str(query or "")


def index_status() -> Dict[str, Dict]:
    app, _db = _app_db()
    status: Dict[str, Dict] = {}
    for name in ("courses", "reviews"):
        path = segment_path(app, name)
        try:
            seg = _registry.get(app, name)
        except IndexUnavailable:
            status[name] = {"built": False, "path": path}
            continue
        status[name] = {
            "built": True,
            "path": path,
            "documents": seg.doc_count,
            "built_at": seg.built_at.isoformat(),
            # built_at is naive UTC; timegm reads it as such, where mktime
            # would read it as local time.
            "age_seconds": time.time() - calendar.timegm(seg.built_at.timetuple()),
            "bytes": os.path.getsize(path),
        }
    status["delta_overflowed"] = delta.overflowed()
    return status
