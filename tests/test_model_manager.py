from voiceinput.asr.model_manager import ModelManager, DownloadCancelled
import pytest


def test_missing_and_corrupt(root):
    manager = ModelManager(root)
    assert not manager.is_installed()
    path = manager.get_model_path()
    path.mkdir(parents=True)
    for name in ("model.int8.onnx", "tokens.txt", "silero_vad.onnx"):
        (path / name).write_bytes(b"corrupt")
    assert not manager.verify()


def test_cancel_download(root, monkeypatch):
    class Response:
        status = 200
        headers = {"Content-Length": "10"}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, n): return b"1234567890"
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: Response())
    with pytest.raises(DownloadCancelled):
        ModelManager(root)._fetch("https://example.test", root / "part", lambda a,b: None, lambda: True)
