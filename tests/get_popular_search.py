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

    data = defaultdict(int)
    print("Please note that SearchLog is usually very large (300M+) and this is a bit slow.", file=sys.stderr)
    with app.app_context():
        for log in tqdm(SearchLog.query):
            data[log.keyword] += 1

    # output sorted data
    for keyword, count in sorted(data.items(), key=lambda x: x[1], reverse=True):
        if count > args.count:
            print(f"{keyword}: {count}")
