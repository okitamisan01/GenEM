#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ $# -eq 0 ]]; then set -- bash; fi
if [[ -t 0 && -t 1 ]]; then
  docker compose exec genem /genem_entrypoint.sh "$@"
else
  docker compose exec -T genem /genem_entrypoint.sh "$@"
fi
