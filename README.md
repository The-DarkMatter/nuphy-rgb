# nuphy-rgb

Open per-key RGB control for **NuPhy** keyboards in **SignalRGB** and
**OpenRGB**, with optional **Lian Li L-Connect 3** sync.

**Supported today: NuPhy WH80.** Other NuPhy hall-effect boards (Air75 HE,
Halo65 HE, Field75 HE, ...) use the same protocol family in NuPhyIO, so they
are likely close. If you own one, see [CONTRIBUTING.md](CONTRIBUTING.md).

The WH80 runs NuPhy's own firmware (not QMK/VIA), so SignalRGB and OpenRGB
don't support it, and NuPhy has said it won't add support. This project
reverse-engineered the keyboard's USB protocol and found a hidden **direct
mode**: the PC streams colours to the keys at 100+ fps, straight into RAM, so
nothing wears out the keyboard's flash. When the app closes, the keyboard goes
back to its own lighting after a second or two.

| Use it with | How | Needs Python |
|---|---|---|
| **SignalRGB** | a plugin file you drop in | no |
| **OpenRGB** | a small background bridge (E1.31) | yes |
| **L-Connect 3** (Lian Li) | the OpenRGB bridge plus a proxy, see [docs/LCONNECT.md](docs/LCONNECT.md) | yes |

**Use one app at a time.** If two apps drive the keyboard, they fight and the
lights flicker.

Tested on Windows 11 with a WH80 on firmware 1.22, over the **USB cable**
(~90-125 fps) and the **2.4 GHz dongle** (~15 fps; a typing test showed no
dropped or delayed keys). The bridge uses the cable when it's plugged in and
the dongle otherwise. Bluetooth is untested.

## SignalRGB

1. Copy [`signalrgb/NuPhy_WH80.js`](signalrgb/NuPhy_WH80.js) into
   `Documents\WhirlwindFX\Plugins\NuPhy\` (create the folders).
   If your Documents folder is synced by OneDrive, the right place is
   `OneDrive\Documents\WhirlwindFX\Plugins\NuPhy\`.
2. **Fully quit** SignalRGB (tray icon → Exit) and start it again.
3. "NuPhy WH80" appears under Devices with an 18×6 key layout.

The SignalRGB plugin currently needs the **USB cable**. Over the 2.4 GHz dongle,
use the OpenRGB route for now (dongle support for the plugin is a welcome
contribution).

## OpenRGB

1. Install [Python 3.10+](https://www.python.org/downloads/) (tick "Add to PATH"),
   then from this folder: `pip install -r requirements.txt`
2. **Close OpenRGB**, then register the keyboard:
   ```
   python wh80/setup_openrgb.py
   ```
   This adds an E1.31 device called **NuPhy WH80** (an 18×6 grid) to
   `%APPDATA%\OpenRGB\OpenRGB.json`, after making a timestamped backup.
3. Start the bridge. It runs hidden in the background:
   ```
   pythonw wh80/wh80_services.pyw
   ```
   To start it automatically at login:
   `powershell -ExecutionPolicy Bypass -File wh80\install_autostart.ps1`
4. Start OpenRGB. **NuPhy WH80** appears as an E1.31 device. Use Direct mode or
   the Effects plugin.

To undo: `python wh80/setup_openrgb.py --remove` and
`install_autostart.ps1 -Remove`.

## Good to know

- **Brightness:** the keyboard scales whatever the PC sends by its own backlight
  brightness for the current mode. If colours look dim, raise the keyboard's
  brightness (Fn keys or NuPhyIO).
- **Front light bar:** the 48-LED bar on the front can't be driven live. In
  direct mode the firmware only takes the 96 key LEDs from the PC and keeps
  running the bar's own saved effect. Set the bar to something you like in
  NuPhyIO.
- The knob, keymap, rapid trigger and other settings are untouched. This only
  does lighting.

## Tools

All in `wh80/`; they work over the cable or the 2.4 GHz dongle. Close the RGB
app first.

| | |
|---|---|
| `python wh80/stream_demo.py rainbow 10` | rainbow across the keys for 10 s |
| `python wh80/stream_demo.py keys W A S D` | light only those keys |
| `python wh80/backup.py backup my.json` / `restore my.json` | save or restore the keyboard's lighting settings |
| `python wh80/keymap_dump.py` | print the keymap by LED index |
| `python signalrgb/gen_plugin.py` | rebuild the SignalRGB plugin after editing `wh80/layout.py` |

## How it works

The full protocol is in [docs/PROTOCOL.md](docs/PROTOCOL.md). In short: 64-byte
HID reports on interface 1. Command `0xDD` writes RGB into a RAM framebuffer
that the firmware shows instead of its built-in effect, and a watchdog hands
control back when frames stop. Per-key colours that NuPhyIO saves use a
different command that writes flash, so it is never used for streaming.

## Safety and disclaimer

Not affiliated with or endorsed by NuPhy or Lian Li. This sends undocumented
commands to your keyboard. The code only uses read commands, the direct-mode
command and two lighting settings commands, and never sends factory-reset,
calibration or firmware-update commands. Use at your own risk; see
[LICENSE](LICENSE).

## Credits

- [nuphykit](https://github.com/gig3m/nuphykit), whose Air100 V3 work showed
  the way into NuPhy's protocols.
- [lian-li-linux](https://github.com/sgtaziz/lian-li-linux), for the Lian Li
  wireless research.

## Contributing

Owners of other NuPhy boards, testers on the 2.4 GHz dongle or Bluetooth, and
anyone who wants to package this better are very welcome. Start with
[CONTRIBUTING.md](CONTRIBUTING.md), which covers how to probe a new board safely.

## License

MIT
