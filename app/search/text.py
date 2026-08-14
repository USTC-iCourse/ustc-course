"""Normalization and token-stream generation.

Everything that enters the index and everything that enters a query passes
through :func:`normalize` here.  That symmetry is the contract the whole engine
rests on: a document is findable by a query if and only if their *normalized*
forms share the structure a retrieval tier looks for.  The previous engine
segmented documents with ``jieba.cut_for_search`` and queries with ``jieba.cut``
and therefore had no such contract -- 17% of substrings taken from real review
text were unfindable at all.

Normalization maps text to runs of "word characters" (CJK ideographs, or ASCII
letters/digits) joined by a single space.  Punctuation becomes a run boundary,
and so does a script change, which is what makes ``微积分B`` a substring of the
normalized form of ``微积分(B1)``.

From a normalized string we derive several parallel token streams.  Each is
indexed as its own field and each backs a different retrieval tier:

``gram``    adjacent character bigrams -- boundary-independent recall.
``skip``    bigrams of characters two apart -- absorbs a one-character
            difference, which is how ``编译原理与技术`` reaches
            ``编译原理和技术`` without a hand-maintained list of connectives.
``char``    single characters -- candidate generator for subsequence matching
            (``数分`` -> ``数学分析``); only meaningful for short documents.
``word``    jieba segmentation -- a ranking signal, never a recall mechanism.
``pinyin``  toneless pinyin syllable bigrams -- homophone and IME-slip recall,
            which is what relates ``紫砂``/``自鲨``/``自沙`` to ``自杀``.
``abbr``    pinyin initials of a whole short name (``数学分析`` -> ``sxfx``).
"""

import os
import re
import unicodedata
from typing import List

import jieba
import zhconv
from pypinyin import Style, lazy_pinyin

# jieba caches its compiled prefix dictionary, and defaults to /tmp for it.
# That is the wrong place here twice over: the service runs with PrivateTmp,
# so the cache would be discarded on every restart, and a /tmp path owned by
# another user makes the write fail outright.  Either way jieba silently falls
# back to rebuilding the dictionary in every process -- about a second, times
# every worker, on every restart.  The module this replaced set the same thing.
jieba.dt.tmp_dir = os.path.expanduser("~/.cache/jieba")
try:
    os.makedirs(jieba.dt.tmp_dir, exist_ok=True)
except OSError:  # read-only home: fall back to jieba's default
    jieba.dt.tmp_dir = None

#: Runs joined by this character in normalized text.  A single space keeps
#: normalized text usable as a plain substring-search haystack.
SEP = " "

#: A "word run": CJK ideographs, or ASCII alphanumerics.  Anything else is a
#: separator.  Listing the two scripts separately is what forces a boundary at
#: a script change.
_RUN = re.compile(r"[㐀-䶿一-鿿豈-﫿]+|[0-9a-z]+")

_CJK_RANGES = (
    ("㐀", "䶿"),
    ("一", "鿿"),
    ("豈", "﫿"),
)

#: Stripped from the *tail* of a query only.  Users type 张老师 but the teacher
#: record says 张三, so an honorific at the end is noise.  Never stripped from
#: documents, and never from the middle of a query, where the same characters
#: are usually meaningful (课 in 课程设计).
#:
#: Only the first group means the user named a *person*.  The rest are just
#: filler; treating 数怎么样 as a person query would aim it at teacher names
#: and find nothing.
_PERSON_HONORIFICS = ("老师", "教授", "同学")
_QUERY_TAIL_FILLER = ("的课", "这门课", "怎么样")
_QUERY_TAIL_NOISE = _PERSON_HONORIFICS + _QUERY_TAIL_FILLER


def is_cjk(ch: str) -> bool:
    return any(lo <= ch <= hi for lo, hi in _CJK_RANGES)


def normalize(text: str) -> str:
    """Fold text to its canonical searchable form.

    NFKC unifies full-width and compatibility forms (``英语交流Ⅰ`` ->
    ``英语交流I``), which is what the ``utf8mb4_unicode_ci`` collation on the
    old cache column was standing in for.  zhconv folds traditional Chinese to
    simplified so pasted traditional text is findable.
    """
    if not text:
        return ""
    folded = unicodedata.normalize("NFKC", text)
    folded = zhconv.convert(folded, "zh-hans")
    return SEP.join(_RUN.findall(folded.lower()))


def normalize_query(text: str) -> str:
    return normalize_query_parts(text)[0]


def normalize_query_parts(text: str):
    """Normalize, then strip trailing honorifics.

    Returns the remaining query and whether an honorific was removed.  That
    flag is worth keeping: ``张老师`` reduces to ``张``, which on its own is a
    terrible query -- a thousand courses contain the character -- but combined
    with the knowledge that the user was naming a *person* it becomes a precise
    one, answered against teacher names rather than against everything.

    Applied to queries only; see :data:`_QUERY_TAIL_NOISE`.
    """
    norm = normalize(text)
    honorific = False
    changed = True
    while changed:
        changed = False
        for noise in _QUERY_TAIL_NOISE:
            stripped = normalize(noise)
            # Strip only when something is left: a bare 老师 is a legitimate
            # query for the word itself.
            if norm.endswith(stripped) and len(norm) > len(stripped):
                norm = norm[: -len(stripped)].strip()
                changed = True
                if noise in _PERSON_HONORIFICS:
                    honorific = True
    return norm, honorific


def runs(norm_text: str) -> List[str]:
    return [r for r in norm_text.split(SEP) if r]


def grams(norm_text: str, gap: int = 1) -> List[str]:
    """Character bigrams at distance ``gap`` within each CJK run.

    Latin/digit runs are emitted whole -- splitting ``python`` into bigrams
    would only add noise, since whitespace already delimits them.

    A CJK run shorter than ``gap + 1`` cannot produce a gapped bigram; it falls
    back to the tightest bigram it can form so that short runs still appear in
    every gram field rather than silently vanishing from one of them.
    """
    out: List[str] = []
    for run in runs(norm_text):
        if not is_cjk(run[0]):
            out.append(run)
            continue
        step = gap
        while step >= 1 and len(run) <= step:
            step -= 1
        if step < 1:
            out.append(run)
        else:
            out.extend(run[i] + run[i + step] for i in range(len(run) - step))
    return out


def chars(norm_text: str) -> List[str]:
    """Every single character of every CJK run, plus whole latin runs."""
    out: List[str] = []
    for run in runs(norm_text):
        if is_cjk(run[0]):
            out.extend(run)
        else:
            out.append(run)
    return out


def words(norm_text: str) -> List[str]:
    """jieba segmentation, used purely as a ranking signal."""
    out: List[str] = []
    for run in runs(norm_text):
        if is_cjk(run[0]):
            out.extend(w for w in jieba.cut_for_search(run) if w.strip())
        else:
            out.append(run)
    return out


def _syllables(run: str) -> List[str]:
    return lazy_pinyin(run, style=Style.NORMAL, errors="ignore")


def pinyin_grams(norm_text: str) -> List[str]:
    """Bigrams of adjacent toneless pinyin syllables.

    ``自杀``/``紫砂``/``自鲨``/``自沙`` all reduce to ``zi|sha``, so one index
    field subsumes the hand-maintained homophone list in ``app/utils.py``.
    Syllables are joined with a separator because concatenation is ambiguous
    (``xi``+``an`` vs ``xian``).
    """
    out: List[str] = []
    for run in runs(norm_text):
        if not is_cjk(run[0]):
            continue
        syl = _syllables(run)
        if not syl:
            continue
        if len(syl) == 1:
            out.append(syl[0])
        else:
            out.extend(syl[i] + "|" + syl[i + 1] for i in range(len(syl) - 1))
    return out


def pinyin_whole(norm_text: str) -> List[str]:
    """Pinyin of a whole run, concatenated -- ``zhangsan`` finds 张三.

    Only worth indexing for short documents, where one run is one concept.
    Kept apart from :func:`pinyin_initials` because the two are evidence of
    very different strength and must not end up in the same conjunction.
    """
    out: List[str] = []
    for run in runs(norm_text):
        if not is_cjk(run[0]):
            continue
        syl = _syllables(run)
        if len(syl) >= 2:
            out.append("".join(syl))
    return out


def pinyin_initials(norm_text: str) -> List[str]:
    """First letters of a run's syllables -- ``sxfx`` finds 数学分析.

    Weak evidence by construction: two or three letters collide constantly, so
    callers should require a reasonable length before trusting it.
    """
    out: List[str] = []
    for run in runs(norm_text):
        if not is_cjk(run[0]):
            continue
        syl = _syllables(run)
        if len(syl) >= 2:
            out.append("".join(s[0] for s in syl))
    return out
