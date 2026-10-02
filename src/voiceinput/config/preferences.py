"""Small, validated UI preferences, including defaults for older installations."""
from voiceinput.config.loader import read_yaml, atomic_yaml, merge

INTERACTION_DEFAULTS = {
    "hotkey": {"mode": "toggle"},
    "output": {"mode": "review"},
    "candidate": {"font_size": 18, "always_on_top": True},
    "toolbar": {"always_on_top": True, "auto_hide": False, "orientation": "horizontal"},
    "sounds": {"enabled": True},
}


def save_preferences(store, updates):
    path = store.root / "config/user.custom.yaml"
    original = read_yaml(path)
    proposed = merge(original, updates)
    atomic_yaml(path, proposed)
    try:
        store.reload()
    except Exception:
        atomic_yaml(path, original)
        raise
