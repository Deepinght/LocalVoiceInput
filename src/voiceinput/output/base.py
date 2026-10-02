from typing import Protocol
from voiceinput.output.windows import OutputResult


class TextOutput(Protocol):
    def commit(self, text: str) -> OutputResult: ...
