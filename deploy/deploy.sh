#!/bin/bash
#
# Deploy USTC iCourse into /srv/ustc-course, verify that it serves, and roll
# back to the previous revision if any step fails.
#
# Runs as the icourse user -- the owner of /srv/ustc-course -- either from the
# GitHub Actions deploy job or by hand:
#
#     sudo -u icourse /srv/ustc-course/deploy/deploy.sh
#
# The only privileged operation is restarting the systemd unit, granted
# narrowly in /etc/sudoers.d/ustc-course-deploy.  See deploy/README.md.
#
# Order of operations, and why:
#
#   fetch -> fast-forward -> dependencies -> compile+import -> migrate ->
#   restart -> health check
#
# The compile-and-import check runs against the *production* configuration
# before the service is touched, so a config-dependent import failure aborts
# with the old code still serving and nothing to undo.  Migrations run before
# the restart because they are additive: the old code tolerates the new schema
# for the few seconds between the two, whereas new code against an old schema
# would not.
#
# Everything lives in main(), called on the last line, so bash has the whole
# script in memory before it runs -- a rollback rewrites the working tree that
# this file may itself be running from.

set -Eeuo pipefail

APP_DIR=${APP_DIR:-/srv/ustc-course}
SERVICE=${SERVICE:-ustc-course.service}
BRANCH=${BRANCH:-master}
DEPLOY_REF=${DEPLOY_REF:-origin/${BRANCH}}
HEALTH_URL=${HEALTH_URL:-http://127.0.0.1:3000/}
HEALTH_TIMEOUT=${HEALTH_TIMEOUT:-120}
PYTHON=${PYTHON:-/usr/bin/python3}
FLASK=${FLASK:-/home/icourse/.local/bin/flask}
LOCK_FILE=${LOCK_FILE:-/home/icourse/.cache/ustc-course-deploy.lock}
# The account that owns APP_DIR. Overridable so that the script can be
# exercised against a staging checkout without impersonating icourse.
DEPLOY_USER=${DEPLOY_USER:-icourse}

STAGE="startup"
PREV_SHA=""
PREV_DB_REV=""
REQS_CHANGED=0
UPGRADE_ATTEMPTED=0
SERVICE_RESTARTED=0

log()  { printf '%s ==> %s\n'  "$(date '+%F %T')" "$*"; }
warn() { printf '%s !!  %s\n'  "$(date '+%F %T')" "$*" >&2; }
err()  { printf '%s ERR %s\n'  "$(date '+%F %T')" "$*" >&2; }

# Give up before anything has been changed: no rollback is needed or possible.
fail() { err "$*"; exit 1; }

# Give up after the working tree has been touched: undo it.
abort() {
    trap - ERR
    err "DEPLOY FAILED during '${STAGE}': $*"
    rollback
    exit 1
}

git_() { git -C "$APP_DIR" "$@"; }

# The Alembic revision the database is actually at, empty if it has none.
db_revision() {
    ( cd "$APP_DIR" && PYTHONPATH=. "$FLASK" db current 2>/dev/null \
        | grep -oE '^[0-9a-f]{8,}' | head -n1 ) || true
}

# The Alembic revision the checked-out code expects.
code_revision() {
    ( cd "$APP_DIR" && PYTHONPATH=. "$FLASK" db heads 2>/dev/null \
        | grep -oE '^[0-9a-f]{8,}' | head -n1 ) || true
}

install_requirements() {
    ( cd "$APP_DIR" && "$PYTHON" -m pip install --user --quiet \
        --no-warn-script-location -r requirements.txt )
}

# Byte-compile, then import the application with the real production config.
# This is what CI cannot do: CI imports against config/default.py.example,
# while this catches anything that depends on the live configuration.
preflight_code() {
    ( cd "$APP_DIR" && "$PYTHON" -m compileall -q app config run.py ) || return 1
    ( cd "$APP_DIR" && PYTHONPATH=. "$PYTHON" - <<'PY'
import sys
import app
routes = len(list(app.app.url_map.iter_rules()))
print("import ok, %d routes registered" % routes)
if routes < 50:
    sys.exit("only %d routes registered -- blueprints failed to load" % routes)
PY
    ) || return 1
}

restart_service() {
    sudo -n /bin/systemctl restart "$SERVICE"
}

# Poll until the site answers 200, or give up.  Checks the unit as well as the
# socket so that a unit that failed to start is reported as such rather than as
# a connection error.
health_check() {
    local deadline=$((SECONDS + HEALTH_TIMEOUT)) code=""
    log "waiting for ${HEALTH_URL} to answer 200 (up to ${HEALTH_TIMEOUT}s)"
    while (( SECONDS < deadline )); do
        if systemctl is-active --quiet "$SERVICE"; then
            code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$HEALTH_URL" || true)
            if [[ "$code" == "200" ]]; then
                log "health check passed (HTTP 200 from ${HEALTH_URL})"
                return 0
            fi
        fi
        sleep 2
    done
    err "health check failed after ${HEALTH_TIMEOUT}s (last HTTP status: ${code:-none})"
    err "unit state: $(systemctl is-active "$SERVICE" 2>&1 || true)"
    systemctl status "$SERVICE" --no-pager --lines=20 >&2 2>&1 || true
    return 1
}

rollback() {
    # Never abandon a rollback half-done: from here on a failing step is
    # reported and the remaining steps still run.
    trap - ERR
    set +e
    if [[ -z "$PREV_SHA" ]]; then
        err "no rollback point was recorded; the working tree was never modified"
        return
    fi

    local now
    now=$(git_ rev-parse HEAD)
    if [[ "$now" == "$PREV_SHA" ]]; then
        log "code is already at ${PREV_SHA:0:8}; nothing to revert"
    else
        warn "reverting code ${now:0:8} -> ${PREV_SHA:0:8}"
        if git_ reset --hard "$PREV_SHA"; then
            git_ submodule update --init --recursive >/dev/null 2>&1 || true
        else
            err "could not revert the working tree -- NEEDS MANUAL ATTENTION"
        fi
        if (( REQS_CHANGED )); then
            warn "reinstalling the previous dependency set"
            install_requirements || err "could not reinstall previous dependencies"
        fi
    fi

    # The schema is deliberately not downgraded.  A downgrade against live data
    # is lossy here -- the search-cache migration, for instance, recreates its
    # tables empty -- and is a worse outcome than a schema that is one revision
    # ahead of the code, which the additive migrations in this project tolerate.
    if (( UPGRADE_ATTEMPTED )); then
        local now_rev
        now_rev=$(db_revision)
        if [[ "$now_rev" != "$PREV_DB_REV" ]]; then
            err "-----------------------------------------------------------------"
            err "THE DATABASE WAS MIGRATED AND HAS NOT BEEN ROLLED BACK."
            err "  schema:  ${PREV_DB_REV:-none} -> ${now_rev:-unknown}"
            err "  code:    reverted to ${PREV_SHA:0:8}"
            err "The schema is now ahead of the running code.  This is safe for"
            err "additive migrations but must be checked by a human.  To undo it:"
            err "    cd ${APP_DIR} && PYTHONPATH=. ${FLASK} db downgrade ${PREV_DB_REV}"
            err "-----------------------------------------------------------------"
        fi
    fi

    if (( SERVICE_RESTARTED )); then
        warn "restarting ${SERVICE} on the previous revision"
        if restart_service && health_check; then
            log "ROLLBACK OK -- ${PREV_SHA:0:8} is serving and healthy"
        else
            err "ROLLBACK FAILED -- ${SERVICE} is not healthy. Investigate now:"
            err "    sudo journalctl -u ${SERVICE} -n 100 --no-pager"
            err "    tail -n 100 /var/log/ustc-course/ustc-course-error.log"
        fi
    else
        log "${SERVICE} was never restarted; it is still serving ${PREV_SHA:0:8}"
    fi
}

main() {
    mkdir -p "$(dirname "$LOCK_FILE")"
    exec 9>"$LOCK_FILE"
    flock -n 9 || fail "another deploy is already running (lock: ${LOCK_FILE})"

    trap 'abort "unexpected error on line ${LINENO}"' ERR

    STAGE="preconditions"
    [[ "$(id -un)" == "$DEPLOY_USER" ]] \
        || fail "must run as ${DEPLOY_USER}, not $(id -un)"
    [[ -d "${APP_DIR}/.git" ]]     || fail "${APP_DIR} is not a git checkout"
    [[ "$(git_ symbolic-ref --short HEAD)" == "$BRANCH" ]] \
        || fail "${APP_DIR} is not on ${BRANCH} (on $(git_ symbolic-ref --short HEAD))"

    # A dirty tree means a production change was made by hand.  Refuse rather
    # than discard it: a fast-forward would either fail here or, after a reset,
    # silently throw the change away.
    local dirty
    dirty=$(git_ status --porcelain --untracked-files=no)
    if [[ -n "$dirty" ]]; then
        err "${APP_DIR} has uncommitted changes to tracked files:"
        printf '%s\n' "$dirty" >&2
        fail "commit them upstream or revert them, then deploy again"
    fi

    # Check the one privilege this script needs up front, rather than
    # discovering it is missing after the code has already been moved.
    sudo -n -l /bin/systemctl restart "$SERVICE" >/dev/null 2>&1 \
        || fail "this user may not restart ${SERVICE}; see deploy/README.md for the sudoers rule"

    STAGE="fetch"
    log "fetching origin/${BRANCH}"
    git_ fetch --quiet origin "$BRANCH"

    PREV_SHA=$(git_ rev-parse HEAD)
    local target
    target=$(git_ rev-parse --verify --quiet "${DEPLOY_REF}^{commit}") \
        || fail "cannot resolve ${DEPLOY_REF}"

    if [[ "$target" == "$PREV_SHA" ]]; then
        log "already at ${PREV_SHA:0:8} -- nothing to deploy"
        exit 0
    fi
    if git_ merge-base --is-ancestor "$target" "$PREV_SHA"; then
        log "${target:0:8} is already contained in ${PREV_SHA:0:8} -- a newer commit"
        log "was deployed while this run was queued; nothing to do"
        exit 0
    fi
    git_ merge-base --is-ancestor "$PREV_SHA" "$target" \
        || fail "${target:0:8} is not a fast-forward from ${PREV_SHA:0:8}; refusing"

    log "deploying ${PREV_SHA:0:8} -> ${target:0:8}"
    git_ --no-pager log --oneline "${PREV_SHA}..${target}" | sed 's/^/      /'
    PREV_DB_REV=$(db_revision)
    log "database is at Alembic revision ${PREV_DB_REV:-none}"

    STAGE="checkout"
    git_ merge --ff-only "$target" >/dev/null
    if ! git_ diff --quiet "$PREV_SHA" HEAD -- .gitmodules app/static/MathJax; then
        log "submodule reference changed; updating submodules"
        git_ submodule update --init --recursive
    fi

    STAGE="dependencies"
    if git_ diff --quiet "$PREV_SHA" HEAD -- requirements.txt; then
        log "requirements.txt unchanged; skipping pip"
    else
        log "requirements.txt changed; installing dependencies"
        REQS_CHANGED=1
        install_requirements || abort "pip install failed"
    fi

    STAGE="pre-flight checks"
    log "byte-compiling and importing the application against the live config"
    preflight_code || abort "the new code does not compile or import"

    STAGE="database migration"
    local want
    want=$(code_revision)
    if [[ -n "$want" && "$want" == "$PREV_DB_REV" ]]; then
        log "database already at ${want}; no migration needed"
    else
        log "migrating database ${PREV_DB_REV:-none} -> ${want:-head}"
        UPGRADE_ATTEMPTED=1
        ( cd "$APP_DIR" && PYTHONPATH=. "$FLASK" db upgrade ) || abort "flask db upgrade failed"
        log "database now at $(db_revision)"
    fi

    STAGE="restart"
    log "restarting ${SERVICE}"
    SERVICE_RESTARTED=1
    restart_service || abort "systemctl restart failed"

    STAGE="health check"
    health_check || abort "the new revision is not serving"

    STAGE="post-deploy"
    # The catalogue index has no freshness overlay, so a change to the search
    # code needs a rebuild.  request_rebuild() only drops a marker file; the
    # existing ustc-course-search-index.timer picks it up within two minutes.
    if ! git_ diff --quiet "$PREV_SHA" HEAD -- app/search/; then
        log "app/search/ changed; requesting an index rebuild"
        ( cd "$APP_DIR" && PYTHONPATH=. "$PYTHON" - <<'PY'
from app import app
from app.search.builder import request_rebuild
for collection in ("courses", "reviews"):
    request_rebuild(app, collection)
print("rebuild requested for courses and reviews")
PY
        ) || warn "could not request an index rebuild; the daily timer will catch up"
    fi

    trap - ERR
    log "DEPLOY OK -- ${APP_DIR} is serving ${target:0:8} ($(git_ log -1 --format=%s))"
}

main "$@"
