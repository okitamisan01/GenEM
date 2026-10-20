# ROS 2 HSR head integration

The ROS 2 adapter is now implemented. It commands **head pan/tilt only** through
`control_msgs/action/FollowJointTrajectory`; it does not control the base or arms.
Physical execution needs a robot-specific profile, read-only preflight and explicit
confirmation for every behavior. Mock remains the default.

## What has actually been verified

- ROS 2 Jazzy `JointTrajectoryController` with `mock_components/GenericSystem`.
- Real Action acceptance/completion and streamed pan/tilt state changes for nod,
  shake, gaze direction and waits; final position checked independently.
- Loss of the actual joint-state broadcaster during an active goal caused the
  watchdog to cancel it, with a terminal Action result confirmed.
- CLI `EXECUTE` confirmation, ROS motion and `hsr_simulator` JSONL provenance.

This is a two-joint ros2_control commissioning rig, **not** full Gazebo HSR or a
physical robot. No command has been sent to an actual HSR. The full TeamSOBITS
Gazebo setup has been source-inspected, not built or run in this task.

## 1. Build the client image

```bash
bash docker/build.sh
bash docker/up.sh
```

The image includes rclpy, control_msgs, trajectory_msgs, controller_manager and
head-controller test dependencies. Profiles in host `config/` are read-only mounted
at `/root/genem_config`. `config/*.local.yaml` is ignored by Git.

## 2. Test locally without a robot

Terminal A:

```bash
bash docker/exec.sh ros2 launch genem_hsr head_test_rig.launch.py
```

Terminal B:

```bash
bash docker/exec.sh ros2 run genem_hsr hsr_probe \
  --profile /root/genem_config/hsr_test_rig.yaml
bash docker/exec.sh ros2 run genem_demo interactive_demo --sim \
  --profile /root/genem_config/hsr_test_rig.yaml --scenario nod
```

Check the printed endpoint and trajectory preview, then type **EXECUTE** to send
one trajectory. Anything else declines. `--yes` is forbidden for all ROS motion.
The test rig has no robot geometry renderer. Use `/joint_states` to inspect changes.
Automated integration test, isolated from all physical robots:

```bash
bash tests/verify_ros2_head.sh
```

## 3. Connect to TeamSOBITS Gazebo HSR

Inspected [TeamSOBITS/hsrb_simulator jazzy](https://github.com/TeamSOBITS/hsrb_simulator/tree/jazzy)
at revision `a4eca087da629b8448fbc2a9adb3227e274f8288` in a temporary, read-only
reference checkout. It documents Ubuntu 24.04 / Jazzy / Gazebo Sim 8 and provides:

- `hsrb_gazebo_bringup/config/gazebo_ros2_control.yaml`: head JTC and joint names.
- `hsrb_gz_ros2_control/gz_hardware_plugins.xml`: `hsrb_gz_ros2_control/IgnitionSystem`.
- `/joint_states` and `/head_trajectory_controller/joint_trajectory` in its README.

The Action endpoint follows the standard JTC contract documented by
[ros2_control Jazzy](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html).
GenEM uses the monitored Action instead of unmonitored topic commands.

Start the already-installed simulator **in its own ROS environment**:

```bash
ros2 launch hsrb_gazebo_bringup hsrb_gazebo_bringup.launch.py
```

If it is not installed, follow that repository's setup instructions in a separate
workspace; it is not automatically installed by the lightweight GenEM image.
Do not run the two-joint test rig and the full simulator in the same domain/namespace.
Match `ROS_DOMAIN_ID` in `docker/.env` to the simulator. It must be on the same host
for LOCALHOST discovery, or explicitly use SUBNET for a remote simulator.
Recreate Compose after environment changes:

```bash
bash docker/up.sh --force-recreate
bash docker/exec.sh ros2 run genem_hsr hsr_probe \
  --profile /root/genem_config/hsr_sim.yaml
bash docker/exec.sh ros2 run genem_demo interactive_demo --sim \
  --profile /root/genem_config/hsr_sim.yaml --scenario nod
```

`hsr_sim.yaml` uses simulation time and checks for a recognized simulator hardware
plugin. Its static `person: [0, 0]` target is a demo direction, not person detection.
If the controller uses a namespace, copy the profile to `config/hsr_sim.local.yaml`
and change controller_manager/controller/joint_states accordingly.

## 4. Connect a physical ROS 2 HSR

ROS 2 was confirmed by the user. The exact robot distribution, namespaces and
calibration still need on-site verification. Connecting the network alone is not a
substitute for those checks. The deployed controller must expose compatible ROS 2
Action, parameter and controller-manager interfaces; ROS 2 across distributions
alone does not guarantee message/service compatibility.

On the host:

```bash
cp config/hsr_hardware.example.yaml config/hsr.local.yaml
```

Set the correct ROS_DOMAIN_ID and, for another machine, discovery range SUBNET in
`docker/.env`; match the robot's RMW configuration. Then:

```bash
bash docker/up.sh --force-recreate
# READ ONLY: allowed even while verified=false
bash docker/exec.sh ros2 run genem_hsr hsr_probe \
  --profile /root/genem_config/hsr.local.yaml
```

The probe sends no trajectory. It checks that the configured controller is active,
commands exactly `head_pan_joint` and `head_tilt_joint`, uses spline interpolation,
uses the expected clock and has a reachable trajectory Action. It also requires
fresh timestamped position AND velocity feedback with the head stationary.

Before enabling motion, the laboratory operator must review the actual robot's
joint calibration, allowed head workspace, velocity/acceleration limits, controller
configuration and emergency stop. Use a clear head workspace, supervision, and no
other client commanding the head controller. Source values are evidence only, not
certification. Edit the local profile's limits and endpoints to the verified values;
then set `verified: true` and write the review basis in `verification_note`.
Do not enable the shipped example unchanged just to bypass a preflight error.

Only after those conditions hold:

```bash
bash docker/exec.sh ros2 run genem_demo interactive_demo --hsr \
  --profile /root/genem_config/hsr.local.yaml --scenario nod
```

The preview is read-only. Type EXECUTE only after checking the actual target.
Every revision requires a fresh confirmation and preflight. Ctrl+C while a goal is
active requests cancellation; the adapter waits for a terminal result. If communication
is broken and cancellation cannot be confirmed, it prints an emergency-stop warning.
Software cancellation is not an independent emergency stop.

## Motion and limitations

Nod/shake excursions are relative to the measured current pose and return to it.
Every waypoint is checked against the local profile. Full sequences are compiled
before any movement, so an unsupported later step refuses the entire plan.
Positions plus zero endpoint velocities request cubic interpolation. Segment times
bound peak command velocity and acceleration (`1.5*d/T`, `6*d/T²`). Speeds above
the profile are time-scaled downward; durations reflect the compiled trajectory,
not the faster Mock estimate. Final feedback must agree with the target within 0.03 rad.

During execution a joint-state watchdog checks timestamps, stream freshness,
position and velocity. Stale/out-of-range feedback, execution failures or result
timeouts trigger cancellation. Initial moving-head states are refused. These checks
do not establish collision safety, physical acceleration tracking or exclusive control.

`look_direction` interprets yaw/pitch as absolute pan/tilt joint angles, not Cartesian
gaze. `look_at` requires manually measured directions in `targets`. The hardware
example provides only `front`; add `person` only with a known measured direction.
There is no person detection/tracking or TF target resolution. `speak` is refused
for ROS execution until a verified speech backend exists; base/arm actions are absent.

## Earlier source evidence

Read-only local HSR sources remain useful references:
[hsrb_launch](https://github.com/hsr-project/hsrb_launch) revision
`6a2077f61840e3d938bb0b0a3bf30e59b148fdea` confirmed head JTC configuration.
[hsrb_common](https://github.com/hsr-project/hsrb_common) revision
`2e43f1db34846b05ba95709a26bda94bb1765c3e`,
`hsrb_description/urdf/ros2_control.robot.xacro`, has pan limits -3.84/1.75 rad,
tilt -1.57/0.52 rad and velocity_limit 1.0. GenEM defaults are much more restrictive;
these source limits were not automatically accepted as physical robot limits.
No external checkout was modified or pushed.
