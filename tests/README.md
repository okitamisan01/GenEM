# Verification entry points

- `python3 -m pytest -q` at repository root runs both packages' tests without ROS.
- ROS/colcon test sources are under `ros2_ws/src/genem_hsr/test/` and
  `ros2_ws/src/genem_demo/test_cli.py`.
- `bash tests/verify_container.sh` verifies the built image with networking disabled:
  build, colcon tests, all five scenarios, feedback and hardware refusal.

No real API key, external model call or robot is used by these checks.
See `docs/validation.md` for observed results.

## Real ROS controller integration

`bash tests/verify_ros2_head.sh` starts the packaged two-joint ros2_control test rig
in an ephemeral `--network none` container. It checks Action completion, joint-state
excursions/final positions, cancellation after broadcaster loss, and CLI confirmation
with simulator history. It cannot reach a physical robot. This is not full Gazebo HSR.

## Distribution and RMW selection

Set `GENEM_IMAGE=genem-hsr:humble` and `GENEM_RMW=rmw_cyclonedds_cpp` to run the
same ROS integration checks on the physical-robot client distribution. Cyclone runs
also load a generated loopback XML and check malformed-config failure. Neither test
script uses the real deployment XML or domain 104. `tests/test_connection_setup.py`
checks safe local preparation; root pytest includes it, while colcon tests remain
within the ROS packages.
