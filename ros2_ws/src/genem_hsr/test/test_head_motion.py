from pathlib import Path
from dataclasses import replace
import copy
import math
import pytest
import yaml
from genem_hsr.behavior import BehaviorError
from genem_hsr.generator import OfflineGenerator, step
from genem_hsr.head_motion import load_profile, compile_head_motion, JOINTS
from genem_hsr.skills import HSRRobotSkillInterface, HardwareDisabledError

ROOT = Path(__file__).resolve().parents[1]


def profile():
    return load_profile(ROOT / 'config/hsr_test_rig.yaml')


def test_whole_head_sequence_has_bounded_cubic_segments():
    p = profile()
    plan = OfflineGenerator().generate('hello')
    plan['behavior']['sequence'] += [step('head_shake', amplitude=0.1, speed=0.5, repetitions=2),
                                      step('look_direction', yaw=0.2, pitch=-0.1)]
    points = compile_head_motion(plan, [0, 0], p)
    assert points[-1].positions == (0.2, -0.1)
    assert any(pt.positions[1] < 0 for pt in points)
    assert any(pt.positions[1] > 0 for pt in points)
    for previous, current in zip(points, points[1:]):
        dt = current.time - previous.time
        assert dt > 0
        for j, a, b in zip(JOINTS, previous.positions, current.positions):
            delta = abs(a - b)
            assert 1.5 * delta / dt <= p.limits[j]['velocity'] + 1e-9
            assert 6 * delta / dt**2 <= p.limits[j]['acceleration'] + 1e-9


def test_nod_relative_to_current_and_returns_to_start():
    points = compile_head_motion(OfflineGenerator().generate('Nod'), [0.1, 0.05], profile())
    assert points[-1].positions == (0.1, 0.05)
    assert all(pt.positions[0] == 0.1 for pt in points)
    assert points[1].positions[1] == pytest.approx(0.2)


def test_nod_swept_waypoints_exceed_limits():
    with pytest.raises(BehaviorError):
        compile_head_motion(OfflineGenerator().generate('Nod'), [0.0, 0.25], profile())


def test_speech_rejects_the_entire_plan():
    plan = OfflineGenerator().generate('hello')
    plan['behavior']['sequence'].append(step('speak', text='Hi'))
    with pytest.raises(BehaviorError, match='entire behavior'):
        compile_head_motion(plan, [0, 0], profile())


def test_person_target_requires_measured_direction():
    with pytest.raises(BehaviorError, match='No measured direction'):
        compile_head_motion(OfflineGenerator().generate('hello'), [0, 0], replace(profile(), targets={}))


def test_real_trajectory_duration_checked_after_time_scaling():
    with pytest.raises(BehaviorError, match='duration'):
        compile_head_motion(OfflineGenerator().generate('Nod'), [0, 0], replace(profile(), max_duration=1))


@pytest.mark.parametrize('state', [[0], [0, float('nan')], [1, 0], [0, True]])
def test_invalid_current_state(state):
    with pytest.raises(BehaviorError):
        compile_head_motion(OfflineGenerator().generate('Nod'), state, profile())


@pytest.mark.parametrize('key,value', [('verified', 'true'), ('environment', 'unknown'),
    ('controller', 'relative'), ('connection_timeout', -1), ('state_timeout', float('nan'))])
def test_invalid_profile_fields(tmp_path, key, value):
    data = yaml.safe_load((ROOT / 'config/hsr_test_rig.yaml').read_text())
    data[key] = value
    path = tmp_path / 'profile.yaml'
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(BehaviorError):
        load_profile(path)


def test_unverified_hardware_fails_before_ros_initialization():
    with pytest.raises(HardwareDisabledError, match='operator-verified'):
        HSRRobotSkillInterface(ROOT / 'config/hsr_hardware.example.yaml')


def test_simulation_profile_cannot_be_selected_as_hardware():
    with pytest.raises(HardwareDisabledError, match='does not match'):
        HSRRobotSkillInterface(ROOT / 'config/hsr_test_rig.yaml', mode='hardware')


def test_simulator_identity_does_not_accept_physical_head_plugin():
    from types import SimpleNamespace as NS
    interfaces = [NS(name=j + '/position') for j in JOINTS]
    real = NS(plugin_name='robot_driver/PhysicalSystem', command_interfaces=interfaces)
    simulated = NS(plugin_name='mock_components/GenericSystem', command_interfaces=interfaces)
    assert HSRRobotSkillInterface._simulated_head([real]) is False
    assert HSRRobotSkillInterface._simulated_head([simulated]) is True
    assert HSRRobotSkillInterface._simulated_head([]) is False
