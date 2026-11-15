"""Background launcher: E1.31 bridge (OpenRGB -> WH80), plus the optional
L-Connect proxy when "lconnect_proxy" is true in settings.

Started at login by a shortcut in the Startup folder (pythonw, no window).
Log: wh80/logs/services.log
"""
import logging
import logging.handlers
import pathlib
import sys
import threading

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

(HERE / "logs").mkdir(exist_ok=True)
handler = logging.handlers.RotatingFileHandler(HERE / "logs" / "services.log",
                                               maxBytes=1_000_000, backupCount=2)
logging.basicConfig(level=logging.INFO, handlers=[handler],
                    format="%(asctime)s %(name)s %(message)s")

import e131_bridge    # noqa: E402
import openrgb_proxy  # noqa: E402

# Only one copy may run: a second bridge would fight over the keyboard.
import socket         # noqa: E402
_lock = socket.socket()
try:
    _lock.bind(("127.0.0.1", 47622))
except OSError:
    logging.info("already running; exiting")
    sys.exit(0)


def guard(name, fn):
    def run():
        while True:
            try:
                fn()
            except Exception:
                logging.exception("%s crashed; restarting", name)
    return run


import settings  # noqa: E402
if settings.load().get("lconnect_proxy"):
    logging.info("L-Connect proxy enabled")
    threading.Thread(target=guard("proxy", openrgb_proxy.run), daemon=True).start()
logging.info("starting bridge")
guard("bridge", e131_bridge.main)()
