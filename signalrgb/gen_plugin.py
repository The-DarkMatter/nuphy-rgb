"""Generate the SignalRGB plugin for the NuPhy WH80 from the shared layout.

    python signalrgb/gen_plugin.py      -> writes signalrgb/NuPhy_WH80.js

LED indices come from wh80/led_map.json (read from the keyboard's own keymap),
grid positions from wh80/layout.py.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "wh80"))
from layout import GRID, LED_MAP, WIDTH, HEIGHT  # noqa: E402

PRETTY = {"Bksp": "Backspace", "Bslash": "\\", "Caps": "Caps Lock",
          "LShift": "Left Shift", "RShift": "Right Shift", "LCtrl": "Left Ctrl",
          "RCtrl": "Right Ctrl", "LAlt": "Left Alt", "RAlt": "Right Alt",
          "LWin": "Left Win", "Ins": "Insert", "Del": "Delete", "PgUp": "Page Up",
          "PgDn": "Page Down", "Minus": "-", "Equal": "="}

keys = sorted(LED_MAP.items(), key=lambda kv: (GRID[kv[1]][1], GRID[kv[1]][0]))
names = [PRETTY.get(name, name) for _, name in keys]
positions = [list(GRID[name]) for _, name in keys]
indices = [idx for idx, _ in keys]
assert len(set(map(tuple, positions))) == len(positions), "duplicate grid positions"

js = ((HERE / "plugin_template.js").read_text()
      .replace("/*LED_NAMES*/", json.dumps(names))
      .replace("/*LED_POSITIONS*/", json.dumps(positions))
      .replace("/*LED_INDICES*/", json.dumps(indices))
      .replace("/*SIZE*/", json.dumps([WIDTH, HEIGHT])))
(HERE / "NuPhy_WH80.js").write_text(js, encoding="utf-8")
print(f"wrote NuPhy_WH80.js with {len(names)} key LEDs")
