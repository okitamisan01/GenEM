FROM ros:jazzy-ros-base-noble@sha256:103b6c417973394659af6804d4917cd489b91e5ed22eb7bef263025a3bed2410
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-colcon-common-extensions python3-rosdep python3-pytest \
    python3-yaml python3-requests \
    && rm -rf /var/lib/apt/lists/*
RUN if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi
RUN rosdep update --rosdistro jazzy
WORKDIR /root/colcon_ws
COPY ros2_ws/src /root/colcon_ws/src
RUN . /opt/ros/jazzy/setup.sh && colcon build --symlink-install
COPY docker/entrypoint.sh /genem_entrypoint.sh
RUN chmod +x /genem_entrypoint.sh && echo 'source /genem_entrypoint.sh' >> /root/.bashrc
ENTRYPOINT ["/genem_entrypoint.sh"]
CMD ["bash"]
