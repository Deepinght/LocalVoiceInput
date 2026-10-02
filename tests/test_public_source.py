from pathlib import Path
import importlib.util


def test_source_export_excludes_personal_runtime_files():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("source_export", root / "scripts/export_source.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    paths = module.public_files()
    names = {path.relative_to(root).as_posix() for path in paths}
    assert "templates/user.yaml" in names
    assert "templates/user.custom.yaml" in names
    assert {"LICENSE", "THIRD_PARTY_NOTICES.md", "LICENSES/GPL-3.0.txt", "LICENSES/LGPL-3.0.txt"} <= names
    assert "dictionaries/user.yaml" not in names
    assert "config/user.custom.yaml" not in names
    assert not any(name.startswith((".private-archive/", "dist/", "build/", "lua/user/", "data/", "logs/")) for name in names)
    module.audit(paths)


def test_public_license_metadata_and_readme_links():
    root = Path(__file__).resolve().parents[1]
    assert (root / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")
    notices = (root / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "PySide6" in notices and "LGPL-3.0" in notices and "SenseVoice" in notices
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "尚未选择自身开源许可证" not in readme
    assert "[MIT License](LICENSE)" in readme


def test_clean_checkout_can_initialize_user_data(tmp_path):
    from voiceinput.common.paths import initialize_user_files
    from voiceinput.config.loader import read_yaml
    root = Path(__file__).resolve().parents[1]
    initialize_user_files(tmp_path, root)
    assert read_yaml(tmp_path / "dictionaries/user.yaml") == {"corrections": []}
    assert read_yaml(tmp_path / "config/user.custom.yaml") == {}
    assert "function filter" in (tmp_path / "lua/user/custom.lua").read_text(encoding="utf-8")
    path = tmp_path / "config/user.custom.yaml"
    path.write_text("custom: keep\n", encoding="utf-8")
    initialize_user_files(tmp_path, root)
    assert read_yaml(path) == {"custom": "keep"}
