# Verification entry points

- `python3 -m pytest -q` at repository root runs both packages' tests without ROS.
- ROS/colcon test sources are under `ros2_ws/src/genem_hsr/test/` and
  `ros2_ws/src/genem_demo/test_cli.py`.
- `bash tests/verify_container.sh` verifies the built image with networking disabled:
  build, colcon tests, all five scenarios, feedback and hardware refusal.

No real API key, external model call or robot is used by these checks.
See `docs/validation.md` for observed results.
