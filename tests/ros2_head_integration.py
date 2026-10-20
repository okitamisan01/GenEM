"""End-to-end test against real ros2_control/JTC with GenericSystem, not a fake Action."""
import json
import time
from sensor_msgs.msg import JointState
from genem_hsr.generator import step
from genem_hsr.skills import HSRRobotSkillInterface, HardwareDisabledError
from genem_hsr.executor import BehaviorExecutor

adapter = HSRRobotSkillInterface('/opt/genem/config/hsr_test_rig.yaml', mode='simulator')
samples = []
observer = adapter.node.create_subscription(
    JointState, '/joint_states', lambda msg: samples.append(dict(zip(msg.name, msg.position))), 10)
try:
    deadline = time.monotonic() + 30
    while True:
        try:
            report = adapter.inspect()
            break
        except HardwareDisabledError:
            if time.monotonic() >= deadline:
                raise
    print('Read-only probe:', json.dumps(report))
    import subprocess
    probe = subprocess.run(['ros2', 'run', 'genem_hsr', 'hsr_probe', '--profile',
                            '/opt/genem/config/hsr_test_rig.yaml'],
                           capture_output=True, text=True, timeout=20)
    assert probe.returncode == 0, probe.stdout + probe.stderr
    assert 'No motion goal sent' in probe.stdout
    print('PASS: installed read-only hsr_probe command.')
    plan = {'behavior': {'name': 'head integration', 'sequence': [
        step('look_at', target='person'),
        step('head_nod', amplitude=0.04, speed=0.2, repetitions=1),
        step('head_shake', amplitude=0.04, speed=0.2, repetitions=1),
        step('look_direction', yaw=0.1, pitch=-0.08),
        step('wait', duration=0.2),
    ]}}
    try:
        BehaviorExecutor(adapter).execute(plan)
    except HardwareDisabledError:
        pass
    else:
        raise AssertionError('ROS execution was possible without confirmation')
    print('Trajectory preflight:', json.dumps(adapter.prepare(plan)))
    result = BehaviorExecutor(adapter).execute(plan, hardware_confirmed=True)
    assert len(samples) > 20, 'No real joint-state stream observed'
    for joint in ('head_pan_joint', 'head_tilt_joint'):
        values = [s[joint] for s in samples if joint in s]
        assert min(values) < -0.02 and max(values) > 0.02, (joint, min(values), max(values))
    final = adapter.inspect()['positions']
    assert abs(final[0] - 0.1) < 0.02 and abs(final[1] + 0.08) < 0.02, final
    print('PASS: Action accepted/completed, nod/shake excursions observed, final position verified.', result)

    # Stop the actual joint-state broadcaster during a goal: watchdog must cancel.
    from controller_manager_msgs.srv import SwitchController
    switcher = adapter.node.create_client(SwitchController, '/controller_manager/switch_controller')
    assert switcher.wait_for_service(timeout_sec=3)
    switch_futures = []
    def stop_state_stream():
        timer.cancel()
        request = SwitchController.Request()
        request.deactivate_controllers = ['joint_state_broadcaster']
        request.strictness = 2
        switch_futures.append(switcher.call_async(request))
    timer = adapter.node.create_timer(1.0, stop_state_stream)
    long_plan = {'behavior': {'name': 'watchdog test', 'sequence': [
        step('look_direction', yaw=-0.2, pitch=0.0), step('wait', duration=5.0)]}}
    try:
        BehaviorExecutor(adapter).execute(long_plan, hardware_confirmed=True)
    except HardwareDisabledError as exc:
        assert 'stream lost' in str(exc), str(exc)
        assert adapter.last_cancel_confirmed is True, 'Controller did not confirm a terminal goal state'
        print('PASS: lost joint-state stream caused confirmed Action cancellation.')
    else:
        raise AssertionError('Motion survived loss of joint-state feedback')
    finally:
        timer.cancel()
        adapter.node.destroy_timer(timer)
        if switch_futures:
            assert adapter._await(switch_futures[0], 3, 'disable broadcaster').ok
        request = SwitchController.Request()
        request.activate_controllers = ['joint_state_broadcaster']
        request.strictness = 2
        assert adapter._await(switcher.call_async(request), 3, 'restore broadcaster').ok
        adapter.node.destroy_client(switcher)
    import subprocess
    import sys
    from pathlib import Path
    cli_log = Path('/tmp/genem-ros-cli.jsonl')
    cli = subprocess.run([
        sys.executable, '-m', 'genem_demo.cli', '--sim',
        '--profile', '/opt/genem/config/hsr_test_rig.yaml', '--scenario', 'nod',
        '--log', str(cli_log)], input='EXECUTE\n', text=True, capture_output=True, timeout=25)
    assert cli.returncode == 0, cli.stdout + cli.stderr
    event = json.loads(cli_log.read_text().splitlines()[-1])
    assert event['adapter'] == 'hsr_simulator' and event['executed'] is True, event
    print('PASS: CLI EXECUTE confirmation, ROS motion and simulator provenance log.')

finally:
    adapter.close()
