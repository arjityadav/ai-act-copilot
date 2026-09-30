#!/usr/bin/env bash
# Pull-based continuous deployment, run on the server by a systemd timer (deploy/ai-act-deploy.timer).
#
# Every run: fetch main; if there is a new commit AND its CI workflow succeeded, fast-forward to it,
# rebuild, wait until the new version is healthy and live, otherwise roll back to the previous commit.
# The server pulls, so no inbound SSH from GitHub is needed and no deploy secrets live in GitHub.
#
# Manual run:  ./deploy/deploy.sh          Logs:  journalctl -u ai-act-deploy -f
set -euo pipefail

REPO="arjityadav/ai-act-copilot"
BRANCH="main"
cd "$(dirname "$0")/.."
DC=(docker compose -f docker-compose.prod.yml --env-file .env.prod)

# Only one deploy at a time (a slow build must not overlap the next timer tick).
exec 9>/tmp/ai-act-deploy.lock
flock -n 9 || { echo "another deploy is running"; exit 0; }

log() { echo "$(date -u +%FT%TZ) $*"; }

git fetch -q origin "$BRANCH"
current=$(git rev-parse HEAD)
target=$(git rev-parse "origin/$BRANCH")
[ "$current" = "$target" ] && exit 0

# A commit that already failed and was rolled back is not retried (otherwise every timer tick would
# redeploy and roll back again). A newer commit on main replaces it; delete the file to force a retry.
FAILED=.deploy-failed
if [ -f "$FAILED" ] && [ "$(cat "$FAILED")" = "$target" ]; then exit 0; fi

# Deploy only commits whose "CI" workflow finished successfully (public repo: no token needed).
ci=$(curl -fsS "https://api.github.com/repos/$REPO/actions/runs?head_sha=$target&event=push" | python3 -c '
import json, sys
runs = [r for r in json.load(sys.stdin)["workflow_runs"] if r["name"] == "CI"]
print(runs[0]["conclusion"] or runs[0]["status"] if runs else "not-found")')
if [ "$ci" != "success" ]; then
  log "commit ${target:0:7}: CI is '$ci', not deploying (will retry)"
  exit 0
fi

set_version() {  # record the deployed commit in .env.prod so every `docker compose up` keeps it
  if grep -q '^APP_VERSION=' .env.prod; then sed -i "s/^APP_VERSION=.*/APP_VERSION=$1/" .env.prod
  else echo "APP_VERSION=$1" >> .env.prod; fi
}

start() {  # build and (re)start the stack at the checked-out commit
  set_version "$1"
  "${DC[@]}" up -d --build --remove-orphans
  # Single-file bind mounts go stale when git replaces the file: recreate Caddy to load the new Caddyfile.
  "${DC[@]}" up -d --force-recreate caddy
}

healthy() {  # the API and UI containers report healthy, and the public site serves the expected version
  local want=$1 domain
  domain=$(grep '^DOMAIN=' .env.prod | cut -d= -f2 | cut -d, -f1 | tr -d ' "')
  for _ in $(seq 1 40); do
    api=$(docker inspect -f '{{.State.Health.Status}}' "$("${DC[@]}" ps -q api)" 2>/dev/null || echo none)
    ui=$(docker inspect -f '{{.State.Health.Status}}' "$("${DC[@]}" ps -q ui)" 2>/dev/null || echo none)
    live=$(curl -fsS -m 5 "https://$domain/version" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])' 2>/dev/null || true)
    if [ "$api" = healthy ] && [ "$ui" = healthy ] && [ "$live" = "$want" ]; then return 0; fi
    sleep 6
  done
  log "not healthy: api=$api ui=$ui live=${live:-none}"
  return 1
}

log "deploying ${current:0:7} -> ${target:0:7}"
git merge -q --ff-only "origin/$BRANCH"
if start "$target" && healthy "$target"; then
  log "deployed ${target:0:7}"
  docker image prune -f >/dev/null   # keep the disk from filling up with old build layers
  exit 0
fi

log "ROLLBACK to ${current:0:7}"
echo "$target" > "$FAILED"
git reset -q --hard "$current"
start "$current"
healthy "$current" && log "rolled back to ${current:0:7}" || log "rollback unhealthy too: check 'docker compose ps'"
exit 1
