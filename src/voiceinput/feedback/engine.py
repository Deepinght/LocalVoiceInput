from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
import shutil
import uuid
from voiceinput.config.loader import read_yaml, atomic_yaml


def suggest(before, after):
    changes = [op for op in SequenceMatcher(None, before, after, autojunk=False).get_opcodes() if op[0] != "equal"]
    if len(changes) != 1 or changes[0][0] != "replace":
        return None
    _, a, b, c, d = changes[0]
    # Include nearby unchanged characters to avoid learning a single Chinese character globally.
    while b-a < 4 and b < len(before) and d < len(after) and before[b] == after[d] and before[b] not in "，。！？ \n0123456789℃":
        b += 1
        d += 1
    while b-a < 2 and a > 0 and c > 0 and before[a-1] == after[c-1]:
        a -= 1
        c -= 1
    source, target = before[a:b], after[c:d]
    if not 2 <= len(source) <= 24 or not 1 <= len(target) <= 24:
        return None
    return source, target


def remember(path, source, target, profile):
    if not 2 <= len(source.strip()) <= 24 or not 1 <= len(target.strip()) <= 24 or source == target:
        raise ValueError("请使用 2～24 字的短词纠错，不能记住整段文字")
    path = Path(path)
    data = read_yaml(path)
    rules = data.get("corrections")
    if not isinstance(rules, list):
        raise ValueError("user.yaml 损坏，未写入")
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("from"), str) or not isinstance(rule.get("to"), str):
            raise ValueError("user.yaml 词条损坏，未写入")
        if rule["from"] == source and (not rule.get("profiles") or profile in rule["profiles"]):
            if rule["to"] == target:
                return
            raise ValueError("已有同名纠错，请先在 user.yaml 中修改旧规则")
    shutil.copy2(path, path.with_name(path.name + "." + datetime.now().strftime("%Y%m%d%H%M%S%f") + ".bak"))
    rules.append({"id": "corr_" + uuid.uuid4().hex[:12], "from": source, "to": target, "profiles": [profile], "created_at": datetime.now().astimezone().isoformat()})
    atomic_yaml(path, data)
