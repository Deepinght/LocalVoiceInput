import ctypes
from ctypes import wintypes
from PySide6.QtCore import QObject, Signal, QAbstractNativeEventFilter


def parse_hotkey(text):
    parts = text.upper().split("+")
    modifiers = {"CTRL": 2, "ALT": 1, "SHIFT": 4, "WIN": 8}
    keys = {"SPACE": 0x20, **{f"F{i}": 0x6F+i for i in range(1, 25)}}
    if len(parts) < 2 or any(x not in modifiers for x in parts[:-1]) or parts[-1] not in keys:
        raise ValueError("快捷键格式：Ctrl+Alt+Space 或 Ctrl+Alt+F9")
    flags = 0
    for part in parts[:-1]:
        flags |= modifiers[part]
    return flags, keys[parts[-1]]


class Hotkey(QAbstractNativeEventFilter):
    def __init__(self, callback, text):
        super().__init__()
        self.callback = callback
        self.registered = False
        self.key = 0x20
        self.text = None
        self.configure(text)

    def configure(self, text):
        flags, key = parse_hotkey(text)
        old_text = self.text
        if self.registered:
            ctypes.windll.user32.UnregisterHotKey(None, 0xA431)
        if not ctypes.windll.user32.RegisterHotKey(None, 0xA431, flags | 0x4000, key):
            self.registered = False
            if old_text:
                old_flags, old_key = parse_hotkey(old_text)
                self.registered = bool(ctypes.windll.user32.RegisterHotKey(None, 0xA431, old_flags | 0x4000, old_key))
            raise RuntimeError("快捷键已被占用，请在设置中更换")
        self.registered = True
        self.key = key
        self.text = text

    def nativeEventFilter(self, event_type, message):
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == 0x0312 and msg.wParam == 0xA431:
            self.callback()
            return True, 0
        return False, 0

    def held(self):
        return bool(ctypes.windll.user32.GetAsyncKeyState(self.key) & 0x8000)

    def close(self):
        if self.registered:
            ctypes.windll.user32.UnregisterHotKey(None, 0xA431)
            self.registered = False


class CancelHotkey(QAbstractNativeEventFilter):
    """Reserve Escape only during recording/recognition, not while idle."""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.registered = False

    def enable(self, enabled):
        if enabled and not self.registered:
            self.registered = bool(ctypes.windll.user32.RegisterHotKey(None, 0xA432, 0x4000, 0x1B))
        elif not enabled and self.registered:
            ctypes.windll.user32.UnregisterHotKey(None, 0xA432)
            self.registered = False
        return self.registered

    def nativeEventFilter(self, event_type, message):
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == 0x0312 and msg.wParam == 0xA432:
            self.callback()
            return True, 0
        return False, 0

    def close(self):
        self.enable(False)
