from voiceinput.engine.pipeline import Pipeline
from voiceinput.engine.context import AsrResult


def test_profile_controls_chemistry(store):
    pipe = Pipeline(store)
    assert pipe.process(AsrResult("氮气与二氧化碳"), "science").text == "N₂与CO₂。"
    assert pipe.process(AsrResult("氮气与二氧化碳"), "normal").text == "氮气与二氧化碳。"
