"""Launch the packaged app without Python on PATH in a clean user directory."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from voiceinput.config.loader import atomic_yaml

root = Path(__file__).resolve().parents[1]
env = os.environ.copy()
env["PATH"] = str(Path(env["SYSTEMROOT"]) / "System32")
env.pop("PYTHONHOME", None)
env.pop("PYTHONPATH", None)
data = Path(tempfile.mkdtemp(prefix="voiceinput-release-"))
env["VOICEINPUT_HOME"] = str(data)
exe = root / "dist/v0.2.1/VoiceInput/VoiceInput.exe"
reports = []
for mode in ("fresh_no_model", "existing_model"):
    if mode == "existing_model":
        model = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "VoiceInput/models/sensevoice-small-int8"
        atomic_yaml(data / "config/user.custom.yaml", {"hotkey": {"push_to_talk": "Ctrl+Alt+F24"}, "asr": {"model_path": str(model)}})
    process = subprocess.run([str(exe), "--smoke-test"], env=env, timeout=35)
    assert process.returncode == 0, process.returncode
    report = json.loads((data / "data/smoke-test.json").read_text(encoding="utf-8"))
    assert report["status"] == "passed", report
    reports.append({"mode": mode, **report})
print(json.dumps(reports, ensure_ascii=True, indent=2))
(root / "docs/package-validation-v021.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
