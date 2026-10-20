"""Robot-independent skill interface; the HSR boundary fails closed."""
from abc import ABC, abstractmethod
import copy


class RobotSkillInterface(ABC):
    @abstractmethod
    def head_nod(self, amplitude, speed, repetitions): ...
    @abstractmethod
    def head_shake(self, amplitude, speed, repetitions): ...
    @abstractmethod
    def look_direction(self, yaw, pitch): ...
    @abstractmethod
    def look_at(self, target): ...
    @abstractmethod
    def wait(self, duration): ...
    @abstractmethod
    def speak(self, text): ...


class MockRobotSkillInterface(RobotSkillInterface):
    """Record logical actions immediately; no perception, sleep or actuator I/O."""
    def __init__(self, output=print):
        self.events = []
        self.output = output

    def _record(self, skill, parameters):
        self.events.append({'skill': skill, 'parameters': copy.deepcopy(parameters)})
        self.output(f'MOCK {skill}({parameters})')

    def head_nod(self, amplitude, speed, repetitions):
        self._record('head_nod', dict(amplitude=amplitude, speed=speed, repetitions=repetitions))

    def head_shake(self, amplitude, speed, repetitions):
        self._record('head_shake', dict(amplitude=amplitude, speed=speed, repetitions=repetitions))

    def look_direction(self, yaw, pitch):
        self._record('look_direction', dict(yaw=yaw, pitch=pitch))

    def look_at(self, target):
        self._record('look_at', dict(target=target))

    def wait(self, duration):
        self._record('wait', dict(duration=duration))

    def speak(self, text):
        self._record('speak', dict(text=text))


class HardwareDisabledError(RuntimeError):
    pass


