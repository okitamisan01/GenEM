# Validation record

Client reporting date: **2026-10-20 (Asia/Tokyo)**.
Tested source milestone: `a19a01e` (subsequent documentation-only changes do not
change the tested package source). Platform: Linux / amd64, Docker Engine 29.6.2.
Container reports Ubuntu 24.04, Python 3.12.3, ROS_DISTRO=jazzy.

| Check | Observed result |
|---|---|
| Host `python3 -m pytest -q` | 55 passed, no real API key |
| `bash docker/build.sh` | image `genem-hsr:jazzy` built successfully, both packages built |
| `colcon build --symlink-install` in image | 2 packages finished |
| `colcon test` and `colcon test-result --verbose` | 55 tests, 0 errors, 0 failures, 0 skipped |
| `bash tests/verify_container.sh` | success with `--network none`; five scenarios, feedback and HSR refusal |
| `bash docker/up.sh` | Compose service created and started |
| `bash docker/exec.sh ...` | noninteractive command path works; ROS and overlay available |
| README `rosdep install --from-paths src --ignore-src -r -y` | all required rosdeps installed successfully |
| Compose-mounted source build/tests | 2 packages; 55 tests, no failures |
| Mock feedback | acknowledge sequence retained gaze; nod speed 0.5 → 0.35 |
| `--hsr --yes --scenario nod` | refused with exit code 2; no robot I/O |
| Shell syntax and `git diff --check` | pass |

The first environment-only image contained no packages because it was built before
package creation; it is not counted as package validation. Later builds included both
packages. During Compose verification a non-resolvable `ament_python` rosdep buildtool
key was corrected to `python3-setuptools`; rosdep and the complete test suite were then
rerun successfully. The exported build type remains `ament_python`.

## Reproduce

```bash
bash docker/build.sh
bash tests/verify_container.sh
```

This script creates an ephemeral container with networking disabled. Its expected
hardware-refusal check prints an error and ROS exit status 2, then the script verifies
that refusal and exits successfully. This is an expected negative test.

For development mounts:

```bash
bash docker/up.sh
bash docker/exec.sh bash -c 'set -e
cd ~/colcon_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
colcon test
colcon test-result --verbose
ros2 run genem_demo interactive_demo --mock --scenario nod --yes'
```

No physical HSR, live LLM provider, GPU configuration or second PC was tested.
Docker save/load instructions are documented; an image archive was not created or
committed. Tests confirm logical Mock execution, not actual timing or expression quality.

## Phase outcomes

| Phase | Result | Remaining work |
|---|---|---|
| 1: Research/environment | repository identities checked; official paper/appendices and local SOBITS configuration investigated; independent Noble/Jazzy image builds | dependency snapshots and other architectures |
| 2: Mock prototype | strict grammar, six skills, two backends, ordered execution, five demos, feedback/history, tests | live-provider compatibility and richer planning |
| 3: HSR integration | source evidence documented; interface scaffold refuses hardware | verified robot contract, working adapter, simulation and supervised hardware testing |
| 4: Reproducibility/materials | build/run/test scripts, English discussion notes and documentation | second-PC verification; merge to main remains unauthorized |

## Git scope

Only `okitamisan01/GenEM` is a development/commit/push target.
Branch: `feature/genem-prototype`. No merge to main is performed.
TeamSOBITS and existing HSR checkouts were read-only references.
For the final push result, compare the remote feature branch to the local HEAD;
this file does not treat a planned push as a completed push.

## Interactive-input regression update

The offline CLI now lists supported inputs, retries unsupported interactive instructions,
and accepts hello/hi/hey as acknowledgement aliases. `quit`/`exit` ends instruction input.
Host pytest and Compose-mounted colcon tests: **58 passed, 0 failures**.
A piped `h8 → hello → y → empty feedback` session was verified through
`ros2 run genem_demo interactive_demo --mock`: the invalid input produced no action,
and the greeting produced look_at followed by head_nod. Unsupported noninteractive
instructions still return status 2 for script error detection.
