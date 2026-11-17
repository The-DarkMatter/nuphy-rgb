# Contributing

Thanks for helping! The most useful contributions right now:

- **Another NuPhy keyboard.** Getting a new board working is mostly finding
  its USB IDs, its LED count and its key-to-LED map.
- **Testing** on the 2.4 GHz dongle or Bluetooth, other firmware versions,
  Linux or macOS.
- **Packaging:** an installer, a tray app, or getting the plugin into
  SignalRGB's and the driver into OpenRGB's official repositories.

Open an issue before starting anything big, so work isn't duplicated.

## Adding a keyboard safely

NuPhy keyboards accept undocumented commands, and some of them are destructive.
Read [docs/PROTOCOL.md](docs/PROTOCOL.md) first.

**Rules**

1. **Read before you write.** Only the `Get*` commands, `0x03` GetInfo and
   `0xDE` LedSyncUpload are reads. Confirm the frame format with those first.
2. **Never sweep or guess opcodes.** On the WH80, `0xEE` is factory reset, and
   other NuPhy boards use different numbering. On the Air100 V3, `0xEF` drops
   the keyboard into its bootloader.
3. **Stream with `0xDD` only.** The "set" commands store settings in flash.
4. **Get the checksum right.** A bad checksum is rejected (`0xAB "cserr"`),
   which is what makes a mistake harmless. Don't rely on it, though.
5. Use the USB cable. The dongle answers some commands itself.

**Steps**

1. Find the board's raw-HID interface: VID `0x19F5`, usage page `0x01`,
   usage `0x00`, 64-byte reports. NuPhyIO's device list also gives the
   product ID.
2. In `wh80/wh80.py`, adjust `PID`, `KEY_LEDS` and `SIDE_LEDS`. NuPhyIO's
   per-model config has `lightCount`.
3. Run `python wh80/keymap_dump.py` (read-only) to see which key sits at each
   LED index, then regenerate `led_map.json` and fill in a grid in
   `wh80/layout.py`.
4. Try `python wh80/stream_demo.py keys W A S D` and check that the right keys
   light up.
5. Send a pull request with the board's name, firmware version, and what you
   tested.

The current code has the WH80 baked in. Turning it into a per-model table is
a welcome first contribution.

## Pull requests

- Keep them focused, and describe what you tested on real hardware.
- Don't include NuPhy's firmware, NuPhyIO code, or other vendors' decompiled
  code. Facts needed for interoperability (opcodes, layouts, IDs) are fine.
- No personal data in logs or config (serials, MAC addresses, paths).
