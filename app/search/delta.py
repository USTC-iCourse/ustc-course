"""Freshness: everything the segment cannot know yet.

A segment is immutable, and rebuilding takes long enough that a review posted
in the meantime would otherwise be invisible to search -- which matters most in
exactly the case where it matters most, an administrator searching for a review
seconds after a crisis alert names it.

Two mechanisms close the gap, and between them the result of a search is exact:

*Changed rows* -- reviews written or edited at or after the segment's watermark
are read from the database, tokenized with the same functions the builder uses,
and matched directly.  Their stale copies in the segment are masked out, so an
edited review is judged only by its current text.  The set is bounded by the
rebuild interval, not by corpus size.

*Visibility* -- blocked, hidden and student-only reviews are a small set (a few
thousand out of thirty-odd thousand) that can be re-read wholesale and cached
briefly.  It is treated as the sole authority on those three flags rather than
as a correction to the segment, so a flag that has been *cleared* is handled as
correctly as one that has been set.

Deletion is the one case not covered here: a deleted review stays in the
segment until the next rebuild.  Hydration drops rows that no longer exist, so
no deleted review is ever displayed; only the result count can briefly overstate
by the number deleted since the last build.
"""

import time
from typing import Dict, List, NamedTuple, Optional, Sequence, Set

import numpy as np

from .collections import review_documents
from .retrieve import MatchQuality, Plan
from .segment import Segment

#: How long the visibility snapshot may be reused within a worker.  Short
#: enough that an administrator hiding a review sees it disappear promptly,
#: long enough that a burst of searches costs one query.
VISIBILITY_TTL = 30.0

#: Refuse to run the overlay if the rebuild timer has died and the changed-row
#: set has grown unbounded; better to serve slightly stale results than to
#: rescan the corpus on every request.  Surfaced in ``index_status``.
MAX_DELTA_ROWS = 5000


class DeltaDoc(NamedTuple):
    doc_id: int
    norm_text: str
    grams: Set[str]
    words: Set[str]
    pinyins: Set[str]
    meta: Set[str]
    gram_counts: Dict[str, int]
    length: int
    course_id: int
    author_id: int
    updated_at: float
    upvotes: float
    #: Read from the same row as the text, so these are the flags to trust for
    #: a changed row.  The visibility snapshot has a longer refresh interval
    #: and cannot yet know about a review posted seconds ago -- consulting it
    #: for one would report "no flags set" and publish a student-only review.
    blocked: bool
    hidden: bool
    student_only: bool


class Visibility(NamedTuple):
    """Authoritative flags for the reviews that have any flag set.

    Sole authority rather than a correction to the segment: a review not named
    here has all three flags clear, so a flag that was *cleared* since the
    build is handled as correctly as one that was set.  Carried as both sets
    (for single lookups) and sorted arrays (for vectorized filtering).
    """

    blocked: Set[int]
    hidden: Set[int]
    student_only: Set[int]
    author_of: Dict[int, int]
    blocked_arr: np.ndarray
    hidden_arr: np.ndarray
    student_only_arr: np.ndarray
    own_cache: Dict[int, np.ndarray]


class _Cache:
    """Per-worker state.  Deliberately not shared: each gunicorn worker keeps
    its own copy and its own expiry, so there is no coordination to get wrong."""

    def __init__(self):
        self.visibility: Optional[Visibility] = None
        self.visibility_at = 0.0
        self.docs: List[DeltaDoc] = []
        self.docs_at = 0.0
        self.docs_watermark = None
        self.overflowed = False


_cache = _Cache()


def visibility(db, ttl: float = VISIBILITY_TTL) -> Visibility:
    import sqlalchemy as sa

    now = time.time()
    if _cache.visibility is not None and now - _cache.visibility_at < ttl:
        return _cache.visibility

    blocked: Set[int] = set()
    hidden: Set[int] = set()
    student_only: Set[int] = set()
    author_of: Dict[int, int] = {}
    rows = db.session.execute(
        sa.text(
            "SELECT id, is_blocked, is_hidden, only_visible_to_student, author_id "
            "FROM reviews WHERE is_blocked = 1 OR is_hidden = 1 OR only_visible_to_student = 1"
        )
    )
    for rid, is_blocked, is_hidden, only_student, author_id in rows:
        if is_blocked:
            blocked.add(rid)
        if is_hidden:
            hidden.add(rid)
        if only_student:
            student_only.add(rid)
            author_of[rid] = author_id or 0
    def sorted_array(values: Set[int]) -> np.ndarray:
        return np.array(sorted(values), dtype=np.int64)

    snapshot = Visibility(
        blocked,
        hidden,
        student_only,
        author_of,
        sorted_array(blocked),
        sorted_array(hidden),
        sorted_array(student_only),
        {},
    )
    _cache.visibility = snapshot
    _cache.visibility_at = now
    return snapshot


def changed_reviews(db, seg: Segment, ttl: float = 5.0) -> List[DeltaDoc]:
    """Reviews written or edited since the segment was built."""
    now = time.time()
    if (
        _cache.docs_watermark == seg.built_at
        and now - _cache.docs_at < ttl
    ):
        return _cache.docs

    docs: List[DeltaDoc] = []
    overflowed = False
    for doc in review_documents(db, since=seg.built_at):
        grams = doc.streams["gram"]
        counts: Dict[str, int] = {}
        for g in grams:
            counts[g] = counts.get(g, 0) + 1
        docs.append(
            DeltaDoc(
                doc_id=doc.doc_id,
                norm_text=doc.norm_text,
                grams=set(grams),
                words=set(doc.streams["word"]),
                pinyins=set(doc.streams["pinyin"]),
                meta=set(doc.streams["meta"]),
                gram_counts=counts,
                length=max(1, len(grams)),
                course_id=int(doc.priors["course_id"]),
                author_id=int(doc.priors["author_id"]),
                updated_at=doc.priors["updated_at"],
                upvotes=doc.priors["upvotes"],
                blocked=bool(doc.priors["blocked"]),
                hidden=bool(doc.priors["hidden"]),
                student_only=bool(doc.priors["student_only"]),
            )
        )
        if len(docs) > MAX_DELTA_ROWS:
            overflowed = True
            break

    _cache.docs = docs
    _cache.docs_at = now
    _cache.docs_watermark = seg.built_at
    _cache.overflowed = overflowed
    return docs


def overflowed() -> bool:
    return _cache.overflowed


def invalidate() -> None:
    """Drop this worker's cached overlay.

    Normally unnecessary -- the caches expire on their own within seconds --
    but tests need to observe a write immediately, and it costs nothing to
    offer a way to say so explicitly.
    """
    _cache.visibility = None
    _cache.visibility_at = 0.0
    _cache.docs = []
    _cache.docs_at = 0.0
    _cache.docs_watermark = None
    _cache.overflowed = False


def match(docs: Sequence[DeltaDoc], plan: Plan, related_courses: Sequence[int] = ()):
    """Grade each changed row against the review tiers.

    Returns ``(doc, quality)`` for every row that matched at all.  Which tiers
    actually reach the page is decided in :mod:`app.search.service`, together
    with the segment's own candidates -- the ladder has to stop at one rung for
    the result as a whole, not once per source.
    """
    if plan.is_empty:
        return []
    related = set(related_courses)
    graded = []
    for doc in docs:
        if all(run in doc.norm_text for run in plan.runs):
            quality = MatchQuality.EXACT
        elif plan.gen_grams and all(g in doc.grams for g in plan.gen_grams):
            quality = MatchQuality.STRONG
        elif related and doc.course_id in related:
            quality = MatchQuality.RELATED
        elif any("u:" + run in doc.meta for run in plan.runs):
            # The author rung, which the segment ladder also has.  Without it a
            # review posted since the last build is unreachable by its author's
            # name while every other tier covers it.
            quality = MatchQuality.RELATED
        elif plan.pinyins and all(p in doc.pinyins for p in plan.pinyins):
            quality = MatchQuality.FUZZY
        else:
            continue
        graded.append((doc, quality))
    return graded


def score(seg: Segment, plan: Plan, doc: DeltaDoc, now: float = 0.0) -> float:
    """Score a changed row on the same scale as an indexed one.

    Inverse document frequency comes from the segment -- one extra document
    cannot meaningfully move a corpus statistic -- while term frequency and
    document length come from the row itself.  Without this, fresh results
    would need an arbitrary placement in the ordering.
    """
    k1, b = 1.2, 0.75
    n_docs = max(seg.doc_count, 1)
    norm = k1 * (1.0 - b + b * doc.length / max(seg.avg_doc_len, 1.0))
    total = 0.0
    for term in dict.fromkeys(plan.gen_grams):
        freq = float(doc.gram_counts.get(term, 0))
        if not freq:
            continue
        df = max(seg.doc_freq("gram", term), 1)
        idf = np.log1p((n_docs - df + 0.5) / (df + 0.5))
        total += idf * (freq * (k1 + 1.0)) / (freq + norm)

    if plan.gen_grams:
        total += 3.0 * (sum(g in doc.grams for g in plan.gen_grams) / len(plan.gen_grams))
    if plan.words:
        total += 2.0 * (sum(w in doc.words for w in plan.words) / len(plan.words))
    if plan.needs_verification and plan.runs and all(r in doc.norm_text for r in plan.runs):
        total += 4.0
    total += 0.4 * float(np.log1p(max(doc.upvotes, 0.0)))
    if now:
        age_years = max(now - doc.updated_at, 0.0) / 31_557_600.0
        total += 1.2 * float(np.exp(-age_years / 4.0))
    return total
