import json
from dataclasses import asdict
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QFont
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QDialogButtonBox, QLineEdit, QFormLayout, QComboBox, QFileDialog,
    QMessageBox, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QSpinBox, QCheckBox, QApplication)
from voiceinput.feedback.engine import suggest, remember
from voiceinput.config.loader import read_yaml, atomic_yaml, merge


def text_dialog(parent, title, text):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(760, 500)
    layout = QVBoxLayout(dialog)
    view = QTextEdit()
    view.setReadOnly(True)
    view.setPlainText(text)
    layout.addWidget(view)
    dialog.exec()


class CandidateWindow(QDialog):
    confirmed = Signal(str)
    cancelled = Signal(str)
    preference_changed = Signal(object)

    def __init__(self, ctx, root, preferences=None, profile_spec=None):
        super().__init__()
        self.ctx, self.root = ctx, root
        profile_spec = profile_spec or {}
        self.setWindowTitle(f"VoiceInput · {profile_spec.get('label', ctx.profile)}")
        preferences = preferences or {"font_size": 18, "always_on_top": True}
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, preferences["always_on_top"])
        self.resize(790, 610)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("最终候选 · 可直接编辑，确认后才写入目标程序"))
        if profile_spec.get("description"):
            description = QLabel(profile_spec["description"])
            description.setWordWrap(True)
            layout.addWidget(description)
        toolbar = QHBoxLayout()
        smaller, larger = QPushButton("A−"), QPushButton("A+")
        self.font_size = QSpinBox()
        self.font_size.setRange(12, 36)
        self.font_size.setSuffix(" pt")
        self.font_size.setValue(preferences["font_size"])
        self.pin = QPushButton("置顶")
        self.pin.setCheckable(True)
        self.pin.setChecked(preferences["always_on_top"])
        self.copy_button = QPushButton("复制候选")
        self.raw_button = QPushButton("使用原始识别")
        self.restore_button = QPushButton("恢复处理结果")
        for widget in (smaller, self.font_size, larger, self.pin, self.copy_button, self.raw_button, self.restore_button):
            toolbar.addWidget(widget)
        layout.addLayout(toolbar)
        self.editor = QTextEdit()
        self.editor.setPlainText(ctx.text)
        self.editor.setAcceptRichText(False)
        layout.addWidget(self.editor, 2)
        layout.addWidget(QLabel("原始识别"))
        self.raw = QTextEdit()
        self.raw.setReadOnly(True)
        self.raw.setPlainText(ctx.raw_text)
        layout.addWidget(self.raw, 1)
        self.notice = QLabel("")
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet("color: #a53d16;")
        layout.addWidget(self.notice)
        smaller.clicked.connect(lambda: self.font_size.setValue(self.font_size.value()-2))
        larger.clicked.connect(lambda: self.font_size.setValue(self.font_size.value()+2))
        self.font_size.valueChanged.connect(self.change_font)
        self.pin.clicked.connect(self.change_top)
        self.copy_button.clicked.connect(self.copy_text)
        self.raw_button.clicked.connect(lambda: self.editor.setPlainText(ctx.raw_text))
        self.restore_button.clicked.connect(lambda: self.editor.setPlainText(ctx.text))
        self.change_font(self.font_size.value(), persist=False)
        row = QHBoxLayout()
        trace = QPushButton("查看处理")
        trace.clicked.connect(self.show_trace)
        learn = QPushButton("学习纠错")
        learn.clicked.connect(self.learn)
        row.addWidget(trace)
        row.addWidget(learn)
        row.addStretch()
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        self.confirm_button = QPushButton("确认并上屏")
        self.confirm_button.clicked.connect(self.confirm)
        for button in (trace, learn, cancel, self.confirm_button):
            button.setAutoDefault(False)
        row.addWidget(cancel)
        row.addWidget(self.confirm_button)
        layout.addLayout(row)
        self.shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut.activated.connect(self.confirm)
        self.finished_commit = False
        self.cancel_emitted = False
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)

    def change_font(self, size, persist=True):
        font = QFont(self.editor.font())
        font.setPointSize(size)
        self.editor.setFont(font)
        font.setPointSize(max(10, size-2))
        self.raw.setFont(font)
        if persist:
            self.preference_changed.emit({"candidate": {"font_size": size}})

    def change_top(self, enabled):
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
        if visible:
            self.show()
        self.preference_changed.emit({"candidate": {"always_on_top": enabled}})

    def copy_text(self):
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.notice.setText("已复制候选文字")

    def show_output_error(self, message):
        self.confirm_button.setEnabled(False)
        self.notice.setText(message + "\n请检查目标内容；可复制候选或取消，本次不会自动重发。")

    def show_trace(self):
        rows = []
        for event in self.ctx.trace:
            marker = "● 已变化" if event.before != event.after else "○ 未变化"
            rows.append(f"{marker}  {event.stage} / {event.component}\n{event.before}\n→ {event.after}\n规则：{event.rule_id or '—'}  来源：{event.source or '内置'}\n{json.dumps(event.details, ensure_ascii=False) if event.details else ''}")
        text_dialog(self, "处理轨迹", "\n\n".join(rows))

    def learn(self):
        proposal = suggest(self.ctx.text, self.editor.toPlainText())
        if not proposal:
            QMessageBox.information(self, "学习纠错", "未发现可安全学习的短替换。可以在下方手动填写 2～24 字的短词。")
            proposal = ("", "")
        dialog = QDialog(self)
        dialog.setWindowTitle("学习纠错 · 保存前请核对词组范围")
        layout = QFormLayout(dialog)
        source, target = QLineEdit(proposal[0]), QLineEdit(proposal[1])
        layout.addRow("识别词", source)
        layout.addRow("正确词", target)
        buttons = QDialogButtonBox()
        once = buttons.addButton("仅本次", QDialogButtonBox.ButtonRole.RejectRole)
        save = buttons.addButton("记住", QDialogButtonBox.ButtonRole.AcceptRole)
        once.clicked.connect(dialog.reject)
        def write():
            try:
                remember(self.root / "dictionaries/user.yaml", source.text(), target.text(), self.ctx.profile)
                dialog.accept()
            except Exception as exc:
                QMessageBox.warning(dialog, "无法保存", str(exc))
        save.clicked.connect(write)
        layout.addRow(buttons)
        dialog.exec()

    def confirm(self):
        if not self.finished_commit and self.confirm_button.isEnabled() and self.editor.toPlainText().strip():
            self.confirm_button.setEnabled(False)
            self.confirmed.emit(self.editor.toPlainText())

    def reject(self):
        if not self.finished_commit and not self.cancel_emitted:
            self.cancel_emitted = True
            self.cancelled.emit(self.editor.toPlainText())
        super().reject()


class SettingsWindow(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VoiceInput 设置")
        self.resize(600, 280)
        layout = QFormLayout(self)
        hotkey = QLineEdit(store.data["hotkey"]["push_to_talk"])
        recording_mode = QComboBox()
        recording_mode.addItem("按一次开始，再按一次结束", "toggle")
        recording_mode.addItem("按住说话，松开结束", "hold")
        recording_mode.setCurrentIndex(recording_mode.findData(store.data["hotkey"]["mode"]))
        commit_mode = QComboBox()
        commit_mode.addItem("审阅后上屏（默认）", "review")
        commit_mode.addItem("直接上屏", "direct")
        commit_mode.setCurrentIndex(commit_mode.findData(store.data["output"]["mode"]))
        font_size = QSpinBox()
        font_size.setRange(12, 36)
        font_size.setSuffix(" pt")
        font_size.setValue(store.data["candidate"]["font_size"])
        candidate_top, toolbar_top, sounds = QCheckBox("候选窗口置顶"), QCheckBox("控制条置顶"), QCheckBox("播放开始、结束和失败提示音")
        candidate_top.setChecked(store.data["candidate"]["always_on_top"])
        toolbar_top.setChecked(store.data["toolbar"]["always_on_top"])
        toolbar_auto = QCheckBox("空闲时自动隐藏为小标签，鼠标移入展开")
        toolbar_auto.setChecked(store.data["toolbar"]["auto_hide"])
        toolbar_orientation = QComboBox()
        toolbar_orientation.addItem("横向", "horizontal")
        toolbar_orientation.addItem("竖向", "vertical")
        toolbar_orientation.setCurrentIndex(toolbar_orientation.findData(store.data["toolbar"]["orientation"]))
        sounds.setChecked(store.data["sounds"]["enabled"])
        profile = QComboBox()
        for name, spec in store.data["profiles"].items():
            profile.addItem(spec.get("label", name), name)
        profile.setCurrentIndex(profile.findData(store.data["profile"]["default"]))
        output = QComboBox()
        output.addItem("标准输入（SendInput）", "sendinput")
        output.addItem("剪贴板粘贴（兼容模式）", "clipboard")
        output.setCurrentIndex(output.findData(store.data["output"]["primary"]))
        model = QLineEdit(store.data["asr"].get("model_path") or "")
        device = QComboBox()
        device.addItem("系统默认麦克风", None)
        import sounddevice as sd
        try:
            for index, info in enumerate(sd.query_devices()):
                if info["max_input_channels"] > 0:
                    device.addItem(info["name"], index)
        except Exception:
            pass
        device.setCurrentIndex(max(0, device.findData(store.data["audio"].get("device"))))
        layout.addRow("录音快捷键", hotkey)
        layout.addRow("录音方式", recording_mode)
        layout.addRow("上屏模式", commit_mode)
        direct_hint = QLabel("直接模式下，识别完成后立即输入；审阅模式会先显示候选。")
        direct_hint.setWordWrap(True)
        layout.addRow(direct_hint)
        layout.addRow("候选字体大小", font_size)
        layout.addRow(candidate_top)
        layout.addRow(toolbar_top)
        layout.addRow(toolbar_auto)
        layout.addRow("控制条方向", toolbar_orientation)
        layout.addRow(sounds)
        layout.addRow("默认模式", profile)
        profile_hint = QLabel()
        profile_hint.setWordWrap(True)
        profile_hint.setTextFormat(Qt.TextFormat.PlainText)
        def describe_profile():
            spec = store.data["profiles"][profile.currentData()]
            profile_hint.setText(spec.get("description", "自定义方案：按当前配置执行。"))
        profile.currentIndexChanged.connect(describe_profile)
        describe_profile()
        layout.addRow(profile_hint)
        compare = QPushButton("三种方案对比（无需录音）")
        from voiceinput.ui.profiles import ProfileComparisonDialog
        compare.clicked.connect(lambda: ProfileComparisonDialog(store, self).exec())
        layout.addRow(compare)
        layout.addRow("麦克风", device)
        layout.addRow("兼容输出方式", output)
        layout.addRow("已有模型目录（可留空）", model)
        browse = QPushButton("选择已有模型目录")
        browse.clicked.connect(lambda: model.setText(QFileDialog.getExistingDirectory(self, "选择模型目录") or model.text()))
        layout.addRow(browse)
        location = QLabel(f"配置、词典、Lua 和历史位置：\n{store.root}")
        location.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addRow(location)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.rejected.connect(self.reject)
        def save():
            try:
                from voiceinput.context.hotkey import parse_hotkey
                from voiceinput.config.preferences import save_preferences
                parse_hotkey(hotkey.text())
                save_preferences(store, {"hotkey": {"push_to_talk": hotkey.text(), "mode": recording_mode.currentData()}, "profile": {"default": profile.currentData()}, "audio": {"device": device.currentData()}, "output": {"primary": output.currentData(), "mode": commit_mode.currentData()}, "candidate": {"font_size": font_size.value(), "always_on_top": candidate_top.isChecked()}, "toolbar": {"always_on_top": toolbar_top.isChecked(), "auto_hide": toolbar_auto.isChecked(), "orientation": toolbar_orientation.currentData()}, "sounds": {"enabled": sounds.isChecked()}, "asr": {"model_path": model.text() or None}})
                self.accept()
            except Exception as exc:
                QMessageBox.warning(self, "设置无效", str(exc))
        buttons.accepted.connect(save)
        layout.addRow(buttons)


class ModelDownloadDialog(QDialog):
    requested = Signal()
    cancelled = Signal()

    def __init__(self, manager):
        super().__init__()
        self.busy = False
        self.setWindowTitle("本地语音模型")
        self.resize(620, 320)
        layout = QVBoxLayout(self)
        spec = manager.manifest["sensevoice-small-int8"]
        label = QLabel(f"SenseVoiceSmall INT8 + Silero VAD\n下载后可离线识别；模型约 230 MB，下载包大小以进度为准。\n位置：{manager.get_model_path()}\n来源：{spec['source']}\n许可：{spec['license']}\n也可在设置中指定已有模型目录。")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(label)
        self.status = QLabel("模型文件已存在，可重新校验下载" if manager.is_installed() else "本地语音模型尚未安装")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.start = QPushButton("开始下载 / 重试")
        self.start.clicked.connect(self.requested.emit)
        layout.addWidget(self.start)
        close = QPushButton("取消 / 关闭")
        close.clicked.connect(self.reject)
        layout.addWidget(close)

    def update_progress(self, current, total):
        self.progress.setRange(0, 100 if total else 0)
        self.progress.setValue(int(current / total * 100) if total else 0)
        self.status.setText(f"已下载 {current / 1048576:.1f} MB" + (f" / {total / 1048576:.1f} MB" if total else ""))

    def reject(self):
        if self.busy:
            self.cancelled.emit()
            self.status.setText("正在取消下载，请稍候……")
        else:
            super().reject()


def show_history(history):
    dialog = QDialog()
    dialog.setWindowTitle("最近 100 次识别 · 仅保存在本机")
    dialog.resize(1050, 550)
    layout = QVBoxLayout(dialog)
    rows = history.recent()
    table = QTableWidget(len(rows), 6)
    table.setHorizontalHeaderLabels(["时间", "模式", "原始识别", "处理结果", "最终编辑", "已发送"])
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    for i, row in enumerate(rows):
        for j, value in enumerate(row[:6]):
            table.setItem(i, j, QTableWidgetItem(str(value or "")))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.cellDoubleClicked.connect(lambda r, c: text_dialog(dialog, "历史处理轨迹", json.dumps(json.loads(rows[r][6]), ensure_ascii=False, indent=2)))
    layout.addWidget(table)
    dialog.exec()
