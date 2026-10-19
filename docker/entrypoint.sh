#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
if [[ -f /root/colcon_ws/install/setup.bash ]]; then
  source /root/colcon_ws/install/setup.bash
fi
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  exec "$@"
fi
