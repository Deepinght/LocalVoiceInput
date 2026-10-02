import pytest
from voiceinput.output import windows


def test_partial_send_never_falls_back(monkeypatch):
    monkeypatch.setattr(windows, "restore_target", lambda *args: None)
    monkeypatch.setattr(windows, "send", lambda events: 1)
    calls = []
    monkeypatch.setattr(windows.ClipboardOutput, "commit", lambda self, text: calls.append(text))
    with pytest.raises(RuntimeError, match="部分"):
        windows.commit_to_target("测试", 1, 2)
    assert calls == []


def test_zero_send_falls_back(monkeypatch):
    monkeypatch.setattr(windows, "restore_target", lambda *args: None)
    monkeypatch.setattr(windows, "send", lambda events: 0)
    calls = []
    def paste(self, text):
        calls.append(text)
        return windows.OutputResult(True)
    monkeypatch.setattr(windows.ClipboardOutput, "commit", paste)
    assert windows.commit_to_target("测试", 1, 2).success
    assert calls == ["测试"]


def test_wrong_target_no_output(monkeypatch):
    def invalid(*args):
        raise RuntimeError("目标窗口已关闭")
    monkeypatch.setattr(windows, "restore_target", invalid)
    calls = []
    monkeypatch.setattr(windows, "send", lambda events: calls.append(events))
    with pytest.raises(RuntimeError):
        windows.commit_to_target("测试", 1, 2)
    assert calls == []
