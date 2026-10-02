from typing import Protocol
from voiceinput.engine.context import AsrResult


class AsrProvider(Protocol):
    def recognize(self, samples) -> AsrResult: ...
