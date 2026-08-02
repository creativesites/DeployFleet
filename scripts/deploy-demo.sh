#!/usr/bin/env bash
# Deploys DeployFleet's own isolated Docker stack to the shared demo
# server. Read DEPLOYMENT.md before running this — it does NOT touch the
# existing production/staging Odoo instances on that server (different
# compose project, dedicated database/volumes/ports), but it does make
# real changes to a shared machine, so this script refuses to run
# without explicit confirmation that the pre-flight inventory has
# actually been reviewed by a human.
#
# Usage:
#   scripts/deploy-demo.sh --confirm-preflight-reviewed [--init-db]
#
# --confirm-preflight-reviewed   Required. You are asserting a human read
#                                 a report from scripts/preflight-inventory.sh
#                                 and confirmed the chosen ports/DB name/
#                                 volume names don't collide with anything
#                                 already on the server.
# --init-db                      Optional. Also creates the DeployFleet
#                                 database and installs the Phase 0/1
#                                 modules. Omit on repeat deploys — this
#                                 is a one-time bootstrap step.
#
# Reads connection/config values from .env.production (see
# .env.production.example) — this file is never committed.

set -euo pipefail
cd "$(dirname "$0")/.."

CONFIRM_PREFLIGHT=0
INIT_DB=0
for arg in "$@"; do
  case "$arg" in
    --confirm-preflight-reviewed) CONFIRM_PREFLIGHT=1 ;;
    --init-db) INIT_DB=1 ;;
    *) echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

if [ "$CONFIRM_PREFLIGHT" -ne 1 ]; then
  cat >&2 <<'EOF'
Refusing to deploy without --confirm-preflight-reviewed.

Run scripts/preflight-inventory.sh first, read the report it produces
under scripts/.preflight-reports/, and confirm by hand that:
  - the chosen POSTGRES_DB/POSTGRES_USER in .env.production don't collide
    with an existing database on the server
  - DEPLOYFLEET_HTTP_PORT/DEPLOYFLEET_LONGPOLLING_PORT aren't already
    listening
  - the reverse proxy addition you plan to make won't shadow an existing
    server_name/host rule

Then re-run with --confirm-preflight-reviewed.
EOF
  exit 1
fi

if [ ! -f .env.production ]; then
  echo ".env.production not found. Copy .env.production.example, fill in real values, and do not commit it." >&2
  exit 1
fi
set -a
source .env.production
set +a

: "${DEPLOYFLEET_DEMO_SSH_HOST:?Set in .env.production}"
: "${DEPLOYFLEET_REMOTE_DIR:?Set in .env.production}"
: "${DEPLOYFLEET_ODOO_MASTER_PASSWORD:?Set in .env.production}"
DEPLOYFLEET_DEMO_SSH_USER="${DEPLOYFLEET_DEMO_SSH_USER:-root}"

SSH_ARGS=(-o ConnectTimeout=10)
if [ -n "${DEPLOYFLEET_DEMO_SSH_KEY:-}" ]; then
  SSH_ARGS+=(-i "$DEPLOYFLEET_DEMO_SSH_KEY")
fi
REMOTE="${DEPLOYFLEET_DEMO_SSH_USER}@${DEPLOYFLEET_DEMO_SSH_HOST}"

echo "Rendering deploy/.generated/odoo.prod.conf from template (not committed)..."
mkdir -p deploy/.generated
DEPLOYFLEET_ODOO_MASTER_PASSWORD="$DEPLOYFLEET_ODOO_MASTER_PASSWORD" \
  envsubst '${DEPLOYFLEET_ODOO_MASTER_PASSWORD}' \
  < deploy/odoo.prod.conf.template > deploy/.generated/odoo.prod.conf

echo "Ensuring remote directory exists: ${REMOTE}:${DEPLOYFLEET_REMOTE_DIR}"
ssh "${SSH_ARGS[@]}" "$REMOTE" "mkdir -p '${DEPLOYFLEET_REMOTE_DIR}'"

echo "Syncing custom_addons/ and deploy/ to the server (code + compose files only, no local .env files)..."
rsync -az --delete \
  -e "ssh ${SSH_ARGS[*]}" \
  --exclude '.generated' \
  custom_addons deploy \
  "${REMOTE}:${DEPLOYFLEET_REMOTE_DIR}/"

echo "Copying rendered odoo.prod.conf and .env.production separately (both gitignored, never part of the rsync above)..."
ssh "${SSH_ARGS[@]}" "$REMOTE" "mkdir -p '${DEPLOYFLEET_REMOTE_DIR}/deploy/.generated'"
scp "${SSH_ARGS[@]}" deploy/.generated/odoo.prod.conf "${REMOTE}:${DEPLOYFLEET_REMOTE_DIR}/deploy/.generated/odoo.prod.conf"
scp "${SSH_ARGS[@]}" .env.production "${REMOTE}:${DEPLOYFLEET_REMOTE_DIR}/.env.production"

echo "Bringing up the DeployFleet stack (dedicated project name 'deployfleet', isolated from other compose projects on this host)..."
ssh "${SSH_ARGS[@]}" "$REMOTE" "cd '${DEPLOYFLEET_REMOTE_DIR}' && docker compose -f deploy/docker-compose.prod.yml --env-file .env.production up -d"

if [ "$INIT_DB" -eq 1 ]; then
  echo "Initializing DeployFleet database and installing Phase 0/1 modules (one-time bootstrap)..."
  MODULES="deployfleet_core,deployfleet_security,deployfleet_event_bus,deployfleet_ai_core,deployfleet_driver,deployfleet_vehicle,deployfleet_customer,deployfleet_route,deployfleet_dispatch,deployfleet_trip,deployfleet_delivery"
  ssh "${SSH_ARGS[@]}" "$REMOTE" "cd '${DEPLOYFLEET_REMOTE_DIR}' && docker compose -f deploy/docker-compose.prod.yml --env-file .env.production exec -T odoo \
    odoo -i ${MODULES} --stop-after-init -d '${POSTGRES_DB}' \
    --db_host=db --db_user='${POSTGRES_USER}' --db_password='${POSTGRES_PASSWORD}'"
fi

echo "Done. DeployFleet should be reachable at http://${DEPLOYFLEET_DEMO_SSH_HOST}:${DEPLOYFLEET_HTTP_PORT}/ once Odoo finishes starting."
echo "Remember: this is HTTP on a raw port for now — wiring the reverse-proxy entry (nginx/Traefik/whatever the server already runs) is a separate, deliberate step per DEPLOYMENT.md, not automated here."
