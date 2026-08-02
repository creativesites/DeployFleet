#!/usr/bin/env bash
# Read-only inventory of the shared demo server, required by DEPLOYMENT.md
# before provisioning DeployFleet's own stack there. Runs nothing that
# creates, modifies, or removes anything on the remote host — every
# command below is a listing/inspection command.
#
# Usage:
#   DEPLOYFLEET_DEMO_SSH_HOST=199.192.23.46 \
#   DEPLOYFLEET_DEMO_SSH_USER=root \
#   scripts/preflight-inventory.sh
#
# Prefer key-based auth: set DEPLOYFLEET_DEMO_SSH_KEY to an identity file
# path. If unset, ssh falls back to your agent/default identity or an
# interactive password prompt — this script never accepts a password as
# an argument or environment variable, so a plaintext credential is never
# passed to or stored by it.
#
# Output is written to scripts/.preflight-reports/<timestamp>.txt
# (gitignored) — never commit this file, since it reveals what else is
# running on a shared server.

set -euo pipefail
cd "$(dirname "$0")/.."

: "${DEPLOYFLEET_DEMO_SSH_HOST:?Set DEPLOYFLEET_DEMO_SSH_HOST (e.g. 199.192.23.46)}"
DEPLOYFLEET_DEMO_SSH_USER="${DEPLOYFLEET_DEMO_SSH_USER:-root}"

SSH_ARGS=(-o BatchMode=no -o ConnectTimeout=10)
if [ -n "${DEPLOYFLEET_DEMO_SSH_KEY:-}" ]; then
  SSH_ARGS+=(-i "$DEPLOYFLEET_DEMO_SSH_KEY")
fi

REPORT_DIR="scripts/.preflight-reports"
mkdir -p "$REPORT_DIR"
REPORT_FILE="$REPORT_DIR/$(date -u +%Y%m%dT%H%M%SZ).txt"

echo "Running read-only pre-flight inventory against ${DEPLOYFLEET_DEMO_SSH_USER}@${DEPLOYFLEET_DEMO_SSH_HOST}..."
echo "Report will be written to $REPORT_FILE (gitignored — do not commit it)."

# Every remote command here is inspection-only: no create/rm/stop/start/exec-into.
remote_script='
echo "=== docker ps -a ==="
docker ps -a
echo
echo "=== docker compose ls (running compose projects) ==="
docker compose ls 2>/dev/null || echo "(docker compose plugin not available or no projects)"
echo
echo "=== Listening ports (ss -tlnp) ==="
ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || echo "(neither ss nor netstat available)"
echo
echo "=== Docker volumes ==="
docker volume ls
echo
echo "=== Docker networks ==="
docker network ls
echo
echo "=== PostgreSQL databases (per running postgres container, if any) ==="
for cid in $(docker ps --filter "ancestor=postgres" --format "{{.ID}}" 2>/dev/null; docker ps --format "{{.ID}} {{.Image}}" | awk "/postgres/{print \$1}"); do
  echo "--- container $cid ---"
  docker exec "$cid" psql -U postgres -l 2>/dev/null || echo "(could not list databases as postgres superuser — check the actual DB user for this container manually)"
done
echo
echo "=== Reverse proxy config (nginx) ==="
if command -v nginx >/dev/null 2>&1 || [ -d /etc/nginx ]; then
  echo "--- /etc/nginx/sites-enabled ---"
  ls -la /etc/nginx/sites-enabled/ 2>/dev/null || true
  echo "--- server_name directives ---"
  grep -r "server_name" /etc/nginx/ 2>/dev/null || true
else
  echo "(no nginx install detected at /etc/nginx — check for Traefik/Caddy containers among the docker ps output above instead)"
fi
echo
echo "=== Disk space ==="
df -h
'

ssh "${SSH_ARGS[@]}" "${DEPLOYFLEET_DEMO_SSH_USER}@${DEPLOYFLEET_DEMO_SSH_HOST}" "$remote_script" | tee "$REPORT_FILE"

echo
echo "Inventory complete. Review $REPORT_FILE, then record a summary in DEPLOYMENT.md before running scripts/deploy-demo.sh."
