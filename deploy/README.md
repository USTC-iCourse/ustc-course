# Continuous deployment

Every push to `master` runs the checks in `.github/workflows/ci.yml`.  If they
pass, the same workflow deploys that exact commit to `icourse.club` and
verifies that the site is serving.  If any step fails, the deploy reverts to the
revision that was running before and restarts onto it.

    push to master ──> CI (GitHub-hosted)  ──pass──> deploy (self-hosted, on the server)
                             │                            │
                           fail                         fail
                             ▼                            ▼
                        nothing deployed            rolled back, site restored

`needs: ci` in the deploy job is the gate: a red check cannot reach production.

## What CI checks

Everything runs on a GitHub-hosted runner against Python 3.9, matching
`/usr/bin/python3` on the server:

* **Syntax** — `py_compile` over every tracked `.py` file, so a `SyntaxError`
  anywhere is caught, including in the maintenance scripts under `tests/`.
* **Dependencies** — `pip install -r requirements.txt` followed by `pip check`,
  which catches an unresolvable or mutually incompatible pin.
* **Imports** — `app/__init__.py` ends in `from app.views import *`, so
  importing the package pulls in every view, model and form.  This is what
  catches a missing dependency or a bad import.  It asserts that the blueprints
  registered their routes; nothing connects to MySQL at import time, so CI
  needs no database.
* **Migrations** — that the Alembic history has exactly one head, since two
  heads would make `flask db upgrade` fail halfway through a deploy.
* **Tests** — `tests/test_search_text.py` and `tests/test_search_segment.py`,
  the two suites that need no database.

## What the deploy does

`deploy/deploy.sh`, run as `icourse` on the server:

1. Refuses to start if the working tree in `/srv/ustc-course` has uncommitted
   changes to tracked files — a hand-edit on the server is never discarded
   silently.
2. Fast-forwards `/srv/ustc-course` to the commit CI passed on.  Not to
   `origin/master`: if master moved on while CI was running, the newer commit is
   deployed by its own run, after its own checks.
3. Installs dependencies, but only if `requirements.txt` changed.
4. Byte-compiles and imports the application **against the live
   `config/default.py`**.  This is the check CI cannot perform, and it happens
   before the service is touched: a failure here reverts the tree with the old
   code still serving and no restart at all.
5. Runs `flask db upgrade`, but only when the code expects a revision the
   database is not at.
6. Restarts `ustc-course.service` and polls the site until it answers 200
   (`HEALTH_TIMEOUT`, 120 s by default).
7. Requests a search-index rebuild if `app/search/` changed; the existing
   `ustc-course-search-index.timer` picks the marker up within two minutes.

Any failure after step 2 reverts the checkout to the previous commit,
reinstalls the previous dependencies if they had changed, restarts, and
re-checks health.

### Migrations are not rolled back

Code is reverted; the schema is not.  A downgrade against live data is lossy
here — the search-cache migration, for one, recreates its tables empty — and a
schema one revision ahead of the code is the safer of the two failures for the
additive migrations this project uses.  When a rollback crosses a migration the
script says so loudly and prints the exact `flask db downgrade` command, and a
human decides.

### Running it by hand

    sudo -u icourse /srv/ustc-course/deploy/deploy.sh

Every path is an environment variable with a production default: `APP_DIR`,
`SERVICE`, `BRANCH`, `DEPLOY_REF`, `HEALTH_URL`, `HEALTH_TIMEOUT`, `PYTHON`,
`FLASK`, `LOCK_FILE`, `DEPLOY_USER`.  An `flock` on `LOCK_FILE` keeps two
deploys from overlapping.

## Server setup

Both steps are done once, by hand, as a user with root.

### 1. The one privilege the deploy needs

The deploy runs as `icourse`, which already owns `/srv/ustc-course`, so the
only thing it cannot do on its own is restart the unit.  Grant exactly that and
nothing else, in `/etc/sudoers.d/ustc-course-deploy` (mode `0440`):

    icourse ALL=(root) NOPASSWD: /bin/systemctl restart ustc-course.service

Validate before trusting it — a malformed sudoers file locks everyone out:

    sudo visudo -c -f /etc/sudoers.d/ustc-course-deploy
    sudo -u icourse sudo -n -l /bin/systemctl restart ustc-course.service

`deploy.sh` checks for this privilege up front and refuses to start without it,
rather than discovering it is missing after moving the code.

### 2. The GitHub Actions runner

The runner is installed under the `icourse` account, so the deploy has exactly
the access it needs — write access to `/srv/ustc-course` and nothing more — and
the server needs no inbound SSH.

    sudo -u icourse -i
    mkdir ~/actions-runner && cd ~/actions-runner
    V=$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | sed -n 's/.*"tag_name": "v\([^"]*\)".*/\1/p')
    curl -o runner.tar.gz -L https://github.com/actions/runner/releases/download/v${V}/actions-runner-linux-x64-${V}.tar.gz
    tar xzf runner.tar.gz && rm runner.tar.gz
    ./config.sh --url https://github.com/USTC-iCourse/ustc-course \
                --token <REGISTRATION_TOKEN> \
                --name icourse-prod --labels icourse-prod --unattended

Get `<REGISTRATION_TOKEN>` (valid one hour) from Settings → Actions → Runners →
New self-hosted runner, or:

    gh api -X POST repos/USTC-iCourse/ustc-course/actions/runners/registration-token --jq .token

Then install it as a service so it survives reboots:

    cd /home/icourse/actions-runner && sudo ./svc.sh install icourse && sudo ./svc.sh start
    sudo ./svc.sh status

The `icourse-prod` label is what `runs-on: [self-hosted, icourse-prod]` selects.

### Security note

This repository is **public** and the runner executes on the production host,
so two things must stay true:

* The deploy job is guarded by
  `if: (push || workflow_dispatch) && github.ref == 'refs/heads/master'`.
  Pull requests — including from forks — run CI on GitHub's runners only, and
  can never reach this machine.
* In Settings → Actions → General → *Fork pull request workflows*, set
  **Require approval for all external contributors**.  Without it, a returning
  contributor could open a pull request whose own edited workflow asks for
  `runs-on: self-hosted` and have it run here.

The runner account is `icourse`, not root: it can restart the application unit
and write `/srv/ustc-course`, which is what deploying requires and no more.

## Failure playbook

The deploy prints why it failed and what it did about it.  If the rollback
itself failed — the only case that needs immediate attention:

    sudo journalctl -u ustc-course.service -n 100 --no-pager
    tail -n 100 /var/log/ustc-course/ustc-course-error.log

    # put the last good revision back by hand
    sudo -u icourse git -C /srv/ustc-course reset --hard <sha>
    sudo systemctl restart ustc-course.service

`git -C /srv/ustc-course reflog` lists the revisions that were deployed, newest
first, which is where `<sha>` comes from.

## Operating the search index

Search reads a memory-mapped index on disk, not the database, so the index must
exist before the site can serve searches — `/search/` returns 503 until a
segment is there. The files live in `data/search-index/`, relocatable with
`SEARCH_INDEX_DIR` in `config/default.py`.

`ustc-course-search-index.timer` fires every two minutes, but the unit is gated
by an `ExecCondition` costing milliseconds, so it does nothing unless there is
work:

* **Reviews** rebuild on age, once a day. Everything written or edited since the
  last build is served exactly by the freshness overlay in `app/search/delta.py`,
  so the rebuild only keeps that overlay small — and this site takes years to
  accumulate the reviews that would fill it.
* **The catalogue has no overlay**, so course edits that change indexed text —
  adding or removing a teacher, or a catalogue import — call
  `app.search.builder.request_rebuild()`, which drops a marker file the timer
  picks up within a couple of minutes. A course rebuild takes about twenty
  seconds.

The marker is written by the web process, so the index directory must be
writable by `icourse`. If it is not, the request is logged and dropped and the
edit waits for the daily rebuild — it never fails the edit. `deploy.sh` requests
a rebuild of both collections whenever a deploy changed `app/search/`.

**Forcing a rebuild.** The catalogue import asks for one itself, so ordinarily
nothing needs doing. To run one immediately:

    cd /srv/ustc-course && sudo -u icourse env PYTHONPATH=. /usr/bin/python3 -m app.search.builder courses

Omit `courses` to rebuild everything. Expect roughly 20 s for courses and 3 min
for reviews.

**Cadence** is `MAX_AGE` in `app/search/builder.py`, per collection. The
`ExecCondition` in the service unit duplicates the threshold as a cheap
pre-filter; keep its `-mmin` just *below* the smallest `MAX_AGE`, since too low
only wastes a process start while too high would skip a due rebuild.

**Disk.** Roughly 130 MB for both segments, plus the same again transiently
while a rebuild writes its temporary file. The builder peaks around 400 MB RSS.

**If the timer stops.** Searches stay *correct* — the overlay covers the gap —
but get slower as it grows. Past `MAX_DELTA_ROWS` the overlay stops expanding
and `index_status()["delta_overflowed"]` becomes true, which is the signal to
look at the timer:

    cd /srv/ustc-course && sudo -u icourse env PYTHONPATH=. /usr/bin/python3 - <<'PY'
    from app import app
    from app.search import index_status
    with app.app_context():
        print(index_status())
    PY

## Logs

    sudo journalctl -u ustc-course.service -f
    sudo journalctl -u ustc-course-search-index.service -n 50
    sudo journalctl -u actions.runner.USTC-iCourse-ustc-course.icourse-prod -n 50
    tail -f /var/log/ustc-course/ustc-course-error.log

Rotation is configured in `/etc/logrotate.d/ustc-course`. `copytruncate` is
used rather than `create` plus a reload, because gunicorn holds each log open
twice — once through a `logging.FileHandler` and once through
`capture_output = True` — and both open in append mode, so truncating in place
is safe and no writer needs signalling:

    /var/log/ustc-course/*.log {
        su icourse icourse
        daily
        rotate 14
        missingok
        notifempty
        compress
        copytruncate
        dateext
        maxsize 1G
    }
