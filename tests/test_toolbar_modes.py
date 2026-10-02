import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from voiceinput.ui.control_bar import ControlBar
from voiceinput.app.lifecycle import State
from voiceinput.config.preferences import save_preferences
from voiceinput.config.loader import ConfigStore


@pytest.fixture
def bar(monkeypatch):
    app = QApplication.instance() or QApplication([])
    widget = ControlBar(auto_hide=True)
    widget.show()
    app.processEvents()
    monkeypatch.setattr(widget, "underMouse", lambda: False)
    yield widget
    widget.close()


def test_idle_collapse_and_busy_expand(bar):
    full_width = bar.width()
    bar.collapse()
    assert bar.collapsed and not bar.body.isVisible() and bar.handle.isVisible()
    assert bar.width() < full_width
    bar.update_status(State.RECORDING, "日常输入", "direct", elapsed=12)
    assert not bar.collapsed and bar.body.isVisible()
    assert "12" in bar.status.text()
    assert "直接" in bar.mode.text()
    assert not bar.hide_timer.isActive()
    bar.collapse()
    assert not bar.collapsed
    bar.update_status(State.IDLE, "日常输入", "direct")
    assert bar.hide_timer.isActive()


@pytest.mark.parametrize("state", [State.PROCESSING, State.REVIEWING, State.COMMITTING, State.MODEL_REQUIRED, State.MODEL_DOWNLOADING])
def test_busy_states_never_collapse(bar, state):
    bar.update_status(state, "日常输入", "review")
    bar.collapse()
    assert not bar.collapsed


def test_hover_and_drag_prevent_hide(bar, monkeypatch):
    monkeypatch.setattr(bar, "underMouse", lambda: True)
    bar.collapse()
    assert not bar.collapsed
    monkeypatch.setattr(bar, "underMouse", lambda: False)
    bar.drag_offset = object()
    bar.collapse()
    assert not bar.collapsed
    bar.drag_offset = None
    bar.collapse()
    bar.handle.click()
    assert not bar.collapsed


def test_orientation_and_top_are_independent(bar):
    bar.apply_preferences(always_on_top=False, auto_hide=True, orientation="vertical")
    assert bar.height() > bar.width()
    assert not bar.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert bar.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    requested = []
    bar.orientation_changed.connect(requested.append)
    bar.orientation_button.click()
    assert requested == ["horizontal"]
    bar.collapse()
    bar.apply_preferences(always_on_top=True, auto_hide=False, orientation="horizontal")
    assert not bar.collapsed and not bar.hide_timer.isActive()
    assert bar.width() > bar.height()
    assert bar.windowFlags() & Qt.WindowType.WindowStaysOnTopHint


def test_toolbar_preferences_persist(store, root):
    prefs = {"always_on_top": False, "auto_hide": True, "orientation": "vertical"}
    save_preferences(store, {"toolbar": prefs})
    assert ConfigStore(root).data["toolbar"] == prefs
    with pytest.raises(ValueError):
        save_preferences(store, {"toolbar": {"orientation": "diagonal"}})
    assert ConfigStore(root).data["toolbar"] == prefs
