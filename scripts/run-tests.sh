#!/usr/bin/env bash
# Installs the given DeployFleet modules with Odoo's test runner enabled.
# Usage: scripts/run-tests.sh [module1,module2,...]
# Defaults to the Phase 0 foundation modules.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/docker-env.sh

MODULES="${1:-deployfleet_core,deployfleet_security,deployfleet_event_bus,deployfleet_ai_core}"

$COMPOSE_BIN -f deploy/docker-compose.yml --env-file .env run --rm odoo \
  odoo -i "$MODULES" --test-enable --stop-after-init --without-demo=all \
  -d deployfleet_test --db_host=db \
  --db_user="${POSTGRES_USER:-deployfleet}" --db_password="${POSTGRES_PASSWORD:-changeme_local_dev_only}"
