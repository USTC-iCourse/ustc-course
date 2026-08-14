"""Scoring.

Retrieval hands over at most a few hundred candidates, so ranking can afford to
be explicit: it is a weighted sum of named features computed with numpy over
the candidate arrays, not an ordering smuggled into the shape of a SQL query.

The engine this replaces had no ranking layer to speak of.  Course results were
ordered by a literal integer column carried through a five-way UNION and read
back out by guessing at SQLAlchemy's generated column names -- the source
comments apologise for it -- and review results were ordered by MySQL's
boolean-mode relevance, which is close to a term count.  Both are gone.
"""

from typing import Optional, Sequence

import numpy as np

from .retrieve import Plan
from .segment import Segment

_K1 = 1.2
_B = 0.75


def bm25(seg: Segment, field: str, terms: Sequence[str], cand: np.ndarray) -> np.ndarray:
    """Okapi BM25 over one field, evaluated only at the candidate documents."""
    scores = np.zeros(cand.size, dtype=np.float64)
    if cand.size == 0 or not terms:
        return scores
    n_docs = max(seg.doc_count, 1)
    doc_len = seg.doc_len[cand].astype(np.float64)
    norm = _K1 * (1.0 - _B + _B * doc_len / max(seg.avg_doc_len, 1.0))
    for term in dict.fromkeys(terms):
        docs, tf = seg.postings(field, term)
        if docs.size == 0:
            continue
        pos = np.clip(np.searchsorted(docs, cand), 0, docs.size - 1)
        hit = docs[pos] == cand
        freq = np.where(hit, tf[pos], 0).astype(np.float64)
        idf = np.log1p((n_docs - docs.size + 0.5) / (docs.size + 0.5))
        scores += idf * (freq * (_K1 + 1.0)) / (freq + norm)
    return scores


def coverage(seg: Segment, field: str, terms: Sequence[str], cand: np.ndarray) -> np.ndarray:
    """Fraction of the query's terms that a document contains.

    Distinguishes a document matching all of a relaxed query from one matching
    the bare minimum the rung allowed through.
    """
    unique = list(dict.fromkeys(terms))
    if cand.size == 0 or not unique:
        return np.zeros(cand.size)
    hits = np.zeros(cand.size, dtype=np.float64)
    for term in unique:
        docs, _ = seg.postings(field, term)
        if docs.size == 0:
            continue
        pos = np.clip(np.searchsorted(docs, cand), 0, docs.size - 1)
        hits += docs[pos] == cand
    return hits / len(unique)


def first_positions(seg: Segment, cand: np.ndarray, needle: bytes) -> np.ndarray:
    """Offset of the query in each candidate's text, or -1."""
    out = np.full(cand.size, -1, dtype=np.int64)
    if not needle:
        return out
    for i, doc in enumerate(cand):
        out[i] = seg.find(int(doc), needle)
    return out


def _bayesian_rate(seg: Segment) -> np.ndarray:
    """Rating shrunk toward the global mean, matching the ordering the rest of
    the site already uses for course lists (``Course.QUERY_ORDER``)."""
    cached = seg.cache.get("bayes")
    if cached is not None:
        return cached
    rate = seg.prior("rate")
    count = seg.prior("review_count")
    rated = count > 0
    prior_mean = float(rate[rated].mean()) if rated.any() else 0.0
    prior_weight = float(count[rated].mean()) if rated.any() else 1.0
    value = (rate * count + prior_mean * prior_weight) / (count + prior_weight)
    seg.cache["bayes"] = value
    return value


def score_courses(
    seg: Segment, plan: Plan, cand: np.ndarray, positions: Optional[np.ndarray] = None
) -> np.ndarray:
    """Relevance for course results.

    Where a match landed matters more than how often it occurred: a query
    hitting the course name is a different event from one hitting a teacher's
    name or a course code.  Rather than pay for three postings fields, each
    document records the byte offsets of its zones and the ranker reads the
    match position.
    """
    if cand.size == 0:
        return np.zeros(0)

    score = bm25(seg, "gram", plan.gen_grams, cand)
    score += 2.0 * coverage(seg, "gram", plan.gen_grams, cand)
    score += 1.5 * coverage(seg, "word", plan.words, cand)

    needle = plan.run_bytes[0] if plan.run_bytes else b""
    pos = positions if positions is not None else first_positions(seg, cand, needle)
    teacher_at = seg.prior("zone_teacher")[cand]
    code_at = seg.prior("zone_code")[cand]

    found = pos >= 0
    in_name = found & (pos < teacher_at)
    in_teacher = found & ~in_name & (pos < code_at)
    in_code = found & ~in_name & ~in_teacher
    score += 6.0 * in_name + 3.0 * in_teacher + 2.0 * in_code
    # A match at the very start of the name is what the user most likely meant.
    score += 3.0 * (in_name & (pos == 0))
    # ...and one that consumes the entire name even more so.
    whole_name = in_name & (teacher_at == len(needle) + 1)
    score += 4.0 * whole_name

    score += 0.35 * _bayesian_rate(seg)[cand]
    score += 0.25 * np.log1p(seg.prior("review_count")[cand])
    # Courses still being taught are more useful than retired ones.
    term = seg.prior("term")[cand]
    newest = term.max() if term.size else 0.0
    score += 0.5 * (term >= newest - 20)
    return score


def score_reviews(
    seg: Segment,
    plan: Plan,
    cand: np.ndarray,
    related: Optional[np.ndarray] = None,
    positions: Optional[np.ndarray] = None,
    now: float = 0.0,
) -> np.ndarray:
    """Relevance for review results."""
    if cand.size == 0:
        return np.zeros(0)

    score = bm25(seg, "gram", plan.gen_grams, cand)
    score += 3.0 * coverage(seg, "gram", plan.gen_grams, cand)
    score += 2.0 * coverage(seg, "word", plan.words, cand)

    if plan.needs_verification and plan.run_bytes:
        # A verbatim occurrence outranks the same characters scattered about.
        pos = positions if positions is not None else first_positions(seg, cand, plan.run_bytes[0])
        score += 4.0 * (pos >= 0)

    if related is not None and related.size == cand.size:
        # Reviews pulled in because they belong to a course the query names.
        # Ranked as their own kind of result rather than competing on text.
        score = np.where(related, 5.0, score)

    score += 0.4 * np.log1p(np.maximum(seg.prior("upvotes")[cand], 0.0))
    if now:
        age_years = np.maximum(now - seg.prior("updated_at")[cand], 0.0) / 31_557_600.0
        score += 1.2 * np.exp(-age_years / 4.0)
    return score


def order(score: np.ndarray, cand: np.ndarray, tiebreak: Optional[np.ndarray] = None):
    """Descending by score, with a deterministic tiebreak so pagination is
    stable across requests."""
    if cand.size == 0:
        return cand
    keys = [cand] if tiebreak is None else [cand, -tiebreak]
    keys.append(-score)
    return cand[np.lexsort(tuple(keys))]
