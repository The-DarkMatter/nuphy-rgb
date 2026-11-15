"""Physical layout of the WH80: key name -> (column, row) on an 18 x 6 grid.

Shared by the SignalRGB plugin generator and the OpenRGB E1.31 bridge.
"""
import json
import pathlib

WIDTH, HEIGHT = 18, 6

GRID: dict[str, tuple[int, int]] = {}


def _row(r, items):
    for name, col in items:
        GRID[name] = (col, r)


_row(0, [("Esc", 0)] + [(f"F{i}", i + 1) for i in range(1, 13)])
_row(1, [("`", 0)] + [(str((i + 1) % 10), i + 1) for i in range(10)]
     + [("Minus", 11), ("Equal", 12), ("Bksp", 13), ("Ins", 15), ("Home", 16), ("PgUp", 17)])
_row(2, [("Tab", 0)] + [(c, i + 1) for i, c in enumerate("QWERTYUIOP")]
     + [("[", 11), ("]", 12), ("Bslash", 13), ("Del", 15), ("End", 16), ("PgDn", 17)])
_row(3, [("Caps", 0)] + [(c, i + 1) for i, c in enumerate("ASDFGHJKL")]
     + [(";", 10), ("'", 11), ("Enter", 13)])
_row(4, [("LShift", 0)] + [(c, i + 2) for i, c in enumerate("ZXCVBNM")]
     + [(",", 9), (".", 10), ("/", 11), ("RShift", 13), ("Up", 16)])
_row(5, [("LCtrl", 0), ("LWin", 1), ("LAlt", 2), ("Space", 6), ("RAlt", 10), ("Fn", 11),
         ("RCtrl", 12), ("Left", 15), ("Down", 16), ("Right", 17)])

LED_MAP = {int(i): n for i, n in json.loads(
    (pathlib.Path(__file__).parent / "led_map.json").read_text())["keys"].items()}


def led_cells() -> list[tuple[int, int, int]]:
    """[(led_index, col, row)] for every mapped key."""
    out = []
    for idx, name in LED_MAP.items():
        if name not in GRID:
            raise KeyError(f"no grid position for {name}")
        col, row = GRID[name]
        out.append((idx, col, row))
    return out
