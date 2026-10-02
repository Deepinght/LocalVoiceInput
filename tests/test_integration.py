from voiceinput.app.lifecycle import State, Session
from voiceinput.history.repository import History
from voiceinput.engine.context import AsrResult
from voiceinput.engine.pipeline import Pipeline
from voiceinput.feedback.engine import remember


def test_review_cancel_history_and_learning(store, root):
    session = Session()
    assert session.transition(State.IDLE, State.RECORDING)
    assert not session.transition(State.IDLE, State.RECORDING)
    assert session.transition(State.RECORDING, State.PROCESSING)
    ctx = Pipeline(store).process(AsrResult("树据分析"), "science")
    history = History(root / "data/history.sqlite3")
    row = history.add(ctx)
    history.finish(row, "数据分析。", False)
    assert history.recent()[0][5] == 0
    remember(root / "dictionaries/user.yaml", "树据分析", "数据分析", "science")
    store.reload()
    assert Pipeline(store).process(AsrResult("树据分析"), "science").text == "数据分析。"
    history.db.close()
