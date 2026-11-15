"""OpenRGB -> NuPhy WH80 bridge over E1.31 (sACN).

OpenRGB sends the keyboard's colours to an "E1.31 device" at 127.0.0.2
(added by setup_openrgb.py). This listens there and pushes each frame to the
keyboard with direct mode (0xDD, RAM only, no flash wear). When OpenRGB stops
sending, the keyboard falls back to its own lighting after ~1-2 s.

Layouts (read from the device entry in OpenRGB.json):
    MATRIX 18x6  one colour per grid cell, for OpenRGB effects
    LINEAR 18    one colour per column; rows act like strips (L-Connect 3)

    python e131_bridge.py --verbose      run in a console with logging
    pythonw wh80_services.pyw            run in the background (normal use)
"""
import json
import logging
import os
import socket
import sys
import time

import settings
from layout import WIDTH, led_cells
from wh80 import WH80, WH80Error, KEY_LEDS, SIDE_LEDS

LISTEN = ("127.0.0.2", 5568)
UNIVERSE = 1
START_CHANNEL = 1
IDLE_AFTER = 2.0          # seconds without packets -> stop feeding the keyboard
MAX_FPS = 90

log = logging.getLogger("wh80-bridge")
CELLS = led_cells()       # (led_index, col, row)

OPENRGB_JSON = settings.openrgb_config_path()
DEVICE_NAME = "NuPhy WH80"
_layout = {"mtime": None, "type": "MATRIX"}


def openrgb_layout() -> str:
    """'MATRIX' or 'LINEAR', from our E1.31 entry in OpenRGB.json (cached)."""
    try:
        mtime = os.path.getmtime(OPENRGB_JSON)
        if mtime != _layout["mtime"]:
            _layout["mtime"] = mtime
            with open(OPENRGB_JSON, encoding="utf-8") as f:
                devs = json.load(f).get("E131Devices", {}).get("devices", [])
            for d in devs:
                if d.get("name") == DEVICE_NAME:
                    _layout["type"] = str(d.get("type", "LINEAR")).upper()
                    log.info("layout from OpenRGB.json: %s", _layout["type"])
    except (OSError, ValueError) as e:
        log.debug("could not read OpenRGB.json: %s", e)
    return _layout["type"]


def parse_e131(pkt: bytes):
    """Return (universe, dmx_bytes) for an E1.31 data packet, else None."""
    if len(pkt) < 126 or pkt[4:16] != b"ASC-E1.17\x00\x00\x00":
        return None
    if pkt[18:22] != b"\x00\x00\x00\x04":          # root vector: E1.31 data
        return None
    if pkt[40:44] != b"\x00\x00\x00\x02":          # framing vector: DMP
        return None
    universe = int.from_bytes(pkt[113:115], "big")
    count = int.from_bytes(pkt[123:125], "big") - 1  # minus start code
    if pkt[125] != 0:                               # DMX start code must be 0
        return None
    return universe, pkt[126:126 + count]


def to_frame(dmx: bytes) -> bytes:
    """Map E1.31 channels to key LEDs.

    LINEAR 18 LEDs (one per column): each colour fills its whole column, so
    every row acts like a strip and effects sweep left -> right (L-Connect).
    MATRIX 18x6 (108 LEDs): one colour per grid cell (OpenRGB matrix effects).
    """
    frame = bytearray(3 * (KEY_LEDS + SIDE_LEDS))
    data = dmx[START_CHANNEL - 1:]
    columns_mode = openrgb_layout() != "MATRIX"
    for idx, col, row in CELLS:
        o = 3 * col if columns_mode else 3 * (row * WIDTH + col)
        if o + 3 <= len(data):
            frame[3 * idx:3 * idx + 3] = data[o:o + 3]
    # The 48-LED front bar is not driven: in direct mode the firmware only
    # copies the 96 key LEDs from the framebuffer (see docs/PROTOCOL.md).
    return bytes(frame[:3 * KEY_LEDS])


def open_keyboard():
    while True:
        try:
            k = WH80()
            log.info("keyboard connected")
            return k
        except Exception as e:  # not plugged in yet
            log.debug("waiting for keyboard: %s", e)
            time.sleep(2)


def main():
    logging.basicConfig(level=logging.DEBUG if "--verbose" in sys.argv else logging.WARNING,
                        format="%(asctime)s %(message)s")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(LISTEN)
    sock.settimeout(0.25)
    log.info("listening on %s:%d universe %d", *LISTEN, UNIVERSE)

    kb = open_keyboard()
    last_rx = 0.0
    last_tx = 0.0
    latest = None
    while True:
        try:
            pkt, _ = sock.recvfrom(1024)
            parsed = parse_e131(pkt)
            if parsed and parsed[0] == UNIVERSE:
                latest = to_frame(parsed[1])
                last_rx = time.monotonic()
        except socket.timeout:
            pass
        except OSError as e:          # e.g. WSAECONNRESET on Windows UDP
            log.debug("socket: %s", e)

        now = time.monotonic()
        if latest is None or now - last_rx > IDLE_AFTER:
            continue
        if now - last_tx < 1 / MAX_FPS:
            continue
        try:
            kb.stream_frame(latest)
            last_tx = now
        except (WH80Error, OSError) as e:
            log.warning("keyboard write failed (%s); reconnecting", e)
            try:
                kb.close()
            except Exception:
                pass
            kb = open_keyboard()


if __name__ == "__main__":
    main()
