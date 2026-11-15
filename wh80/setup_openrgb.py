"""Add (or update) the NuPhy WH80 as an E1.31 device in OpenRGB's config.

    python wh80/setup_openrgb.py                 # 18x6 matrix  (OpenRGB effects)
    python wh80/setup_openrgb.py --columns       # 18-LED strip (L-Connect 3)

Close OpenRGB first (and anything that launches it, e.g. L-Connect 3), run this,
then start OpenRGB again. A timestamped backup of OpenRGB.json is written first.
"""
import argparse
import json
import shutil
import sys
import time

import settings

NAME = "NuPhy WH80"


def entry(columns: bool) -> dict:
    base = {"name": NAME, "ip": "127.0.0.2", "rgb_order": "RGB",
            "start_universe": 1, "start_channel": 1, "universe_size": 512,
            "keepalive_time": 500}
    if columns:
        return {**base, "type": "LINEAR", "num_leds": 18}
    return {**base, "type": "MATRIX", "num_leds": 108, "matrix_width": 18,
            "matrix_height": 6, "matrix_order": "HORIZONTAL_TOP_LEFT"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--columns", action="store_true",
                    help="one LED per column: rows act like strips (best for L-Connect 3)")
    ap.add_argument("--config", help="path to OpenRGB.json (default from settings / %%APPDATA%%)")
    ap.add_argument("--remove", action="store_true", help="remove the WH80 entry instead")
    args = ap.parse_args()

    path = args.config or settings.openrgb_config_path()
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        sys.exit(f"{path} not found. Start OpenRGB once so it creates its config, or pass --config.")

    backup = f"{path}.{time.strftime('%Y%m%d-%H%M%S')}.bak"
    shutil.copy2(path, backup)

    devices = cfg.setdefault("E131Devices", {}).setdefault("devices", [])
    devices[:] = [d for d in devices if d.get("name") != NAME]
    if not args.remove:
        devices.append(entry(args.columns))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

    print(f"backup: {backup}")
    print("removed" if args.remove else
          f"added '{NAME}' as {'18-LED strip' if args.columns else '18x6 matrix'} -> {path}")
    print("Now (re)start OpenRGB and run the bridge: pythonw wh80/wh80_services.pyw")


if __name__ == "__main__":
    main()
