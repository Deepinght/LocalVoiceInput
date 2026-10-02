"""Preview the real processing pipeline without recording, history or output."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QComboBox, QScrollArea, QWidget)
from voiceinput.engine.context import AsrResult
from voiceinput.engine.pipeline import Pipeline


class ProfileComparisonDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.setWindowTitle("三种方案对比 · 不录音、不上屏")
        self.resize(760, 680)
        self.store = store
        self.pipeline = Pipeline(store)
        layout = QVBoxLayout(self)
        intro = QLabel("把同一段识别文字交给不同方案处理，看看哪些变化对你有用。\n这里演示文字处理，不代表麦克风的识别准确率；使用当前已保存的词典与 Lua，不写历史。")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        row = QHBoxLayout()
        self.samples = QComboBox()
        for name, spec in store.data["profiles"].items():
            if spec.get("example"):
                self.samples.addItem(spec.get("label", name) + "示例", spec["example"])
        row.addWidget(self.samples, 1)
        self.run_button = QPushButton("对比处理结果")
        row.addWidget(self.run_button)
        layout.addLayout(row)
        layout.addWidget(QLabel("原始识别文字（可以改写或粘贴自己的文字）"))
        self.input = QTextEdit()
        self.input.setAcceptRichText(False)
        self.input.setMaximumHeight(64)
        layout.addWidget(self.input)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        panel = QWidget()
        results = QVBoxLayout(panel)
        results.setSpacing(6)
        self.outputs = {}
        self.statuses = {}
        for name, spec in store.data["profiles"].items():
            heading = QLabel(spec.get("label", name))
            heading.setStyleSheet("font-weight: bold;")
            results.addWidget(heading)
            description = QLabel(spec.get("description", "自定义方案：按当前配置执行。"))
            description.setWordWrap(True)
            results.addWidget(description)
            output = QTextEdit()
            output.setReadOnly(True)
            output.setFixedHeight(52)
            results.addWidget(output)
            status = QLabel()
            status.setWordWrap(True)
            status.setTextFormat(Qt.TextFormat.PlainText)
            results.addWidget(status)
            self.outputs[name], self.statuses[name] = output, status
        scroll.setWidget(panel)
        layout.addWidget(scroll, 1)
        close = QPushButton("关闭")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        self.run_button.clicked.connect(self.compare)
        self.samples.currentIndexChanged.connect(self.load_example)
        self.input.textChanged.connect(self.mark_stale)
        self.load_example()

    def mark_stale(self):
        for name in self.outputs:
            self.outputs[name].clear()
            self.statuses[name].setText("文字已变化，点击“对比处理结果”更新。")

    def load_example(self, *_):
        self.input.setPlainText(self.samples.currentData() or "请连接WIFI，等待三分钟，进度百分之五十")
        self.compare()

    def compare(self):
        raw = self.input.toPlainText()
        for name in self.outputs:
            try:
                ctx = self.pipeline.process(AsrResult(raw), name)
                self.outputs[name].setPlainText(ctx.text)
                changes = list(dict.fromkeys(e.component for e in ctx.trace if e.stage != "asr" and e.before != e.after))
                errors = ctx.metadata.get("errors", [])
                if errors:
                    status = "处理有异常：" + "；".join(errors)
                elif changes:
                    labels = {"correction_dictionary": "已记住的纠错", "terminology_dictionary": "词语格式", "number_normalizer": "数字", "unit_normalizer": "单位", "chemistry_normalizer": "化学式", "punctuation_filter": "标点", "final_cleanup": "两端空白", "lua:builtin/science_format": "专业格式"}
                    status = "本次变化：" + "、".join(labels.get(c, c) for c in changes)
                else:
                    status = "本次无需修改，结果与原始文字相同。"
                self.statuses[name].setText(status)
            except Exception as exc:
                self.outputs[name].setPlainText(raw)
                self.statuses[name].setText(f"无法处理，保留原文：{exc}")
