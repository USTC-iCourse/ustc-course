from app import app
from app.models import SearchLog
from collections import defaultdict
from tqdm import tqdm
import argparse
import sys


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get popular search")
    parser.add_argument("--count", type=int, default=1, help="count threshold")
    args = parser.parse_args()

    data = defaultdict(lambda : {"search_course": 0, "search_reviews": 0})
    print("Please note that SearchLog is usually very large (300M+) and this is a bit slow.", file=sys.stderr)
    with app.app_context():
        for log in tqdm(SearchLog.query):
            data[log.keyword.replace("\n", " ").replace("\r", "").strip()][log.module] += 1

    # output sorted data
    for keyword, count_dict in sorted(data.items(), key=lambda x: x[1]["search_course"] + x[1]["search_reviews"], reverse=True):
        total = count_dict["search_course"] + count_dict["search_reviews"]
        if total > args.count:
            print(f"{keyword}: {total} ({count_dict['search_course']} / {count_dict['search_reviews']})")
