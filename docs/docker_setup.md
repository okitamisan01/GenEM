# Docker setup and portability

## Reference investigation

Inspected local `TeamSOBITS/docker_ws` revision
`26c79cfb9ac0cfe1818e5b686d4e820e62dc5cc7`, read-only. It differs from the
current public default branch observed during research.

| Reference file/setting | Observed design | GenEM decision |
|---|---|---|
| env.sh | local defaults Ubuntu 22.04/Humble/GPU; selectable versions | fixed Noble/Jazzy, CPU default, .env example |
| Dockerfile | CPU/CUDA multistage, optional ROS/OpenCV/PyTorch, generated entrypoint | official ROS base, no external SOBITS image dependency |
| build.sh | creates .env, generated entrypoint, conditional stages, optional image pushes | simple compose build; no image push |
| up.sh / exec.sh | choose CPU/GPU service, named project | script-relative paths, one service |
| compose file | host network, source mount, privileged/device/GUI/audio access | host network retained; localhost discovery; no privileged/devices/GUI |
| workspace | mount src under a user home, set up ROS/workspace | /root/colcon_ws/src bind mount, conditional overlay sourcing |
| GPU | CUDA base and NVIDIA runtime device reservation | optional Compose GPU override; no local inference/CUDA requirement |

The public README also describes Ubuntu 24.04 and Jazzy selection.
Reference: [TeamSOBITS/docker_ws](https://github.com/TeamSOBITS/docker_ws).
The BSD license was checked. Files here were written independently; see
[notices](third_party_notices.md). No changes or pushes were made to that repository.

## Build/run

```bash
bash docker/build.sh
bash docker/up.sh
bash docker/exec.sh
```

Paths are resolved relative to each script. Docker uses repository root build context.
The image contains the packages, so a one-shot run does not need source mounts:

```bash
docker run --rm --network none genem-hsr:jazzy \
  ros2 run genem_demo interactive_demo --mock --scenario nod --yes
```

Compose mounts only repository `ros2_ws/src` , `config` (read-only) and `logs`; build/install remain in the
container and are recreated by an image build. After source changes, run colcon build
inside the container. Rebuilding/recreating is required for package metadata/dependency
changes. `exec.sh` sources both ROS and the workspace for commands and interactive shells.
Stopping: `cd docker && docker compose down`.

The base is `ros:jazzy-ros-base-noble`, pinned to manifest digest
`sha256:103b6c417973394659af6804d4917cd489b91e5ed22eb7bef263025a3bed2410`.
Installed tools: Python 3.12, colcon, rosdep, pytest, PyYAML, requests and ROS dependencies.
There is no need to disable Ubuntu's externally-managed Python policy or pip into system Python.
Image apt packages and rosdep indexes are fetched at build time; exact rebuilds require
repository snapshots or exporting the validated image. The image uses root for this
research development workflow; mounted files written inside may be root-owned.

## Environment and networking

Copy `docker/env.example` to `docker/.env` and edit only required values. Compose reads
this file; no shell sourcing of user-controlled .env is needed. Never commit it.
`ROS_DOMAIN_ID=42` and `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` are defaults.
Host networking targets Linux Docker Engine; Docker Desktop behavior differs and is untested.
For a future verified ROS 2 HSR deployment, select the matching domain/RMW and explicitly
set discovery range to `SUBNET`, check firewall/multicast and namespaces. Hardware support additionally requires a reviewed local profile and per-plan confirmation. No robot addresses are hardcoded.
For ROS 1 robots, host networking alone does not bridge message types or actions.

## Optional GPU

GPU is unnecessary for Mock or a remote API backend. With a separately installed
NVIDIA driver and NVIDIA Container Toolkit, Compose supporting `gpus` (2.30+) can run:

```bash
cd docker
docker compose -f compose.yaml -f compose.gpu.yaml up -d
```

This exposes GPU devices only; no CUDA/PyTorch/local model stack is installed.
GPU execution has not been tested in this project.

## Another PC / offline transport

```bash
git clone --branch feature/genem-prototype https://github.com/okitamisan01/GenEM.git
cd GenEM
bash docker/build.sh
bash docker/up.sh
bash docker/exec.sh
```

No username, absolute host path, robot IP or `docker_ws` checkout is required.
Use the same branch on the second PC; main is intentionally not merged.

```bash
docker save -o genem_hsr.tar genem-hsr:jazzy
# transfer the file outside Git to a machine with the same CPU architecture
docker load -i genem_hsr.tar
# docker/up.sh can now use the loaded image without a build
```

A different architecture needs its own build/compatible multi-platform image. Do not
add image archives to Git. Initial online builds require registry, Ubuntu/ROS apt and
rosdep access. Only Mock execution after building is verified without networking.

## ROS 2 head client dependencies

The client image now includes control_msgs, controller_manager/ros2_control,
joint_trajectory_controller, joint_state_broadcaster and robot_state_publisher.
The package includes an original two-joint test URDF and launch file. It is not a
copy of the HSR model and does not provide full-body physics or camera rendering.
The full TeamSOBITS simulator runs in its own separately prepared ROS environment.
