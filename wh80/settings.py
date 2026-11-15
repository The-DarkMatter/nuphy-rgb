"""settings.json merged with an optional, git-ignored settings.local.json."""
import json
import os
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def load() -> dict:
    merged = {}
    for name in ("settings.json", "settings.local.json"):
        try:
            merged.update(json.loads((HERE / name).read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return merged


def openrgb_config_path() -> str:
    path = load().get("openrgb_config") or os.environ.get("OPENRGB_CONFIG", "")
    return path or os.path.expandvars(r"%APPDATA%\OpenRGB\OpenRGB.json")
