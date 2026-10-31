#!/usr/bin/env bash
# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
DRACULA_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$DRACULA_ROOT"
command -v docker >/dev/null || { printf 'Install Docker Engine with the Compose plugin first.\n' >&2; exit 1; }
docker compose version >/dev/null || { printf 'The Docker Compose plugin is required.\n' >&2; exit 1; }
docker compose build
if ! docker compose run --rm -T --no-deps dracula python3 -m dracula.web_setup --check; then
  read -r -s -p 'Create a dashboard password (at least 8 characters): ' dracula_password
  echo
  printf '%s\n' "$dracula_password" | docker compose run --rm -T --no-deps dracula python3 -m dracula.web_setup
  unset dracula_password
fi
if [ "${BUNDLE_JAVA:-false}" != true ]; then
  docker compose run --rm -T --no-deps dracula python3 -c 'from dracula.launcher import setup_java; setup_java()'
fi
docker compose up -d
printf 'DRACula is ready at http://localhost:%s\n' "${DRACULA_PORT:-8788}"
