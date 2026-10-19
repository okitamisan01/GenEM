#!/usr/bin/env bash
# Run from any directory after docker/build.sh; needs no API credentials or robot.
set -euo pipefail
docker run --rm --network none genem-hsr:jazzy bash -c '
set -e
cd /root/colcon_ws
colcon build --symlink-install
source install/setup.bash
colcon test --event-handlers console_direct+
colcon test-result --verbose
for scenario in nod shake_head become_attentive acknowledge_person pay_attention_to_person; do
  ros2 run genem_demo interactive_demo --mock --scenario "$scenario" --yes
done
ros2 run genem_demo interactive_demo --mock --scenario acknowledge_person \
  --feedback "Make it slower and friendlier." --yes
if ros2 run genem_demo interactive_demo --hsr --scenario nod --yes; then
  echo "ERROR: disabled HSR unexpectedly succeeded" >&2
  exit 1
else
  result=$?
  test "$result" -eq 2
fi
'
