"""Exercise the real Windows hotkey registration and release polling."""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from voiceinput.context.hotkey import Hotkey
from voiceinput.output.windows import key, send
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--hotkey", default="Ctrl+Alt+F24", help="独立测试键，避免影响已运行程序")
args = parser.parse_args()

app = QApplication([])
observed = []
hotkey = Hotkey(lambda: observed.append("down"), args.hotkey)
app.installNativeEventFilter(hotkey)

def press():
    assert send([key(0x11), key(0x12), key(hotkey.key)]) == 3

def release():
    observed.append("held" if hotkey.held() else "not_held")
    send([key(hotkey.key, flags=2), key(0x12, flags=2), key(0x11, flags=2)])

def finish():
    observed.append("released" if not hotkey.held() else "stuck")
    hotkey.close()
    app.quit()

QTimer.singleShot(200, press)
QTimer.singleShot(600, release)
QTimer.singleShot(900, finish)
try:
    app.exec()
finally:
    send([key(hotkey.key, flags=2), key(0x12, flags=2), key(0x11, flags=2)])
    hotkey.close()
assert observed == ["down", "held", "released"], observed
print("Global hotkey down / held / released PASS")
