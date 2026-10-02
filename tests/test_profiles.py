import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from voiceinput.engine.context import AsrResult
from voiceinput.engine.pipeline import Pipeline
from voiceinput.config.loader import atomic_yaml, read_yaml
from voiceinput.feedback.engine import remember


@pytest.mark.parametrize("text,expected", [
    ("请连接WIFI，等待三分钟，进度百分之五十", [
        "请连接Wi-Fi，等待3分钟，进度50%。",
        "请连接Wi-Fi，等待3 min，进度50%。",
        "请连接WIFI，等待三分钟，进度百分之五十"]),
    ("氮气流量一百标方每小时温度五百度", [
        "氮气流量100标方每小时温度500度。",
        "N₂流量为100 Nm³/h，温度为500 ℃。",
        "氮气流量一百标方每小时温度五百度"]),
    ("请把pdf文件和excel表格通过USB C复制", [
        "请把PDF文件和Excel表格通过USB-C复制。",
        "请把PDF文件和Excel表格通过USB-C复制。",
        "请把pdf文件和excel表格通过USB C复制"]),
])
def test_documented_profile_examples(store, text, expected):
    pipeline = Pipeline(store)
    assert [pipeline.process(AsrResult(text), name).text for name in ("normal", "science", "raw")] == expected


def test_raw_skips_learned_rules_and_lua(store, root):
    remember(root / "dictionaries/user.yaml", "树据分析", "数据分析", "raw")
    (root / "lua/user/custom.lua").write_text('function filter(ctx) ctx.text="CHANGED"; return ctx end', encoding="utf-8")
    store.reload()
    assert Pipeline(store).process(AsrResult("  树据分析  "), "raw").text == "树据分析"


def test_comparison_uses_real_pipeline_without_persistence(store, root):
    from voiceinput.ui.profiles import ProfileComparisonDialog
    app = QApplication.instance() or QApplication([])
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    dialog = ProfileComparisonDialog(store)
    dialog.input.setPlainText("氮气流量一百标方每小时温度五百度")
    assert all(not output.toPlainText() for output in dialog.outputs.values())
    dialog.compare()
    assert dialog.outputs["science"].toPlainText() == "N₂流量为100 Nm³/h，温度为500 ℃。"
    assert "化学式" in dialog.statuses["science"].text()
    assert dialog.outputs["raw"].toPlainText() == dialog.input.toPlainText()
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    dialog.close()


def test_upgrade_preserves_custom_profiles_and_backs_up_original(tmp_path):
    from voiceinput.common.paths import upgrade_profiles
    source = Path(__file__).resolve().parents[1] / "config/profiles.yaml"
    target = tmp_path / "profiles.yaml"
    legacy = {"profiles": {
        "normal": {"label": "普通", "dictionaries": [], "disabled": ["unit_normalizer", "chemistry_normalizer", "lua:builtin/science_format"]},
        "science": {"label": "科研", "dictionaries": ["science", "chemistry", "units"], "disabled": []},
        "raw": {"label": "原文", "dictionaries": [], "only": ["profile_processor", "final_cleanup"]}}}
    atomic_yaml(target, legacy)
    upgrade_profiles(target, source)
    assert read_yaml(target) == read_yaml(source)
    assert read_yaml(tmp_path / "profiles.pre-0.2.1.yaml.bak") == legacy
    legacy["profiles"]["normal"]["label"] = "我的方案"
    atomic_yaml(target, legacy)
    upgrade_profiles(target, source)
    assert read_yaml(target) == legacy
    target.write_text("profiles: [", encoding="utf-8")
    upgrade_profiles(target, source)
    assert target.read_text(encoding="utf-8") == "profiles: ["


def test_invalid_profile_description_keeps_last_valid_config(store, root):
    previous = store.data
    atomic_yaml(root / "config/user.custom.yaml", {"profiles": {"normal": {"description": ["invalid"]}}})
    with pytest.raises(ValueError, match="说明"):
        store.reload()
    assert store.data is previous
