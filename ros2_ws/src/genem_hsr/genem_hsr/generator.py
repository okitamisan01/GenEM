"""Replaceable generators: offline fixtures and a generic chat-completions API."""
from abc import ABC, abstractmethod
import copy
import json
import os
from urllib.parse import urlsplit
import requests
from .behavior import SKILLS, BehaviorError, parse_behavior, validate_behavior

SCENARIOS = {
    'nod': 'Nod.',
    'shake_head': 'Shake your head.',
    'become_attentive': 'Become attentive.',
    'acknowledge_person': 'Acknowledge the person.',
    'pay_attention_to_person': 'Pay attention to the person.',
}


def step(skill, **parameters):
    return {'skill': skill, 'parameters': parameters}


class BehaviorGenerator(ABC):
    @abstractmethod
    def generate(self, instruction, previous=None, feedback=None): ...


class OfflineGenerator(BehaviorGenerator):
    """Deterministic demonstration rules; this backend is NOT an LLM."""
    def generate(self, instruction, previous=None, feedback=None):
        if not isinstance(instruction, str) or not instruction.strip():
            raise BehaviorError('Instruction must not be empty')
        if previous is not None:
            plan = validate_behavior(previous)
        else:
            text = instruction.strip().lower()
            nod = step('head_nod', amplitude=0.15, speed=0.5, repetitions=1)
            gaze = step('look_at', target='person')
            if 'shake' in text:
                sequence = [step('head_shake', amplitude=0.15, speed=0.5, repetitions=1)]
            elif 'acknowledge' in text or text.rstrip('!.') in ('hello', 'hi', 'hey'):
                sequence = [gaze, nod]
            elif 'attention' in text:
                sequence = [gaze, step('wait', duration=2.0)]
            elif 'attentive' in text:
                sequence = [step('look_direction', yaw=0.0, pitch=0.0), step('wait', duration=1.0)]
            elif 'nod' in text:
                sequence = [nod]
            else:
                raise BehaviorError('Offline backend supports the five demo scenarios only')
            plan = {'behavior': {'name': instruction[:80], 'sequence': sequence}}
        if feedback:
            text = feedback.lower()
            supported = any(s in text for s in ('slow', 'friend', 'enthusiastic'))
            if not supported:
                raise BehaviorError('Offline feedback supports slower, friendlier, enthusiastic')
            for item in plan['behavior']['sequence']:
                if item['skill'] in ('head_nod', 'head_shake'):
                    if 'slow' in text:
                        item['parameters']['speed'] *= 0.7
                    if 'enthusiastic' in text:
                        item['parameters']['repetitions'] += 1
            if 'friend' in text or 'enthusiastic' in text:
                if not any(s['skill'] == 'look_at' for s in plan['behavior']['sequence']):
                    plan['behavior']['sequence'].insert(0, step('look_at', target='person'))
        return validate_behavior(plan)


class APIBehaviorGenerator(BehaviorGenerator):
    """Generic provider contract, not tied to one vendor SDK.

    POST /chat/completions with messages/model; expect choices[0].message.content
    containing a JSON/YAML behavior. Credentials never enter prompts or logs.
    """
    def __init__(self, transport=None):
        self.base = os.environ.get('GENEM_API_BASE', '').rstrip('/')
        self.model = os.environ.get('GENEM_MODEL', '')
        self.key = os.environ.get('GENEM_API_KEY', '')
        self.transport = transport if transport is not None else requests.Session()
        parsed = urlsplit(self.base)
        if not self.base or not self.model or not self.key:
            raise BehaviorError('Set GENEM_API_BASE, GENEM_MODEL and GENEM_API_KEY')
        if parsed.scheme != 'https' and not (
            parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', '::1')
        ):
            raise BehaviorError('API endpoint requires HTTPS (HTTP allowed only on loopback)')
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise BehaviorError('API base must not contain credentials, query or fragment')

    def generate(self, instruction, previous=None, feedback=None):
        if not isinstance(instruction, str) or not 1 <= len(instruction) <= 4000:
            raise BehaviorError('Instruction must contain 1..4000 characters')
        if feedback is not None and (not isinstance(feedback, str) or len(feedback) > 4000):
            raise BehaviorError('Feedback must be text of at most 4000 characters')
        if previous is not None:
            previous = validate_behavior(previous)
        system = (
            'Create expressive robot behavior as JSON only, no code or Markdown. '
            'Schema: {"behavior":{"name":"name","sequence":'
            '[{"skill":"skill_name","parameters":{}}]}}. '
            'Use exactly the listed parameter names. Angles are radians, speed rad/s. '
            'repetitions is an integer. Limits below apply to mock only. '
            'At most 20 steps, estimated total duration at most 60 seconds. '
            'Nod/shake duration = 4*amplitude*repetitions/speed; gaze=3s; '
            'speech=2+len(text)/10 seconds. Speech text has 1..200 characters. '
            'Allowed skills and parameter bounds: ' + json.dumps(SKILLS)
        )
        payload = {'model': self.model, 'temperature': 0,
                   'messages': [{'role': 'system', 'content': system},
                                {'role': 'user', 'content': json.dumps({
                                    'instruction': instruction, 'previous': previous,
                                    'feedback': feedback})}]}
        try:
            response = self.transport.post(
                self.base + '/chat/completions', json=payload,
                headers={'Authorization': 'Bearer ' + self.key}, timeout=(10, 45),
                allow_redirects=False)
            if response.status_code != 200:
                raise BehaviorError('LLM API returned a non-200 status')
            content = response.json()['choices'][0]['message']['content']
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
            raise BehaviorError('LLM API failed or returned an invalid response') from exc
        return parse_behavior(content)
