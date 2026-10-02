from voiceinput.feedback.engine import remember
from voiceinput.engine.context import AsrResult
from voiceinput.engine.pipeline import Pipeline


def test_learning_reload(store, root):
    remember(root / "dictionaries/user.yaml", "树据分析", "数据分析", "science")
    store.reload()
    assert Pipeline(store).process(AsrResult("树据分析"), "science").text == "数据分析。"
    assert list((root / "dictionaries").glob("*.bak"))
