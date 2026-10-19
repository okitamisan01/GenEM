"""Strict, bounded JSON/YAML behavior language. Limits are MOCK ONLY."""
import copy
import json
import math
import yaml


class BehaviorError(ValueError):
    pass


# Numeric parameters: inclusive ranges, radians / radians per second / seconds.
SKILLS = {
    'head_nod': {'amplitude': (0.01, 0.3), 'speed': (0.05, 0.8), 'repetitions': (1, 4)},
    'head_shake': {'amplitude': (0.01, 0.3), 'speed': (0.05, 0.8), 'repetitions': (1, 4)},
    'look_direction': {'yaw': (-0.5, 0.5), 'pitch': (-0.3, 0.3)},
    'look_at': {'target': ('person', 'front')},
    'wait': {'duration': (0, 10)},
    'speak': {'text': 'text'},
}
MAX_DURATION = 60.0
MAX_STEPS = 20
MAX_BYTES = 32768


class UniqueLoader(yaml.SafeLoader):
    """Refuse aliases and repeated mapping keys to avoid ambiguous plans."""
    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise BehaviorError('YAML aliases are not allowed')
        return super().compose_node(parent, index)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if not isinstance(key, str) or key in result:
            raise BehaviorError('Mapping keys must be unique strings')
        result[key] = value
    return result


def unique_mapping(loader, node):
    return unique_pairs([(loader.construct_object(k), loader.construct_object(v))
                         for k, v in node.value])


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def parse_behavior(text):
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_BYTES:
        raise BehaviorError('Behavior must be text of at most 32768 bytes')
    try:
        try:
            result = json.loads(text, object_pairs_hook=unique_pairs)
        except json.JSONDecodeError:
            result = yaml.load(text, Loader=UniqueLoader)
        return validate_behavior(result)
    except (yaml.YAMLError, RecursionError, TypeError) as exc:
        raise BehaviorError('Invalid behavior encoding') from exc


def exact_keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise BehaviorError(f'{label} requires exactly {sorted(keys)}')


def step_duration(skill, p):
    if skill in ('head_nod', 'head_shake'):
        # center -> +amplitude -> -amplitude -> center for each repetition.
        return 4 * p['amplitude'] * p['repetitions'] / p['speed']
    if skill == 'wait':
        return p['duration']
    if skill == 'speak':
        return 2 + len(p['text']) / 10
    return 3.0  # Mock gaze duration, not a hardware timing guarantee.


def validate_behavior(value):
    exact_keys(value, ['behavior'], 'root')
    b = value['behavior']
    exact_keys(b, ['name', 'sequence'], 'behavior')
    if not isinstance(b['name'], str) or not 1 <= len(b['name']) <= 80:
        raise BehaviorError('name must have 1..80 characters')
    steps = b['sequence']
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise BehaviorError('sequence must have 1..20 steps')
    total = 0.0
    for step in steps:
        exact_keys(step, ['skill', 'parameters'], 'step')
        skill, p = step['skill'], step['parameters']
        if not isinstance(skill, str) or skill not in SKILLS:
            raise BehaviorError(f'Unknown skill: {skill!r}')
        exact_keys(p, SKILLS[skill], skill)
        for key, rule in SKILLS[skill].items():
            val = p[key]
            if rule == 'text':
                if not isinstance(val, str) or not 1 <= len(val) <= 200:
                    raise BehaviorError('speech must have 1..200 characters')
            elif key == 'target':
                if not isinstance(val, str) or val not in rule:
                    raise BehaviorError('Unknown mock gaze target')
            else:
                if type(val) not in (int, float) or not math.isfinite(val):
                    raise BehaviorError(f'{key} must be a finite number')
                if not rule[0] <= val <= rule[1]:
                    raise BehaviorError(f'{key} outside mock range {rule}')
                if key == 'repetitions' and type(val) is not int:
                    raise BehaviorError('repetitions must be an integer')
        total += step_duration(skill, p)
    if total > MAX_DURATION:
        raise BehaviorError(f'Estimated duration {total:.2f}s exceeds {MAX_DURATION}s')
    return copy.deepcopy(value)
