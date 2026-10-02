from enum import Enum, auto


class State(Enum):
    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()
    REVIEWING = auto()
    COMMITTING = auto()
    MODEL_REQUIRED = auto()
    MODEL_DOWNLOADING = auto()


class Session:
    def __init__(self):
        self.state = State.IDLE

    def transition(self, expected, target):
        if self.state != expected:
            return False
        self.state = target
        return True
