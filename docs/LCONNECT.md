# Syncing the WH80 with Lian Li L-Connect 3

L-Connect 3 (beta with "Open RGB" support, tested v2.1.29) can run one effect
across Lian Li devices (Strimers, fans, screens) **and** the devices of the
OpenRGB copy it bundles. With this setup the WH80 joins that list.

## Why it needs a proxy

L-Connect reads devices from its bundled OpenRGB, but has two quirks that keep
the WH80 out:

1. It only accepts OpenRGB devices whose type is **Motherboard, DRAM or GPU**.
   The WH80 arrives as an E1.31 device (type "LED strip") and is silently
   dropped. The same happens to any other E1.31 or LED-strip device.
2. It numbers ordinary devices by their OpenRGB index, but the motherboard's
   zones by their position in its own list. Any device listed after the
   motherboard ends up with the same number as one of the zones, so effects
   never reach it.

`wh80/openrgb_proxy.py` sits between L-Connect and OpenRGB on
`127.0.0.1:6742`. It passes everything through unchanged, except that it:

- reports the devices named in `lconnect_relabel` as **DRAM**, and
- lists the motherboard last, translating device numbers in both directions.

It only listens while OpenRGB is running. A starting OpenRGB that finds another
server on that port turns itself into a client and skips hardware detection,
which would leave L-Connect with zero devices.

## Setup

1. Install Python and the requirements (see the main README).
2. Quit L-Connect 3 completely, so its OpenRGB stops too.
3. Register the keyboard as an **18-LED strip**, one LED per column, so each
   key row acts like a Strimer strip and effects sweep left to right:
   ```
   python wh80/setup_openrgb.py --columns
   ```
4. Create `wh80/settings.local.json` to turn the proxy on:
   ```json
   { "lconnect_proxy": true, "lconnect_relabel": ["NuPhy WH80"] }
   ```
   Add the names of any other OpenRGB E1.31 devices you want L-Connect to
   control to `lconnect_relabel`.
5. Start the services (`pythonw wh80/wh80_services.pyw`, or install autostart),
   then start L-Connect 3.
6. On Quick/Sync Lighting → Open RGB, click **Reconnect OpenRGB**, wait about
   15 s, click refresh, tick **NuPhy WH80** and **Apply**.

## Notes

- The keyboard shows up in L-Connect as a RAM-type device. That's cosmetic.
- L-Connect's brightness slider and the keyboard's own brightness multiply.
  Raise one of them if the keys look dim.
- The front light bar keeps its own effect (firmware limit, see the main README).
- If the list ever comes up empty after a restart, click **Reconnect OpenRGB**
  once more. The log at `wh80/logs/services.log` shows what the proxy saw.
