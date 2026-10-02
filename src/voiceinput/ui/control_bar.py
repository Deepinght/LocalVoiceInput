from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QBoxLayout, QLabel, QPushButton, QProgressBar
from voiceinput.app.lifecycle import State


class ControlBar(QWidget):
    record_requested = Signal()
    cancel_requested = Signal()
    settings_requested = Signal()
    top_changed = Signal(bool)
    mode_requested = Signal()
    auto_hide_changed = Signal(bool)
    orientation_changed = Signal(str)

    def __init__(self, always_on_top=True, auto_hide=False, orientation="horizontal"):
        super().__init__()
        self.setWindowTitle("VoiceInput")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, always_on_top)
        self.setStyleSheet("ControlBar {background: #f4f7fb; border: 1px solid #b9c8df; border-radius: 10px;} QPushButton {padding: 6px 10px;} QLabel {border: none;}")
        outer = QVBoxLayout(self)
        self.body = QWidget()
        outer.addWidget(self.body)
        layout = QVBoxLayout(self.body)
        layout.setContentsMargins(0, 0, 0, 0)
        self.heading = heading = QHBoxLayout()
        self.title = QLabel("VoiceInput · 日常输入")
        heading.addWidget(self.title)
        heading.addStretch()
        self.mode = QPushButton("审阅后上屏")
        self.mode.clicked.connect(self.mode_requested.emit)
        heading.addWidget(self.mode)
        self.pin = QPushButton("置顶")
        self.pin.setCheckable(True)
        self.pin.setChecked(always_on_top)
        self.pin.clicked.connect(lambda checked: self.top_changed.emit(checked))
        heading.addWidget(self.pin)
        layout.addLayout(heading)
        options = QHBoxLayout()
        self.auto_hide_button = QPushButton("自动隐藏")
        self.auto_hide_button.setCheckable(True)
        self.auto_hide_button.setToolTip("空闲且鼠标离开后收起为小标签，移入展开；录音和识别时保持显示")
        self.auto_hide_button.clicked.connect(lambda checked: self.auto_hide_changed.emit(checked))
        self.orientation_button = QPushButton("切换为竖向")
        self.orientation_button.clicked.connect(lambda: self.orientation_changed.emit("vertical" if self.orientation == "horizontal" else "horizontal"))
        options.addWidget(self.auto_hide_button)
        options.addWidget(self.orientation_button)
        layout.addLayout(options)
        self.status = QLabel("就绪")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setValue(0)
        self.meter.setTextVisible(False)
        self.meter.setFixedHeight(8)
        layout.addWidget(self.meter)
        self.actions = actions = QHBoxLayout()
        self.record = QPushButton("开始录音")
        self.record.clicked.connect(self.record_requested.emit)
        self.cancel = QPushButton("取消")
        self.cancel.clicked.connect(self.cancel_requested.emit)
        self.settings = QPushButton("设置")
        self.settings.clicked.connect(self.settings_requested.emit)
        hide = QPushButton("收起")
        hide.setToolTip("可从系统托盘重新显示控制条")
        hide.clicked.connect(self.hide)
        for button in (self.record, self.cancel, self.settings, hide):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.handle = QPushButton("VoiceInput · 展开")
        self.handle.setToolTip("鼠标移入或点击展开控制条")
        self.handle.clicked.connect(self.expand)
        outer.addWidget(self.handle)
        self.handle.hide()
        for button in self.findChildren(QPushButton):
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.drag_offset = None
        self.current_state = State.IDLE
        self.last_hint = ""
        self.collapsed = False
        self.auto_hide = False
        self.orientation = None
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(2500)
        self.hide_timer.timeout.connect(self.collapse)
        self.apply_preferences(always_on_top, auto_hide, orientation)

    def apply_preferences(self, always_on_top=True, auto_hide=False, orientation="horizontal"):
        self.set_top(always_on_top)
        changed = self.auto_hide != auto_hide or self.orientation != orientation
        self.auto_hide = auto_hide
        self.auto_hide_button.setChecked(auto_hide)
        self.orientation = orientation
        direction = QBoxLayout.Direction.TopToBottom if orientation == "vertical" else QBoxLayout.Direction.LeftToRight
        self.heading.setDirection(direction)
        self.actions.setDirection(direction)
        self.orientation_button.setText("切换为横向" if orientation == "vertical" else "切换为竖向")
        if changed:
            self.expand()
        self.schedule_hide()

    def fit_to_screen(self):
        self.layout().activate()
        self.adjustSize()
        screen = self.screen()
        if screen:
            area = screen.availableGeometry()
            self.move(max(area.left(), min(self.x(), area.right()-self.width()+1)),
                      max(area.top(), min(self.y(), area.bottom()-self.height()+1)))

    def expand(self):
        self.hide_timer.stop()
        self.collapsed = False
        self.handle.hide()
        self.body.show()
        self.setMinimumWidth(220 if self.orientation == "vertical" else 440)
        self.setMaximumWidth(260 if self.orientation == "vertical" else 16777215)
        self.fit_to_screen()
        self.schedule_hide()

    def collapse(self):
        if not self.auto_hide or self.current_state != State.IDLE or self.underMouse() or self.drag_offset is not None or not self.isVisible():
            return
        self.collapsed = True
        self.body.hide()
        self.handle.show()
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.fit_to_screen()

    def schedule_hide(self):
        if self.auto_hide and self.current_state == State.IDLE and not self.collapsed and not self.underMouse() and self.isVisible():
            self.hide_timer.start(6000 if self.last_hint else 2500)
        else:
            self.hide_timer.stop()

    def enterEvent(self, event):
        self.expand()
        self.hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.schedule_hide()
        super().leaveEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "hide_timer"):
            self.schedule_hide()

    def hideEvent(self, event):
        if hasattr(self, "hide_timer"):
            self.hide_timer.stop()
        super().hideEvent(event)

    def nativeEvent(self, event_type, message):
        # A mouse click must not activate this window or move the text caret.
        from ctypes import wintypes
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == 0x0021:  # WM_MOUSEACTIVATE
            return True, 3  # MA_NOACTIVATE: deliver the click without activation
        return super().nativeEvent(event_type, message)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_offset = None
        self.schedule_hide()
        super().mouseReleaseEvent(event)

    def set_top(self, value):
        visible = self.isVisible()
        self.pin.setChecked(value)
        if bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint) == value:
            return
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, value)
        if visible:
            self.show()

    def update_status(self, state, profile, mode, elapsed=0, level=0, hint=""):
        changed = state != self.current_state or hint != self.last_hint
        self.current_state, self.last_hint = state, hint
        if state != State.IDLE:
            self.hide_timer.stop()
            if self.collapsed:
                self.expand()
        elif changed:
            self.schedule_hide()
        labels = {State.IDLE: "就绪", State.RECORDING: "● 正在录音", State.PROCESSING: "正在本地识别…", State.REVIEWING: "等待审阅", State.COMMITTING: "正在上屏…", State.MODEL_REQUIRED: "请安装本地模型", State.MODEL_DOWNLOADING: "正在下载模型"}
        self.title.setText(f"VoiceInput · {profile}")
        self.mode.setText("⚡ 直接上屏" if mode == "direct" else "审阅后上屏")
        self.handle.setText("VoiceInput · 直接" if mode == "direct" else "VoiceInput · 审阅")
        self.handle.setToolTip(f"{profile} · {'直接上屏' if mode == 'direct' else '审阅后上屏'}\n鼠标移入或点击展开")
        self.mode.setStyleSheet("background: #ffe4b5; color: #723d00;" if mode == "direct" else "")
        timer = f"  {int(elapsed)//60:02d}:{int(elapsed)%60:02d}" if state in (State.RECORDING, State.PROCESSING) else ""
        self.status.setText((hint if state == State.IDLE and hint else labels[state]) + timer)
        self.status.setStyleSheet("color: #bd2532;" if state == State.RECORDING else "color: #245da3;")
        self.meter.setValue(round(level * 100) if state == State.RECORDING else 0)
        self.record.setText("结束录音" if state == State.RECORDING else "开始录音")
        self.record.setEnabled(state in (State.IDLE, State.RECORDING))
        self.cancel.setEnabled(state in (State.RECORDING, State.PROCESSING, State.REVIEWING))
        self.settings.setEnabled(state in (State.IDLE, State.MODEL_REQUIRED))
        self.mode.setEnabled(state == State.IDLE)
        if changed and not self.collapsed:
            self.fit_to_screen()
