#!/usr/bin/env bash
# Isolated ROS domain AND no network: cannot reach a real robot.
set -euo pipefail
docker run --rm --network none -e RMW_IMPLEMENTATION="${GENEM_RMW:-rmw_fastrtps_cpp}" -e ROS_DOMAIN_ID=91 "${GENEM_IMAGE:-genem-hsr:jazzy}" bash -c '
set -e
if [[ "${RMW_IMPLEMENTATION:-}" == rmw_cyclonedds_cpp ]]; then
  python3 /opt/genem/scripts/prepare_hsr_connection.py --interface lo --robot-ip 127.0.0.1 --domain 91
  export CYCLONEDDS_URI=file:///opt/genem/config/cyclonedds.local.xml
fi
ros2 launch genem_hsr head_test_rig.launch.py > /tmp/head-rig.log 2>&1 &
rig_pid=$!
trap '\''kill -INT "$rig_pid" 2>/dev/null || true'\'' EXIT
if ! python3 /opt/genem/tests/ros2_head_integration.py; then
  cat /tmp/head-rig.log
  exit 1
fi
'
