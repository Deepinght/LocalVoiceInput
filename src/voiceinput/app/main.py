import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import threading
import time

from PySide6.QtCore import QObject, QThread, QTimer, Signal, QLockFile, QDir
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPainter, QPixmap, QFont
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox

from voiceinput.common.paths import user_root, resource_root
from voiceinput.config.loader import ConfigStore
from voiceinput.engine.pipeline import Pipeline
from voiceinput.engine.context import AsrResult
from voiceinput.app.lifecycle import Session, State
from voiceinput.asr.model_manager import ModelManager, DownloadCancelled
from voiceinput.history.repository import History
from voiceinput.ui.windows import CandidateWindow, SettingsWindow, ModelDownloadDialog, show_history
from voiceinput.ui.control_bar import ControlBar
from voiceinput.config.preferences import save_preferences
from voiceinput.common.sounds import SoundCues


class Job(QThread):
    result = Signal(object)
    error = Signal(str)
    progress = Signal(object, object)

    def __init__(self, function):
        super().__init__()
        self.function = function

    def run(self):
        try:
            self.result.emit(self.function())
        except Exception as exc:
            logging.error("Background operation failed: %s", type(exc).__name__)
            self.error.emit(str(exc))


class Controller(QObject):
    def __init__(self, app, root):
        super().__init__()
        self.app, self.root = app, root
        startup_error = None
        try:
            self.store = ConfigStore(root)
        except Exception as exc:
            startup_error = f"用户配置无效，暂用随程序提供的默认配置；原文件已保留：{exc}"
            self.store = ConfigStore(resource_root())
            self.store.root = root
            self.store.fingerprint = None
        self.pipeline = Pipeline(self.store)
        self.history = History(root / "data/history.sqlite3")
        self.session = Session()
        self.profile = self.store.data["profile"]["default"]
        self.provider = None
        self.provider_path = None
        self.jobs = set()
        self.candidate = None
        self.model_dialog = None
        self.last_error = None
        self.target = None
        self.hotkey = None
        self.recorder = None
        self.stopping = False
        self.cancel_download = threading.Event()
        self.record_started = 0
        self.processing_started = 0
        self.processing_cancelled = False
        self.last_external = None
        self.current_context = None
        self.status_hint = ""
        self.sounds = SoundCues()
        self.tray = QSystemTrayIcon(self.icon(), self)
        self.menu = QMenu()
        self.start_action = self.menu.addAction("开始录音", self.tray_start)
        self.menu.addAction("显示控制条", self.show_bar)
        self.profile_menu = self.menu.addMenu("当前 Profile")
        self.build_profiles()
        self.menu.addAction("最近识别", lambda: self.safe(lambda: show_history(self.history)))
        self.menu.addAction("设置", self.settings)
        self.menu.addAction("模型", self.models)
        self.menu.addSeparator()
        self.menu.addAction("退出", self.quit)
        self.tray.setContextMenu(self.menu)
        self.tray.setToolTip("VoiceInput")
        self.tray.show()
        self.bar = ControlBar(**self.store.data["toolbar"])
        self.bar.record_requested.connect(self.tray_start)
        self.bar.cancel_requested.connect(self.cancel_current)
        self.bar.settings_requested.connect(self.settings)
        self.bar.top_changed.connect(lambda value: self.save_ui_preferences({"toolbar": {"always_on_top": value}}))
        self.bar.auto_hide_changed.connect(lambda value: self.save_ui_preferences({"toolbar": {"auto_hide": value}}))
        self.bar.orientation_changed.connect(lambda value: self.save_ui_preferences({"toolbar": {"orientation": value}}))
        self.bar.mode_requested.connect(self.toggle_output_mode)
        screen = app.primaryScreen().availableGeometry()
        self.bar.adjustSize()
        self.bar.move(screen.center().x() - self.bar.width()//2, screen.top()+24)
        self.bar.show()
        if startup_error:
            QTimer.singleShot(300, lambda: self.error(startup_error))
        from voiceinput.audio.recorder import Recorder
        self.recorder = Recorder()
        from voiceinput.context.hotkey import CancelHotkey
        self.escape = CancelHotkey(self.cancel_current)
        self.app.installNativeEventFilter(self.escape)
        self.configure_hotkey()
        self.poll = QTimer(self)
        self.poll.timeout.connect(self.poll_recording)
        self.poll.start(40)
        self.watcher = QTimer(self)
        self.watcher.timeout.connect(self.reload)
        self.watcher.start(1000)
        self.refresh_bar()

    def show_bar(self):
        self.bar.expand()
        self.bar.show()

    def play_sound(self, name):
        self.sounds.play(name, self.store.data["sounds"]["enabled"])

    def refresh_bar(self):
        state = self.session.state
        start = self.record_started if state == State.RECORDING else self.processing_started
        elapsed = max(0, time.monotonic()-start) if state in (State.RECORDING, State.PROCESSING) else 0
        spec = self.store.data["profiles"].get(self.profile, {})
        self.bar.update_status(state, spec.get("label", self.profile), self.store.data["output"]["mode"], elapsed, getattr(self.recorder, "level", 0), self.status_hint)
        if state == State.RECORDING:
            end_hint = "松开快捷键结束" if self.from_hotkey and self.record_hotkey_mode == "hold" else "再次按快捷键或点击结束"
            self.bar.status.setText(self.bar.status.text() + " · " + end_hint)
        elif state == State.PROCESSING and self.processing_cancelled:
            self.bar.status.setText("本次已取消，正在结束识别…")
        self.profile_menu.setEnabled(state == State.IDLE)
        self.start_action.setText("结束录音" if state == State.RECORDING else "开始录音")
        self.start_action.setEnabled(state in (State.IDLE, State.RECORDING))

    def save_ui_preferences(self, updates):
        try:
            save_preferences(self.store, updates)
            self.bar.apply_preferences(**self.store.data["toolbar"])
            self.refresh_bar()
        except Exception as exc:
            self.error("设置未保存：" + str(exc))

    def toggle_output_mode(self):
        if self.session.state == State.IDLE:
            mode = "direct" if self.store.data["output"]["mode"] == "review" else "review"
            self.save_ui_preferences({"output": {"mode": mode}})

    def icon(self):
        image = QPixmap(64, 64)
        image.fill(QColor("#2463eb"))
        painter = QPainter(image)
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setPixelSize(38)
        painter.setFont(font)
        painter.drawText(image.rect(), 0x84, "语")
        painter.end()
        return QIcon(image)

    def safe(self, fn):
        try:
            return fn()
        except Exception as exc:
            self.error(str(exc))

    def error(self, message):
        logging.error("Application error: %s", message)
        self.tray.showMessage("VoiceInput", message, QSystemTrayIcon.MessageIcon.Warning, 8000)
        self.status_hint = message
        if hasattr(self, "bar"):
            self.refresh_bar()

    def configure_hotkey(self):
        from voiceinput.context.hotkey import Hotkey
        try:
            if self.hotkey:
                self.hotkey.configure(self.store.data["hotkey"]["push_to_talk"])
            else:
                self.hotkey = Hotkey(self.hotkey_pressed, self.store.data["hotkey"]["push_to_talk"])
                self.app.installNativeEventFilter(self.hotkey)
            self.tray.setToolTip(f"VoiceInput · {self.profile} · {self.store.data['hotkey']['push_to_talk']}")
        except Exception as exc:
            self.error(str(exc) + "；可用控制条开始录音，或打开设置更换快捷键。")

    def hotkey_pressed(self):
        if self.session.state == State.RECORDING:
            if self.record_hotkey_mode == "toggle" or not self.from_hotkey:
                self.stop_recording()
        elif self.session.state == State.IDLE:
            self.start_recording(True)

    def build_profiles(self):
        self.profile_menu.clear()
        self.profile_group = QActionGroup(self)
        for name, spec in self.store.data["profiles"].items():
            action = QAction(spec.get("label", name), self.profile_group)
            action.setToolTip(spec.get("description", ""))
            action.setCheckable(True)
            action.setChecked(name == self.profile)
            action.triggered.connect(lambda checked, n=name: self.choose_profile(n))
            self.profile_menu.addAction(action)

    def choose_profile(self, name):
        if self.session.state != State.IDLE:
            return
        self.profile = name
        self.tray.setToolTip(f"VoiceInput · {self.store.data['profiles'][name].get('label', name)}")
        self.refresh_bar()

    def reload(self):
        if self.session.state != State.IDLE or not self.store.data["config"].get("hot_reload", True):
            return
        try:
            old_hotkey = self.store.data["hotkey"]["push_to_talk"]
            old_default = self.store.data["profile"]["default"]
            if self.store.reload():
                if self.profile not in self.store.data["profiles"] or old_default != self.store.data["profile"]["default"]:
                    self.profile = self.store.data["profile"]["default"]
                self.build_profiles()
                if old_hotkey != self.store.data["hotkey"]["push_to_talk"]:
                    self.configure_hotkey()
                self.bar.apply_preferences(**self.store.data["toolbar"])
                self.refresh_bar()
            self.last_error = None
        except Exception as exc:
            message = str(exc)
            if message != self.last_error:
                self.error("配置更新失败，保留上次有效配置：" + message)
                self.last_error = message

    def manager(self):
        return ModelManager(self.root, self.store.data["asr"].get("model_path"))

    def job(self, fn, success, failure):
        worker = Job(fn)
        self.jobs.add(worker)
        worker.result.connect(success)
        worker.error.connect(failure)
        worker.finished.connect(lambda: self.jobs.discard(worker))
        worker.finished.connect(worker.deleteLater)
        worker.start()
        return worker

    def tray_start(self):
        if self.session.state == State.RECORDING:
            self.stop_recording()
        elif self.session.state == State.IDLE:
            self.start_recording(False)

    def external_window(self):
        from voiceinput.context.foreground_app import foreground
        import win32process
        hwnd, title = foreground()
        return hwnd, win32process.GetWindowThreadProcessId(hwnd)[1], title

    def start_recording(self, from_hotkey):
        if self.session.state != State.IDLE or self.stopping:
            return
        try:
            self.reload()
            if not self.manager().is_installed():
                self.models()
                return
            try:
                hwnd, pid, title = self.external_window()
            except RuntimeError:
                if from_hotkey or not self.last_external:
                    raise
                hwnd, pid, title = self.last_external
            import win32gui, win32process
            if not win32gui.IsWindow(hwnd) or win32process.GetWindowThreadProcessId(hwnd)[1] != pid:
                raise RuntimeError("请先点击要输入文字的窗口，再开始录音")
            self.target = (hwnd, pid)
            self.app_name = title
            self.record_profile = self.profile
            self.from_hotkey = from_hotkey
            self.record_hotkey_mode = self.store.data["hotkey"]["mode"]
            self.record_output_mode = self.store.data["output"]["mode"]
            self.record_output = {key: self.store.data["output"].get(key) for key in ("primary", "fallback")}
            self.processing_cancelled = False
            self.current_context = None
            self.candidate = None
            self.status_hint = ""
            self.recorder.start(self.store.data["audio"].get("device"), self.store.data["audio"].get("max_seconds", 120))
            self.record_started = time.monotonic()
            self.session.state = State.RECORDING
            self.start_action.setText("停止录音")
            self.tray.setToolTip("VoiceInput · 正在录音")
            self.escape.enable(True)
            self.bar.show()
            self.refresh_bar()
            self.play_sound("start")
        except Exception as exc:
            self.fail(str(exc))

    def poll_recording(self):
        if self.session.state in (State.RECORDING, State.PROCESSING) and not self.escape.registered:
            import ctypes
            if ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000:
                self.cancel_current()
        if self.session.state == State.IDLE:
            try:
                self.last_external = self.external_window()
            except Exception:
                pass
        if self.session.state == State.RECORDING:
            if (self.from_hotkey and self.record_hotkey_mode == "hold" and self.hotkey and not self.hotkey.held()) or time.monotonic()-self.record_started >= self.store.data["audio"].get("max_seconds", 120):
                self.stop_recording()
        self.refresh_bar()

    def cancel_current(self):
        state = self.session.state
        if state == State.RECORDING:
            try:
                self.recorder.cancel()
            except Exception as exc:
                self.error(str(exc))
            self.escape.enable(False)
            self.session.state = State.IDLE
            self.status_hint = "录音已取消"
        elif state == State.PROCESSING:
            self.processing_cancelled = True
            self.escape.enable(False)
        elif state == State.REVIEWING and self.candidate:
            self.candidate.reject()
        self.refresh_bar()

    def stop_recording(self):
        if not self.session.transition(State.RECORDING, State.PROCESSING):
            return
        self.processing_started = time.monotonic()
        self.refresh_bar()
        try:
            samples = self.recorder.stop()
            self.play_sound("stop")
            manager = self.manager()
            path = manager.get_model_path()
            self.tray.setToolTip("VoiceInput · 本地识别中")
            def recognize():
                from voiceinput.asr.sensevoice import SenseVoiceProvider
                fingerprint = (str(path), (path / "model.int8.onnx").stat().st_mtime_ns)
                if self.provider_path != fingerprint:
                    if not manager.verify():
                        raise RuntimeError("模型完整性校验失败，请在模型页面重新下载")
                    self.provider = SenseVoiceProvider(path)
                    self.provider_path = fingerprint
                return self.provider.recognize(samples)
            self.job(recognize, self.recognized, self.fail)
        except Exception as exc:
            self.fail(str(exc))

    def recognized(self, result):
        if self.stopping:
            return
        self.escape.enable(False)
        if self.processing_cancelled:
            self.session.state = State.IDLE
            self.status_hint = "本次识别已取消"
            self.refresh_bar()
            return
        if self.session.state != State.PROCESSING:
            return
        try:
            if not result.text.strip():
                raise RuntimeError("没有识别到文字，请重新开始录音")
            ctx = self.pipeline.process(result, self.record_profile, self.app_name)
            self.history_id = self.history.add(ctx)
            self.current_context = ctx
            for error in ctx.metadata.get("errors", []):
                self.error(error)
            if self.record_output_mode == "direct" and ctx.text.strip() and not ctx.metadata.get("errors"):
                self.session.state = State.COMMITTING
                self.refresh_bar()
                QTimer.singleShot(250, lambda: self.commit(ctx.text, direct=True))
            else:
                self.open_candidate(ctx)
        except Exception as exc:
            self.fail(str(exc))

    def open_candidate(self, ctx, output_error=None):
        self.session.state = State.REVIEWING
        self.candidate = CandidateWindow(ctx, self.root, self.store.data["candidate"], self.store.data["profiles"].get(ctx.profile))
        self.candidate.preference_changed.connect(self.save_ui_preferences)
        self.candidate.confirmed.connect(self.confirm)
        self.candidate.cancelled.connect(self.cancel)
        if output_error:
            self.candidate.show_output_error(output_error)
        self.candidate.show()
        self.candidate.raise_()
        self.candidate.activateWindow()
        self.refresh_bar()

    def cancel(self, text):
        if self.session.state != State.REVIEWING:
            return
        self.safe(lambda: self.history.finish(self.history_id, text, False))
        self.session.state = State.IDLE
        self.tray.setToolTip("VoiceInput · 已取消")
        self.status_hint = "候选已取消"
        self.refresh_bar()

    def confirm(self, text):
        if not self.session.transition(State.REVIEWING, State.COMMITTING):
            return
        self.candidate.ctx.user_edited_text = text
        self.candidate.hide()
        self.refresh_bar()
        # Let the confirm shortcut release before sending keys to another application.
        QTimer.singleShot(250, lambda: self.commit(text))

    def commit(self, text, direct=False):
        if self.session.state != State.COMMITTING:
            return
        try:
            if direct:
                # A changed focus converts direct output into a recoverable review.
                hwnd, pid, _ = self.external_window()
                if (hwnd, pid) != self.target:
                    raise RuntimeError("输入窗口已切换，本次未直接上屏。请复制候选文字")
            from voiceinput.output.windows import commit_to_target
            result = commit_to_target(text, *self.target, **self.record_output)
            if not result.success:
                raise RuntimeError(result.message)
        except Exception as exc:
            if self.candidate:
                self.session.state = State.REVIEWING
                self.candidate.show_output_error(str(exc))
                self.candidate.show()
            else:
                self.open_candidate(self.current_context, str(exc))
            self.play_sound("error")
            self.refresh_bar()
            return
        self.safe(lambda: self.history.finish(self.history_id, text, True))
        if self.candidate:
            self.candidate.finished_commit = True
            self.candidate.accept()
        self.session.state = State.IDLE
        if result.message:
            self.error(result.message)
        self.tray.setToolTip("VoiceInput · 已发送")
        self.status_hint = "已发送，可开始下一次录音"
        self.refresh_bar()

    def fail(self, message):
        self.escape.enable(False)
        self.session.state = State.IDLE
        if self.processing_cancelled:
            self.status_hint = "本次识别已取消"
            self.refresh_bar()
            return
        self.play_sound("error")
        if any(word in message.lower() for word in ("portaudio", "inputstream", "device", "麦克风")):
            message += "；点击控制条“设置”检查或更换麦克风。"
        self.error(message)

    def settings(self):
        if self.session.state not in (State.IDLE, State.MODEL_REQUIRED):
            self.error("请先结束当前录音、候选或下载")
            return
        def open_settings():
            if SettingsWindow(self.store).exec():
                self.profile = self.store.data["profile"]["default"]
                self.configure_hotkey()
                self.build_profiles()
                self.bar.apply_preferences(**self.store.data["toolbar"])
                self.status_hint = "设置已保存"
                self.refresh_bar()
        self.safe(open_settings)

    def models(self):
        if self.session.state not in (State.IDLE, State.MODEL_REQUIRED, State.MODEL_DOWNLOADING):
            return
        if self.model_dialog and self.model_dialog.isVisible():
            self.model_dialog.raise_()
            return
        try:
            manager = self.manager()
            dialog = ModelDownloadDialog(manager)
            self.model_dialog = dialog
            self.session.state = State.MODEL_REQUIRED
            dialog.requested.connect(lambda: self.download(manager, dialog))
            dialog.cancelled.connect(self.cancel_download.set)
            dialog.finished.connect(lambda _: self.model_closed())
            dialog.show()
            self.refresh_bar()
        except Exception as exc:
            self.fail(str(exc))

    def model_closed(self):
        if self.session.state == State.MODEL_REQUIRED:
            self.session.state = State.IDLE

    def download(self, manager, dialog):
        if not self.session.transition(State.MODEL_REQUIRED, State.MODEL_DOWNLOADING):
            return
        self.cancel_download.clear()
        dialog.busy = True
        dialog.start.setEnabled(False)
        worker = Job(lambda: manager.download(progress_cb=worker.progress.emit, cancelled=self.cancel_download.is_set))
        self.jobs.add(worker)
        worker.progress.connect(dialog.update_progress)
        def done(message):
            dialog.busy = False
            dialog.start.setEnabled(True)
            dialog.status.setText(message)
            self.session.state = State.MODEL_REQUIRED
            self.provider_path = None
        worker.result.connect(lambda _: done("模型安装完成，关闭此窗口后即可离线使用。"))
        worker.error.connect(done)
        worker.finished.connect(lambda: self.jobs.discard(worker))
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def quit(self):
        if self.session.state == State.COMMITTING:
            return
        self.stopping = True
        self.cancel_download.set()
        self.poll.stop()
        self.watcher.stop()
        if self.recorder and self.recorder.stream:
            self.safe(self.recorder.stop)
        if self.candidate:
            self.candidate.reject()
        if self.jobs:
            self.tray.showMessage("VoiceInput", "正在结束后台任务，完成后退出。")
            QTimer.singleShot(250, self.quit)
            return
        if self.hotkey:
            self.hotkey.close()
        self.escape.close()
        self.bar.hide()
        self.history.db.close()
        self.tray.hide()
        self.app.quit()


def main():
    parser = argparse.ArgumentParser(description="VoiceInput 本地语音输入")
    parser.add_argument("--smoke-test", action="store_true", help="启动托盘后自动退出，不录音也不上屏")
    parser.add_argument("--preview", metavar="TEXT", help="预览文本处理和候选面板；不能上屏")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setApplicationName("VoiceInput")
    app.setQuitOnLastWindowClosed(False)
    root = user_root()
    handler = RotatingFileHandler(root / "logs/app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(message)s")
    lock = QLockFile(str(root / "app.lock"))
    if not lock.tryLock(100):
        QMessageBox.information(None, "VoiceInput", "程序已在运行，请查看系统托盘。")
        return
    import pythoncom
    pythoncom.OleInitialize()
    try:
        controller = Controller(app, root)
        logging.info("VoiceInput started")
        smoke_failed = []
        if args.smoke_test:
            def smoke():
                report = {}
                try:
                    ctx = controller.pipeline.process(AsrResult("氮气流量一百标方每小时温度五百度"), "science")
                    report["pipeline"] = ctx.text
                    report["trace_events"] = len(ctx.trace)
                    if ctx.metadata.get("errors"):
                        raise RuntimeError(str(ctx.metadata["errors"]))
                    manager = controller.manager()
                    report["model_present"] = manager.is_installed()
                    if manager.is_installed():
                        import numpy as np
                        from voiceinput.asr.sensevoice import SenseVoiceProvider
                        provider = SenseVoiceProvider(manager.get_model_path())
                        try:
                            provider.recognize(np.zeros(16000, dtype=np.float32))
                            raise ValueError("静音不应被识别")
                        except RuntimeError as exc:
                            if "未检测到语音" not in str(exc):
                                raise
                        report["asr_and_vad"] = "passed"
                    report["status"] = "passed"
                except Exception as exc:
                    report["status"] = "failed"
                    report["error"] = str(exc)
                    smoke_failed.append(str(exc))
                (root / "data/smoke-test.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                controller.quit()
            QTimer.singleShot(1000, smoke)
        if args.preview:
            ctx = controller.pipeline.process(AsrResult(args.preview), "science")
            preview = CandidateWindow(ctx, root)
            preview.confirm_button.setEnabled(False)
            preview.setWindowTitle("VoiceInput · 处理预览（不连接输出）")
            preview.show()
        app.exec()
        if smoke_failed:
            raise SystemExit(1)
    except Exception as exc:
        logging.exception("Startup failed")
        QMessageBox.critical(None, "VoiceInput 启动失败", str(exc))
        raise
    finally:
        import ctypes
        ctypes.windll.ole32.OleUninitialize()
        lock.unlock()


if __name__ == "__main__":
    main()
