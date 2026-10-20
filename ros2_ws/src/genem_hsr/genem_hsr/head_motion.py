"""ROS-independent HSR head profile and bounded zero-velocity spline waypoints."""
from dataclasses import dataclass
from pathlib import Path
import math
import yaml
from .behavior import BehaviorError, validate_behavior

JOINTS = ('head_pan_joint', 'head_tilt_joint')


def number(value, label, low, high):
    if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
        raise BehaviorError(f'{label} must be finite and within [{low}, {high}]')
    return float(value)


@dataclass(frozen=True)
class HeadProfile:
    environment: str
    verified: bool
    verification_note: str
    controller_manager: str
    controller: str
    joint_states: str
    use_sim_time: bool
    limits: dict
    targets: dict
    max_duration: float
    state_timeout: float
    connection_timeout: float

    @property
    def action_name(self):
        return self.controller.rstrip('/') + '/follow_joint_trajectory'


def load_profile(path):
    try:
        data = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as exc:
        raise BehaviorError('Cannot read HSR profile') from exc
    keys = {'environment', 'verified', 'verification_note', 'controller_manager', 'controller',
            'joint_states', 'use_sim_time', 'limits', 'targets', 'max_duration',
            'state_timeout', 'connection_timeout'}
    if not isinstance(data, dict) or set(data) != keys:
        raise BehaviorError('Invalid HSR profile fields')
    if data['environment'] not in ('hardware', 'simulator'):
        raise BehaviorError('environment must be hardware or simulator')
    for key in ('verified', 'use_sim_time'):
        if type(data[key]) is not bool:
            raise BehaviorError(f'{key} must be a boolean')
    if not isinstance(data['verification_note'], str):
        raise BehaviorError('verification_note must be text')
    if data['environment'] == 'hardware' and data['use_sim_time']:
        raise BehaviorError('Hardware profile must use wall time')
    for key in ('controller_manager', 'controller', 'joint_states'):
        name = data[key]
        if not isinstance(name, str) or not name.startswith('/') or ' ' in name or '//' in name:
            raise BehaviorError(f'{key} must be an absolute ROS name')
    if not isinstance(data['limits'], dict) or set(data['limits']) != set(JOINTS):
        raise BehaviorError('Profile must define both head joints only')
    for joint, limit in data['limits'].items():
        if not isinstance(limit, dict) or set(limit) != {'min', 'max', 'velocity', 'acceleration'}:
            raise BehaviorError('Invalid joint limit fields')
        lo = number(limit['min'], 'min', -4, 2)
        hi = number(limit['max'], 'max', -4, 2)
        if lo >= hi:
            raise BehaviorError('Joint min must be less than max')
        # Absolute engineering ceilings. Operators may only choose stricter profiles.
        number(limit['velocity'], 'velocity', 0.01, 0.35)
        number(limit['acceleration'], 'acceleration', 0.01, 0.5)
    if not isinstance(data['targets'], dict):
        raise BehaviorError('targets must be a mapping of manually measured directions')
    for name, values in data['targets'].items():
        if name not in ('front', 'person') or not isinstance(values, list) or len(values) != 2:
            raise BehaviorError('Targets require front/person: [yaw, pitch]')
        for joint, val in zip(JOINTS, values):
            number(val, 'target', data['limits'][joint]['min'], data['limits'][joint]['max'])
    number(data['max_duration'], 'max_duration', 1, 60)
    number(data['state_timeout'], 'state_timeout', 0.1, 2)
    number(data['connection_timeout'], 'connection_timeout', 0.1, 15)
    return HeadProfile(**data)


@dataclass(frozen=True)
class Waypoint:
    positions: tuple
    time: float


def compile_head_motion(behavior, current, profile):
    """Compile the ENTIRE sequence before any side effect, including unsupported skills.

    Supplying positions and zero velocities makes JTC use cubic splines.
    For displacement d over T, peak speed=1.5*d/T and peak acceleration=6*d/T².
    Each segment therefore uses both bounds, rounded upwards to microseconds.
    """
    plan = validate_behavior(behavior)
    if not isinstance(current, (tuple, list)) or len(current) != 2:
        raise BehaviorError('Expected current pan/tilt')
    position = []
    for joint, val in zip(JOINTS, current):
        limits = profile.limits[joint]
        position.append(number(val, joint, limits['min'], limits['max']))
    points = [Waypoint(tuple(position), 0.0)]
    elapsed = 0.0

    def append(target, requested_speed=None, hold=None):
        nonlocal elapsed, position
        duration = 0.1
        for i, joint in enumerate(JOINTS):
            limits = profile.limits[joint]
            number(target[i], joint, limits['min'], limits['max'])
            distance = abs(target[i] - position[i])
            speed = limits['velocity']
            if requested_speed is not None:
                speed = min(speed, requested_speed)
            duration = max(duration, 1.5 * distance / speed,
                           math.sqrt(6 * distance / limits['acceleration']))
        duration = max(duration, hold or 0)
        elapsed = math.ceil((elapsed + duration) * 1e6) / 1e6
        if elapsed > profile.max_duration:
            raise BehaviorError('Compiled trajectory exceeds profile duration limit')
        position = list(target)
        points.append(Waypoint(tuple(position), elapsed))

    for item in plan['behavior']['sequence']:
        skill, params = item['skill'], item['parameters']
        if skill == 'speak':
            raise BehaviorError('HSR speech is not configured; refusing entire behavior')
        if skill == 'look_at':
            target = params['target']
            if target not in profile.targets:
                raise BehaviorError(f'No measured direction configured for {target}; perception is not implemented')
            append(profile.targets[target])
        elif skill == 'look_direction':
            append([params['yaw'], params['pitch']])
        elif skill == 'wait':
            append(position, hold=params['duration'])
        else:
            axis = 1 if skill == 'head_nod' else 0
            center = list(position)
            for _ in range(params['repetitions']):
                for offset in (params['amplitude'], -params['amplitude'], 0):
                    target = list(center)
                    target[axis] += offset
                    append(target, requested_speed=params['speed'])
    return points
