"""Explicit compatibility test in a new, disposable Word document."""
import ctypes
import time
import pythoncom
import win32com.client
import win32process
import win32gui
from PySide6.QtWidgets import QApplication
from voiceinput.output.windows import commit_to_target

app = QApplication([])
pythoncom.OleInitialize()
word = None
try:
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = True
    doc = word.Documents.Add()
    doc.Activate()
    word.Activate()
    time.sleep(0.5)
    hwnd = win32gui.GetAncestor(word.ActiveWindow.Hwnd, 2)
    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
    text = "VoiceInput 验证：N₂流量100 Nm³/h，温度500 ℃。"
    result = commit_to_target(text, hwnd, pid)
    assert result.success, result
    time.sleep(0.5)
    actual = doc.Content.Text.rstrip("\r\x07")
    assert actual == text, repr(actual)
    print("Word SendInput PASS")
    result = commit_to_target("剪贴板回退验证。", hwnd, pid, primary="clipboard")
    assert result.success and not result.message, result
    time.sleep(0.5)
    assert doc.Content.Text.rstrip("\r\x07") == text + "剪贴板回退验证。"
    print("Word Clipboard + restore PASS")
    doc.Close(False)
finally:
    if word:
        word.Quit(False)
    ctypes.windll.ole32.OleUninitialize()
