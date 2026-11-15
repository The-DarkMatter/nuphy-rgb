"""Live per-key RGB on the WH80 via direct mode (0xDD, RAM only, no flash wear).

    python stream_demo.py rainbow [seconds]   moving rainbow at ~100+ fps
    python stream_demo.py keys W A S D        light only these keys (5 s)

When frames stop, the keyboard returns to its saved effect after ~1-2 s.
Brightness in direct mode follows the active mode's backlight brightness.
"""
import colorsys
import json
import sys
import time

from wh80 import WH80, KEY_LEDS, SIDE_LEDS

N = KEY_LEDS + SIDE_LEDS
LED_MAP = json.load(open(__file__.replace("stream_demo.py", "led_map.json")))["keys"]


def rainbow(seconds=10.0):
    with WH80() as k:
        t0 = time.perf_counter()
        frames = 0
        while time.perf_counter() - t0 < seconds:
            ph = (time.perf_counter() - t0) / 3
            buf = bytearray()
            for i in range(N):
                r, g, b = colorsys.hsv_to_rgb((i / N + ph) % 1, 1, 1)
                buf += bytes((int(r * 255), int(g * 255), int(b * 255)))
            k.stream_frame(bytes(buf))
            frames += 1
        print(f"{frames / (time.perf_counter() - t0):.0f} fps")


def keys(names, seconds=5.0):
    want = {n.upper() for n in names}
    idx = [int(i) for i, n in LED_MAP.items() if n.upper() in want]
    buf = bytearray(3 * N)
    for i in idx:
        buf[3 * i:3 * i + 3] = b"\xff\x00\x00"
    with WH80() as k:
        end = time.time() + seconds
        while time.time() < end:          # keep feeding the firmware watchdog
            k.stream_frame(bytes(buf))
            time.sleep(0.05)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "rainbow"
    if cmd == "rainbow":
        rainbow(float(sys.argv[2]) if len(sys.argv) > 2 else 10)
    elif cmd == "keys":
        keys(sys.argv[2:])
