#!/usr/bin/env bash
# Resolves the docker and docker-compose binaries across macOS and Linux.
# Sourced by the other scripts in this directory — not meant to be run directly.

set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed or not on PATH." >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_BIN="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_BIN="docker-compose"
else
  echo "Neither 'docker compose' (plugin) nor 'docker-compose' (standalone) is available." >&2
  exit 1
fi

export COMPOSE_BIN
