import os
import win32gui
import win32process


def foreground():
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd or not win32gui.IsWindow(hwnd):
        raise RuntimeError("没有可用的前台窗口")
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    if pid == os.getpid():
        raise RuntimeError("请先将光标放入目标程序，再按语音快捷键")
    return hwnd, win32gui.GetWindowText(hwnd)
