import copy
import json
from pathlib import Path
from unittest.mock import Mock
import pytest
import requests
import yaml
from genem_hsr.behavior import BehaviorError, parse_behavior, validate_behavior
from genem_hsr.generator import APIBehaviorGenerator, OfflineGenerator, SCENARIOS
from genem_hsr.executor import BehaviorExecutor
from genem_hsr.history import record_history
from genem_hsr.skills import MockRobotSkillInterface, HSRRobotSkillInterface, HardwareDisabledError


def nod():
    return OfflineGenerator().generate('Nod')


@pytest.mark.parametrize('encode', [json.dumps, yaml.safe_dump])
def test_parse_valid(encode):
    assert parse_behavior(encode(nod())) == nod()


@pytest.mark.parametrize('text', ['{', '', 'null', '[]', 'behavior: null',
    '!!python/object/apply:os.system ["echo forbidden"]',
    '{"behavior": 1, "behavior": 2}', 'a: &a [*a]', 'a: 1\na: 2'])
def test_bad_encoding(text):
    with pytest.raises(BehaviorError):
        parse_behavior(text)


def test_oversize_and_depth():
    for text in (' ' * 32769, '[' * 1500 + '0' + ']' * 1500):
        with pytest.raises(BehaviorError):
            parse_behavior(text)


@pytest.mark.parametrize('value', [-1, 0, 0.31, float('nan'), float('inf'), 10**500, True, '0.1', None])
def test_bad_amplitude(value):
    plan = nod()
    plan['behavior']['sequence'][0]['parameters']['amplitude'] = value
    with pytest.raises(BehaviorError):
        validate_behavior(plan)


@pytest.mark.parametrize('value', [0, 5, 1.5, True])
def test_repetitions(value):
    plan = nod()
    plan['behavior']['sequence'][0]['parameters']['repetitions'] = value
    with pytest.raises(BehaviorError):
        validate_behavior(plan)


@pytest.mark.parametrize('skill,params', [('eval', {}), ('base_rotate', {'angle': 0.1}),
    ('look_direction', {'yaw': 1, 'pitch': 0}), ('look_at', {'target': 'unknown'}),
    ('wait', {'duration': -1}), ('speak', {'text': 'a' * 201}),
    ('head_nod', {'amplitude': 0.1, 'speed': 0, 'repetitions': 1}),
    ('head_shake', {'amplitude': 0.1, 'speed': 2, 'repetitions': 1}),
    ('look_direction', {'yaw': 0}), ('wait', {'duration': 1, 'code': 'x'})])
def test_invalid_skill_params(skill, params):
    plan = {'behavior': {'name': 'bad', 'sequence': [{'skill': skill, 'parameters': params}]}}
    with pytest.raises(BehaviorError):
        validate_behavior(plan)


def test_duration_and_step_limit():
    plan = nod()
    item = plan['behavior']['sequence'][0]
    item['parameters'] = {'amplitude': 0.3, 'speed': 0.05, 'repetitions': 4}
    with pytest.raises(BehaviorError, match='duration'):
        validate_behavior(plan)
    plan = nod()
    plan['behavior']['sequence'] *= 21
    with pytest.raises(BehaviorError, match='20 steps'):
        validate_behavior(plan)


def test_revalidation_before_any_side_effect():
    plan = nod()
    plan['behavior']['sequence'].append({'skill': 'forbidden', 'parameters': {}})
    adapter = MockRobotSkillInterface(output=lambda _: None)
    with pytest.raises(BehaviorError):
        BehaviorExecutor(adapter).execute(plan)
    assert adapter.events == []


@pytest.mark.parametrize('instruction', SCENARIOS.values())
def test_scenarios_execute_in_order(instruction):
    plan = OfflineGenerator().generate(instruction)
    adapter = MockRobotSkillInterface(output=lambda _: None)
    BehaviorExecutor(adapter).execute(plan)
    assert adapter.events == plan['behavior']['sequence']


def test_feedback_immutable_and_logged(tmp_path):
    gen = OfflineGenerator()
    old = nod()
    original = copy.deepcopy(old)
    updated = gen.generate('Nod', old, 'slower, friendlier and more enthusiastic')
    assert old == original
    seq = updated['behavior']['sequence']
    assert seq[0]['skill'] == 'look_at'
    assert seq[1]['parameters']['speed'] < 0.5
    assert seq[1]['parameters']['repetitions'] == 2
    path = tmp_path / 'history.jsonl'
    record_history(path, 'Nod', old, 'slower', updated)
    row = json.loads(path.read_text())
    assert row['generated_behavior'] == old
    assert row['updated_behavior'] == updated
    assert row['human_feedback'] == 'slower'
    assert row['timestamp'].endswith('+00:00')


def test_feedback_over_limit_rejected():
    plan = nod()
    plan['behavior']['sequence'][0]['parameters']['repetitions'] = 4
    with pytest.raises(BehaviorError):
        OfflineGenerator().generate('Nod', plan, 'more enthusiastic')


def test_unconfigured_hsr_disabled_even_with_confirmation():
    with pytest.raises(HardwareDisabledError):
        HSRRobotSkillInterface()
    adapter = object.__new__(HSRRobotSkillInterface)
    with pytest.raises(HardwareDisabledError):
        BehaviorExecutor(adapter).execute(nod(), hardware_confirmed=True)


def api(monkeypatch, response=None):
    monkeypatch.setenv('GENEM_API_BASE', 'https://provider.example/v1')
    monkeypatch.setenv('GENEM_MODEL', 'test-model')
    monkeypatch.setenv('GENEM_API_KEY', 'fake-test-key')
    transport = Mock()
    transport.post.return_value.status_code = 200
    transport.post.return_value.json.return_value = response or {
        'choices': [{'message': {'content': json.dumps(nod())}}]}
    return APIBehaviorGenerator(transport), transport


def test_api_mocked_without_real_key(monkeypatch):
    gen, transport = api(monkeypatch)
    assert gen.generate('Nod') == nod()
    kwargs = transport.post.call_args.kwargs
    assert kwargs['allow_redirects'] is False
    assert kwargs['timeout'] == (10, 45)
    assert 'fake-test-key' not in json.dumps(kwargs['json'])
    gen.generate('Nod', nod(), 'slower')
    body = json.loads(transport.post.call_args.kwargs['json']['messages'][1]['content'])
    assert body['previous'] == nod() and body['feedback'] == 'slower'


def test_missing_credentials(monkeypatch):
    for key in ('GENEM_API_BASE', 'GENEM_MODEL', 'GENEM_API_KEY'):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(BehaviorError):
        APIBehaviorGenerator()


@pytest.mark.parametrize('failure', ['timeout', 'http', 'malformed', 'invalid_behavior'])
def test_api_failures(monkeypatch, failure):
    gen, transport = api(monkeypatch)
    if failure == 'timeout':
        transport.post.side_effect = requests.Timeout('sensitive detail')
    elif failure == 'http':
        transport.post.return_value.status_code = 302
    elif failure == 'malformed':
        transport.post.return_value.json.return_value = {'choices': []}
    else:
        transport.post.return_value.json.return_value = {'choices': [{'message': {'content': '{}'}}]}
    with pytest.raises(BehaviorError):
        gen.generate('Nod')


def test_api_rejects_remote_plain_http(monkeypatch):
    api(monkeypatch)
    monkeypatch.setenv('GENEM_API_BASE', 'http://provider.example/v1')
    with pytest.raises(BehaviorError):
        APIBehaviorGenerator()
