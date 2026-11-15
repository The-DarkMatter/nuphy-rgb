# NuPhy WH80 raw-HID protocol (firmware 1.22 / 1.23)

USB `VID 0x19F5 / PID 0xA011`, interface 1, usage page `0x01` usage `0x00`,
64-byte reports on report ID 0. Bootloader is PID `0x8A04` ("NuPhy WH80 Upgrader").
The 2.4G dongle is PID `0x8F01`.

This is NuPhy's **hall-effect (HE) family** protocol. It is *not* the Air100 V3
protocol documented by [nuphykit](https://github.com/gig3m/nuphykit): different
frame layout, no session key, and `0xEE` means factory reset here.

Recovered for interoperability from NuPhyIO's public web app (HE driver,
`createCommand`, command enum) and checked against the command handler in
NuPhy's published firmware 1.23 (WCH CH32V RISC-V, image base `0x5000`, packet
handler `0x1990`, command jump table `0x160B8`). The firmware itself is not
included here; NuPhy publishes it.

## Frame

```
[0] 0x55 (host->dev)        reply: 0xAA ok, 0xAB + "cserr" = checksum error
[1] command
[2] 0x00                    (key; HE boards use plaintext)
[3] checksum = sum(bytes[4 .. 8+len]) & 0xFF   (data beyond len must be 0)
[4] len (<= 56)
[5] addr lo  [6] addr hi
[7] 0
[8..8+len] data
```

The reply echoes the header (`len`, `addr`) and carries data at byte 8.
Round trip is ~1 ms. The firmware has a single receive buffer: send, wait for
the ack, then send the next packet (pipelining loses packets).

## Commands (firmware jump table)

| cmd | name | notes |
|---|---|---|
| 0x01/0x02 | QuickCommStart/End | |
| 0x03 | GetInfo | fw version = data[1]<<8\|data[0] (hex), rf = data[5]<<8\|data[4], build date string |
| 0x04 | GetBase | |
| 0x05/0x06 | GetFunc/SetFunc | 64 B per mode at `mode*64`; lighting records below |
| 0x07/0x08/0x09 | Get default / Get use / Set use key matrix | 512 B per layer, 3 B per key `[type, code0, code1]` |
| 0x0A/0x0B | Get/SetLedDefine | per-key custom colours, 512 B per mode at `mode*512`, RGB per key index. **SetLedDefine writes flash directly** (`0x0801D800+addr`); fine for saving, never for streaming |
| 0x0C/0x0D | Get/SetMacro | |
| 0x10/0x11 | Get/SetGamepad | |
| 0xA0..0xA7 | RT / DKS / MT / TGL get+set | |
| 0xA8/0xA9/0xAA | Calibration start/end/info | don't touch |
| 0xB0 | (undocumented) | returns the 12-byte chip unique ID |
| 0xB1 | (undocumented) | sets an internal flag; unknown, avoid |
| **0xDD** | **LedSyncDownload** | **direct mode**: writes RGB into a RAM framebuffer (`addr+len <= 450`, 150 LEDs). First packet resets effect state; each packet reloads a watchdog (60) and the LED task skips the built-in effect while it is non-zero. Falls back to the saved effect ~1-2 s after the last frame. No flash access. ~125 fps for all 96 key LEDs. **Only the 96 key LEDs are displayed** (see below) |
| 0xDE | LedSyncUpload | read the rendered LED frame (3 B per LED, brightness-scaled) |
| 0xEE | RestoreFactorySettings | sets a flag; reset happens in the main loop. Never send |
| 0xF1/0xF2 | Get/SetAppDefine | |

## Lighting records inside the Func block (`mode*64 + offset`)

Modes: 0, 1, 2 (app names: Gaming, Windows, Mac).

| offset | record |
|---|---|
| 8  | main backlight: `effect, brightness 0-100, speed (stored 4-x), direction, isRGB, colorIndex, R, G, B` |
| 24 | side light: `effect, brightness, speed, isRGB, colorIndex, R, G, B` |
| 35 | third light, same layout as side |

Main effect indices: 0 Custom (renders LedDefine), 1 Spectrum, 2 Gradient,
3 Static, 4 Breathe, 5 Flower, 6 Wave, 7 Wave up/down, 8 Fountain, 9 Galaxy,
10 Rotation, 11 Tide, 12 Sea wave, 13 Ripple, 14 Constant ripple,
15 Single point, 16 Grid, 17 Piano, 18 Flowing, 19 Falling rain, 20 Starry,
21 Firework, 22 Wave band, 255 Off.

Direct-mode output is scaled by the active mode's backlight brightness.

### Direct mode only drives the keys

While direct mode is active, the LED task skips the built-in key effect and
calls a render routine (`0xCA84`) that copies exactly `0x60` = 96 LEDs from the
`0xDD` framebuffer, applying the brightness table. The 48-LED front light bar is
never read from the framebuffer; it keeps running its own saved side-light
effect (effect / colour / brightness at Func offset 24). Driving it live would
need a firmware change.

## LED indexing

LED index = key data index (same index into the key matrix, LedDefine, 0xDD and
0xDE). 96 key slots (83 populated, see `wh80/led_map.json`) + 48 front-bar LEDs
at 96..143 (readable with 0xDE, not drivable with 0xDD).
Matrix slots 96-98 are the knob (mute, vol-, vol+).

## Safety notes

- `0xEE` is **RestoreFactorySettings** on this board (it is the session
  handshake on the Air100 V3). A frame with a bad checksum is rejected with
  `0xAB "cserr"`, which is the only reason a mistaken `0xEE` is harmless.
- `0x0B` is verified to write flash on every packet. The other Set commands
  (`0x06`, `0x09`, `0x0D`, `0x11`, `0xA1`/`0xA3`/`0xA5`/`0xA7`, `0xF2`) store
  persistent settings and should be assumed to as well. Stream with `0xDD` only.
- Avoid `0xA8`/`0xA9` (calibration) and the undocumented `0xB1`.
