const seconds = Math.max(15, Number(process.env.SOAK_SECONDS || 60));
const websocketUrl = process.env.CAMERA_WS_URL || "ws://127.0.0.1:8765/ws/camera";
const statusUrl = process.env.STATUS_URL || "http://127.0.0.1:8765/api/status";

function trackedClient(name) {
  const state = { name, frames: 0, bytes: 0, firstSequence: null, lastSequence: null, invalid: 0, reordered: 0 };
  const socket = new WebSocket(websocketUrl);
  socket.binaryType = "arraybuffer";
  const opened = new Promise((resolve, reject) => {
    socket.onopen = resolve;
    socket.onerror = () => reject(new Error(`${name} could not connect`));
  });
  socket.onmessage = (event) => {
    if (!(event.data instanceof ArrayBuffer) || event.data.byteLength < 24) { state.invalid += 1; return; }
    const bytes = new Uint8Array(event.data);
    const header = new DataView(event.data);
    const isEnvelope = bytes[0] === 73 && bytes[1] === 67 && bytes[2] === 65 && bytes[3] === 77;
    const length = isEnvelope ? header.getUint32(16, true) : 0;
    const sequence = isEnvelope ? header.getUint32(4, true) : null;
    const jpegStart = 20;
    if (!isEnvelope || length !== event.data.byteLength - jpegStart || bytes[jpegStart] !== 0xff || bytes[jpegStart + 1] !== 0xd8) {
      state.invalid += 1;
      return;
    }
    if (state.lastSequence !== null && sequence <= state.lastSequence) state.reordered += 1;
    state.firstSequence ??= sequence;
    state.lastSequence = sequence;
    state.frames += 1;
    state.bytes += length;
  };
  return { socket, state, opened };
}

async function healthyStatus() {
  const response = await fetch(statusUrl, { cache: "no-store" });
  if (!response.ok) throw new Error(`Status endpoint returned ${response.status}`);
  const status = await response.json();
  if (!status.connected || !status.telemetry?.camera_ready) throw new Error("Camera target disconnected during soak");
  return status;
}

const startedAt = Date.now();
const first = trackedClient("fast-a");
let second = trackedClient("fast-b");
const passive = new WebSocket(websocketUrl);
passive.binaryType = "arraybuffer";
await Promise.all([first.opened, second.opened, new Promise((resolve, reject) => {
  passive.onopen = resolve;
  passive.onerror = () => reject(new Error("passive client could not connect"));
})]);

const samples = [];
let reconnected = false;
try {
  while (Date.now() - startedAt < seconds * 1000) {
    samples.push(await healthyStatus());
    const elapsed = (Date.now() - startedAt) / 1000;
    if (!reconnected && elapsed >= seconds / 3) {
      second.socket.close(1000, "reconnect-test");
      await new Promise((resolve) => setTimeout(resolve, 750));
      second = trackedClient("fast-b-reconnected");
      await second.opened;
      reconnected = true;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
} finally {
  first.socket.close();
  second.socket.close();
  passive.close();
}

for (const client of [first.state, second.state]) {
  if (client.invalid || client.reordered) throw new Error(`${client.name} transport errors: ${JSON.stringify(client)}`);
  if (client.frames < seconds * 2 / 3) throw new Error(`${client.name} received too few frames: ${client.frames}`);
}
const sourceProgress = samples.at(-1).frame_sequence - samples[0].frame_sequence;
if (sourceProgress < seconds * 2) throw new Error(`Source progressed only ${sourceProgress} frames in ${seconds} seconds`);
const runtimeSamples = samples.map((sample) => sample.runtime).filter(Boolean);
let memorySummary = "runtime memory unavailable";
if (runtimeSamples.length) {
  const rss = runtimeSamples.map((sample) => Number(sample.rss_bytes));
  const rssRise = rss.at(-1) - rss[0];
  const rssSpan = Math.max(...rss) - Math.min(...rss);
  if (rssRise > 64 * 1024 * 1024 || rssSpan > 128 * 1024 * 1024) {
    throw new Error(`Server memory budget exceeded: rise ${rssRise} bytes, span ${rssSpan} bytes`);
  }
  const threads = runtimeSamples.map((sample) => Number(sample.threads));
  if (Math.max(...threads) - Math.min(...threads) > 8) throw new Error("Server thread count was not stable during soak");
  memorySummary = `RSS rise ${rssRise} bytes / span ${rssSpan} bytes`;
}
const firstTelemetry = samples[0].telemetry;
for (const sample of samples) {
  if (sample.telemetry.ble_advertising !== firstTelemetry.ble_advertising || sample.telemetry.wifi_ap_active !== firstTelemetry.wifi_ap_active || sample.telemetry.wifi_station_connected !== firstTelemetry.wifi_station_connected) {
    throw new Error("BLE or Wi-Fi device state changed unexpectedly during soak");
  }
}
console.log(
  `SOAK_OK: ${seconds}s, source +${sourceProgress} frames, fast-a ${first.state.frames} frames, ` +
  `reconnected fast-b ${second.state.frames} frames, passive client did not stall delivery, ${samples.length} health samples, ${memorySummary}`,
);
