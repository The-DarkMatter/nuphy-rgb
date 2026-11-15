"""NuPhy WH80 (hall-effect, VID 0x19F5 PID 0xA011) raw-HID protocol.

Recovered from NuPhyIO's web bundle (HE-family driver, module 86736/64177/99726)
and verified on hardware. This is NOT the Air100 V3 protocol (gig3m/nuphykit):
different frame layout, no session key, and 0xEE means RestoreFactorySettings.

Frame (64 bytes, report id 0):
    [0] 0x55 host->dev   (reply 0xAA)
    [1] command
    [2] 0x00 key (HE boards send plaintext)
    [3] sum(bytes[4:64]) & 0xFF
    [4] length (<=56)
    [5] addr lo   [6] addr hi
    [7] 0
    [8:8+len] data
"""
from __future__ import annotations

import time
import hid

VID, PID = 0x19F5, 0xA011

# HE command set (module 99726 export EG)
GET_INFO = 0x03
GET_BASE = 0x04
GET_FUNC, SET_FUNC = 0x05, 0x06
GET_DEFAULT_KEYMATRIX, GET_USE_KEYMATRIX = 0x07, 0x08
GET_LED_DEFINE, SET_LED_DEFINE = 0x0A, 0x0B
GET_MACRO = 0x0C
GET_GAMEPAD = 0x10
LED_SYNC_DOWNLOAD = 0xDD    # host -> device; unused by NuPhyIO
LED_SYNC_UPLOAD = 0xDE      # device -> host: live rendered LED frame
GET_KEY_RT, GET_DKS, GET_MT, GET_TGL, GET_CALIB = 0xA0, 0xA2, 0xA4, 0xA6, 0xAA
GET_APPDEFINE = 0xF1

STREAM = {LED_SYNC_DOWNLOAD}   # RAM-only direct-mode framebuffer (firmware 0x6796)
READS = {GET_INFO, GET_BASE, GET_FUNC, GET_DEFAULT_KEYMATRIX, GET_USE_KEYMATRIX,
         GET_LED_DEFINE, GET_MACRO, GET_GAMEPAD, LED_SYNC_UPLOAD, GET_KEY_RT,
         GET_DKS, GET_MT, GET_TGL, GET_CALIB, GET_APPDEFINE}
WRITES = {SET_FUNC, SET_LED_DEFINE}
# Never sent by this tool: 0xEE RestoreFactorySettings, 0xA8/0xA9 calibration,
# 0x09 SetUseKeyMatrix, macros/RT/DKS writes, IAP.

CHUNK = 56
MODES = 3                   # Gaming / Windows / Mac
FUNC_SIZE = 64              # per-mode Func block, addr = mode*64
LED_DEFINE_SIZE = 512       # per-mode custom-colour block, addr = mode*512
KEY_LEDS, SIDE_LEDS = 96, 48

# Func block light records (offsets within the mode's 64 bytes)
MAIN_OFF = 8    # [effect, brightness, speed, direction, isRGB, colorIndex, R, G, B]
SIDE_OFF = 24   # [effect, brightness, speed, isRGB, colorIndex, R, G, B]
THIRD_OFF = 35  # same layout as side

EFFECTS = {0: "Custom (per-key)", 1: "Spectrum", 2: "Gradient", 3: "Static",
           4: "Breathe", 5: "Flower", 6: "Wave", 7: "Wave Up/Down",
           8: "Fountain", 9: "Galaxy", 10: "Rotation", 11: "Tide",
           12: "Sea Wave", 13: "Ripple", 14: "Constant Ripple",
           15: "Single Point", 16: "Grid", 17: "Piano", 18: "Flowing",
           19: "Falling Rain", 20: "Starry", 21: "Firework", 22: "Wave Band",
           255: "Off"}


class WH80Error(RuntimeError):
    pass


def find_path() -> bytes:
    for d in hid.enumerate(VID, PID):
        if d.get("usage_page") == 0x01 and d.get("usage") == 0x00:
            return d["path"]
    raise WH80Error("WH80 raw interface not found (USB cable connected?)")


class WH80:
    def __init__(self, path: bytes | None = None):
        self.h = hid.device()
        self.h.open_path(path or find_path())

    def close(self):
        self.h.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    @staticmethod
    def frame(cmd: int, length: int = 0, addr: int = 0, data: bytes = b"") -> bytes:
        f = bytearray(64)
        f[0], f[1], f[4] = 0x55, cmd, length & 0xFF
        f[5], f[6] = addr & 0xFF, (addr >> 8) & 0xFF
        f[8:8 + len(data)] = data
        f[3] = sum(f[4:]) & 0xFF
        return bytes(f)

    def _drain(self):
        while self.h.read(64, 1):
            pass

    def transact(self, cmd: int, length: int = 0, addr: int = 0,
                 data: bytes = b"", timeout: float = 0.5) -> bytes:
        if cmd not in READS | WRITES | STREAM:
            raise WH80Error(f"command 0x{cmd:02X} is not on the allow-list")
        # No per-call drain: on Windows a 1 ms read timeout costs a full ~15 ms
        # timer tick, while a real round trip is ~1 ms. Stale or unsolicited
        # reports (key/state reports) are skipped by matching flag+cmd+addr.
        self.h.write(b"\x00" + self.frame(cmd, length, addr, data))
        end = time.perf_counter() + timeout
        while time.perf_counter() < end:
            r = self.h.read(64, 50)
            if (r and r[0] == 0xAA and r[1] == cmd
                    and r[5] == (addr & 0xFF) and r[6] == ((addr >> 8) & 0xFF)):
                return bytes(r)
        raise WH80Error(f"no reply to 0x{cmd:02X} addr {addr}")

    def get(self, cmd: int, addr: int, size: int) -> bytes:
        out = bytearray()
        while len(out) < size:
            n = min(CHUNK, size - len(out))
            r = self.transact(cmd, n, addr + len(out))
            out += r[8:8 + n]
        return bytes(out)

    def set(self, cmd: int, addr: int, data: bytes) -> None:
        for o in range(0, len(data), CHUNK):
            part = data[o:o + CHUNK]
            self.transact(cmd, len(part), addr + o, part)

    # --- high level -------------------------------------------------------
    def info(self) -> dict:
        r = self.transact(GET_INFO)[8:]
        return {"fw": f"{r[1]:x}{r[0]:02x}".lstrip("0"), "rf": f"{r[5]:x}{r[4]:02x}".lstrip("0"),
                "build": r[6:32].split(b"\0")[0].decode("latin1").strip()}

    def func(self, mode: int) -> bytes:
        return self.get(GET_FUNC, mode * FUNC_SIZE, FUNC_SIZE)

    def led_define(self, mode: int) -> bytes:
        return self.get(GET_LED_DEFINE, mode * LED_DEFINE_SIZE, LED_DEFINE_SIZE)

    def live_frame(self) -> bytes:
        return self.get(LED_SYNC_UPLOAD, 0, 3 * (KEY_LEDS + SIDE_LEDS))

    def set_main_light(self, mode: int, **f) -> None:
        """Partial write of the main backlight record. Fields: effect,
        brightness(0-100), speed(0-4, 4=fastest), direction, rgb=(r,g,b)."""
        base = mode * FUNC_SIZE + MAIN_OFF
        if "effect" in f:
            self.set(SET_FUNC, base + 0, bytes([f["effect"]]))
        if "brightness" in f:
            self.set(SET_FUNC, base + 1, bytes([max(0, min(100, f["brightness"]))]))
        if "speed" in f:
            self.set(SET_FUNC, base + 2, bytes([abs(f["speed"] - 4)]))
        if "rgb" in f:
            self.set(SET_FUNC, base + 4, bytes([0, 0, *f["rgb"]]))

    def stream_frame(self, rgb: bytes, wait_ack: bool = True) -> None:
        """Direct mode: push a full frame (up to 150 LEDs * RGB) to the RAM
        framebuffer with 0xDD. No flash writes. The firmware shows it instead of
        the built-in effect and falls back after a timeout if frames stop."""
        assert len(rgb) <= 450
        for o in range(0, len(rgb), CHUNK):
            part = rgb[o:o + CHUNK]
            if wait_ack:
                self.transact(LED_SYNC_DOWNLOAD, len(part), o, part)
            else:
                self.h.write(b"\x00" + self.frame(LED_SYNC_DOWNLOAD, len(part), o, part))

    def set_key_colors(self, mode: int, colors: dict[int, tuple[int, int, int]]) -> None:
        """colors: {key data index: (r,g,b)}; writes contiguous runs only."""
        base = mode * LED_DEFINE_SIZE
        idx = sorted(colors)
        i = 0
        while i < len(idx):
            j = i
            while j + 1 < len(idx) and idx[j + 1] == idx[j] + 1:
                j += 1
            buf = b"".join(bytes(colors[k]) for k in idx[i:j + 1])
            self.set(SET_LED_DEFINE, base + 3 * idx[i], buf)
            i = j + 1


def describe_light(rec: bytes, main: bool) -> str:
    if main:
        eff, bri, spd, dirn, isrgb, ci, r, g, b = rec[:9]
    else:
        eff, bri, spd, isrgb, ci, r, g, b = rec[:8]
    return (f"effect {eff} ({EFFECTS.get(eff, '?')}), brightness {bri}, "
            f"speed {abs(spd - 4)}, {'cycling' if isrgb else 'fixed'} #{r:02X}{g:02X}{b:02X}")
