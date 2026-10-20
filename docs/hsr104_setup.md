# HSR104: supplied startup procedure → GenEM head client

## Deployment decision

The supplied checklist identifies a Linux host running Ubuntu 24.04, an existing
`human_concept_ws` Jazzy container, and an HSR104 running **ROS 2 Humble**.
This repository keeps the default Noble/Jazzy image and adds an **optional Jammy/Humble
client image** for the robot. Host OS and the existing human_concept container remain
unchanged. There is no automatic SSH, robot startup, torque activation, posture reset,
host IP configuration, clock configuration or sysctl modification.

Reason: the inspected Humble and Jazzy `ControllerState`/`HardwareComponentState`
definitions differ. The current FollowJointTrajectory definitions match, but this does
not make all controller-manager services compatible. The adapter uses those services
for preflight, so the dedicated client matches the robot distribution.

Primary sources: [Humble controller state](https://github.com/ros-controls/ros2_control/blob/humble/controller_manager_msgs/msg/ControllerState.msg),
[Jazzy controller state](https://github.com/ros-controls/ros2_control/blob/jazzy/controller_manager_msgs/msg/ControllerState.msg),
[Humble trajectory Action](https://github.com/ros-controls/control_msgs/blob/humble/control_msgs/action/FollowJointTrajectory.action),
[Cyclone interface selection](https://cyclonedds.io/docs/cyclonedds/latest/config/network_interfaces.html).
The actual robot's installed package versions still require on-site verification.

## Locations and order

1. **Host:** follow your checklist A: correct wired IP/interface, ping, clock sync
   and required receive buffer. GenEM does not perform these system changes.
2. **HSR SSH terminal:** follow checklist B: synchronize time and start `hsrb_minimal`.
   Release emergency stop only at the indicated supervised stage, and keep that
   terminal open. Never store the robot password in this repository.
3. **Existing human_concept container:** keep using `hsrb_mode` in each terminal
   as required by that environment. GenEM does not modify or assume that alias's body.
4. **Host:** run the separate GenEM client below. Its Compose environment sets the
   known domain/RMW/XML values every time; it has no `hsrb_mode` alias dependency.

Microphone recording, image DDS transport and display/browser startup are unnecessary
for head nod/shake execution. The known camera `serdata.cpp` issue remains unresolved;
successful head tests do not imply camera transport is fixed. GenEM does not execute
the arm/base posture commands from the checklist.

## First-time preparation on the connected PC

```bash
cd ~/GenEM
bash docker/hsr104.sh build
```

Prepare **local** settings with the actual wired interface and HSR address from the
checklist. Replace the placeholder arguments; do not paste angle-bracket placeholders
literally. This runs in an offline container and requires no host Python packages:

```bash
bash docker/hsr104.sh prepare \
  --interface WIRED_INTERFACE --robot-ip HSR_IP --domain 104
```

Generated files:

- `config/cyclonedds.local.xml`: explicit wired interface and discovery peer.
- `config/hsr104.local.yaml`: head endpoints and restrictive limits; **verified=false**.
- `docker/hsr104.local.env`: domain 104 and Cyclone configuration.

All three are excluded from Git and Docker build contexts. They are not automatically
transferred by cloning. Preparation refuses to overwrite existing/reviewed files.
The helper never enables hardware or connects to the robot.

### Reuse the known-working DDS XML when available

The XML path in the supplied checklist is inside the old container. It is not assumed
to exist on the host or in this new client. If you can access a known-working XML on
the host, copy it into `config/cyclonedds.source.local.xml` and prepare with:

```bash
bash docker/hsr104.sh prepare \
  --interface WIRED_INTERFACE --robot-ip HSR_IP --domain 104 \
  --working-dds /workspace/config/cyclonedds.source.local.xml
```

If only the running old container has the XML, use `docker cp` to retrieve that file
first, using the actual container name and source path. No original file is modified.
If local settings already exist, review and replace only the local XML manually.
The generated minimal XML is not claimed to be identical to the previously working
profile. Interface names must match the **connected host**, not the development PC.

## Start the GenEM client — host terminal

```bash
bash docker/hsr104.sh up
bash docker/hsr104.sh exec
```

**Inside the GenEM Humble client**:

```bash
echo "$ROS_DISTRO"          # humble
echo "$ROS_DOMAIN_ID"       # 104
echo "$RMW_IMPLEMENTATION"  # rmw_cyclonedds_cpp
echo "$CYCLONEDDS_URI"      # file:///root/genem_config/cyclonedds.local.xml
```

The XML has a stable container path, rather than the old user's absolute home path.
`GENEM_HSR_DOMAIN_ID` in the local env file drives the dedicated Compose service;
ambient host ROS_DOMAIN_ID does not silently select another robot domain.
The default Jazzy project and the dedicated Humble project are separately named.

## Read-only checks — no movement

From the **host**, with the robot stack already started:

```bash
bash docker/hsr104.sh exec ros2 topic list
bash docker/hsr104.sh exec ros2 run genem_hsr hsr_probe \
  --profile /root/genem_config/hsr104.local.yaml
```

The probe shows ROS distribution, configured domain, actual RMW identifier, selected
Action, joint names and current pan/tilt. It sends no motion goal, even with an
unverified hardware profile. Topics appearing alone are insufficient: the probe also
requires a reachable active head JTC, expected clock/interpolation, and fresh timestamped
position AND velocity feedback. A DDS configuration/interface initialization failure
is reported as a preflight error rather than an unhandled traceback.

If any check fails, stop at diagnosis. Do not remove preflight checks to make it move.
A source/profile mismatch or stale feedback must be resolved with the robot operator.
No claim is made that physical HSR104 has passed these checks yet.

## First supervised head movement

The supplied checklist confirms the head Action name and pan/tilt joint names, but
does **not** establish joint/velocity/acceleration limits or collision clearance.
Review the actual robot and the local YAML with the laboratory operator, keep the
head workspace clear and have emergency stop available. Only then set `verified`
to true and write the review basis in `verification_note`. Other head-command clients
must be stopped. Do not mark the profile verified based only on this checklist.

A small first nod (0.04 rad amplitude, 0.1 rad/s requested speed) is packaged:

```bash
bash docker/hsr104.sh exec ros2 run genem_demo interactive_demo --hsr \
  --profile /root/genem_config/hsr104.local.yaml \
  --behavior-file /opt/genem/demos/hsr_first_nod.json
```

It previews the whole trajectory first and requires typing **EXECUTE**. `--yes` is
forbidden. Excursions are relative to measured current pose; out-of-range paths
are refused before any command. The software monitors feedback and requests Action
cancellation on a fault/interrupt; this is not an independent emergency stop.

After on-site verification, `--scenario nod` and `--scenario shake_head` use the normal
presets. `hello` also requests `look_at(person)`; the physical template intentionally
has no person direction until manually measured. Speech, camera perception, microphone
input, display control and base/arm motion are not integrated into GenEM yet.

## Offline verification

These tests never connect to domain 104 or a physical robot:

```bash
GENEM_IMAGE=genem-hsr:humble GENEM_RMW=rmw_cyclonedds_cpp bash tests/verify_ros2_head.sh
GENEM_IMAGE=genem-hsr:humble GENEM_RMW=rmw_cyclonedds_cpp bash tests/verify_container.sh
```

Motion tests use network isolation and domain 91. The first test also loads a generated
loopback-only DDS XML, checks clean failure for invalid XML, verifies actual JTC motion,
cancels after state-stream loss, and exercises CLI confirmation/provenance. This
validates the client and test mechanism, not the physical robot or mixed-distro traffic.
