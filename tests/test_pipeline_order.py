from voiceinput.engine.pipeline import Pipeline
from voiceinput.engine.context import AsrResult


def test_baseline(store):
    ctx = Pipeline(store).process(AsrResult("氮气流量一百标方每小时温度五百度"), "science")
    assert ctx.text == "N₂流量为100 Nm³/h，温度为500 ℃。"
    filters = [e.component for e in ctx.trace if e.stage == "filters" and e.rule_id is None]
    assert filters == store.data["engine"]["filters"]


def test_raw(store):
    assert Pipeline(store).process(AsrResult("  氮气一百  "), "raw").text == "氮气一百"
