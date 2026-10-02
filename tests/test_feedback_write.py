import pytest
from voiceinput.feedback.engine import remember


def test_corrupt_file_never_overwritten(root):
    path = root / "dictionaries/user.yaml"
    path.write_text("corrections: [", encoding="utf-8")
    with pytest.raises(Exception):
        remember(path, "错误词", "正确词", "science")
    assert path.read_text(encoding="utf-8") == "corrections: ["
