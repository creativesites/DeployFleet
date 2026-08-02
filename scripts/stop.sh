#!/usr/bin/env bash
# Stops the local DeployFleet dev stack.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/docker-env.sh

$COMPOSE_BIN -f deploy/docker-compose.yml down
