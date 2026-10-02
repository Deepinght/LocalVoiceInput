import pytest
from voiceinput.engine.context import AsrResult
from voiceinput.engine.pipeline import Pipeline


def test_trace_and_immutable_original(store):
    ctx = Pipeline(store).process(AsrResult("氮气"), "science")
    assert ctx.raw_text == "氮气"
    assert any(e.rule_id == "nitrogen" and e.source == "dictionaries/chemistry.yaml" for e in ctx.trace)
    with pytest.raises(AttributeError):
        ctx.raw_text = "changed"
