"""Make L-Connect 3 show and drive OpenRGB devices it normally ignores.

    L-Connect --> 127.0.0.1:6742 (this proxy) --> 127.0.0.5:6742 (OpenRGB on 0.0.0.0)

Two L-Connect quirks are worked around (see lianli.slv3.dll OpenRGBController):

1. GetDevices() keeps only Motherboard / DRAM / GPU devices. Controller-data
   replies for names in RELABEL are rewritten from LEDSTRIP (4) to DRAM (1).

2. GetDevices() numbers ordinary devices by their OpenRGB index but the
   motherboard's zones by list position. Any device after the motherboard then
   collides with a zone and is never driven. The proxy presents a virtual order
   with motherboards last and translates device indices in both directions.

The proxy listens on 127.0.0.1:6742 (SO_REUSEADDR) ONLY while OpenRGB is up:
a starting OpenRGB that finds something on 127.0.0.1:6742 skips detection.
It rebinds within ~0.1 s of OpenRGB's server appearing so L-Connect, which
connects a few seconds after launching OpenRGB, comes through the proxy.
"""
import logging
import socket
import struct
import subprocess
import threading
import time

import settings

LISTEN = ("127.0.0.1", 6742)
UPSTREAM = ("127.0.0.5", 6742)        # reaches OpenRGB's 0.0.0.0:6742 listener


def _load_relabel():
    """Device names to expose to L-Connect (settings.json / settings.local.json)."""
    return set(settings.load().get("lconnect_relabel") or ["NuPhy WH80"])


RELABEL = _load_relabel()
MOTHERBOARD, DRAM, LEDSTRIP = 0, 1, 4
REQUEST_CONTROLLER_COUNT = 0
REQUEST_CONTROLLER_DATA = 1
REQUEST_PROTOCOL_VERSION = 40
DEVICE_LIST_UPDATED = 100
HDR = struct.Struct("<4sIII")          # magic, dev_idx, pkt_id, pkt_size

log = logging.getLogger("openrgb-proxy")


def recv_exact(s, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("closed")
        buf += chunk
    return bytes(buf)


def read_packet(s):
    magic, dev, pid, size = HDR.unpack(recv_exact(s, HDR.size))
    if magic != b"ORGB":
        raise ConnectionError("bad magic")
    return dev, pid, (recv_exact(s, size) if size else b"")


def send_packet(s, dev, pid, payload=b""):
    s.sendall(HDR.pack(b"ORGB", dev, pid, len(payload)) + payload)


def parse_type_name(payload):
    dev_type = struct.unpack_from("<i", payload, 4)[0]
    name_len = struct.unpack_from("<H", payload, 8)[0]
    return dev_type, payload[10:10 + name_len].rstrip(b"\0").decode("utf-8", "replace")


def relabel(payload: bytes) -> bytes:
    if len(payload) < 10:
        return payload
    dev_type, name = parse_type_name(payload)
    if dev_type == LEDSTRIP and name in RELABEL:
        return payload[:4] + struct.pack("<i", DRAM) + payload[8:]
    return payload


def query_order():
    """Ask OpenRGB for its controllers; return virtual->real index list."""
    with socket.create_connection(UPSTREAM, timeout=3) as s:
        send_packet(s, 0, REQUEST_PROTOCOL_VERSION, struct.pack("<I", 5))
        ver = None
        count = None
        send_packet(s, 0, REQUEST_CONTROLLER_COUNT)
        types = []
        while count is None or len(types) < count:
            dev, pid, payload = read_packet(s)
            if pid == REQUEST_PROTOCOL_VERSION:
                ver = min(struct.unpack("<I", payload)[0], 5)
            elif pid == REQUEST_CONTROLLER_COUNT:
                count = struct.unpack("<I", payload)[0]
                for i in range(count):
                    send_packet(s, i, REQUEST_CONTROLLER_DATA, struct.pack("<I", ver or 0))
            elif pid == REQUEST_CONTROLLER_DATA:
                types.append(parse_type_name(payload))
    order = sorted(range(len(types)), key=lambda i: (types[i][0] == MOTHERBOARD, i))
    log.info("virtual order: %s", [types[i][1] for i in order])
    return order


class Session:
    def __init__(self, client, upstream):
        self.c, self.u = client, upstream
        self.v2r: list[int] = []
        self.r2v: dict[int, int] = {}
        self.lock = threading.Lock()

    def set_order(self, order):
        with self.lock:
            self.v2r = order
            self.r2v = {r: v for v, r in enumerate(order)}

    def to_real(self, v):
        with self.lock:
            return self.v2r[v] if v < len(self.v2r) else v

    def to_virtual(self, r):
        with self.lock:
            return self.r2v.get(r, r)

    def close(self):
        for s in (self.c, self.u):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            s.close()

    def client_to_server(self):
        try:
            while True:
                dev, pid, payload = read_packet(self.c)
                if pid == REQUEST_CONTROLLER_COUNT:
                    try:
                        self.set_order(query_order())
                    except (OSError, ConnectionError) as e:
                        log.warning("could not query order: %s", e)
                if pid == REQUEST_CONTROLLER_DATA or pid >= 1000:
                    dev = self.to_real(dev)
                send_packet(self.u, dev, pid, payload)
        except (OSError, ConnectionError):
            pass
        finally:
            self.close()

    def server_to_client(self):
        try:
            while True:
                dev, pid, payload = read_packet(self.u)
                if pid == REQUEST_CONTROLLER_DATA:
                    dev = self.to_virtual(dev)
                    payload = relabel(payload)
                elif pid == DEVICE_LIST_UPDATED:
                    log.info("device list updated upstream")
                send_packet(self.c, dev, pid, payload)
        except (OSError, ConnectionError):
            pass
        finally:
            self.close()


def connect_upstream(wait=20.0):
    # Clients that connect while OpenRGB is still detecting are held until its
    # server opens, rather than being turned away.
    end = time.monotonic() + wait
    while True:
        try:
            u = socket.create_connection(UPSTREAM, timeout=1)
            u.settimeout(None)
            return u
        except OSError:
            if time.monotonic() > end:
                return None
            time.sleep(0.1)


def handle(client):
    up = connect_upstream()
    if up is None:
        log.info("OpenRGB not up yet; closing client so it retries")
        client.close()
        return
    for s in (client, up):
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sess = Session(client, up)
    try:
        sess.set_order(query_order())
    except (OSError, ConnectionError) as e:
        log.warning("initial order query failed: %s", e)
    threading.Thread(target=sess.client_to_server, daemon=True).start()
    threading.Thread(target=sess.server_to_client, daemon=True).start()


def openrgb_up() -> bool:
    try:
        socket.create_connection(UPSTREAM, timeout=0.5).close()
        return True
    except OSError:
        return False


def openrgb_pid():
    """PID of the running OpenRGB.exe (any session), or None."""
    try:
        out = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH", "/FI", "IMAGENAME eq OpenRGB.exe"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) > 1 and parts[0].lower() == "openrgb.exe":
            return int(parts[1])
    return None


# A starting OpenRGB probes 127.0.0.1:6742 within its first few ms and, if
# anything answers, becomes a client and skips hardware detection (0 devices).
# Its own server only opens ~5 s later, after detection. So: bind once the
# process has been alive for SETTLE seconds (probe done, server not yet up),
# which beats L-Connect's reconnect every time, and release the moment the
# process goes away or changes.
SETTLE = 1.0


def serve_for_pid(pid):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(LISTEN)
    srv.listen(8)
    srv.settimeout(0.2)
    log.info("OpenRGB pid %s settled; proxy listening on %s:%d", pid, *LISTEN)
    last_check = 0.0
    try:
        while True:
            try:
                client, _ = srv.accept()
                threading.Thread(target=handle, args=(client,), daemon=True).start()
            except socket.timeout:
                pass
            if time.monotonic() - last_check > 0.5:
                last_check = time.monotonic()
                if openrgb_pid() != pid:
                    log.info("OpenRGB pid %s gone; releasing port", pid)
                    return
    finally:
        srv.close()


def run():
    seen_pid, seen_at = None, 0.0
    while True:
        pid = openrgb_pid()
        if pid is None:
            seen_pid = None
            time.sleep(0.1)
            continue
        if pid != seen_pid:
            seen_pid, seen_at = pid, time.monotonic()
        if time.monotonic() - seen_at < SETTLE:
            time.sleep(0.05)
            continue
        try:
            serve_for_pid(pid)
        except OSError as e:
            log.warning("listener error: %s", e)
            time.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    run()
