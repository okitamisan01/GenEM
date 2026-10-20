#!/usr/bin/env bash
# Host-side helper. No SSH, robot launch, actuator command or host network mutation.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
operation="${1:-}"
if [[ $# -gt 0 ]]; then shift; fi
if [[ "$operation" == build ]]; then
  # Build never reads deployment env or connects to an HSR.
  docker compose -f compose.yaml -f compose.hsr104.yaml build "$@"
  exit
fi
if [[ "$operation" == prepare ]]; then
  project_root="$(cd .. && pwd)"
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    --entrypoint python3 --mount "type=bind,source=${project_root},target=/workspace" \
    genem-hsr:humble /workspace/scripts/prepare_hsr_connection.py "$@"
  exit
fi
deployment_env="${GENEM_HSR_ENV:-hsr104.local.env}"
if [[ ! -f "$deployment_env" ]]; then
  echo 'Prepare local deployment files first; see docs/hsr104_setup.md.' >&2
  exit 2
fi
compose=(docker compose --env-file "$deployment_env" -f compose.yaml -f compose.hsr104.yaml)
case "$operation" in
  up) "${compose[@]}" up -d "$@" ;;
  down) "${compose[@]}" down "$@" ;;
  exec)
    if [[ $# -eq 0 ]]; then set -- bash; fi
    if [[ -t 0 && -t 1 ]]; then
      "${compose[@]}" exec genem /genem_entrypoint.sh "$@"
    else
      "${compose[@]}" exec -T genem /genem_entrypoint.sh "$@"
    fi
    ;;
  *) echo 'Usage: bash docker/hsr104.sh {build|prepare|up|exec|down} [args...]' >&2; exit 2 ;;
esac
