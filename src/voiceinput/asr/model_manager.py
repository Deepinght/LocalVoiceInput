from pathlib import Path
import hashlib
import json
import os
import shutil
import tarfile
import urllib.request
import urllib.error
from voiceinput.config.loader import read_yaml


class DownloadCancelled(Exception):
    pass


class ModelManager:
    def __init__(self, root, override=None):
        self.root = Path(root)
        self.manifest = read_yaml(self.root / "config/models.yaml")["models"]
        self.override = override

    def get_model_path(self, model_id="sensevoice-small-int8"):
        return Path(self.override) if self.override else self.root / self.manifest[model_id]["path"]

    def is_installed(self, model_id="sensevoice-small-int8"):
        path = self.get_model_path(model_id)
        return all((path / f).is_file() and (path / f).stat().st_size > 0 for f in self.manifest[model_id]["files"])

    def verify(self, model_id="sensevoice-small-int8"):
        if not self.is_installed(model_id):
            return False
        path = self.get_model_path(model_id)
        index = path / "integrity.json"
        if index.exists():
            digests = json.loads(index.read_text())
            for filename in self.manifest[model_id]["files"]:
                with (path / filename).open("rb") as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != digests.get(filename):
                        return False
            return True
        # Imported files receive runtime validation when loaded by sherpa-onnx.
        return (path / "model.int8.onnx").stat().st_size > 1000000 and (path / "silero_vad.onnx").stat().st_size > 100000

    def _fetch(self, url, target, progress, cancelled):
        offset = target.stat().st_size if target.exists() else 0
        headers = {"User-Agent": "VoiceInput/0.1"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        try:
            response = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20)
        except urllib.error.HTTPError as exc:
            if exc.code == 416:
                target.unlink(missing_ok=True)
                return self._fetch(url, target, progress, cancelled)
            raise
        with response:
            if response.status != 206:
                offset = 0
            total = int(response.headers.get("Content-Length", 0)) + offset
            with target.open("ab" if offset else "wb") as output:
                while True:
                    if cancelled():
                        raise DownloadCancelled("下载已取消，下次可继续")
                    block = response.read(256 * 1024)
                    if not block:
                        break
                    output.write(block)
                    offset += len(block)
                    progress(offset, total)
            if total and offset != total:
                raise IOError("下载未完成，请重试")

    def download(self, model_id="sensevoice-small-int8", progress_cb=lambda a, b: None, cancelled=lambda: False):
        spec = self.manifest[model_id]
        target = self.get_model_path(model_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = target.parent / (target.name + ".staging")
        staging.mkdir(exist_ok=True)
        archive = staging / "model.tar.bz2.part"
        self._fetch(spec["archive"], archive, progress_cb, cancelled)
        try:
            with tarfile.open(archive, "r:bz2") as tar:
                for filename in ("model.int8.onnx", "tokens.txt"):
                    member = next((m for m in tar if Path(m.name).name == filename and m.isfile()), None)
                    if not member or member.size > 1024**3:
                        raise ValueError("模型压缩包内容无效")
                    with tar.extractfile(member) as source, (staging / filename).open("wb") as out:
                        shutil.copyfileobj(source, out)
        except Exception:
            archive.unlink(missing_ok=True)
            raise
        self._fetch(spec["vad"], staging / "silero_vad.onnx.part", progress_cb, cancelled)
        os.replace(staging / "silero_vad.onnx.part", staging / "silero_vad.onnx")
        if cancelled():
            raise DownloadCancelled("下载已取消")
        from voiceinput.asr.sensevoice import SenseVoiceProvider
        import sherpa_onnx
        SenseVoiceProvider(staging)
        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(staging / "silero_vad.onnx")
        sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=1)
        digests = {}
        for filename in spec["files"]:
            with (staging / filename).open("rb") as stream:
                digests[filename] = hashlib.file_digest(stream, "sha256").hexdigest()
        (staging / "integrity.json").write_text(json.dumps(digests), encoding="utf-8")
        target.mkdir(exist_ok=True)
        for filename in spec["files"] + ["integrity.json"]:
            os.replace(staging / filename, target / filename)
        archive.unlink(missing_ok=True)
