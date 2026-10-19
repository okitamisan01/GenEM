"""Revalidate the entire plan before any adapter side effect."""
from .behavior import validate_behavior
from .skills import HSRRobotSkillInterface, HardwareDisabledError


class BehaviorExecutor:
    def __init__(self, adapter):
        self.adapter = adapter

    def execute(self, behavior, *, hardware_confirmed=False):
        plan = validate_behavior(behavior)
        if isinstance(self.adapter, HSRRobotSkillInterface):
            raise HardwareDisabledError('HSR execution disabled even with confirmation')
        for step in plan['behavior']['sequence']:
            getattr(self.adapter, step['skill'])(**step['parameters'])
        return plan
