"""Candidate generation: postings algebra and the relaxation ladder.

The old engine had exactly two behaviours -- an exact token match, or nothing.
``班风`` returned zero results because jieba never emitted it as a token, while
``微积分B`` returned 5,699 reviews because the bare token ``B`` was OR'd into
everything.  Both read to a user as a broken search.

What replaces it is a ladder.  Each rung is a strictly weaker way of matching
than the one above, retrieval stops at the first rung that produces anything,
and the rung that fired is reported so the page can say whether these are exact
results or approximations.  Nothing is silently widened.
"""

from enum import IntEnum
from typing import List, NamedTuple, Optional, Sequence

import numpy as np

from . import text as T
from .segment import Segment

_EMPTY = np.zeros(0, dtype=np.int32)

#: Guard on the OR rung.  Unioning very long postings lists is the one
#: operation here that can get expensive; when the bound bites, the terms that
#: were dropped are reported rather than quietly discarded.
_MAX_UNION_POSTINGS = 4_000_000

#: Longest query the engine will consider, in normalized characters.  Cost
#: grows with the number of grams, so an unbounded query is an unbounded
#: amount of work for one request.  No real search is anywhere near this; the
#: previous engine cut queries to ten whitespace-separated keywords.
MAX_QUERY_CHARS = 120


class MatchQuality(IntEnum):
    """How much the query had to be weakened to find anything."""

    EXACT = 4  # every query run occurs verbatim in the document
    STRONG = 3  # every query gram present, possibly non-contiguously
    RELATED = 2  # abbreviation, or reached through a related document
    FUZZY = 1  # one-character difference, or a homophone
    PARTIAL = 0  # only some of the query matched


class Plan(object):
    """A parsed query, in every form the tiers might need.

    The lower rungs of the ladder are reached by a small minority of queries,
    so the streams only they use -- jieba segmentation, pinyin -- are computed
    on first access rather than up front.  A query answered by the exact tier
    never loads the pinyin dictionary at all.
    """

    __slots__ = (
        "raw",
        "norm",
        "runs",
        "run_bytes",
        "gen_grams",
        "needs_verification",
        "person_hint",
        "truncated",
        "_memo",
    )

    def __init__(self, raw: str, strip_honorific: bool = True):
        self.raw = raw
        #: An honorific was stripped, so the query names a person.  Used to
        #: aim a short query at teacher names instead of at the whole corpus.
        #:
        #: Only worth doing against *names*.  In review prose ``谢老师`` is
        #: ordinary text that occurs verbatim, so review search plans the full
        #: query and lets the course lookup supply the stripped reading.
        if strip_honorific:
            self.norm, self.person_hint = T.normalize_query_parts(raw)
        else:
            self.norm, self.person_hint = T.normalize(raw), False
        #: The query was too long and only its prefix was searched.  Reported,
        #: because answering a shorter question than the one asked and calling
        #: the result exact is exactly the failure mode this engine exists to
        #: avoid.
        self.truncated = len(self.norm) > MAX_QUERY_CHARS
        if self.truncated:
            # Cut on a run boundary so the truncated query is still a sequence
            # of whole terms rather than a word sliced in half.
            self.norm = self.norm[:MAX_QUERY_CHARS].rsplit(T.SEP, 1)[0]
        self.runs = T.runs(self.norm)
        self.run_bytes = [r.encode("utf-8") for r in self.runs]
        # Grams usable for *generating* candidates.  A run of a single
        # character has no bigram, and its bare character is not a token of a
        # longer run -- ``b`` is not a token of ``b1``.  Such a run still
        # constrains the result, but through verification rather than through
        # the postings lists.
        self.gen_grams = T.grams(T.SEP.join(r for r in self.runs if len(r) >= 2), gap=1)
        # Verification is skipped only when the query is one run whose single
        # gram *is* that run, in which case a gram hit already proves a
        # substring hit.
        self.needs_verification = not (
            len(self.runs) == 1 and self.gen_grams == [self.runs[0]]
        )
        self._memo = {}

    def _lazy(self, key, fn):
        value = self._memo.get(key)
        if value is None:
            value = self._memo[key] = fn(self.norm)
        return value

    @property
    def skips(self) -> List[str]:
        return self._lazy("skips", lambda norm: T.grams(norm, gap=2))

    @property
    def chars(self) -> List[str]:
        return self._lazy("chars", T.chars)

    @property
    def words(self) -> List[str]:
        return self._lazy("words", T.words)

    @property
    def pinyins(self) -> List[str]:
        return self._lazy("pinyins", T.pinyin_grams)

    @property
    def pynames(self) -> List[str]:
        return self._lazy(
            "pynames",
            lambda norm: T.pinyin_whole(norm)
            + [r for r in self.runs if not T.is_cjk(r[0]) and len(r) >= 3],
        )

    @property
    def pyinits(self) -> List[str]:
        return self._lazy(
            "pyinits", lambda norm: [i for i in T.pinyin_initials(norm) if len(i) >= 3]
        )

    @property
    def is_empty(self) -> bool:
        return not self.runs

    @property
    def scannable(self) -> bool:
        """No gram is selective enough to generate candidates from, so the only
        way to answer the query is to look at every document."""
        return bool(self.runs) and not self.gen_grams

    def __repr__(self):
        return "Plan(%r -> %r)" % (self.raw, self.norm)


class Candidates(NamedTuple):
    doc_idx: np.ndarray
    quality: MatchQuality
    tier: str
    #: Terms the OR rung had to drop to stay inside its budget.
    dropped: Sequence[str] = ()
    #: Aligned with ``doc_idx``: this document was reached through a related
    #: document (a review of a course the query names) rather than by matching
    #: the query itself.
    related: Optional[np.ndarray] = None
    #: Aligned with ``doc_idx``: byte offset of the query in each document, or
    #: -1.  Verification already had to find it; carrying the answer forward
    #: saves the ranker from repeating the search.
    positions: Optional[np.ndarray] = None


def plan_query(raw: str, strip_honorific: bool = True) -> Plan:
    return Plan(raw, strip_honorific=strip_honorific)


def warmup() -> None:
    """Load the tokenizer dictionaries.

    jieba, pypinyin and zhconv each load a large table on first use, which
    would otherwise land on whichever unlucky request came first -- measured at
    just under a second.  Called at import so that a preloading gunicorn pays
    it once, before forking.
    """
    plan = Plan("预热 warmup")
    plan.words, plan.pinyins, plan.pynames, plan.pyinits, plan.skips, plan.chars


# --------------------------------------------------------------------------
# Postings algebra
# --------------------------------------------------------------------------


def intersect(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Intersection of two ascending, duplicate-free postings lists.

    ``searchsorted`` of the shorter into the longer is O(|a| log |b|); the
    caller sorts by length so ``a`` is always the shorter one.
    """
    if a.size == 0 or b.size == 0:
        return _EMPTY
    pos = np.searchsorted(b, a)
    np.clip(pos, 0, b.size - 1, out=pos)
    return a[b[pos] == a]


def match_all(seg: Segment, field: str, terms: Sequence[str]) -> np.ndarray:
    """Documents containing every term."""
    if not terms:
        return _EMPTY
    lists = []
    for term in dict.fromkeys(terms):
        docs, _ = seg.postings(field, term)
        if docs.size == 0:
            return _EMPTY
        lists.append(docs)
    lists.sort(key=lambda arr: arr.size)
    acc = lists[0]
    for other in lists[1:]:
        acc = intersect(acc, other)
        if acc.size == 0:
            return _EMPTY
    return acc


def match_at_least(seg: Segment, field: str, terms: Sequence[str], minimum: int):
    """Documents containing at least ``minimum`` of the terms.

    Returns the postings and the terms that were dropped to stay within the
    union budget.
    """
    unique = list(dict.fromkeys(terms))
    if not unique:
        return _EMPTY, ()
    by_size = sorted(
        ((seg.postings(field, t)[0], t) for t in unique), key=lambda pair: pair[0].size
    )
    kept, dropped, missing, total = [], [], 0, 0
    for docs, term in by_size:
        if docs.size == 0:
            # A term nothing contains.  It cannot be counted toward the
            # threshold, and if the threshold needed it the query is
            # unsatisfiable -- not merely satisfiable by whatever is left.
            missing += 1
            continue
        if total + docs.size > _MAX_UNION_POSTINGS and kept:
            dropped.append(term)
            continue
        kept.append(docs)
        total += docs.size
    if not kept or minimum > len(unique) - missing - len(dropped):
        return _EMPTY, tuple(dropped)
    need = max(1, min(minimum, len(kept)))
    if need == 1:
        return np.unique(np.concatenate(kept)), tuple(dropped)
    values, counts = np.unique(np.concatenate(kept), return_counts=True)
    return values[counts >= need].astype(np.int32), tuple(dropped)


def match_all_dropping(seg: Segment, field: str, terms: Sequence[str]):
    """AND, then progressively drop the least selective term until something
    matches.  Keeps at least half the query, so a two-word search never decays
    into a one-word search."""
    unique = list(dict.fromkeys(terms))
    if not unique:
        return _EMPTY, ()
    ranked = sorted(unique, key=lambda t: -seg.doc_freq(field, t))  # least selective first
    dropped: List[str] = []
    floor = max(1, (len(unique) + 1) // 2)
    while len(ranked) - len(dropped) >= floor:
        remaining = ranked[len(dropped) :]
        hits = match_all(seg, field, remaining)
        if hits.size:
            return hits, tuple(dropped)
        if len(remaining) <= floor:
            break
        dropped.append(ranked[len(dropped)])
    return _EMPTY, tuple(dropped)


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------


def verify_substrings(seg: Segment, cand: np.ndarray, needles: Sequence[bytes]):
    """Keep candidates whose normalized text contains every query run.

    Turns a gram match, which only proves the characters co-occur, into a real
    substring match.  Returns the survivors and where the first run was found
    in each, which is the ranker's strongest positional signal.
    """
    if cand.size == 0 or not needles:
        return cand, None
    keep = np.zeros(cand.size, dtype=bool)
    pos = np.full(cand.size, -1, dtype=np.int64)
    find = seg.find
    head, rest = needles[0], needles[1:]
    for i, doc in enumerate(cand):
        idx = int(doc)
        first = find(idx, head)
        if first < 0 or any(find(idx, needle) < 0 for needle in rest):
            continue
        keep[i] = True
        pos[i] = first
    return cand[keep], pos[keep]


def scan(seg: Segment, plan: Plan, zone: str = "") -> np.ndarray:
    """Answer a query too short to have a bigram.

    A single Chinese character has no bigram, and its bare character is not a
    token of any longer run, so the ``gram`` field cannot generate candidates
    for it.  The ``char`` field can, and does so exactly: it holds every
    character of every run, so a character-level conjunction *is* the answer
    for single-character runs -- no verification needed.

    Only if a segment predates that field does this fall back to reading every
    document, which is linear but still exact.

    ``zone="teacher"`` keeps only matches inside the teacher-name region of a
    course document, which is what makes ``张老师`` mean "a teacher called 张"
    rather than "anything containing the character 张".
    """
    needles = plan.run_bytes
    if not needles:
        return _EMPTY
    find = seg.find

    # A latin run is indexed whole, not per letter, so ``a`` is not a token of
    # ``abc`` and the char field cannot generate candidates for it.  Chinese
    # characters are always indexed individually, so they can.
    latin_fragment = any(len(r) == 1 and not T.is_cjk(r[0]) for r in plan.runs)

    if "char" in seg.fields and not latin_fragment:
        hits = match_all(seg, "char", plan.chars)
        # Runs longer than one character still need their order checked; a
        # single-character run is already proven by its posting.
        if any(len(r) > 1 for r in plan.runs):
            hits = verify_substrings(seg, hits, needles)[0]
    else:
        hits = np.array(
            [i for i in range(seg.doc_count) if all(find(i, n) >= 0 for n in needles)],
            dtype=np.int32,
        )

    if zone != "teacher" or not seg.has_prior("zone_teacher") or hits.size == 0:
        return hits
    starts = seg.prior("zone_teacher")
    ends = seg.prior("zone_code")
    keep = np.zeros(hits.size, dtype=bool)
    for i, doc in enumerate(hits):
        idx = int(doc)
        lo, hi = int(starts[idx]), int(ends[idx])
        if hi <= lo:
            continue
        found = find(idx, needles[0], lo)
        keep[i] = 0 <= found < hi
    return hits[keep]


def verify_subsequence(seg: Segment, cand: np.ndarray, plan: Plan, limit: int = 0) -> np.ndarray:
    """Keep candidates whose text contains the query's characters *in order*.

    This is what turns ``数分`` into ``数学分析``.  It is only meaningful for
    short documents: over a 300-character review almost any two characters
    appear in order somewhere, which is why reviews have no subsequence tier.

    ``limit`` bounds the search to the document's leading zone (a course's
    name), so an abbreviation cannot be assembled out of a teacher's name.
    """
    if cand.size == 0 or not plan.chars:
        return cand
    needles = [c.encode("utf-8") for c in plan.chars]
    keep = np.zeros(cand.size, dtype=bool)
    zone = seg.prior("zone_teacher") if limit and seg.has_prior("zone_teacher") else None
    for i, doc in enumerate(cand):
        idx = int(doc)
        stop = int(zone[idx]) if zone is not None else 0
        at = 0
        ok = True
        for needle in needles:
            found = seg.find(idx, needle, at)
            if found < 0 or (stop and found >= stop):
                ok = False
                break
            at = found + len(needle)
        keep[i] = ok
    return cand[keep]


# --------------------------------------------------------------------------
# The ladders
# --------------------------------------------------------------------------


def _verified(seg: Segment, plan: Plan, hits: np.ndarray):
    if not plan.needs_verification:
        return hits, None
    return verify_substrings(seg, hits, plan.run_bytes)


def retrieve_courses(seg: Segment, plan: Plan) -> Candidates:
    if plan.is_empty:
        return Candidates(_EMPTY, MatchQuality.PARTIAL, "empty")

    if plan.scannable:
        # A query left this short by stripping an honorific is a surname, and
        # belongs against teacher names only.
        found = scan(seg, plan, zone="teacher" if plan.person_hint else "")
        if found.size:
            return Candidates(found, MatchQuality.EXACT, "scan")

    hits = match_all(seg, "gram", plan.gen_grams)
    verified, positions = _verified(seg, plan, hits)
    if verified.size:
        return Candidates(verified, MatchQuality.EXACT, "gram+verify", positions=positions)
    if hits.size and not plan.needs_verification:
        return Candidates(hits, MatchQuality.EXACT, "gram")
    if hits.size:
        return Candidates(hits, MatchQuality.STRONG, "gram")

    # Abbreviations: 数分 -> 数学分析, 程设 -> 程序设计.  Single characters
    # generate the candidates; ordered-subsequence verification makes them mean
    # something.  Restricted to the name zone.
    chars = match_all(seg, "char", plan.chars)
    abbrev = verify_subsequence(seg, chars, plan, limit=1)
    if abbrev.size:
        return Candidates(abbrev, MatchQuality.RELATED, "subsequence")

    # One character different: absorbs typos, and connective variation
    # (编译原理与技术 vs 编译原理和技术) without a hand-maintained word list.
    skips = match_all(seg, "skip", plan.skips)
    if skips.size:
        return Candidates(skips, MatchQuality.FUZZY, "skipgram")

    # Homophones and IME slips.  Whole-run pinyin first (``zhangsan`` -> 张三),
    # then syllable bigrams (``自杀``/``紫砂``), then initials -- which are weak
    # enough that plan_query only keeps them at three letters or more.
    whole = match_all(seg, "pyname", plan.pynames)
    if whole.size:
        return Candidates(whole, MatchQuality.FUZZY, "pinyin-name")

    homophone = match_all(seg, "pinyin", plan.pinyins)
    if homophone.size:
        return Candidates(homophone, MatchQuality.FUZZY, "pinyin")

    initials = match_all(seg, "pyinit", plan.pyinits)
    if initials.size:
        return Candidates(initials, MatchQuality.FUZZY, "pinyin-initials")

    partial, dropped = match_all_dropping(seg, "gram", plan.gen_grams)
    if partial.size:
        return Candidates(partial, MatchQuality.PARTIAL, "gram-partial", dropped)

    # De-duplicate before counting: match_at_least works on distinct terms, so
    # a repeated character (数学数) would demand more matches than exist and
    # turn the last-resort rung into a no-op.
    loose, dropped = match_at_least(
        seg, "char", plan.chars, len(dict.fromkeys(plan.chars))
    )
    if loose.size:
        return Candidates(loose, MatchQuality.PARTIAL, "char", dropped)
    return Candidates(_EMPTY, MatchQuality.PARTIAL, "none")


def retrieve_reviews(seg: Segment, plan: Plan, related_courses: Sequence[int] = ()) -> Candidates:
    """Review ladder.

    Deliberately shorter than the course ladder: reviews are long-form text,
    where subsequence and single-character-difference matching stop being
    evidence of anything.
    """
    if plan.is_empty:
        return Candidates(_EMPTY, MatchQuality.PARTIAL, "empty")

    if plan.scannable:
        found = scan(seg, plan)
        if found.size:
            return Candidates(found, MatchQuality.EXACT, "scan")

    hits = match_all(seg, "gram", plan.gen_grams)
    verified, positions = _verified(seg, plan, hits)
    if verified.size:
        content, quality, tier = verified, MatchQuality.EXACT, "gram+verify"
    elif hits.size and not plan.needs_verification:
        content, quality, tier, positions = hits, MatchQuality.EXACT, "gram", None
    else:
        content, quality, tier, positions = hits, MatchQuality.STRONG, "gram", None

    # Reviews of a course the query names.  This is the relationship the old
    # engine expressed by copying each course's text into every one of its
    # reviews five times over; here it is a join, merged with the content
    # matches rather than smuggled into them.
    by_course = _EMPTY
    if related_courses:
        by_course = match_at_least(seg, "meta", ["c:%d" % cid for cid in related_courses], 1)[0]

    if content.size or by_course.size:
        merged = np.union1d(content, by_course).astype(np.int32)
        related = np.isin(merged, by_course) & ~np.isin(merged, content)
        merged_pos = None
        if positions is not None:
            # ``content`` is a sorted subset of ``merged``, so searchsorted
            # places each verified position at its row in the merged array.
            merged_pos = np.full(merged.size, -1, dtype=np.int64)
            merged_pos[np.searchsorted(merged, content)] = positions
        if not content.size:
            quality, tier = MatchQuality.RELATED, "course"
        elif by_course.size:
            tier += "+course"
        return Candidates(merged, quality, tier, (), related, merged_pos)

    author = match_at_least(seg, "meta", ["u:" + r for r in plan.runs], 1)[0]
    if author.size:
        return Candidates(author, MatchQuality.RELATED, "author")

    homophone = match_all(seg, "pinyin", plan.pinyins)
    if homophone.size:
        return Candidates(homophone, MatchQuality.FUZZY, "pinyin")

    partial, dropped = match_all_dropping(seg, "gram", plan.gen_grams)
    if partial.size:
        return Candidates(partial, MatchQuality.PARTIAL, "gram-partial", dropped)
    return Candidates(_EMPTY, MatchQuality.PARTIAL, "none")
