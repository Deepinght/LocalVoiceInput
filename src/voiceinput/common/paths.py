import os
import sys
import shutil
import hashlib
import yaml
from pathlib import Path


def upgrade_profiles(target, source):
    """Upgrade only the unmodified original presets; keep all custom profiles."""
    from voiceinput.config.loader import read_yaml, atomic_yaml
    legacy = {"profiles": {
        "normal": {"label": "普通", "dictionaries": [], "disabled": ["unit_normalizer", "chemistry_normalizer", "lua:builtin/science_format"]},
        "science": {"label": "科研", "dictionaries": ["science", "chemistry", "units"], "disabled": []},
        "raw": {"label": "原文", "dictionaries": [], "only": ["profile_processor", "final_cleanup"]},
    }}
    try:
        if read_yaml(target) == legacy:
            # Keep even comments from the original file available for recovery.
            backup = target.with_name("profiles.pre-0.2.1.yaml.bak")
            if not backup.exists():
                shutil.copy2(target, backup)
            atomic_yaml(target, read_yaml(source))
    except (ValueError, OSError, yaml.YAMLError):
        # Normal configuration loading will report unreadable/invalid settings.
        return


def resource_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))


def user_root():
    root = Path(os.environ.get("VOICEINPUT_HOME", Path(os.environ.get("LOCALAPPDATA", Path.home())) / "VoiceInput"))
    root.mkdir(parents=True, exist_ok=True)
    for folder in ("config", "dictionaries", "lua"):
        for source in (resource_root() / folder).rglob("*"):
            if source.is_file():
                target = root / source.relative_to(resource_root())
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copy2(source, target)
                elif source.relative_to(resource_root()).as_posix() == "config/profiles.yaml":
                    upgrade_profiles(target, source)
                elif source.name in ("chemistry.yaml", "science.yaml"):
                    # Only replace an unchanged, previously shipped dictionary.
                    # Locally edited dictionaries and learned rules are preserved.
                    legacy = {"chemistry.yaml": "a71b945dd2d2d5b2edcc82d2abd8b0b2dae43a0b79add4b35c2555822121d06b", "science.yaml": "8bb879a1f90c859610fcd0b8e8c64a571bd7c1f2de265a4a3da9b87a28097cc8"}
                    if hashlib.sha256(target.read_bytes()).hexdigest() == legacy[source.name]:
                        from voiceinput.config.loader import read_yaml, atomic_yaml
                        atomic_yaml(target, read_yaml(source))
    initialize_user_files(root, resource_root())
    for folder in ("logs", "models", "data"):
        (root / folder).mkdir(exist_ok=True)
    return root


def initialize_user_files(root, resources):
    for template, destination in (("user.custom.yaml", "config/user.custom.yaml"), ("user.yaml", "dictionaries/user.yaml"), ("custom.lua", "lua/user/custom.lua")):
        target = Path(root) / destination
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(resources) / "templates" / template, target)
