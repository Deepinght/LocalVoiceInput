from copy import deepcopy
from pathlib import Path
import os
import tempfile
import yaml


def read_yaml(path):
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: 顶层必须是 YAML 映射")
    return value


def merge(a, b):
    result = deepcopy(a)
    for key, value in b.items():
        result[key] = merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else deepcopy(value)
    return result


def atomic_yaml(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            yaml.safe_dump(value, stream, allow_unicode=True, sort_keys=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class ConfigStore:
    def __init__(self, root):
        self.root = Path(root)
        self.data = {}
        self.dictionaries = {}
        self.fingerprint = None
        self.reload()

    def reload(self):
        paths = sorted((self.root / "config").glob("*.yaml")) + sorted((self.root / "dictionaries").glob("*.yaml"))
        fingerprint = [(str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in paths]
        if fingerprint == self.fingerprint:
            return False
        from voiceinput.config.preferences import INTERACTION_DEFAULTS
        data = deepcopy(INTERACTION_DEFAULTS)
        for name in ("default.yaml", "profiles.yaml", "user.custom.yaml"):
            if name == "user.custom.yaml" and not (self.root / "config" / name).exists():
                continue
            data = merge(data, read_yaml(self.root / "config" / name))
        profiles = data.get("profiles")
        if not isinstance(profiles, dict) or data["profile"]["default"] not in profiles:
            raise ValueError("Profile 配置无效")
        known = {"profile_processor", "correction_dictionary", "terminology_dictionary", "number_normalizer", "unit_normalizer", "chemistry_normalizer", "punctuation_filter", "final_cleanup"}
        for stage in ("processors", "translators", "filters"):
            items = data["engine"][stage]
            if not isinstance(items, list) or any(not isinstance(x, str) or (x not in known and not x.startswith("lua:")) for x in items):
                raise ValueError(f"engine.{stage} 包含无效组件")
        for profile in profiles.values():
            if not isinstance(profile, dict) or any(not isinstance(profile.get(k, []), list) for k in ("dictionaries", "disabled", "only")):
                raise ValueError("Profile 必须包含列表配置")
            if any(not isinstance(profile.get(k, ""), str) for k in ("label", "description", "example")):
                raise ValueError("Profile 的名称、说明和示例必须是文本")
        if data["audio"]["sample_rate"] != 16000 or data["audio"]["channels"] != 1:
            raise ValueError("V0.1 音频必须为 16000 Hz 单声道")
        if not 1 <= data["audio"].get("max_seconds", 120) <= 300:
            raise ValueError("录音时长应为 1 至 300 秒")
        if data["output"]["primary"] not in ("sendinput", "clipboard"):
            raise ValueError("输出方式无效")
        if data["output"].get("fallback") not in ("clipboard", None):
            raise ValueError("回退方式应为 clipboard 或 null")
        if data["output"]["mode"] not in ("review", "direct"):
            raise ValueError("上屏模式必须是 review 或 direct")
        if data["hotkey"]["mode"] not in ("toggle", "hold"):
            raise ValueError("录音方式必须是 toggle 或 hold")
        size = data["candidate"]["font_size"]
        if type(size) is not int or not 12 <= size <= 36:
            raise ValueError("候选字号必须为 12～36")
        if data["toolbar"]["orientation"] not in ("horizontal", "vertical"):
            raise ValueError("控制条方向必须是 horizontal 或 vertical")
        for section, key in (("candidate", "always_on_top"), ("toolbar", "always_on_top"), ("toolbar", "auto_hide"), ("sounds", "enabled")):
            if type(data[section][key]) is not bool:
                raise ValueError(f"{section}.{key} 必须为 true 或 false")
        # Validate the manifest during reload as well, before publishing new settings.
        manifest = read_yaml(self.root / "config/models.yaml").get("models")
        if not isinstance(manifest, dict) or "sensevoice-small-int8" not in manifest:
            raise ValueError("模型清单无效")
        from voiceinput.context.hotkey import parse_hotkey
        parse_hotkey(data["hotkey"]["push_to_talk"])
        dictionaries = {}
        for path in (self.root / "dictionaries").glob("*.yaml"):
            content = read_yaml(path)
            for key in ("terms", "corrections"):
                entries = content.get(key, [])
                if not isinstance(entries, list):
                    raise ValueError(f"{path}: {key} 必须是列表")
                for entry in entries:
                    if not isinstance(entry, dict):
                        raise ValueError(f"{path}: 词条必须是映射")
                    if "profiles" in entry and (not isinstance(entry["profiles"], list) or any(not isinstance(p, str) for p in entry["profiles"])):
                        raise ValueError(f"{path}: profiles 必须是字符串列表")
                    fields = ("from", "to") if key == "corrections" else ("output",)
                    if any(not isinstance(entry.get(f), str) or not entry[f] for f in fields):
                        raise ValueError(f"{path}: 词条文本不能为空")
                    if key == "terms" and (not isinstance(entry.get("spoken"), list) or not entry["spoken"] or any(not isinstance(s, str) or not s for s in entry["spoken"])):
                        raise ValueError(f"{path}: spoken 必须是非空字符串列表")
            dictionaries[path.stem] = content
        self.data, self.dictionaries, self.fingerprint = data, dictionaries, fingerprint
        return True
