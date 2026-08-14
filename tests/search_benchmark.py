"""Latency and recall benchmark for the search engine.

Reports the two numbers that matter and are easy to regress silently: how long
a search takes end to end, and what fraction of substrings drawn from real
review text are findable at all.

    PYTHONPATH=. python3 tests/search_benchmark.py
"""

import random
import re
import time

import sqlalchemy as sa

from app import app, db
from app.search import ranked_review_ids, search_courses, search_reviews

QUERIES = [
    "数分",
    "线代",
    "数据结构",
    "概率论与数理统计",
    "微积分B",
    "自杀",
    "紫砂",
    "程学",
    "班风",
    "张老师",
    "数",
]
CJK = re.compile(r"[一-鿿]{2,}")
TAGS = re.compile(r"<[^>]+>")


class Anonymous:
    is_authenticated = False
    identity = None
    id = None


def latency(anon):
    print(f"{'query':16} {'ms':>7}  {'courses':>7} {'reviews':>7}  tier")
    for query in QUERIES:
        timings = []
        for _ in range(5):
            start = time.perf_counter()
            courses = search_courses(query, 1, 10)
            reviews = search_reviews(query, 1, 10, anon)
            timings.append((time.perf_counter() - start) * 1000)
        timings.sort()
        print(
            f"{query:16} {timings[2]:7.1f}  {courses.total:7} {reviews.total:7}  {reviews.tier}"
        )


def recall(anon, sample=600, probes=150, seed=11):
    """Draw substrings out of real reviews and check each finds its source."""
    rows = db.session.execute(
        sa.text(
            "SELECT id, content FROM reviews WHERE is_blocked = 0 AND is_hidden = 0 "
            "AND only_visible_to_student = 0 ORDER BY id DESC LIMIT :n"
        ),
        {"n": sample},
    ).fetchall()

    rng = random.Random(seed)
    drawn = []
    for review_id, content in rows:
        plain = TAGS.sub("", content or "")
        runs = [m for m in CJK.findall(plain) if len(m) >= 2]
        if not runs:
            continue
        run = rng.choice(runs)
        width = min(len(run), rng.choice([2, 2, 3]))
        start = rng.randrange(0, len(run) - width + 1)
        drawn.append((review_id, run[start : start + width]))
    rng.shuffle(drawn)
    drawn = drawn[:probes]

    missing = on_first_page = 0
    for review_id, probe in drawn:
        ids = ranked_review_ids(probe, anon)[0].tolist()
        if review_id not in set(ids):
            missing += 1
        elif review_id in ids[:10]:
            on_first_page += 1

    print(f"\nprobes={len(drawn)}")
    print(f"  found on page 1                : {on_first_page}")
    print(f"  unfindable (recall failure)    : {missing}")


if __name__ == "__main__":
    with app.app_context():
        anon = Anonymous()
        search_courses("warmup", 1, 5)
        search_reviews("warmup", 1, 5, anon)
        latency(anon)
        recall(anon)
