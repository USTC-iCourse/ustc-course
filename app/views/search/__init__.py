"""Compatibility shim over :mod:`app.search`.

The two SQL backends that used to live here -- ``sql-like`` and ``sql-cache``,
selected by a config switch, so that development and production ran different
matching code -- are gone.  This module remains only so that existing scripts
(``tests/search_eval.py``, ``tests/eval_popular_search.py``) keep working.
New code should import from :mod:`app.search` directly.
"""

from app.search import search_courses, search_reviews  # noqa: F401
from app.search.text import normalize_query

from .pagination import MyPagination  # noqa: F401


def filter(query):
    """Historically stripped punctuation before the caller ``.split()`` it.

    Normalization now happens inside the engine, against the same function the
    index was built with, so this only has to be harmless: it returns the
    normalized query, whose whitespace-separated runs are exactly the units the
    old callers expected to get from ``.split()``.
    """
    return normalize_query(query)


def search(query, page, per_page):
    return search_courses(query, page, per_page)
