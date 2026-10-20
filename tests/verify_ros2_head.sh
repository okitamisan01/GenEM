#!/usr/bin/env bash
# Isolated ROS domain AND no network: cannot reach a real robot.
set -euo pipefail
docker run --rm --network none -e ROS_DOMAIN_ID=91 genem-hsr:jazzy bash -c '
set -e
ros2 launch genem_hsr head_test_rig.launch.py > /tmp/head-rig.log 2>&1 &
rig_pid=$!
trap '\''kill -INT "$rig_pid" 2>/dev/null || true'\'' EXIT
if ! python3 /opt/genem/tests/ros2_head_integration.py; then
  cat /tmp/head-rig.log
  exit 1
fi
'
