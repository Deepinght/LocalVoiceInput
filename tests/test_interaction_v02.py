import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from types import SimpleNamespace
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from voiceinput.app.lifecycle import State
from voiceinput.engine.context import AsrResult, TextContext
from voiceinput.config.loader import ConfigStore, atomic_yaml
from voiceinput.config.preferences import save_preferences


@pytest.fixture
def controller(root, monkeypatch):
    from voiceinput.app.main import Controller
    from voiceinput.context.hotkey import Hotkey, CancelHotkey
    from voiceinput.audio.recorder import Recorder
    from voiceinput.common.sounds import SoundCues
    import win32gui, win32process
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(Hotkey, "configure", lambda self, text: None)
    monkeypatch.setattr(Hotkey, "held", lambda self: False)
    monkeypatch.setattr(CancelHotkey, "enable", lambda self, enabled: enabled)
    monkeypatch.setattr(SoundCues, "play", lambda *args: None)
    monkeypatch.setattr(Recorder, "start", lambda *args: None)
    monkeypatch.setattr(Recorder, "stop", lambda *args: [0.1] * 16000)
    monkeypatch.setattr(Recorder, "cancel", lambda *args: None)
    monkeypatch.setattr(win32gui, "IsWindow", lambda hwnd: True)
    monkeypatch.setattr(win32process, "GetWindowThreadProcessId", lambda hwnd: (1, 222))
    current = Controller(app, root)
    current.poll.stop()
    current.watcher.stop()
    current.external_window = lambda: (111, 222, "Test editor")
    current.manager = lambda: SimpleNamespace(is_installed=lambda: True, get_model_path=lambda: root)
    current.pending_jobs = []
    current.job = lambda fn, success, failure: current.pending_jobs.append((success, failure))
    current.scheduled = []
    monkeypatch.setattr("voiceinput.app.main.QTimer.singleShot", lambda delay, callback: current.scheduled.append(callback))
    current.outputs = []
    from voiceinput.output.windows import OutputResult
    def commit(text, *args, **kwargs):
        current.outputs.append(text)
        return OutputResult(True)
    monkeypatch.setattr("voiceinput.output.windows.commit_to_target", commit)
    yield current
    current.session.state = State.IDLE
    current.bar.close()
    if current.candidate:
        current.candidate.finished_commit = True
        current.candidate.close()
    current.tray.hide()
    app.removeNativeEventFilter(current.hotkey)
    app.removeNativeEventFilter(current.escape)
    current.history.db.close()


def recognize(controller, text="测试文字"):
    controller.start_recording(True)
    controller.stop_recording()
    controller.recognized(AsrResult(text))


def test_toggle_does_not_stop_on_release(controller):
    controller.hotkey_pressed()
    assert controller.session.state == State.RECORDING
    controller.poll_recording()
    assert controller.session.state == State.RECORDING
    controller.hotkey_pressed()
    assert controller.session.state == State.PROCESSING
    assert len(controller.pending_jobs) == 1


def test_hold_stops_on_release(controller):
    controller.store.data["hotkey"]["mode"] = "hold"
    controller.hotkey_pressed()
    controller.poll_recording()
    assert controller.session.state == State.PROCESSING


def test_cancel_recording_never_decodes(controller):
    controller.hotkey_pressed()
    controller.cancel_current()
    assert controller.session.state == State.IDLE
    assert not controller.pending_jobs and not controller.outputs


def test_cancel_processing_discards_late_result(controller):
    controller.start_recording(True)
    controller.stop_recording()
    controller.cancel_current()
    controller.hotkey_pressed()
    assert len(controller.pending_jobs) == 1
    controller.recognized(AsrResult("迟到的结果"))
    assert controller.session.state == State.IDLE
    assert not controller.outputs and not controller.candidate
    assert controller.history.recent() == []


def test_review_only_commits_edited_text_after_confirm(controller):
    recognize(controller)
    assert controller.outputs == []
    controller.candidate.editor.setPlainText("编辑后的内容")
    controller.candidate.confirm()
    controller.candidate.confirm()
    assert len(controller.scheduled) == 1
    controller.scheduled.pop()()
    assert controller.outputs == ["编辑后的内容"]
    assert controller.history.recent()[0][4:6] == ("编辑后的内容", 1)


def test_review_cancel_produces_no_output(controller):
    recognize(controller)
    controller.candidate.reject()
    assert controller.outputs == []
    assert controller.history.recent()[0][5] == 0


def test_direct_is_opt_in_and_no_candidate_on_success(controller):
    assert controller.store.data["output"]["mode"] == "review"
    controller.store.data["output"]["mode"] = "direct"
    recognize(controller)
    assert controller.session.state == State.COMMITTING
    assert controller.candidate is None
    controller.scheduled.pop()()
    assert controller.outputs == ["测试文字。"]
    assert controller.history.recent()[0][5] == 1


def test_direct_changed_target_retains_copyable_candidate(controller):
    controller.store.data["output"]["mode"] = "direct"
    recognize(controller)
    controller.external_window = lambda: (333, 444, "Other editor")
    controller.scheduled.pop()()
    assert controller.outputs == []
    assert controller.session.state == State.REVIEWING
    assert controller.candidate.editor.toPlainText() == "测试文字。"
    assert not controller.candidate.confirm_button.isEnabled()


def test_direct_output_error_no_automatic_retry(controller, monkeypatch):
    controller.store.data["output"]["mode"] = "direct"
    def failure(*args, **kwargs):
        raise RuntimeError("partial delivery")
    monkeypatch.setattr("voiceinput.output.windows.commit_to_target", failure)
    recognize(controller)
    controller.scheduled.pop()()
    assert controller.session.state == State.REVIEWING
    assert "partial delivery" in controller.candidate.notice.text()
    assert not controller.scheduled


def test_empty_recognition_never_commits(controller):
    controller.store.data["output"]["mode"] = "direct"
    recognize(controller, "  ")
    assert controller.session.state == State.IDLE
    assert not controller.outputs and not controller.scheduled


def test_preferences_survive_restart(store, root):
    save_preferences(store, {"candidate": {"font_size": 26, "always_on_top": False}, "output": {"mode": "direct"}})
    restored = ConfigStore(root)
    assert restored.data["candidate"]["font_size"] == 26
    assert restored.data["candidate"]["always_on_top"] is False
    assert restored.data["output"]["mode"] == "direct"


def test_old_config_gets_safe_defaults(root):
    from voiceinput.config.loader import read_yaml
    path = root / "config/default.yaml"
    data = read_yaml(path)
    data["hotkey"].pop("mode")
    data["output"].pop("mode")
    data["candidate"] = {"require_confirmation": True}
    del data["toolbar"], data["sounds"]
    atomic_yaml(path, data)
    store = ConfigStore(root)
    assert store.data["hotkey"]["mode"] == "toggle"
    assert store.data["output"]["mode"] == "review"
    assert store.data["candidate"]["font_size"] == 18


def test_candidate_controls_preserve_text_and_original(controller):
    recognize(controller)
    candidate = controller.candidate
    candidate.editor.setPlainText("我的修改")
    candidate.font_size.setValue(24)
    assert candidate.editor.toPlainText() == "我的修改"
    assert candidate.editor.font().pointSize() == 24
    candidate.raw_button.click()
    assert candidate.editor.toPlainText() == "测试文字"
    candidate.restore_button.click()
    assert candidate.editor.toPlainText() == "测试文字。"
    assert candidate.ctx.raw_text == "测试文字"
    assert not controller.outputs


def test_toolbar_does_not_accept_focus_and_displays_direct_mode(controller):
    assert controller.bar.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    controller.toggle_output_mode()
    assert "直接上屏" in controller.bar.mode.text()
    controller.start_recording(False)
    assert controller.bar.record.text() == "结束录音"
    assert not controller.bar.settings.isEnabled()


def test_toolbar_controls_save_and_tray_expands(controller):
    controller.bar.orientation_button.click()
    controller.bar.auto_hide_button.click()
    assert controller.store.data["toolbar"]["orientation"] == "vertical"
    assert controller.store.data["toolbar"]["auto_hide"] is True
    controller.bar.pin.click()
    assert controller.store.data["toolbar"]["always_on_top"] is False
    assert not controller.bar.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert controller.bar.orientation == "vertical"
    controller.bar.hide()
    controller.show_bar()
    assert controller.bar.isVisible() and not controller.bar.collapsed
