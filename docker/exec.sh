#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ $# -eq 0 ]]; then set -- bash; fi
docker compose exec genem /genem_entrypoint.sh "$@"
