"""Create a public source archive from an explicit list of source resources."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = {"src", "tests", "scripts", "docs", "templates", "LICENSES"}
EXTENSIONS = {".py", ".ps1", ".md", ".txt", ".json", ".png", ".yaml", ".lua"}
ROOT_FILES = {".gitignore", "LICENSE", "THIRD_PARTY_NOTICES.md", "pyproject.toml", "requirements-lock.txt", "README.md", "CHANGELOG.md", "VoiceInput.spec", "启动语音输入.cmd", "VoiceInput_V0.1_需求与架构基线.md"}
RESOURCES = {"config/default.yaml", "config/profiles.yaml", "config/models.yaml", "dictionaries/common.yaml", "dictionaries/science.yaml", "dictionaries/chemistry.yaml", "dictionaries/units.yaml", "lua/builtin/science_format.lua", "lua/builtin/punctuation.lua", "models/.gitkeep"}


def public_files():
    selected = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in ("__pycache__", ".venv", "build", "dist", ".private-archive", ".pytest_cache") or part.endswith(".egg-info") for part in relative.parts):
            continue
        if relative.as_posix() in RESOURCES or (len(relative.parts) == 1 and (path.name in ROOT_FILES or path.name.startswith("M") and path.name.endswith("_CHECKPOINT.md"))):
            selected.append(path)
        elif relative.parts[0] in FOLDERS and path.suffix in EXTENSIONS:
            selected.append(path)
    return sorted(selected)


def audit(paths):
    for path in paths:
        if path.suffix == ".png":
            continue
        text = path.read_text(encoding="utf-8-sig")
        if re.search(r"[A-Za-z]:[\\/]Users[\\/][^\s]+", text):
            raise ValueError(f"Absolute personal directory: {path.relative_to(ROOT)}")
        if re.search(r"(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_]{20,}", text):
            raise ValueError(f"Possible credential: {path.relative_to(ROOT)}")
        # Project-specific samples removed from all public files; keep the scanner
        # independent of any particular developer's name or working directory.
        if any(chr(code) in text for code in (0x7164, 0x94c0)):
            raise ValueError(f"Legacy project-specific example: {path.relative_to(ROOT)}")


def main():
    paths = public_files()
    audit(paths)
    target = ROOT / "dist/VoiceInput-V0.2.1-source.zip"
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, "VoiceInput/" + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
    with target.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    report = {"file": target.name, "files": len(paths), "sha256": digest, "source_audit": "passed", "excludes_personal_config_history_models_logs": True}
    (ROOT / "dist/source-verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
