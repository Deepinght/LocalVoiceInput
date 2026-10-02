from pathlib import Path
import shutil
import pytest
from voiceinput.config.loader import ConfigStore


@pytest.fixture
def root(tmp_path):
    base = Path(__file__).resolve().parents[1]
    for folder in ("config", "dictionaries", "lua"):
        shutil.copytree(base / folder, tmp_path / folder)
    from voiceinput.common.paths import initialize_user_files
    initialize_user_files(tmp_path, base)
    (tmp_path / "data").mkdir()
    return tmp_path


@pytest.fixture
def store(root):
    return ConfigStore(root)
