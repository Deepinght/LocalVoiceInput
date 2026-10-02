"""Render the real candidate widget for visual QA without recording or output."""
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from voiceinput.config.loader import ConfigStore
from voiceinput.engine.pipeline import Pipeline
from voiceinput.engine.context import AsrResult
from voiceinput.ui.windows import CandidateWindow
from voiceinput.ui.windows import SettingsWindow
from voiceinput.ui.profiles import ProfileComparisonDialog
from voiceinput.ui.control_bar import ControlBar
from voiceinput.app.lifecycle import State
from voiceinput.common.paths import initialize_user_files

root = Path(__file__).resolve().parents[1]
app = QApplication([])
app.setFont(QFont("Microsoft YaHei UI", 10))
initialize_user_files(root, root)
store = ConfigStore(root)
ctx = Pipeline(store).process(AsrResult("氮气流量一百标方每小时温度五百度"), "science")
window = CandidateWindow(ctx, root, profile_spec=store.data["profiles"]["science"])
window.show()
app.processEvents()
(root / "docs").mkdir(exist_ok=True)
window.grab().save(str(root / "docs/candidate-preview.png"))
print("Candidate screenshot saved")
bar = ControlBar()
bar.update_status(State.RECORDING, "日常输入", "direct", elapsed=18, level=0.62)
bar.show()
app.processEvents()
bar.grab().save(str(root / "docs/control-bar-preview.png"))
settings = SettingsWindow(ConfigStore(root))
from PySide6.QtWidgets import QLabel
for label in settings.findChildren(QLabel):
    if str(root) in label.text():
        label.setText("配置、词典、Lua 和历史位置：\n%LOCALAPPDATA%\\VoiceInput")
settings.show()
app.processEvents()
settings.grab().save(str(root / "docs/settings-preview.png"))
print("Control bar and settings screenshots saved")
bar.apply_preferences(always_on_top=True, auto_hide=True, orientation="vertical")
app.processEvents()
bar.grab().save(str(root / "docs/control-bar-vertical-preview.png"))
bar.update_status(State.IDLE, "日常输入", "direct")
bar.collapse()
app.processEvents()
bar.grab().save(str(root / "docs/control-bar-collapsed-preview.png"))
comparison = ProfileComparisonDialog(store)
comparison.samples.setCurrentIndex(1)
comparison.show()
app.processEvents()
comparison.grab().save(str(root / "docs/profile-comparison-preview.png"))
print("Profile comparison screenshot saved")
