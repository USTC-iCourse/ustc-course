# Deployment Instructions

Covers deploying the search engine in `app/search/`, which replaced the two
MySQL FULLTEXT backends and the one-time search-token scheme.

## What changed operationally

* Search reads a **memory-mapped index on disk**, not the database. It must be
  built before the site can serve searches, and rebuilt on a timer.
* The `course_search_cache`, `review_search_cache` and `search_tokens` tables
  are dropped by an Alembic migration.
* `/search/` and `/search-reviews/` are plain GET endpoints again — no token,
  no rate limit. `/api/search/token` no longer exists. A search costs a few
  milliseconds against a memory-mapped index, so it is no more expensive to
  serve than any other page.
* New Python dependencies: `numpy`, `pypinyin`, `zhconv`.

## Step 1: Install dependencies

```bash
sudo -u icourse /usr/bin/python3 -m pip install --user -r /srv/ustc-course/requirements.txt
```

## Step 2: Deploy code

```bash
sudo cp -r /home/boj/test-ustc-course/app /srv/ustc-course/
sudo cp /home/boj/test-ustc-course/gunicorn_config.py /srv/ustc-course/
sudo cp -r /home/boj/test-ustc-course/migrations /srv/ustc-course/
sudo chown -R icourse:icourse /srv/ustc-course/
```

## Step 3: Build the index **before** restarting

The site returns HTTP 503 for searches until a segment exists, so build first.
A full build is roughly 20 s for courses and 3 min for reviews.

```bash
sudo -u icourse mkdir -p /srv/ustc-course/data/search-index
cd /srv/ustc-course && sudo -u icourse env PYTHONPATH=. /usr/bin/python3 -m app.search.builder
```

Expect output like:

```
courses   17509 docs    20.2 s     9.1 MB  ->  /srv/ustc-course/data/search-index/courses.seg
reviews   33704 docs   198.2 s   118.4 MB  ->  /srv/ustc-course/data/search-index/reviews.seg
```

To keep the index off the application volume, set `SEARCH_INDEX_DIR` in
`config/default.py` and make sure the `icourse` user can write it.

## Step 4: Install the rebuild timer

```bash
sudo cp /home/boj/test-ustc-course/ustc-course-search-index.service /etc/systemd/system/
sudo cp /home/boj/test-ustc-course/ustc-course-search-index.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ustc-course-search-index.timer
systemctl list-timers ustc-course-search-index.timer
```

Hourly is deliberate, not conservative: reviews written or edited since the
last build are served exactly by the freshness overlay
(`app/search/delta.py`), so the rebuild only exists to keep that overlay small.

## Step 5: Restart the application

```bash
sudo systemctl restart ustc-course.service
```

Optional: setting `preload_app = True` in `gunicorn_config.py` makes the 32
workers share one load of the jieba/pypinyin/zhconv dictionaries (~1 s each)
instead of paying it per worker at startup. It does mean `systemctl reload`
(SIGHUP) no longer picks up new code, since the app is imported in the master —
deploys must use `systemctl restart`, which Step 5 already does. The index
itself is shared either way: a memory-mapped file is one physical copy across
all workers regardless of how they were started.

## Step 6: Apply the migration

Only after the new code is serving correctly — the old tables are then
provably unused, and rolling back before this step needs no database work.

```bash
cd /srv/ustc-course && sudo -u icourse env PYTHONPATH=. /home/icourse/.local/bin/flask db upgrade
```

This drops `review_search_cache` (~65 MB), `course_search_cache` and
`search_tokens`. All three are derived or ephemeral; the downgrade recreates
the schema empty.

## Verifying

```bash
cd /srv/ustc-course && sudo -u icourse env PYTHONPATH=. /usr/bin/python3 - <<'PY'
from app import app
from app.search import index_status
with app.app_context():
    print(index_status())
PY
```

Then, on the site:

* search a two-character word that appears in reviews — `班风`, `程学`, `末考`
  all returned nothing under the old engine and must now return results;
* search a course abbreviation — `数分` should reach 数学分析;
* search while signed in on a **Teacher** account — this raised
  `ArgumentError` for all 667 non-Student accounts before;
* reload a search URL, page through results, and open a search with
  JavaScript disabled — all were 403s under the token scheme;
* post a review and immediately search for a phrase in it — the freshness
  overlay should surface it within a few seconds, well before the next rebuild.

Run the test suites against production data if you want the full check:

```bash
cd /srv/ustc-course
for t in text segment engine freshness; do
  sudo -u icourse env PYTHONPATH=. /usr/bin/python3 tests/test_search_$t.py
done
sudo -u icourse env PYTHONPATH=. /usr/bin/python3 tests/search_benchmark.py
```

## Operational notes

**After importing courses.** The catalogue import scripts no longer maintain a
cache table; rebuild the course segment when they finish:

```bash
cd /srv/ustc-course && sudo -u icourse env PYTHONPATH=. /usr/bin/python3 -m app.search.builder courses
```

**Disk.** Roughly 130 MB for both segments, plus the same again transiently
while a rebuild writes its temporary file. The builder peaks around 400 MB RSS.

**If the timer stops.** Searches stay *correct* — the overlay covers the gap —
but get slower as it grows. Past `MAX_DELTA_ROWS` the overlay stops expanding
and `index_status()["delta_overflowed"]` becomes true, which is the signal to
look at the timer.

**Rollback.** Before Step 6, `git checkout` the previous revision and restart;
the old tables are still present and populated. After Step 6, run
`flask db downgrade` first, then repopulate the caches — which requires the old
engine's code to do.

## Logs

```bash
sudo journalctl -u ustc-course.service -f
sudo journalctl -u ustc-course-search-index.service -n 50
tail -f /var/log/ustc-course-error.log
```

Log rotation, in `/etc/logrotate.d/ustc-course`:

```
/var/log/ustc-course-*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 icourse icourse
    sharedscripts
    postrotate
        systemctl reload ustc-course.service > /dev/null 2>&1 || true
    endscript
}
```
