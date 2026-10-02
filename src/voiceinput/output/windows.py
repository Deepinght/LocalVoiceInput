import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import time
import win32gui
import win32process
import pythoncom
import win32clipboard
import win32con

ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", wintypes.DWORD), ("data", UNION)]


@dataclass
class OutputResult:
    success: bool
    message: str = ""


def send(events):
    array = (INPUT * len(events))(*events)
    function = ctypes.windll.user32.SendInput
    function.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    function.restype = wintypes.UINT
    return function(len(events), array, ctypes.sizeof(INPUT))


def key(vk=0, scan=0, flags=0):
    return INPUT(type=1, ki=KEYBDINPUT(vk, scan, flags, 0, 0))


def restore_target(hwnd, expected_pid):
    if not win32gui.IsWindow(hwnd) or win32process.GetWindowThreadProcessId(hwnd)[1] != expected_pid:
        raise RuntimeError("目标窗口已关闭，请取消本次输入")
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, 9)
    if win32gui.GetForegroundWindow() != hwnd:
        win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.08)
    if win32gui.GetForegroundWindow() != hwnd:
        raise RuntimeError("无法恢复目标窗口，未发送文字。请重新录音")
    if any(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000 for vk in (0x10, 0x11, 0x12, 0x5B, 0x5C)):
        raise RuntimeError("请松开 Ctrl、Alt、Shift、Win 后再次确认")


class SendInputOutput:
    def commit(self, text):
        encoded = text.replace("\r\n", "\n").encode("utf-16-le")
        events = []
        for offset in range(0, len(encoded), 2):
            code = int.from_bytes(encoded[offset:offset+2], "little")
            if code == 10:
                code = 13
            events.extend((key(scan=code, flags=4), key(scan=code, flags=6)))
        if not events:
            return OutputResult(True)
        sent = send(events)
        if sent == len(events):
            return OutputResult(True)
        if sent:
            # Retrying after partial delivery could duplicate text.
            raise RuntimeError("仅发送了部分按键，已停止。请检查目标文本，勿直接重试")
        return OutputResult(False, "SendInput 被目标程序拒绝")


class ClipboardOutput:
    def commit(self, text):
        from PySide6.QtCore import QMimeData, QEventLoop, QTimer
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QImage
        clipboard = QApplication.clipboard()
        current = clipboard.mimeData()
        original = QMimeData()
        # Materialize delayed clipboard formats before changing ownership.
        if current:
            for fmt in current.formats():
                original.setData(fmt, current.data(fmt))
            if current.hasImage():
                original.setImageData(QImage(current.imageData()).copy())
        clipboard.setText(text)
        sequence = ctypes.windll.user32.GetClipboardSequenceNumber()
        events = [key(0x11), key(0x56), key(0x56, flags=2), key(0x11, flags=2)]
        sent = send(events)
        warning = ""
        if sent != 4:
            send([key(0x56, flags=2), key(0x11, flags=2)])
        loop = QEventLoop()
        QTimer.singleShot(500, loop.quit)
        loop.exec()
        try:
            if ctypes.windll.user32.GetClipboardSequenceNumber() == sequence:
                clipboard.setMimeData(original)
                pythoncom.OleFlushClipboard()
            else:
                warning = "剪贴板被其他程序更改，未覆盖新内容。"
        except Exception:
            warning = "无法恢复原剪贴板，当前可能仍是候选文字。"
        return OutputResult(sent == 4, warning or ("" if sent == 4 else "粘贴按键未完整发送，请检查目标文本"))


def commit_to_target(text, hwnd, pid, primary="sendinput", fallback="clipboard"):
    restore_target(hwnd, pid)
    if primary == "clipboard":
        return ClipboardOutput().commit(text)
    result = SendInputOutput().commit(text)
    if not result.success and fallback == "clipboard":
        restore_target(hwnd, pid)
        return ClipboardOutput().commit(text)
    return result
