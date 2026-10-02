"""Check mouse interaction with our own toolbar against a disposable editor."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import win32api
import win32con
import win32gui
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from voiceinput.ui.control_bar import ControlBar
from voiceinput.app.lifecycle import State

app = QApplication([])
bar = ControlBar()
clicks = []
bar.record_requested.connect(lambda: clicks.append("record"))
bar.update_status(State.IDLE, "普通", "review")
cursor = win32gui.GetCursorPos()
with tempfile.TemporaryDirectory(prefix="voiceinput-focus-") as temporary:
    folder = Path(temporary)
    child = subprocess.Popen([sys.executable, str(Path(__file__).with_name("verify_windows_output.py")), "--fixture", temporary])
    try:
        for _ in range(100):
            if (folder / "ready.json").exists():
                break
            QTest.qWait(50)
        info = json.loads((folder / "ready.json").read_text())
        bar.move(700, 100)
        bar.show()
        QTest.qWait(150)
        if win32gui.GetForegroundWindow() != info["hwnd"]:
            win32gui.SetWindowPos(info["hwnd"], win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
            target_rect = win32gui.GetWindowRect(info["hwnd"])
            win32api.SetCursorPos((target_rect[0]+80, target_rect[1]+80))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
        QTest.qWait(100)
        before = win32gui.GetForegroundWindow()
        rect = win32gui.GetWindowRect(int(bar.winId()))
        point = bar.record.mapTo(bar, bar.record.rect().center())
        scale = bar.devicePixelRatioF()
        win32api.SetCursorPos((rect[0]+round(point.x()*scale), rect[1]+round(point.y()*scale)))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
        QTest.qWait(200)
        assert clicks == ["record"], clicks
        after = win32gui.GetForegroundWindow()
        assert after == before == info["hwnd"], {"before_class": win32gui.GetClassName(before), "after_class": win32gui.GetClassName(after), "before_is_editor": before == info["hwnd"], "after_is_toolbar": after == int(bar.winId())}
        print("Native mouse click: start signal received; external editor kept foreground PASS")
        for orientation in ("vertical", "horizontal"):
            bar.apply_preferences(always_on_top=True, auto_hide=True, orientation=orientation)
            # Move off the bar, then test the genuine delayed collapse/hover path.
            target_rect = win32gui.GetWindowRect(info["hwnd"])
            win32api.SetCursorPos((target_rect[0]+80, target_rect[1]+80))
            QTest.qWait(2800)
            assert bar.collapsed, orientation
            rect = win32gui.GetWindowRect(int(bar.winId()))
            win32api.SetCursorPos((rect[0]+20, rect[1]+20))
            QTest.qWait(150)
            assert not bar.collapsed, orientation
            rect = win32gui.GetWindowRect(int(bar.winId()))
            point = bar.record.mapTo(bar, bar.record.rect().center())
            win32api.SetCursorPos((rect[0]+round(point.x()*scale), rect[1]+round(point.y()*scale)))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
            QTest.qWait(150)
            assert win32gui.GetForegroundWindow() == info["hwnd"], orientation
            print(f"{orientation}: timed collapse, hover expansion and focus-preserving click PASS")
        assert clicks == ["record"] * 3
    finally:
        bar.close()
        win32api.SetCursorPos(cursor)
        (folder / "stop").touch()
        child.wait(timeout=10)
