"""Back up (or restore) the WH80 lighting state: Func blocks + per-key colours."""
import json
import sys
import time
from wh80 import WH80, MODES, FUNC_SIZE, LED_DEFINE_SIZE, SET_FUNC, SET_LED_DEFINE, describe_light, MAIN_OFF, SIDE_OFF


def backup(path):
    with WH80() as k:
        snap = {"info": k.info(), "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "func": [k.func(m).hex() for m in range(MODES)],
                "led_define": [k.led_define(m).hex() for m in range(MODES)]}
    with open(path, "w") as f:
        json.dump(snap, f, indent=1)
    print("saved", path, snap["info"])
    for m, fx in enumerate(snap["func"]):
        b = bytes.fromhex(fx)
        print(f" mode {m}: main {describe_light(b[MAIN_OFF:], True)}")
        print(f"         side {describe_light(b[SIDE_OFF:], False)}")


def restore(path):
    snap = json.load(open(path))
    with WH80() as k:
        for m in range(MODES):
            k.set(SET_LED_DEFINE, m * LED_DEFINE_SIZE, bytes.fromhex(snap["led_define"][m]))
            # only the light records (bytes 8..42); leave the rest of Func alone
            fb = bytes.fromhex(snap["func"][m])
            k.set(SET_FUNC, m * FUNC_SIZE + 8, fb[8:43])
        for m in range(MODES):
            assert k.led_define(m).hex() == snap["led_define"][m], f"led_define {m} mismatch"
            assert k.func(m)[8:43] == bytes.fromhex(snap["func"][m])[8:43], f"func {m} mismatch"
    print("restored and verified", path)


if __name__ == "__main__":
    {"backup": backup, "restore": restore}[sys.argv[1]](sys.argv[2])
