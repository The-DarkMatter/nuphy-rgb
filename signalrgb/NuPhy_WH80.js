export function Name() { return "NuPhy WH80"; }
export function VendorId() { return 0x19F5; }
export function ProductId() { return 0xA011; }
export function Publisher() { return "nuphy-rgb"; }
export function Size() { return [18, 6]; }
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
const vLedNames = ["Esc", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12", "`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Backspace", "Insert", "Home", "Page Up", "Tab", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]", "\\", "Delete", "End", "Page Down", "Caps Lock", "A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'", "Enter", "Left Shift", "Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "Right Shift", "Up", "Left Ctrl", "Left Win", "Left Alt", "Space", "Right Alt", "Fn", "Right Ctrl", "Left", "Down", "Right"];
const vLedPositions = [[0, 0], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0], [7, 0], [8, 0], [9, 0], [10, 0], [11, 0], [12, 0], [13, 0], [0, 1], [1, 1], [2, 1], [3, 1], [4, 1], [5, 1], [6, 1], [7, 1], [8, 1], [9, 1], [10, 1], [11, 1], [12, 1], [13, 1], [15, 1], [16, 1], [17, 1], [0, 2], [1, 2], [2, 2], [3, 2], [4, 2], [5, 2], [6, 2], [7, 2], [8, 2], [9, 2], [10, 2], [11, 2], [12, 2], [13, 2], [15, 2], [16, 2], [17, 2], [0, 3], [1, 3], [2, 3], [3, 3], [4, 3], [5, 3], [6, 3], [7, 3], [8, 3], [9, 3], [10, 3], [11, 3], [13, 3], [0, 4], [2, 4], [3, 4], [4, 4], [5, 4], [6, 4], [7, 4], [8, 4], [9, 4], [10, 4], [11, 4], [13, 4], [16, 4], [0, 5], [1, 5], [2, 5], [6, 5], [10, 5], [11, 5], [12, 5], [15, 5], [16, 5], [17, 5]];
const vLedIndices = [9, 21, 33, 45, 57, 69, 81, 93, 8, 20, 32, 44, 56, 7, 19, 31, 43, 55, 67, 79, 91, 6, 18, 30, 42, 54, 66, 78, 76, 62, 5, 17, 29, 41, 53, 65, 77, 89, 4, 16, 28, 40, 52, 64, 90, 88, 74, 3, 15, 27, 39, 51, 63, 75, 87, 2, 14, 26, 38, 50, 1, 25, 37, 49, 61, 73, 85, 0, 12, 24, 36, 48, 60, 10, 22, 34, 46, 58, 82, 70, 94, 72, 84];

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
