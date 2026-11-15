"""Print the WH80 default keymap by key data index (= LED index)."""
from wh80 import WH80, GET_DEFAULT_KEYMATRIX, GET_USE_KEYMATRIX

HID = {0x04 + i: chr(ord('A') + i) for i in range(26)}
HID.update({0x1E + i: str((i + 1) % 10) for i in range(10)})
HID.update({0x3A + i: f"F{i + 1}" for i in range(12)})
HID.update({
    0x28: "Enter", 0x29: "Esc", 0x2A: "Bksp", 0x2B: "Tab", 0x2C: "Space",
    0x2D: "Minus", 0x2E: "Equal", 0x2F: "[", 0x30: "]", 0x31: "Bslash", 0x32: "#",
    0x33: ";", 0x34: "'", 0x35: "`", 0x36: ",", 0x37: ".", 0x38: "/",
    0x39: "Caps", 0x46: "PrtSc", 0x47: "ScrLk", 0x48: "Pause", 0x49: "Ins",
    0x4A: "Home", 0x4B: "PgUp", 0x4C: "Del", 0x4D: "End", 0x4E: "PgDn",
    0x4F: "Right", 0x50: "Left", 0x51: "Down", 0x52: "Up", 0x64: "ISO",
    0x65: "Menu", 0xE0: "LCtrl", 0xE1: "LShift", 0xE2: "LAlt", 0xE3: "LWin",
    0xE4: "RCtrl", 0xE5: "RShift", 0xE6: "RAlt", 0xE7: "RWin",
})


def name(t, c0, c1):
    if t == c0 == c1 == 0:
        return "-"
    if t == 0x10:
        if c1 == 0 and c0:   # modifier bitmask
            mods = ["LCtrl", "LShift", "LAlt", "LWin", "RCtrl", "RShift", "RAlt", "RWin"]
            return "+".join(m for b, m in enumerate(mods) if c0 >> b & 1)
        return HID.get(c1, f"kc{c0:02x}{c1:02x}")
    return f"t{t:02x}:{c0:02x}{c1:02x}"


def keymap(raw):
    return [name(*raw[3 * i:3 * i + 3]) for i in range(len(raw) // 3)]


if __name__ == "__main__":
    import sys
    layer = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    with WH80() as k:
        raw = k.get(GET_DEFAULT_KEYMATRIX, layer * 512, 512)
    names = keymap(raw)
    for r in range(0, 104, 16):
        print(f"{r:3d}: " + " ".join(f"{n:<7}" for n in names[r:r + 16]))
