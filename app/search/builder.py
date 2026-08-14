"""Builds index segments from the database.

Runs out of process, on a timer.  A full rebuild of both collections takes
well under a minute, which is why there is no incremental-update machinery to
get wrong: the index is simply replaced, and everything written since the build
started is served by the freshness overlay in :mod:`app.search.delta` until the
next rebuild catches up.

The watermark stored in the segment is the instant *before* the build began, so
a row edited while the build is running is covered by the overlay rather than
falling into the gap between the two.
"""

import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

from .collections import ALL, DOCUMENT_SOURCES
from .segment import SegmentWriter


def segment_dir(app) -> str:
    configured = app.config.get("SEARCH_INDEX_DIR")
    if configured:
        return configured
    return os.path.join(os.path.dirname(os.path.abspath(app.root_path)), "data", "search-index")


def segment_path(app, collection: str) -> str:
    return os.path.join(segment_dir(app), "%s.seg" % collection)


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

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from app import app, db  # noqa: E402  (import after sys.path fix)

    parser = argparse.ArgumentParser(description="Build search index segments")
    parser.add_argument(
        "collections",
        nargs="*",
        default=None,
        help="collections to build (default: all of %s)" % ", ".join(sorted(ALL)),
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    names = args.collections or sorted(ALL)
    unknown = [n for n in names if n not in ALL]
    if unknown:
        parser.error("unknown collection(s): %s" % ", ".join(unknown))

    def progress(n):
        if not args.quiet:
            print("  %d documents..." % n, end="\r", flush=True)

    with app.app_context():
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
