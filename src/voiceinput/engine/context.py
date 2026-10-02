from dataclasses import dataclass, field


@dataclass
class AsrResult:
    text: str
    language: str | None = None
    duration_ms: int | None = None
    confidence: float | None = None
    segments: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class TraceEvent:
    stage: str
    component: str
    before: str
    after: str
    rule_id: str | None = None
    source: str | None = None
    details: dict = field(default_factory=dict)


@dataclass
class TextContext:
    raw_text: str
    text: str
    profile: str
    app_name: str | None = None
    language: str | None = None
    trace: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    user_edited_text: str | None = None

    def __setattr__(self, name, value):
        if name == "raw_text" and "raw_text" in self.__dict__:
            raise AttributeError("raw_text 不可覆盖")
        super().__setattr__(name, value)
