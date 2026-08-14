"""Inspect what a single query returns, for eyeballing relevance.

    PYTHONPATH=. python3 tests/search_eval.py 数据结构
"""

import argparse
import re
import time

from app import app
from app.search import IndexUnavailable, index_status, search_courses, search_reviews
from app.models import Course, Review
from app.utils import abstract_by_keyword


class AnonymousUser:
    def __init__(self):
        self.is_authenticated = False
        self.identity = "Anonymous"
        self.id = None


def _describe(results):
    line = f"{results.total} results, tier={results.tier}, match={results.quality.name}"
    if results.note:
        line += f"\n  note: {results.note}"
    return line


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Eval a search query")
    parser.add_argument("query", type=str, help="search query")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--per-page", type=int, default=10)
    args = parser.parse_args()

    with app.app_context():
        try:
            for name, info in index_status().items():
                if isinstance(info, dict) and info.get("built"):
                    print(
                        f"{name}: {info['documents']} docs, "
                        f"{info['bytes'] / 1048576:.1f} MB, "
                        f"built {info['age_seconds'] / 60:.0f} min ago"
                    )
        except IndexUnavailable as exc:
            raise SystemExit(str(exc))

        print("\nCourse results:")
        t = time.perf_counter()
        res = search_courses(args.query, args.page, args.per_page)
        print(f"Time: {(time.perf_counter() - t) * 1000:.1f} ms. {_describe(res)}")
        i: Course
        for i in res.items:
            if i.review_count:
                print(f"  {i}, {i.rate.average_rate:.2f} 分, {i.review_count} 条评论")
            else:
                print(f"  {i}, 无评论")

        print("\nReview results:")
        t = time.perf_counter()
        res = search_reviews(args.query, args.page, args.per_page, AnonymousUser())
        print(f"Time: {(time.perf_counter() - t) * 1000:.1f} ms. {_describe(res)}")
        i: Review
        for idx, i in enumerate(res.items):
            text = abstract_by_keyword(i.content, args.query)
            user = i.author.username if not i.is_anonymous else "匿名用户"
            # ANSI escape code for red and bold
            text = re.sub(
                r'<span style="color:#B22222;font-weight:bold;">(.*?)</span>',
                "\033[1m\033[31m\\1\033[0m",
                text,
                flags=re.IGNORECASE,
            )
            print(f"  {idx} (from {user} in {i.course}, {i.update_time}): {text}")
