#!/usr/bin/env bash
# Starts the local DeployFleet dev stack (Postgres + Odoo).
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/docker-env.sh

if [ ! -f .env ]; then
  echo "No .env found — copying .env.example. Edit it before continuing if you need non-default values."
  cp .env.example .env
fi

mkdir -p .local/postgres .local/odoo
if [ ! -f .local/odoo.conf ]; then
  cat > .local/odoo.conf <<'EOF'
[options]
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
data_dir = /var/lib/odoo
EOF
fi

$COMPOSE_BIN -f deploy/docker-compose.yml --env-file .env up -d
echo "DeployFleet dev stack starting. Odoo will be reachable at http://localhost:${ODOO_HTTP_PORT:-8169} once ready."
