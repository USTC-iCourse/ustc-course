"""Search engine for courses and reviews.

See :mod:`app.search.text` for the normalization contract, :mod:`app.search.segment`
for the on-disk format, :mod:`app.search.retrieve` for the relaxation ladder and
:mod:`app.search.service` for the public entry points.
"""

from .results import SearchResults  # noqa: F401
from .retrieve import MatchQuality, warmup  # noqa: F401
from .service import (  # noqa: F401
    IndexUnavailable,
    index_status,
    ranked_review_ids,
    search_courses,
    search_reviews,
)

# Pay the tokenizer dictionary loads at import time, where a preloading
# gunicorn absorbs them once before forking, rather than on the first search.
warmup()
