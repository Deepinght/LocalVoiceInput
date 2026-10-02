import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from voiceinput.ui.windows import CandidateWindow
from voiceinput.engine.context import TextContext


def test_explicit_confirmation_only(root):
    app = QApplication.instance() or QApplication([])
    window = CandidateWindow(TextContext("原始", "候选", "normal"), root)
    confirmed, cancelled = [], []
    window.confirmed.connect(confirmed.append)
    window.cancelled.connect(cancelled.append)
    window.editor.setPlainText("编辑后")
    app.processEvents()
    assert confirmed == []
    window.reject()
    assert cancelled == ["编辑后"] and confirmed == []
    other = CandidateWindow(TextContext("原始", "候选", "normal"), root)
    other.confirmed.connect(confirmed.append)
    other.editor.setPlainText("最终文字")
    other.confirm()
    other.confirm()
    assert confirmed == ["最终文字"]
