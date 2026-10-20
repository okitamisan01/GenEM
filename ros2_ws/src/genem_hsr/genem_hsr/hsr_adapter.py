"""ROS 2 HSR head Action adapter. ROS imports are lazy to keep Mock independent."""
import math
import os
import time
from .behavior import BehaviorError
from .head_motion import JOINTS, load_profile, compile_head_motion
from .skill_base import RobotSkillInterface, HardwareDisabledError


class HSRRobotSkillInterface(RobotSkillInterface):
    requires_confirmation = True

    def __init__(self, profile_path=None, *, mode='hardware', read_only=False):
        if profile_path is None:
            raise HardwareDisabledError('HSR execution disabled: --profile is required')
        self.profile = load_profile(profile_path)
        if self.profile.environment != mode:
            raise HardwareDisabledError('Profile environment does not match --hsr/--sim')
        if not read_only and (not self.profile.verified or not self.profile.verification_note.strip()):
            raise HardwareDisabledError('HSR execution disabled: robot profile is not operator-verified')
        self.read_only = read_only
        self._initialized = False
        self._active = None
        self.last_cancel_confirmed = None
        self._state = None
        self._received = None
        try:
            import rclpy
            from rclpy.context import Context
            from rclpy.executors import SingleThreadedExecutor
            from rclpy.signals import SignalHandlerOptions
            from rclpy.parameter import Parameter
            from rclpy.action import ActionClient
            from rclpy.qos import qos_profile_sensor_data
            from control_msgs.action import FollowJointTrajectory
            from controller_manager_msgs.srv import ListControllers, ListHardwareComponents
            from rcl_interfaces.srv import GetParameters
            from sensor_msgs.msg import JointState
        except ImportError as exc:
            raise HardwareDisabledError('ROS control dependencies missing; rebuild the Docker image') from exc
        self.ros = rclpy
        self.context = Context()
        rclpy.init(context=self.context, signal_handler_options=SignalHandlerOptions.NO)
        self.node = rclpy.create_node(
            f'genem_head_adapter_{os.getpid()}', context=self.context,
            parameter_overrides=[Parameter('use_sim_time', value=self.profile.use_sim_time)])
        self.executor = SingleThreadedExecutor(context=self.context)
        self.executor.add_node(self.node)
        self.action_type = FollowJointTrajectory
        self.hardware_type = ListHardwareComponents
        self.list_type = ListControllers
        self.params_type = GetParameters
        self.subscription = self.node.create_subscription(
            JointState, self.profile.joint_states, self._joint_state, qos_profile_sensor_data)
        self.action = ActionClient(self.node, FollowJointTrajectory, self.profile.action_name)
        self.controllers = self.node.create_client(
            ListControllers, self.profile.controller_manager.rstrip('/') + '/list_controllers')
        self.hardware = self.node.create_client(
            ListHardwareComponents, self.profile.controller_manager.rstrip('/') + '/list_hardware_components')
        self.parameters = self.node.create_client(
            GetParameters, self.profile.controller.rstrip('/') + '/get_parameters')
        self._initialized = True

    def _joint_state(self, msg):
        try:
            if len(set(msg.name)) != len(msg.name):
                raise ValueError('duplicate names')
            indices = [msg.name.index(j) for j in JOINTS]
            positions = tuple(msg.position[i] for i in indices)
            velocities = tuple(msg.velocity[i] for i in indices)
            if not all(math.isfinite(x) for x in positions + velocities):
                raise ValueError('nonfinite state')
            self._state = (positions, velocities, msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9)
            self._received = time.monotonic()
        except (ValueError, IndexError, TypeError):
            self._state = None

    def _await(self, future, timeout, label):
        deadline = time.monotonic() + timeout
        while not future.done() and time.monotonic() < deadline:
            if not self.context.ok():
                raise HardwareDisabledError('ROS context stopped')
            self.executor.spin_once(timeout_sec=0.05)
        if not future.done():
            raise HardwareDisabledError(f'Timed out: {label}')
        try:
            result = future.result()
        except Exception as exc:
            raise HardwareDisabledError(f'ROS request failed: {label}') from exc
        if result is None:
            raise HardwareDisabledError(f'No ROS response: {label}')
        return result

    def _check_controller(self):
        timeout = self.profile.connection_timeout
        if not self.controllers.wait_for_service(timeout_sec=timeout):
            raise HardwareDisabledError('controller_manager not reachable; check domain, discovery and namespace')
        result = self._await(self.controllers.call_async(self.list_type.Request()), timeout, 'list controllers')
        name = self.profile.controller.rsplit('/', 1)[-1]
        matches = [c for c in result.controller if c.name == name]
        if len(matches) != 1 or matches[0].state != 'active' or matches[0].type != 'joint_trajectory_controller/JointTrajectoryController':
            raise HardwareDisabledError('Configured head controller is not an active JointTrajectoryController')
        if not self.parameters.wait_for_service(timeout_sec=timeout):
            raise HardwareDisabledError('Head controller parameters unavailable')
        req = self.params_type.Request()
        req.names = ['joints', 'interpolation_method', 'use_sim_time']
        values = self._await(self.parameters.call_async(req), timeout, 'controller parameters').values
        if len(values) != 3 or set(values[0].string_array_value) != set(JOINTS) or len(values[0].string_array_value) != 2:
            raise HardwareDisabledError('Controller must command exactly the two HSR head joints')
        if values[1].string_value != 'splines':
            raise HardwareDisabledError('Bounded trajectories require JTC interpolation_method=splines')
        if values[2].bool_value != self.profile.use_sim_time:
            raise HardwareDisabledError('Controller clock and profile use_sim_time disagree')
        if self.profile.environment == 'simulator':
            if not self.hardware.wait_for_service(timeout_sec=timeout):
                raise HardwareDisabledError('Cannot verify simulation hardware component')
            components = self._await(self.hardware.call_async(self.hardware_type.Request()),
                                     timeout, 'simulation hardware identity').component
            if not self._simulated_head(components):
                raise HardwareDisabledError('Simulator mode requires a recognized fake/Gazebo head hardware plugin')
        if not self.action.wait_for_server(timeout_sec=timeout):
            raise HardwareDisabledError('FollowJointTrajectory Action server unavailable')

    @staticmethod
    def _simulated_head(components):
        required = {j + '/position' for j in JOINTS}
        known = {'mock_components/GenericSystem', 'fake_components/GenericSystem',
                 'hsrb_gz_ros2_control/IgnitionSystem'}
        return any(required.issubset({i.name for i in c.command_interfaces}) and
                   (getattr(c, 'plugin_name', '') or getattr(c, 'class_type', '')) in known
                   for c in components)

    def _current(self):
        deadline = time.monotonic() + self.profile.connection_timeout
        while time.monotonic() < deadline:
            self.executor.spin_once(timeout_sec=0.05)
            if self._state is None:
                continue
            positions, velocities, stamp = self._state
            now = self.node.get_clock().now().nanoseconds / 1e9
            age = now - stamp
            if now > 0 and -0.1 <= age <= self.profile.state_timeout and time.monotonic() - self._received <= self.profile.state_timeout:
                if any(abs(v) > 0.02 for v in velocities):
                    raise HardwareDisabledError('Head is moving; refusing to replace an active motion')
                return positions
        raise HardwareDisabledError('Fresh, timestamped pan/tilt position AND velocity state unavailable')

    def inspect(self):
        """Read-only: no goal is sent, including for an unverified hardware profile."""
        self._check_controller()
        positions = self._current()
        return {'environment': self.profile.environment, 'action': self.profile.action_name,
                'joint_states': self.profile.joint_states, 'joints': list(JOINTS),
                'positions': list(positions), 'profile_verified': self.profile.verified,
                'use_sim_time': self.profile.use_sim_time}

    def prepare(self, behavior):
        self._check_controller()
        points = compile_head_motion(behavior, self._current(), self.profile)
        return {'action': self.profile.action_name, 'environment': self.profile.environment,
                'points': len(points), 'duration_seconds': points[-1].time,
                'final_pan_tilt': list(points[-1].positions)}

    def _await_motion(self, future, duration):
        deadline = time.monotonic() + duration + 5.0
        while not future.done() and time.monotonic() < deadline:
            self.executor.spin_once(timeout_sec=0.05)
            if self._state is None or time.monotonic() - self._received > self.profile.state_timeout:
                raise HardwareDisabledError('Joint-state stream lost during motion')
            positions, velocities, stamp = self._state
            age = self.node.get_clock().now().nanoseconds / 1e9 - stamp
            if not -0.1 <= age <= self.profile.state_timeout:
                raise HardwareDisabledError('Joint-state timestamps stale during motion')
            for joint, pos, vel in zip(JOINTS, positions, velocities):
                limit = self.profile.limits[joint]
                if not limit['min'] <= pos <= limit['max'] or abs(vel) > limit['velocity'] * 1.1 + 0.02:
                    raise HardwareDisabledError('Measured head state violates the robot profile')
        return self._await(future, 0, 'head trajectory result')

    def _cancel(self):
        if self._active is None:
            return
        self.last_cancel_confirmed = False
        try:
            self._await(self._active.cancel_goal_async(), 2.0, 'cancel head motion')
            terminal = self._await(self._active.get_result_async(), 2.0, 'canceled goal result')
            self.last_cancel_confirmed = terminal.status in (4, 5, 6)
            if not self.last_cancel_confirmed:
                self.node.get_logger().error('Cancellation not confirmed. Operator emergency stop may be required.')
        except (Exception, KeyboardInterrupt):
            self.node.get_logger().error('Cannot confirm cancellation. Operator emergency stop may be required.')
        finally:
            self._active = None

    def execute_behavior(self, behavior, *, hardware_confirmed=False):
        if not getattr(self, '_initialized', False) or self.read_only:
            raise HardwareDisabledError('HSR execution disabled for this adapter')
        if not hardware_confirmed:
            raise HardwareDisabledError('Explicit ROS motion confirmation is required for every behavior')
        self._check_controller()
        points = compile_head_motion(behavior, self._current(), self.profile)
        from trajectory_msgs.msg import JointTrajectoryPoint
        from builtin_interfaces.msg import Duration
        goal = self.action_type.Goal()
        goal.trajectory.joint_names = list(JOINTS)
        for point in points:
            item = JointTrajectoryPoint()
            item.positions = list(point.positions)
            item.velocities = [0.0, 0.0]
            ns = int(round(point.time * 1e9))
            item.time_from_start = Duration(sec=ns // 1000000000, nanosec=ns % 1000000000)
            goal.trajectory.points.append(item)
        goal.goal_time_tolerance = Duration(sec=2)
        self._abandoning = False
        self.last_cancel_confirmed = None
        pending = self.action.send_goal_async(goal)
        # Retain accepted handles in the callback too, so interruption immediately
        # after acceptance can still cancel. Late acceptance is canceled while draining.
        def accepted_goal(future):
            try:
                handle = future.result()
                if handle is not None and handle.accepted:
                    self._active = handle
                    if self._abandoning:
                        handle.cancel_goal_async()
            except Exception:
                pass
        pending.add_done_callback(accepted_goal)
        try:
            handle = self._await(pending, self.profile.connection_timeout, 'goal acceptance')
            if not handle.accepted:
                raise HardwareDisabledError('Head trajectory goal rejected')
            self._active = handle
            response = self._await_motion(handle.get_result_async(), points[-1].time)
            if response.status != 4 or response.result.error_code != 0:
                raise HardwareDisabledError('Head trajectory failed: ' + response.result.error_string)
            final = self._current()
            if any(abs(a - b) > 0.03 for a, b in zip(final, points[-1].positions)):
                raise HardwareDisabledError('Final joint state does not match the commanded target')
            self._active = None
            return {'duration_seconds': points[-1].time, 'action': self.profile.action_name}
        except BaseException:
            self._abandoning = True
            if not pending.done():
                deadline = time.monotonic() + 2.0
                while not pending.done() and time.monotonic() < deadline:
                    self.executor.spin_once(timeout_sec=0.05)
                if not pending.done():
                    self.node.get_logger().error('Goal acceptance unknown. Check robot; use emergency stop if required.')
            self._cancel()
            raise

    def close(self):
        if not getattr(self, '_initialized', False):
            return
        self._cancel()
        self.action.destroy()
        self.executor.shutdown()
        self.node.destroy_node()
        if self.context.ok():
            self.context.shutdown()
        self._initialized = False

    # Individual calls are deliberately refused: use whole-plan preflight/execute only.
    def _whole_plan_required(self, *args, **kwargs):
        raise HardwareDisabledError('Use BehaviorExecutor for prevalidated whole-plan ROS motion')

    head_nod = head_shake = look_direction = look_at = wait = speak = _whole_plan_required
