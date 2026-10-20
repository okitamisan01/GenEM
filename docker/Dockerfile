ARG ROS_IMAGE=ros:jazzy-ros-base-noble@sha256:103b6c417973394659af6804d4917cd489b91e5ed22eb7bef263025a3bed2410
ARG ROS_DISTRO=jazzy
FROM ${ROS_IMAGE}
ARG ROS_DISTRO
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-colcon-common-extensions python3-rosdep python3-pytest \
    python3-yaml python3-requests \
    ros-${ROS_DISTRO}-control-msgs ros-${ROS_DISTRO}-controller-manager ros-${ROS_DISTRO}-ros2-control \
    ros-${ROS_DISTRO}-joint-trajectory-controller ros-${ROS_DISTRO}-joint-state-broadcaster \
    ros-${ROS_DISTRO}-robot-state-publisher ros-${ROS_DISTRO}-rmw-cyclonedds-cpp \
    && rm -rf /var/lib/apt/lists/*
RUN if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi
RUN rosdep update --rosdistro ${ROS_DISTRO}
WORKDIR /root/colcon_ws
COPY ros2_ws/src /root/colcon_ws/src
RUN . /opt/ros/${ROS_DISTRO}/setup.sh && colcon build --symlink-install
COPY config /opt/genem/config
COPY tests /opt/genem/tests
COPY demos /opt/genem/demos
COPY scripts /opt/genem/scripts
COPY docker/entrypoint.sh /genem_entrypoint.sh
RUN chmod +x /genem_entrypoint.sh && echo 'source /genem_entrypoint.sh' >> /root/.bashrc
ENTRYPOINT ["/genem_entrypoint.sh"]
CMD ["bash"]
