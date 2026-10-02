import pytest
from voiceinput.config.loader import atomic_yaml


def test_invalid_retains_previous(store, root):
    previous = store.data
    (root / "config/user.custom.yaml").write_text("bad: [", encoding="utf-8")
    with pytest.raises(Exception):
        store.reload()
    assert store.data == previous


def test_custom_profile_and_order(store, root):
    atomic_yaml(root / "config/user.custom.yaml", {"profiles": {"custom": {"dictionaries": [], "only": ["final_cleanup"]}}, "profile": {"default": "custom"}})
    assert store.reload()
    assert store.data["profile"]["default"] == "custom"


def test_schema_validation(store, root):
    atomic_yaml(root / "config/user.custom.yaml", {"engine": {"filters": ["unknown"]}})
    with pytest.raises(ValueError):
        store.reload()
