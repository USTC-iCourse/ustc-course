from app import app
from app.views.search import filter, search, search_reviews
from app.utils import abstract_by_keyword
from app.models import Course, Review
import re
import argparse
import time


class AnonymousUser:
    def __init__(self):
        self.is_authenticated = False
        self.identity = "Anonymous"
        self.id = None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Eval a search query with a backend")
    parser.add_argument("query", type=str, help="search query")
    parser.add_argument("--backend", type=str, default=None, help="search backend (use config as default)")

    args = parser.parse_args()
    if args.backend:
        app.config["SEARCH_BACKEND"] = args.backend
    print(f"Using backend: {app.config['SEARCH_BACKEND']}")

    with app.app_context():
        keywords = filter(args.query).split()
        print("Keywords:", keywords)
        print("Search results:")
        t = time.perf_counter()
        res = search(keywords, 1, 10)
        print(f"Time: {time.perf_counter() - t:.2f} s. Total {res.total} results.")
        i: Course
        for i in res.items:
            if i.review_count:
                print(f"{i}, {i.rate.average_rate:.2f} 分, {i.review_count} 条评论")
            else:
                print(f"{i}, 无评论")
        print("Review search results:")
        t = time.perf_counter()
        res = search_reviews(keywords, 1, 10, AnonymousUser())
        print(f"Time: {time.perf_counter() - t:.2f} s. Total {res.total} results.")
        i: Review
        for idx, i in enumerate(res.items):
            text = abstract_by_keyword(i.content, args.query)
            user = i.author.username if not i.is_anonymous else "匿名用户"
            # ANSI escape code for red and bold
            text = re.sub(r'<span style="color:#B22222;font-weight:bold;">(.*?)</span>',
              '\033[1m\033[31m\\1\033[0m', text, flags=re.IGNORECASE)
            print(f"{idx} (from {user} in {i.course}, {i.update_time}): {text}")
