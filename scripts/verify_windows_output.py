"""Send only synthetic test text to a dedicated disposable fixture window."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def fixture(folder):
    import win32gui
    import win32con
    import ctypes
    hwnd = win32gui.CreateWindowEx(0, "EDIT", "", win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE | win32con.ES_MULTILINE, 100, 100, 550, 200, 0, 0, 0, None)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass  # The focus test can activate this disposable window with a click.
    win32gui.SetFocus(hwnd)
    ctypes.windll.user32.AllowSetForegroundWindow(-1)
    folder = Path(folder)
    (folder / "ready.json").write_text(json.dumps({"hwnd": hwnd, "pid": os.getpid()}))
    deadline = time.monotonic()+30
    while time.monotonic() < deadline:
        win32gui.PumpWaitingMessages()
        (folder / "text.txt").write_text(win32gui.GetWindowText(hwnd), encoding="utf-8")
        if (folder / "stop").exists():
            break
        time.sleep(0.02)
    win32gui.DestroyWindow(hwnd)


def verify():
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    import pythoncom
    import ctypes
    import win32clipboard
    import win32api
    import win32gui
    import win32con
    from voiceinput.output.windows import commit_to_target, INPUT
    pythoncom.OleInitialize()
    try:
        with tempfile.TemporaryDirectory(prefix="voiceinput-test-") as temporary:
            folder = Path(temporary)
            child = subprocess.Popen([sys.executable, __file__, "--fixture", temporary])
            try:
                for _ in range(100):
                    if (folder / "ready.json").exists():
                        break
                    time.sleep(0.05)
                info = json.loads((folder / "ready.json").read_text())
                time.sleep(0.3)
                if win32gui.GetForegroundWindow() != info["hwnd"]:
                    cursor = win32gui.GetCursorPos()
                    win32gui.SetWindowPos(info["hwnd"], win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
                    rect = win32gui.GetWindowRect(info["hwnd"])
                    win32api.SetCursorPos((rect[0]+80, rect[1]+80))
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
                    time.sleep(0.15)
                    win32api.SetCursorPos(cursor)
                expected = "确认后上屏：N₂，H₂O，500 ℃。😀"
                result = commit_to_target(expected, info["hwnd"], info["pid"])
                assert result.success, result
                time.sleep(0.5)
                actual = (folder / "text.txt").read_text(encoding="utf-8")
                print("actual:", repr(actual), "result:", result)
                assert actual == expected, (actual, expected)
                print("SendInput Unicode + surrogate pairs PASS; INPUT size", ctypes.sizeof(INPUT))
                # The original clipboard object remains preserved by ClipboardOutput.
                result = commit_to_target("剪贴板回退", info["hwnd"], info["pid"], primary="clipboard")
                assert result.success, result
                time.sleep(0.5)
                assert (folder / "text.txt").read_text(encoding="utf-8") == expected + "剪贴板回退"
                print("Clipboard paste PASS; warning:", result.message or "none")
                assert not result.message
            finally:
                (folder / "stop").touch()
                child.wait(timeout=10)
    finally:
        ctypes.windll.ole32.OleUninitialize()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture")
    args = parser.parse_args()
    fixture(args.fixture) if args.fixture else verify()
