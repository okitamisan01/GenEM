FROM ros:jazzy-ros-base-noble
ENV DEBIAN_FRONTEND=noninteractive
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
