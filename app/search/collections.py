"""What a course document and a review document are made of.

Two collections, deliberately given different field sets.  Course documents are
tiny -- the whole catalogue is 0.8 MB of text -- so they can afford every field
that might help: gapped grams for typo tolerance, single characters to drive
subsequence matching (``数分`` -> ``数学分析``), whole-name pinyin and initials.
Review documents are 10 MB of prose, where those tiers are either expensive or
meaningless: a two-character query is a subsequence of nearly every review, so
a subsequence tier over reviews would match everything and rank nothing.

Course metadata is deliberately *not* copied into review documents.  The
previous engine spliced each course's text into every one of its reviews five
times over to weight it, which turned 10 MB of content into a 65 MB cache and
made course-name matches outrank the review text a user was actually looking
for.  Here that relationship is a join instead: reviews carry a ``meta`` token
for their course, so matching courses can pull in their reviews at query time,
scored as what it is rather than smuggled in as content.
"""

import html
import re
from typing import Callable, Dict, Iterator, List, NamedTuple, Sequence

from . import text as T

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


class Document(NamedTuple):
    doc_id: int
    norm_text: str
    streams: Dict[str, Sequence[str]]
    priors: Dict[str, float]


class Collection(NamedTuple):
    name: str
    fields: List[str]
    #: Fields whose tokens are derived from the document's normalized text.
    derived: Dict[str, Callable[[str], List[str]]]


def _skip_grams(norm: str) -> List[str]:
    return T.grams(norm, gap=2)


#: Streams every collection derives the same way.  ``gram`` must come first:
#: the writer measures document length in units of the first field, and BM25
#: scores over grams.
_GRAM = ("gram", lambda norm: T.grams(norm, gap=1))
_WORD = ("word", T.words)
_PINYIN = ("pinyin", T.pinyin_grams)

COURSES = Collection(
    name="courses",
    fields=["gram", "skip", "char", "word", "pinyin", "pyname", "pyinit", "meta"],
    derived=dict(
        [
            _GRAM,
            ("skip", _skip_grams),
            ("char", T.chars),
            _WORD,
            _PINYIN,
            ("pyname", T.pinyin_whole),
            ("pyinit", T.pinyin_initials),
        ]
    ),
)

REVIEWS = Collection(
    name="reviews",
    # ``char`` earns its ~25 MB by answering single-character queries from a
    # postings lookup instead of a linear scan of every review.  It is *only*
    # used for that: reviews get no subsequence tier, because over 300
    # characters of prose almost any two characters appear in order somewhere.
    fields=["gram", "char", "word", "pinyin", "meta"],
    derived=dict([_GRAM, ("char", T.chars), _WORD, _PINYIN]),
)

ALL = {c.name: c for c in (COURSES, REVIEWS)}


def build_streams(collection: Collection, norm: str, meta: Sequence[str]) -> Dict[str, List[str]]:
    streams = {name: fn(norm) for name, fn in collection.derived.items()}
    streams["meta"] = list(meta)
    return streams


def strip_html(content: str) -> str:
    """Reviews are stored as HTML.  A tag strip plus entity unescape is all the
    index needs, and is ~50x faster than routing 10 MB through html2text."""
    if not content:
        return ""
    return _WS.sub(" ", html.unescape(_TAG.sub(" ", content))).strip()


# --------------------------------------------------------------------------
# Document extraction
# --------------------------------------------------------------------------


def course_documents(db) -> Iterator[Document]:
    """One document per course: name, teacher names, course codes.

    The three zones are concatenated into one normalized string and their byte
    offsets recorded as priors, so the ranker can tell a name match from a
    teacher match from a code match by looking at *where* the match landed --
    without paying for three separate postings fields.
    """
    import sqlalchemy as sa

    codes: Dict[int, List[str]] = {}
    latest_term: Dict[int, str] = {}
    for cid, series, code, term in db.session.execute(
        sa.text(
            "SELECT course_id, courseries, code, term FROM course_terms "
            "WHERE course_id IS NOT NULL"
        )
    ):
        bucket = codes.setdefault(cid, [])
        for value in (series, code):
            if value and value not in bucket:
                bucket.append(value)
        if term and term > latest_term.get(cid, ""):
            latest_term[cid] = term

    rows = db.session.execute(
        sa.text(
            "SELECT c.id, c.name, "
            "       COALESCE(GROUP_CONCAT(DISTINCT t.name SEPARATOR ' '), ''), "
            "       COALESCE(cr.review_count, 0), COALESCE(cr._rate_average, 0), "
            "       COALESCE(cr.upvote_count, 0) "
            "FROM courses c "
            "LEFT JOIN course_teachers ct ON ct.course_id = c.id "
            "LEFT JOIN teachers t ON t.id = ct.teacher_id "
            "LEFT JOIN course_rates cr ON cr.id = c.id "
            "GROUP BY c.id"
        )
    )

    for cid, name, teachers, review_count, rate, upvotes in rows:
        norm_name = T.normalize(name or "")
        norm_teachers = T.normalize(teachers or "")
        norm_codes = T.normalize(" ".join(codes.get(cid, ())))
        parts = [p for p in (norm_name, norm_teachers, norm_codes) if p]
        norm = T.SEP.join(parts)
        teacher_at = len(norm_name.encode("utf-8")) + 1 if norm_name else 0
        code_at = teacher_at + (len(norm_teachers.encode("utf-8")) + 1 if norm_teachers else 0)
        term = latest_term.get(cid, "")
        yield Document(
            doc_id=cid,
            norm_text=norm,
            streams=build_streams(COURSES, norm, ["c:%d" % cid]),
            priors={
                "zone_teacher": float(teacher_at),
                "zone_code": float(code_at),
                "review_count": float(review_count or 0),
                "rate": float(rate or 0),
                "upvotes": float(upvotes or 0),
                "term": float(term) if term.isdigit() else 0.0,
            },
        )


def review_documents(db, chunk: int = 2000, since=None) -> Iterator[Document]:
    """One document per review: the review text, nothing else.

    Visibility flags travel with the document so retrieval can apply them
    before pagination without a database round trip; the delta overlay keeps
    them exact between rebuilds.
    """
    import sqlalchemy as sa

    last_id = 0
    while True:
        rows = db.session.execute(
            sa.text(
                "SELECT r.id, r.content, COALESCE(r.course_id, 0), COALESCE(r.author_id, 0), "
                "       r.update_time, COALESCE(r.upvote_count, 0), "
                "       COALESCE(r.is_blocked, 0), COALESCE(r.is_hidden, 0), "
                "       COALESCE(r.only_visible_to_student, 0), COALESCE(r.is_anonymous, 0), "
                "       u.username, COALESCE(u.is_profile_hidden, 0) "
                "FROM reviews r LEFT JOIN users u ON u.id = r.author_id "
                "WHERE r.id > :last " + ("AND r.update_time >= :since " if since else "")
                + "ORDER BY r.id LIMIT :lim"
            ),
            dict({"last": last_id, "lim": chunk}, **({"since": since} if since else {})),
        ).fetchall()
        if not rows:
            return
        for row in rows:
            (
                rid,
                content,
                course_id,
                author_id,
                update_time,
                upvotes,
                blocked,
                hidden,
                student_only,
                anonymous,
                username,
                profile_hidden,
            ) = row
            last_id = rid
            norm = T.normalize(strip_html(content))
            meta = ["c:%d" % course_id, "a:%d" % author_id]
            if username and not anonymous and not profile_hidden:
                meta.append("u:" + T.normalize(username))
            yield Document(
                doc_id=rid,
                norm_text=norm,
                streams=build_streams(REVIEWS, norm, meta),
                priors={
                    "course_id": float(course_id or 0),
                    "author_id": float(author_id or 0),
                    "updated_at": float(update_time.timestamp()) if update_time else 0.0,
                    "upvotes": float(upvotes or 0),
                    "blocked": float(bool(blocked)),
                    "hidden": float(bool(hidden)),
                    "student_only": float(bool(student_only)),
                },
            )


DOCUMENT_SOURCES = {
    "courses": course_documents,
    "reviews": review_documents,
}
