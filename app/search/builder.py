"""Builds index segments from the database.

Runs out of process, on a timer.  There is no incremental-update machinery to
get wrong: the index is simply replaced, and everything written since the build
started is served by the freshness overlay in :mod:`app.search.delta` until the
next rebuild catches up.  On production that costs about twenty seconds for the
catalogue and five minutes for the reviews.

The watermark stored in the segment is the instant *before* the build began, so
a row edited while the build is running is covered by the overlay rather than
falling into the gap between the two.
"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence

from .collections import ALL, DOCUMENT_SOURCES
from .segment import SegmentWriter


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: How stale a segment may become before the timer rebuilds it even though
#: nothing asked for one.  Per collection, because the two are safety nets
#: against different things:
#:
#: ``courses``  Rebuilds are event-driven -- every route and script that edits
#:              indexed catalogue data calls :func:`request_rebuild`.  The age
#:              path only catches what bypasses that: a direct database edit,
#:              or a marker that could not be written.
#: ``reviews``  Has no event path and does not need one; the overlay serves
#:              every row written since the build, exactly.  Rebuilding only
#:              bounds how much the overlay carries, and this site accumulates
#:              its fifty thousand reviews over *years* -- a day's writes are a
#:              few dozen, against MAX_DELTA_ROWS of five thousand.
#:
#: An hour was the original guess for both.  Measured over twelve hours of
#: production it cost about forty-five minutes of CPU -- some 7% of a core,
#: continuously -- to rebuild an index that nothing had invalidated, because
#: the overlay was already serving the handful of new reviews correctly.
MAX_AGE = {
    "courses": 86400.0,
    "reviews": 86400.0,
}

#: Used for a collection with no entry above.
DEFAULT_MAX_AGE = 86400.0


def default_segment_dir() -> str:
    """Where segments live, resolved without importing the application.

    The timer wakes every couple of minutes and almost always has nothing to
    do; importing Flask, jieba, pypinyin and zhconv to discover that costs four
    seconds of CPU each time, against about fifty milliseconds for this.
    """
    try:
        import config.default as cfg  # noqa: F401  (plain module, no side effects)

        configured = getattr(cfg, "SEARCH_INDEX_DIR", None)
    except Exception:
        configured = None
    return configured or os.path.join(_REPO_ROOT, "data", "search-index")


def segment_dir(app) -> str:
    configured = app.config.get("SEARCH_INDEX_DIR")
    if configured:
        return configured
    return os.path.join(os.path.dirname(os.path.abspath(app.root_path)), "data", "search-index")


def segment_path(app, collection: str) -> str:
    return os.path.join(segment_dir(app), "%s.seg" % collection)


def _request_path(app, collection: str) -> str:
    return os.path.join(segment_dir(app), "%s.rebuild" % collection)


def request_rebuild(app, collection: str) -> None:
    """Ask the next builder run to rebuild this collection now.

    For reviews, freshness is the overlay's job and this is never needed.  The
    catalogue is different: it has no overlay, it changes only when an
    administrator edits it, and rebuilding the whole of it costs less than
    twenty seconds -- so for courses, a full rebuild *is* the incremental
    update, and this marker is how a request for one survives the web process.

    Deliberately a filesystem marker rather than a background thread: an edit
    made while a rebuild is running must not be swallowed by it, and thirty-two
    workers must not be able to start thirty-two rebuilds.
    """
    try:
        path = _request_path(app, collection)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a"):
            pass
    except OSError:
        # A missed marker costs freshness until the next scheduled rebuild; it
        # must never cost the edit that triggered it.
        logging.getLogger(__name__).warning(
            "could not request a %s index rebuild", collection, exc_info=True
        )


def take_requests(app, collections: Optional[Sequence[str]] = None) -> List[str]:
    """Clear the pending-request markers for the given collections.

    Cleared *before* building, not after: a request arriving mid-build then
    recreates the marker and is served by the next run, where clearing
    afterwards would discard it.

    ``collections`` must name exactly what the caller is about to build.
    Clearing every marker regardless would drop a request that arrived for a
    *different* collection between deciding what to build and starting -- a
    window several seconds wide, since the application import sits in it.
    """
    taken = []
    for collection in sorted(ALL if collections is None else collections):
        try:
            os.unlink(_request_path(app, collection))
        except OSError:
            continue
        taken.append(collection)
    return taken


def _work_pending(index_dir: str, max_age: Optional[float] = None) -> List[str]:
    """Which collections need building, decided from the filesystem alone.

    ``max_age`` overrides :data:`MAX_AGE` for every collection; leave it unset
    to use each collection's own limit.
    """
    needed = []
    for collection in sorted(ALL):
        if os.path.exists(os.path.join(index_dir, "%s.rebuild" % collection)):
            needed.append(collection)
            continue
        limit = max_age if max_age is not None else MAX_AGE.get(collection, DEFAULT_MAX_AGE)
        try:
            age = time.time() - os.stat(os.path.join(index_dir, "%s.seg" % collection)).st_mtime
        except OSError:
            age = float("inf")
        if age >= limit:
            needed.append(collection)
    return needed


def segment_age(app, collection: str) -> float:
    """Seconds since the segment was written; ``inf`` if there isn't one."""
    try:
        return max(time.time() - os.stat(segment_path(app, collection)).st_mtime, 0.0)
    except OSError:
        return float("inf")


def build(app, db, collection: str, progress=None) -> Dict[str, float]:
    """Build one collection and atomically replace its segment."""
    spec = ALL[collection]
    source = DOCUMENT_SOURCES[collection]

    started = time.time()
    # The watermark is a UTC timestamp because review.update_time is written
    # with datetime.utcnow(); comparing against a local-clock instant would
    # silently skip or re-scan hours of rows.
    watermark = datetime.utcnow() - timedelta(seconds=1)

    writer = SegmentWriter(
        collection,
        spec.fields,
        # Stored as a naive-UTC ISO string, the same shape as the column it is
        # compared against.  An epoch float would invite a local-time reading.
        meta={"built_at_utc": watermark.isoformat(), "built_wall": started},
    )
    count = 0
    for doc in source(db):
        writer.add_doc(doc.doc_id, doc.norm_text, doc.streams, doc.priors)
        count += 1
        if progress and count % 2000 == 0:
            progress(count)

    path = segment_path(app, collection)
    writer.write(path)
    elapsed = time.time() - started
    return {
        "collection": collection,
        "documents": count,
        "seconds": elapsed,
        "bytes": os.path.getsize(path),
        "path": path,
    }


def build_all(app, db, progress=None) -> Dict[str, Dict[str, float]]:
    return {name: build(app, db, name, progress=progress) for name in ALL}


def main(argv: Optional[list] = None) -> int:
    import argparse
    import sys

    sys.path.insert(0, _REPO_ROOT)

    parser = argparse.ArgumentParser(description="Build search index segments")
    parser.add_argument(
        "collections",
        nargs="*",
        default=None,
        help="collections to build (default: all of %s)" % ", ".join(sorted(ALL)),
    )
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--if-needed",
        action="store_true",
        help="build only what has been requested by the application or has "
        "aged past --max-age; exits without work otherwise",
    )
    parser.add_argument(
        "--max-age",
        type=float,
        default=None,
        help="with --if-needed, rebuild a segment older than this many seconds, "
        "overriding the per-collection defaults (%s)"
        % ", ".join("%s=%gs" % kv for kv in sorted(MAX_AGE.items())),
    )
    args = parser.parse_args(argv)

    names = args.collections or sorted(ALL)
    unknown = [n for n in names if n not in ALL]
    if unknown:
        parser.error("unknown collection(s): %s" % ", ".join(unknown))

    if args.if_needed:
        # Decided from the filesystem, before the expensive imports: the timer
        # fires every couple of minutes and usually has nothing to do.
        pending = set(_work_pending(default_segment_dir(), args.max_age))
        names = [name for name in names if name in pending]
        if not names:
            return 0

    from app import app, db  # noqa: E402  (imported late, and after sys.path)

    def progress(n):
        if not args.quiet:
            print("  %d documents..." % n, end="\r", flush=True)

    with app.app_context():
        if args.if_needed:
            # Clear the markers now, before building: a request arriving while
            # a build runs recreates its marker and is served by the next run.
            # Only for what we are actually about to build.
            take_requests(app, names)
        for name in names:
            stats = build(app, db, name, progress=progress)
            if not args.quiet:
                print(
                    "%-8s %6d docs  %6.1f s  %6.1f MB  ->  %s"
                    % (
                        stats["collection"],
                        stats["documents"],
                        stats["seconds"],
                        stats["bytes"] / 1048576.0,
                        stats["path"],
                    )
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
