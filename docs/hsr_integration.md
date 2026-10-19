# HSR integration: evidence and remaining work

**Hardware execution is disabled.** No robot discovery, publishers, services,
action clients or actuation commands were created during this implementation.
`HSRRobotSkillInterface` is an interface scaffold, not a working driver.

## Source evidence

Read-only inspection of an existing local `docker_inside/hsr_ros2_ws/src` checkout
found ROS 2 HSR packages. Repository identity and revisions were read with
per-command `safe.directory` overrides; no global Git configuration or upstream
repository content was changed.

| Evidence | Confirmed in source | What it does not establish |
|---|---|---|
| [hsrb_launch](https://github.com/hsr-project/hsrb_launch), revision `6a2077f61840e3d938bb0b0a3bf30e59b148fdea`, `hsrb_rviz_simulator/config/controllers.yaml` | `head_trajectory_controller` is a `joint_trajectory_controller/JointTrajectoryController`; ordered joints `head_tilt_joint`, `head_pan_joint`; position command/state interfaces | actual robot namespace, active action server, controller version or supported Jazzy deployment |
| [hsrb_common](https://github.com/hsr-project/hsrb_common), revision `2e43f1db34846b05ba95709a26bda94bb1765c3e`, `hsrb_description/urdf/ros2_control.robot.xacro` | head pan min/max -3.84/1.75 rad, tilt -1.57/0.52 rad, velocity_limit 1.0 for each in this source profile | calibration, model/firmware match, collision-free limits or permission to command this lab's robot |
| local `hsrb_teleop/hsrb_joystick_teleop/.../joystick_control.py` | subscribes to `joint_states`; gripper uses a JointTrajectory topic | verified head action/topic names or speech interface on the robot |

The names above are source evidence, not endpoints to try speculatively. No action
or service name was confirmed on a running HSR. No TMC source files were vendored.
The existing `docker_ws` selects Humble locally, while local built HSR artifacts also
contain Python 3.10 paths. This is insufficient to claim Jazzy binary compatibility.
No HSR-specific SOBITS control wrapper was verified; only the SOBITS Docker design
was inspected. Access to public HSR ROS 2 source does not establish the lab robot's
ROS version: it may use ROS 1, ROS 2, or a separately managed integration stack.

## Skill decisions

All six requested head/gaze/wait/speech skills exist as robot-independent methods
and Mock records. Head nod/shake and look_direction are plausible candidates for
the confirmed pan/tilt joints, but no motion conversion is implemented before a
verified state/trajectory/control contract exists. `look_at(person)` requires
perception, a timestamped target transform and loss-of-target handling. Speech
requires a verified speech API and timeout. `base_rotate` is excluded from the
whitelist because base safety and its deployed control interface are unverified.

## Required next steps before a hardware implementation

1. Obtain robot model, software version, ROS distribution/RMW, lab-approved network
   settings and manufacturer/lab control instructions. Identify ROS 1 versus ROS 2.
2. In an authorized read-only session, inspect available topics, service/action types,
   controller parameters, joint_states and robot_description. Record exact endpoints,
   namespaces, QoS, joint order and source revisions in a reviewed robot profile.
3. Reconcile limits/calibration with the physical robot. Add current-state bounds,
   acceleration/velocity and swept-motion checks; never reuse the mock policy.
4. For ROS 2, build matching drivers/controller dependencies for the supported
   distribution and validate in simulation. Jazzy support is currently unproven.
   For ROS 1, investigate a separate compatible bridge host or explicit vetted gateway;
   do not assume a binary ros1_bridge exists on Noble/Jazzy. Custom messages/actions
   may need interface packages and an action-aware gateway.
5. Implement an adapter with explicit goal confirmation, bounded server waits,
   acceptance/result checks, timeout/cancellation, stale-state rejection and fail-stop.
   Revalidate every feedback revision under the actual robot profile.
6. Only then perform supervised low-amplitude tests with a clear area, verified
   emergency stop and operator authorization. Record results separately from Mock.

The current CLI always refuses `--hsr`, including `--hsr --yes`. There is no env
variable or force option to bypass this boundary. This is the intentionally incomplete
Phase 3 outcome allowed when physical interfaces and safety conditions are unavailable.
