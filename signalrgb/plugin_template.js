export function Name() { return "NuPhy WH80"; }
export function VendorId() { return 0x19F5; }
export function ProductId() { return 0xA011; }
export function Publisher() { return "WH80 RGB community"; }
export function Size() { return /*SIZE*/; }
export function DefaultPosition() { return [10, 100]; }
export function DefaultScale() { return 8.0; }
export function DeviceType() { return "keyboard"; }
export function ImageUrl() { return "https://assets.signalrgb.com/devices/default/keyboards/tkl-keyboard-render.png"; }
/* global
LightingMode:readonly
forcedColor:readonly
*/
export function ControllableParameters() {
	return [
		{property:"LightingMode", group:"lighting", label:"Lighting Mode", description:"Canvas follows the active SignalRGB effect; Forced sets one colour", type:"combobox", values:["Canvas", "Forced"], default:"Canvas"},
		{property:"forcedColor", group:"lighting", label:"Forced Color", description:"Colour used in Forced mode", min:"0", max:"360", type:"color", default:"#009bde"},
	];
}

// Raw interface: interface 1, usage page 0x01, usage 0x00 (64-byte reports, report id 0).
export function Validate(endpoint) {
	return endpoint.interface === 1 && endpoint.usage_page === 0x0001 && endpoint.usage === 0x0000;
}

// Generated from wh80/led_map.json: LED index on the keyboard for each SignalRGB LED.
const vLedNames = /*LED_NAMES*/;
const vLedPositions = /*LED_POSITIONS*/;
const vLedIndices = /*LED_INDICES*/;

export function LedNames() { return vLedNames; }
export function LedPositions() { return vLedPositions; }

// Protocol (see docs/PROTOCOL.md). Command 0xDD "LedSyncDownload" writes into a RAM
// framebuffer (no flash wear). The keyboard shows it instead of its own effect and
// returns to its saved lighting ~1-2 s after frames stop, so Shutdown needs no command.
const LED_SYNC_DOWNLOAD = 0xDD;
const TOTAL_LEDS = 96;           // key LEDs; the 48-LED front bar cannot be driven in direct mode (firmware limit)
const CHUNK = 56;

export function Initialize() {
	device.setFrameRateTarget(60);
	device.clearReadBuffer();
}

export function Render() {
	sendColors();
}

export function Shutdown(SystemSuspending) {
	// Nothing to do: the firmware's watchdog restores the keyboard's own effect.
}

function sendColors() {
	const frame = new Array(TOTAL_LEDS * 3).fill(0);
	const forced = LightingMode === "Forced" ? hexToRgb(forcedColor) : null;

	for (let i = 0; i < vLedIndices.length; i++) {
		const color = forced ? forced : device.color(vLedPositions[i][0], vLedPositions[i][1]);
		const o = vLedIndices[i] * 3;
		frame[o] = color[0];
		frame[o + 1] = color[1];
		frame[o + 2] = color[2];
	}

	// Only the key range is sent; side LEDs (96..143) are left as-is for now.
	const used = 96 * 3;
	for (let addr = 0; addr < used; addr += CHUNK) {
		sendChunk(addr, frame.slice(addr, Math.min(addr + CHUNK, used)));
	}
}

function sendChunk(addr, data) {
	const packet = new Array(65).fill(0);   // [0] = report id 0
	packet[1] = 0x55;
	packet[2] = LED_SYNC_DOWNLOAD;
	packet[5] = data.length;
	packet[6] = addr & 0xFF;
	packet[7] = (addr >> 8) & 0xFF;
	for (let i = 0; i < data.length; i++) {
		packet[9 + i] = data[i];
	}
	let sum = 0;
	for (let i = 5; i < 65; i++) { sum += packet[i]; }
	packet[4] = sum & 0xFF;

	device.write(packet, 65);
	waitAck(addr);
}

// The firmware has a single receive buffer: wait for the 0xAA ack before the next packet.
function waitAck(addr) {
	for (let tries = 0; tries < 4; tries++) {
		const r = device.read([0x00], 65, 5);
		if (device.getLastReadSize() <= 0) { continue; }
		const base = r[0] === 0xAA ? 0 : 1;   // tolerate report id being present or stripped
		if (r[base] === 0xAA && r[base + 1] === LED_SYNC_DOWNLOAD && r[base + 5] === (addr & 0xFF)) {
			return true;
		}
	}
	return false;
}

function hexToRgb(hex) {
	const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
	return [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)];
}
