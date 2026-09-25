import {
  Bluetooth,
  Camera,
  Eye,
  EyeOff,
  MonitorSmartphone,
  PlugZap,
  Power,
  RadioTower,
  RefreshCw,
  Router,
  Search,
  Signal,
  SlidersHorizontal,
  Usb,
  Wifi,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import type { BenchStatus, Hardware, HostWifiScan, Inspection, WifiNetwork } from "./types";

type LogTone = "ok" | "warn" | "error";
type Log = (channel: string, message: string, tone?: LogTone) => void;

function bytes(value?: number) {
  if (!Number.isFinite(value)) return "--";
  if ((value || 0) < 1024) return `${value} B`;
  if ((value || 0) < 1024 ** 2) return `${((value || 0) / 1024).toFixed(1)} KB`;
  return `${((value || 0) / 1024 ** 2).toFixed(1)} MB`;
}

function uptime(value?: number) {
  if (!value) return "--";
  const seconds = Math.floor(value / 1000);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m ${seconds % 60}s`;
}

function capabilitySet(inspection: Inspection | null) {
  return new Set((inspection?.capabilities || []).map((item) => item.id));
}

export function selectedHasLiveAdapter(selected: Hardware | null, status: BenchStatus | null) {
  return Boolean(selected?.kind === "serial" && selected.device && status?.connected && status.port === selected.device);
}

function Direction({ label, value, active }: { label: string; value: string; active: boolean }) {
  return <span className="radio-direction"><i className={active ? "active" : ""} /><span>{label}</span><b>{value}</b></span>;
}

type CameraPerformance = { browserFps: number; latencyMs: number; throughputKbps: number; droppedFrames: number; stalls: number };

function CameraSocketImage({ active, resetKey, onState, onPerformance }: { active: boolean; resetKey: number; onState: (failed: boolean) => void; onPerformance: (performance: CameraPerformance) => void }) {
  const imageRef = useRef<HTMLImageElement | null>(null);
  const stateCallback = useRef(onState);
  stateCallback.current = onState;
  const performanceCallback = useRef(onPerformance);
  performanceCallback.current = onPerformance;

  useEffect(() => {
    if (!active) return;
    let disposed = false;
    let decoding = false;
    let pending: { jpeg: ArrayBuffer; sequence: number | null; receivedAt: number } | null = null;
    let reconnectTimer = 0;
    let socket: WebSocket | null = null;
    let pageVisible = !document.hidden;
    let lastSequence: number | null = null;
    let droppedFrames = 0;
    let lastMetricAt = 0;
    let activeUrl = "";
    const displayed: Array<{ at: number; bytes: number }> = [];
    const displayLatest = () => {
      if (decoding || disposed || !pending || !imageRef.current) return;
      decoding = true;
      const frame = pending;
      pending = null;
      const image = imageRef.current;
      const url = URL.createObjectURL(new Blob([frame.jpeg], { type: "image/jpeg" }));
      image.onload = () => {
        if (activeUrl) URL.revokeObjectURL(activeUrl);
        activeUrl = url;
        decoding = false;
        if (frame.sequence !== null && lastSequence !== null && frame.sequence > lastSequence + 1) droppedFrames += frame.sequence - lastSequence - 1;
        if (frame.sequence !== null) lastSequence = frame.sequence;
        stateCallback.current(false);
        const now = Date.now();
        displayed.push({ at: now, bytes: frame.jpeg.byteLength });
        while (displayed.length && now - displayed[0].at > 2000) displayed.shift();
        if (now - lastMetricAt >= 500) {
          const elapsed = displayed.length > 1 ? displayed[displayed.length - 1].at - displayed[0].at : 0;
          const browserFps = elapsed > 0 ? (displayed.length - 1) * 1000 / elapsed : displayed.length;
          const throughputKbps = elapsed > 0 ? displayed.reduce((sum, item) => sum + item.bytes, 0) * 8 / elapsed : 0;
          performanceCallback.current({ browserFps, latencyMs: frame.receivedAt ? Math.max(0, now - frame.receivedAt) : 0, throughputKbps, droppedFrames, stalls: 0 });
          lastMetricAt = now;
        }
        displayLatest();
      };
      image.onerror = () => {
        URL.revokeObjectURL(url);
        decoding = false;
        stateCallback.current(true);
        displayLatest();
      };
      image.src = url;
    };
    const connect = () => {
      if (disposed || !pageVisible || socket?.readyState === WebSocket.OPEN || socket?.readyState === WebSocket.CONNECTING) return;
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${protocol}://${window.location.host}/ws/camera`);
      socket.binaryType = "arraybuffer";
      socket.onmessage = (event) => {
        if (disposed || !(event.data instanceof ArrayBuffer)) return;
        const packet = event.data;
        const header = new DataView(packet, 0, Math.min(packet.byteLength, 20));
        const enveloped = packet.byteLength >= 20 && header.getUint8(0) === 73 && header.getUint8(1) === 67 && header.getUint8(2) === 65 && header.getUint8(3) === 77;
        const declaredLength = enveloped ? header.getUint32(16, true) : packet.byteLength;
        pending = {
          sequence: enveloped ? header.getUint32(4, true) : null,
          receivedAt: enveloped ? header.getFloat64(8, true) : 0,
          jpeg: enveloped ? packet.slice(20, 20 + declaredLength) : packet,
        };
        displayLatest();
      };
      socket.onclose = () => {
        socket = null;
        if (!disposed) {
          stateCallback.current(true);
          if (pageVisible) reconnectTimer = window.setTimeout(connect, 750);
        }
      };
      socket.onerror = () => socket?.close();
    };
    const visibilityChanged = () => {
      pageVisible = !document.hidden;
      if (pageVisible) connect();
      else socket?.close(1000, "hidden tab");
    };
    document.addEventListener("visibilitychange", visibilityChanged);
    connect();
    return () => {
      disposed = true;
      document.removeEventListener("visibilitychange", visibilityChanged);
      window.clearTimeout(reconnectTimer);
      socket?.close();
      if (activeUrl) URL.revokeObjectURL(activeUrl);
    };
  }, [active, resetKey]);

  return <img ref={imageRef} alt="Live camera stream from selected device" />;
}

function DirectCameraImage({ active, url, resetKey, onState }: { active: boolean; url: string; resetKey: number; onState: (failed: boolean) => void }) {
  if (!active || !url) return null;
  return <img key={resetKey} src={`${url}${url.includes("?") ? "&" : "?"}session=${resetKey}`} alt="Live direct camera stream from selected device" onLoad={() => onState(false)} onError={() => onState(true)} />;
}

export function DeviceLivePanel({ selected, inspection, status, onRefresh, onLog }: {
  selected: Hardware | null;
  inspection: Inspection | null;
  status: BenchStatus | null;
  onRefresh: () => Promise<void> | void;
  onLog: Log;
}) {
  const [streamKey, setStreamKey] = useState(0);
  const [streamError, setStreamError] = useState(false);
  const [desiredTransport, setDesiredTransport] = useState<"direct" | "websocket">("direct");
  const [activeTransport, setActiveTransport] = useState<"direct" | "websocket" | null>(null);
  const [transportBusy, setTransportBusy] = useState(false);
  const [cameraBusy, setCameraBusy] = useState("");
  const [cameraControlsOpen, setCameraControlsOpen] = useState(false);
  const [cameraPerformance, setCameraPerformance] = useState<CameraPerformance>({ browserFps: 0, latencyMs: 0, throughputKbps: 0, droppedFrames: 0, stalls: 0 });
  const live = selectedHasLiveAdapter(selected, status);
  const telemetry = live ? status?.telemetry || {} : {};
  const capabilities = capabilitySet(inspection);
  const hasBle = capabilities.has("ble") || Boolean(live && (telemetry.ble_advertisement_configured || telemetry.ble_device_address));
  const hasWifi = capabilities.has("wifi_24") || capabilities.has("wifi_5") || Boolean(live && (telemetry.wifi_ap_ssid || telemetry.wifi_station_status));
  const cameraComponent = inspection?.components.find((item) => item.type === "camera");
  const cameraExpected = Boolean(live && (telemetry.camera_ready || cameraComponent || selected?.is_esp32));
  const cameraReady = Boolean(cameraExpected && telemetry.camera_ready);
  const directUrl = telemetry.wifi_station_connected && telemetry.wifi_station_ip ? `http://${telemetry.wifi_station_ip}/stream` : "";
  const benchmarkFps = activeTransport === "direct" ? Number(telemetry.camera_fps || 0) : cameraPerformance.browserFps;
  const benchmarkStalls = activeTransport === "direct" ? 0 : cameraPerformance.stalls;
  const benchmarkTone = benchmarkFps <= 0 ? "warming" : benchmarkFps >= 23.5 && benchmarkStalls === 0 ? "pass" : benchmarkFps >= 12 && benchmarkStalls <= 1 ? "degraded" : "fail";

  useEffect(() => {
    setDesiredTransport("direct");
    setActiveTransport(null);
    setStreamError(false);
    setStreamKey((value) => value + 1);
    setCameraPerformance({ browserFps: 0, latencyMs: 0, throughputKbps: 0, droppedFrames: 0, stalls: 0 });
  }, [selected?.id]);

  useEffect(() => {
    if (!cameraReady) return;
    const requested = desiredTransport === "direct" && directUrl ? "direct" : "websocket";
    let current = true;
    setTransportBusy(true);
    setStreamError(false);
    setCameraPerformance({ browserFps: 0, latencyMs: 0, throughputKbps: 0, droppedFrames: 0, stalls: 0 });
    void api.setCameraTransport(requested).then((result) => {
      if (!current) return;
      if (!result.confirmed) throw new Error(`Camera transport did not confirm ${requested} mode`);
      setActiveTransport(requested);
      setStreamKey((value) => value + 1);
      onLog("camera", requested === "direct" ? `Streaming directly from ${result.direct_url}.` : "Streaming through the USB WebSocket fallback.", "ok");
    }).catch((error) => {
      if (!current) return;
      if (requested === "direct") {
        onLog("camera", "Direct camera path was unavailable; switching to USB WebSocket.", "warn");
        setDesiredTransport("websocket");
      } else {
        setStreamError(true);
        onLog("camera", error instanceof Error ? error.message : "Camera transport failed", "error");
      }
    }).finally(() => { if (current) setTransportBusy(false); });
    return () => { current = false; };
  }, [cameraReady, desiredTransport, directUrl, selected?.id, onLog]);

  const refresh = async () => {
    try {
      if (live) await api.refreshDeviceStatus();
      await onRefresh();
      setStreamError(false); setStreamKey((value) => value + 1);
      onLog("device", "Live camera and radio telemetry refreshed.", "ok");
    } catch (error) { onLog("device", error instanceof Error ? error.message : "Live status refresh failed", "error"); }
  };

  const setCameraControl = async (setting: "brightness" | "contrast" | "saturation" | "sharpness" | "exposure" | "quality", value: number) => {
    setCameraBusy(setting);
    try {
      const result = await api.setCameraControl(setting, value);
      onLog("camera", result.confirmed ? `${setting} set to ${result.value}.` : `${setting} command was not confirmed.`, result.confirmed ? "ok" : "warn");
    } catch (error) {
      onLog("camera", error instanceof Error ? error.message : `Unable to set ${setting}.`, "error");
    } finally {
      setCameraBusy("");
    }
  };

  return <>
    <section className="live-device-grid">
      <div className="camera-panel">
        <div className="section-heading"><div><p className="eyebrow">Live input</p><h2>Camera</h2></div><div className="camera-metrics"><div className="camera-transport-selector segmented compact" role="group" aria-label="Camera transport"><button type="button" className={desiredTransport === "direct" ? "active" : ""} disabled={!directUrl || transportBusy} onClick={() => setDesiredTransport("direct")}><Wifi size={14} />Direct</button><button type="button" className={desiredTransport === "websocket" ? "active" : ""} disabled={transportBusy} onClick={() => setDesiredTransport("websocket")}><Usb size={14} />USB</button></div><span title={activeTransport === "direct" ? "Frames per second reported by the device's direct stream" : "Frames decoded and painted by this browser"}><strong>{benchmarkFps.toFixed(1)}</strong> FPS</span><span title="JPEG payload throughput"><strong>{activeTransport === "direct" ? "direct" : cameraPerformance.throughputKbps.toFixed(0)}</strong> {activeTransport === "direct" ? "path" : "kbps"}</span><span title="Camera frames discarded to preserve live latency"><strong>{activeTransport === "direct" ? 0 : cameraPerformance.droppedFrames}</strong> skipped</span><span title="One-second periods without a completed frame"><strong>{benchmarkStalls}</strong> stalls</span><span className={`camera-benchmark ${benchmarkTone}`} title="Pass requires at least 23.5 FPS with no stalls">{benchmarkTone}</span><button className={`icon-button ${cameraControlsOpen ? "active" : ""}`} type="button" aria-label="Camera image controls" title="Camera image controls" onClick={() => setCameraControlsOpen((value) => !value)}><SlidersHorizontal size={17} /></button><button className="icon-button" type="button" aria-label="Refresh camera and device telemetry" onClick={() => void refresh()}><RefreshCw size={17} /></button></div></div>
        <div className={`camera-viewport ${cameraReady && !streamError ? "receiving" : ""}`}>
          {cameraReady && activeTransport === "direct" && <DirectCameraImage active resetKey={streamKey} url={directUrl} onState={(failed) => { setStreamError(failed); if (failed) setDesiredTransport("websocket"); }} />}
          {cameraReady && activeTransport === "websocket" && <CameraSocketImage active resetKey={streamKey} onState={setStreamError} onPerformance={setCameraPerformance} />}
          {(!cameraReady || streamError || !activeTransport) && <div className="camera-empty"><Camera size={28} /><strong>{!cameraExpected ? "No camera detected for selected hardware" : streamError ? "Camera stream interrupted" : transportBusy ? "Opening fastest camera path" : cameraComponent?.status === "unavailable" ? `${cameraComponent.name} is configured but not detected` : "Camera detected; waiting for frames"}</strong></div>}
          {cameraReady && activeTransport && !streamError && <div className="feed-badge"><span />{activeTransport === "direct" ? "DEVICE DIRECT" : "USB WEBSOCKET"}</div>}
        </div>
        {cameraReady && cameraControlsOpen && <div className="camera-controls camera-control-drawer" aria-label="Camera image controls">
          {([
            ["brightness", "Brightness", -2, 2, telemetry.camera_brightness ?? 0],
            ["contrast", "Contrast", -2, 2, telemetry.camera_contrast ?? 0],
            ["saturation", "Saturation", -2, 2, telemetry.camera_saturation ?? 0],
            ["sharpness", "Sharpness", -2, 2, telemetry.camera_sharpness ?? 0],
            ["exposure", "Exposure", -2, 2, telemetry.camera_ae_level ?? 0],
            ["quality", "JPEG quality", 4, 63, telemetry.camera_jpeg_quality ?? 12],
          ] as const).map(([setting, label, min, max, value]) => <label key={setting}><span>{label}<b>{value}</b></span><input type="range" min={min} max={max} value={value} disabled={Boolean(cameraBusy)} onChange={(event) => void setCameraControl(setting, Number(event.target.value))} /></label>)}
        </div>}
      </div>
      <aside className="selected-hardware-panel" aria-label="Selected hardware live status">
        <div><p className="eyebrow">Control link</p><h2>Selected hardware</h2></div>
        <div className="hardware-primary"><span className="icon-tile"><Usb size={18} /></span><div><strong>{selected?.device || selected?.interface || selected?.ip_address || "No interface"}</strong><span>{telemetry.device || selected?.name || "Waiting for selection"}</span></div><b className={live ? "online" : "offline"}>{live ? "Online" : "Identity only"}</b></div>
        <dl className="hardware-stats"><div><dt>Packets</dt><dd>{live ? (status?.packets_received || 0).toLocaleString() : "--"}</dd></div><div><dt>Received</dt><dd>{live ? bytes(status?.bytes_received) : "--"}</dd></div><div><dt>Protocol</dt><dd>{live && telemetry.firmware ? "Compatible" : "Identity only"}</dd></div></dl>
        <div className={`radio-channel ${hasBle ? "" : "unsupported"}`} aria-disabled={!hasBle}><Bluetooth size={18} /><div><strong>Bluetooth (BLE)</strong><small>{live ? telemetry.ble_device_address || "Address unavailable" : hasBle ? "Hardware detected; telemetry unavailable" : "Unavailable on selected hardware"}</small><div className="direction-states"><Direction label="Broadcast" value={live ? telemetry.ble_advertising ? "On" : "Off" : hasBle ? "Detected" : "Unavailable"} active={Boolean(live && telemetry.ble_advertising)} /><Direction label="Incoming" value={live ? telemetry.ble_connected ? `${telemetry.ble_client_count || 0} connected` : "Waiting" : hasBle ? "Unknown" : "Unavailable"} active={Boolean(live && telemetry.ble_connected)} /><Direction label="Computer link" value={hasBle && status?.ble.connection_verified ? "Verified" : hasBle ? "None" : "Unavailable"} active={Boolean(hasBle && status?.ble.connection_verified)} /></div></div></div>
        <div className={`radio-channel ${hasWifi ? "" : "unsupported"}`} aria-disabled={!hasWifi}><Wifi size={18} /><div><strong>Wi-Fi</strong><small>{live ? telemetry.wifi_station_connected ? `${telemetry.wifi_station_ssid} at ${telemetry.wifi_station_ip}` : telemetry.wifi_ap_active ? `${telemetry.wifi_ap_ssid} broadcasting` : "Radio idle" : hasWifi ? "Hardware detected; telemetry unavailable" : "Unavailable on selected hardware"}</small><div className="direction-states"><Direction label="Broadcast" value={live ? telemetry.wifi_ap_active ? "On" : "Off" : hasWifi ? "Detected" : "Unavailable"} active={Boolean(live && telemetry.wifi_ap_active)} /><Direction label="Clients" value={live ? `${telemetry.wifi_ap_clients || 0}` : hasWifi ? "Unknown" : "Unavailable"} active={Boolean(live && telemetry.wifi_ap_clients)} /><Direction label="Router" value={live ? telemetry.wifi_station_connected ? "Connected" : "Offline" : hasWifi ? "Unknown" : "Unavailable"} active={Boolean(live && telemetry.wifi_station_connected)} /></div></div></div>
      </aside>
    </section>
    <section className="device-telemetry"><div className="section-heading"><div><p className="eyebrow">Compatible device adapter</p><h2>Telemetry reported by selected device</h2></div><span>{live ? "Live" : "No compatible data received"}</span></div><div className="telemetry-grid"><div><span>Firmware / OS</span><strong>{telemetry.firmware || "--"}</strong></div><div><span>Camera</span><strong>{telemetry.camera_ready ? `Ready${telemetry.camera_sensor_pid ? ` | PID ${telemetry.camera_sensor_pid}` : ""}` : telemetry.camera_status || "Unavailable"}</strong></div><div><span>Free memory / heap</span><strong>{bytes(telemetry.free_heap_bytes)}</strong></div><div><span>PSRAM</span><strong>{bytes(telemetry.psram_bytes)}</strong></div><div><span>Uptime</span><strong>{uptime(telemetry.uptime_ms)}</strong></div><div><span>Radio clients</span><strong>{live ? (telemetry.wifi_ap_clients || 0) + (telemetry.ble_client_count || 0) : "--"}</strong></div></div></section>
  </>;
}

function ActionMessage({ text }: { text: string }) {
  return text ? <p className="control-message" role="status">{text}</p> : null;
}

export function WirelessControls({ selected, inspection, status, onLog }: { selected: Hardware | null; inspection: Inspection | null; status: BenchStatus | null; onLog: Log }) {
  const capabilities = capabilitySet(inspection);
  const live = selectedHasLiveAdapter(selected, status) && Boolean(status?.telemetry.firmware);
  const telemetry = live ? status?.telemetry || {} : {};
  const hasBle = capabilities.has("ble") || Boolean(live && (telemetry.ble_advertisement_configured || telemetry.ble_device_address));
  const hasWifi = capabilities.has("wifi_24") || capabilities.has("wifi_5") || Boolean(live && (telemetry.wifi_ap_ssid || telemetry.wifi_station_status));
  const [radio, setRadio] = useState<"ble" | "wifi">(hasBle || !hasWifi ? "ble" : "wifi");
  const [bleMode, setBleMode] = useState<"broadcast" | "nearby">("broadcast");
  const [wifiMode, setWifiMode] = useState<"broadcast" | "router">("broadcast");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [bleDevices, setBleDevices] = useState(status?.ble.devices || []);
  const [deviceNetworks, setDeviceNetworks] = useState<WifiNetwork[]>(telemetry.wifi_networks || []);
  const [hostNetworks, setHostNetworks] = useState<HostWifiScan | null>(null);
  const [ssid, setSsid] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [accessName, setAccessName] = useState(telemetry.device || "");
  const [accessPassword, setAccessPassword] = useState("");

  useEffect(() => { setBleDevices(status?.ble.devices || []); }, [status?.ble.devices]);
  useEffect(() => { if (hasWifi && !hasBle) setRadio("wifi"); else if (hasBle && !hasWifi) setRadio("ble"); }, [hasBle, hasWifi]);
  useEffect(() => { if (telemetry.device) setAccessName(telemetry.device); }, [telemetry.device]);

  const act = async (id: string, task: () => Promise<string>) => {
    setBusy(id); setMessage("");
    try { const result = await task(); setMessage(result); onLog("wireless", result, "ok"); }
    catch (error) { const text = error instanceof Error ? error.message : "Wireless operation failed"; setMessage(text); onLog("wireless", text, "error"); }
    finally { setBusy(""); }
  };

  const sortedBle = useMemo(() => [...bleDevices].sort((a, b) => b.rssi_dbm - a.rssi_dbm), [bleDevices]);
  if (!inspection) return null;
  return <section className="wireless-controls">
    <div className="section-heading"><div><p className="eyebrow">Wireless controls for selected hardware</p><h2>Connections</h2></div><span className={`status ${hasBle || hasWifi ? "status-verified" : "status-unavailable"}`}>{!hasBle && !hasWifi ? "Unavailable" : radio === "ble" ? "Bluetooth (BLE)" : "Wi-Fi"}</span></div>
    <div className="wireless-selector"><span>{hasBle && hasWifi ? "Select a supported radio" : hasBle ? "This hardware reports Bluetooth (BLE)" : hasWifi ? "This hardware reports Wi-Fi" : "No wireless capability was identified"}</span><div className="segmented" role="tablist" aria-label="Wireless connection"><button type="button" className={radio === "ble" ? "active" : ""} disabled={!hasBle} onClick={() => setRadio("ble")}><Bluetooth size={16} />Bluetooth (BLE)</button><button type="button" className={radio === "wifi" ? "active" : ""} disabled={!hasWifi} onClick={() => setRadio("wifi")}><Wifi size={16} />Wi-Fi</button></div></div>

    {radio === "ble" && hasBle && <div className="wireless-panel">
      <div className="segmented compact"><button type="button" className={bleMode === "broadcast" ? "active" : ""} onClick={() => setBleMode("broadcast")}>Broadcast from device</button><button type="button" className={bleMode === "nearby" ? "active" : ""} onClick={() => setBleMode("nearby")}>Read nearby with computer</button></div>
      {bleMode === "broadcast" ? <><div className="connection-summary"><div className="summary-title"><span className="icon-tile"><RadioTower size={18} /></span><div><small>Bluetooth broadcast name</small><strong>{telemetry.device || "Unavailable"}</strong></div><span className={telemetry.ble_advertising ? "status status-verified" : "status status-unavailable"}>{telemetry.ble_advertising ? "On" : "Off"}</span></div><dl><div><dt>Profile</dt><dd>Connectable GATT</dd></div><div><dt>Connected clients</dt><dd>{telemetry.ble_client_count || 0}</dd></div><div><dt>Verified sessions</dt><dd>{telemetry.ble_connections_total || 0}</dd></div><div><dt>Device address</dt><dd>{telemetry.ble_device_address || "--"}</dd></div><div><dt>Service</dt><dd>{telemetry.ble_service_uuid || "--"}</dd></div></dl></div><div className="control-toolbar"><button className="tool-button" type="button" disabled={!live || Boolean(busy)} onClick={() => void act("ble-power", async () => { const result = await api.setBlePower(!telemetry.ble_advertising); return result.confirmed ? `BLE broadcast ${result.enabled ? "started" : "stopped"} and confirmed.` : "BLE command sent but not confirmed."; })}><Power size={15} />{busy === "ble-power" ? "Applying..." : telemetry.ble_advertising ? "Stop BLE broadcast" : "Start BLE broadcast"}</button><details><summary>Broadcast settings</summary><div className="inline-settings"><label>Device name<input value={accessName} maxLength={24} onChange={(event) => setAccessName(event.target.value)} /></label><label>New direct-access password<input type="password" value={accessPassword} maxLength={63} onChange={(event) => setAccessPassword(event.target.value)} placeholder="Leave blank to keep current" /></label><button className="tool-button" type="button" disabled={!live || !accessName || Boolean(busy)} onClick={() => void act("access", async () => { const result = await api.configureDeviceAccess(accessName, accessPassword); setAccessPassword(""); return result.confirmed ? `Device access name updated to ${result.name}.` : "Access settings sent but not confirmed."; })}>Apply settings</button></div></details></div></> : <><div className="view-heading"><div><h3>BLE advertisements read by this computer</h3><p>{sortedBle.length ? `${sortedBle.length} nearby advertisements received` : "No scan results yet"}</p></div><button className="primary" type="button" disabled={Boolean(busy)} onClick={() => void act("ble-scan", async () => { const result = await api.scanBle(); setBleDevices(result.devices || []); return result.detected ? `${result.name} received at ${result.rssi_dbm} dBm.` : `${result.devices?.length || 0} nearby BLE devices found.`; })}><Search size={15} />{busy === "ble-scan" ? "Scanning..." : "Scan with computer"}</button></div><div className="discovery-list">{sortedBle.map((device) => <div className="discovery-row" key={device.address}><Bluetooth size={16} /><div><strong>{device.name || "Unnamed BLE device"}</strong><small>{device.address}{device.service_uuids.length ? ` | ${device.service_uuids.join(", ")}` : ""}</small></div><span>{device.rssi_dbm} dBm</span></div>)}{!sortedBle.length && <p>No BLE advertisements detected.</p>}</div><button className="tool-button" type="button" disabled={!status?.ble.detected || Boolean(busy)} onClick={() => void act("ble-verify", async () => { const result = await api.verifyBle(); return result.verified ? `GATT data exchange verified with ${result.address}.` : result.error || "GATT verification failed."; })}><PlugZap size={15} />{busy === "ble-verify" ? "Verifying..." : "Verify selected-device GATT"}</button></>}
    </div>}

    {radio === "wifi" && hasWifi && <div className="wireless-panel">
      <div className="segmented compact"><button type="button" className={wifiMode === "broadcast" ? "active" : ""} onClick={() => setWifiMode("broadcast")}>Broadcast from device</button><button type="button" className={wifiMode === "router" ? "active" : ""} onClick={() => setWifiMode("router")}>Connect device to Wi-Fi</button></div>
      {wifiMode === "broadcast" ? <><div className="connection-summary"><div className="summary-title"><span className="icon-tile"><Router size={18} /></span><div><small>Direct Wi-Fi broadcast name</small><strong>{telemetry.wifi_ap_ssid || "Unavailable"}</strong></div><span className={telemetry.wifi_ap_active ? "status status-verified" : "status status-unavailable"}>{telemetry.wifi_ap_active ? "Broadcasting" : "Off"}</span></div><dl><div><dt>Band</dt><dd>2.4 GHz</dd></div><div><dt>Connected clients</dt><dd>{telemetry.wifi_ap_clients || 0}</dd></div><div><dt>Device address</dt><dd>{telemetry.wifi_ap_ip || "--"}</dd></div><div><dt>Security</dt><dd>{telemetry.wifi_ap_configured === false ? "Setup required" : "Password protected"}</dd></div></dl></div><button className="tool-button" type="button" disabled={!live || telemetry.wifi_ap_configured === false || Boolean(busy)} title={telemetry.wifi_ap_configured === false ? "Configure a direct-access password in Broadcast settings first" : undefined} onClick={() => void act("wifi-power", async () => { const result = await api.setWifiAccessPoint(!telemetry.wifi_ap_active); return result.confirmed ? `Direct Wi-Fi broadcast ${result.enabled ? "started" : "stopped"} at ${result.ip || "its configured address"}.` : "Wi-Fi command sent but not confirmed."; })}><Power size={15} />{busy === "wifi-power" ? "Applying..." : telemetry.wifi_ap_active ? "Stop Wi-Fi broadcast" : "Start Wi-Fi broadcast"}</button></> : <><div className="current-link"><Wifi size={18} /><div><small>Selected device internet link</small><strong>{telemetry.wifi_station_ssid || "Not connected"}</strong><span>{telemetry.wifi_station_connected ? `${telemetry.wifi_station_ip} | ${telemetry.wifi_rssi_dbm} dBm` : telemetry.wifi_station_status || "No router selected"}</span></div><b className={telemetry.wifi_station_connected ? "online" : "offline"}>{telemetry.wifi_station_connected ? "Connected" : "Offline"}</b></div><div className="internet-check"><div><strong>Internet traffic verification</strong><span>{telemetry.internet_reachable ? `${telemetry.internet_probe_latency_ms || 0} ms | ${bytes(telemetry.internet_bytes_sent)} out / ${bytes(telemetry.internet_bytes_received)} in` : (telemetry.internet_probe_status || "Not tested").replaceAll("_", " ")}</span></div><button className="tool-button" type="button" disabled={!live || !telemetry.wifi_station_connected || Boolean(busy)} onClick={() => void act("internet", async () => { const result = await api.testDeviceInternet(); return result.reachable ? `Internet verified in ${result.latency_ms} ms (${bytes(result.bytes_sent)} out / ${bytes(result.bytes_received)} in).` : `Internet test result: ${result.status.replaceAll("_", " ")}.`; })}><Signal size={15} />{busy === "internet" ? "Testing..." : "Test Internet"}</button></div><div className="view-heading"><div><h3>Available networks</h3><p>Compare what the selected device and this computer can receive.</p></div><div className="control-toolbar"><button className="primary" type="button" disabled={!live || Boolean(busy)} onClick={() => void act("wifi-scan", async () => { const result = await api.scanDeviceWifi(); setDeviceNetworks(result.networks || []); return `${result.networks.length} compatible networks found by the selected device.`; })}><Search size={15} />{busy === "wifi-scan" ? "Scanning..." : "Scan with device"}</button><button className="tool-button" type="button" disabled={Boolean(busy)} onClick={() => void act("host-wifi", async () => { const result = await api.scanHostWifi(); setHostNetworks(result); return result.available ? `${result.networks.length} networks found by this computer.` : result.error || "Computer Wi-Fi adapter unavailable."; })}><MonitorSmartphone size={15} />{busy === "host-wifi" ? "Scanning..." : "Scan computer"}</button></div></div><div className="network-columns"><div><strong>Selected device radio</strong><div className="discovery-list">{deviceNetworks.map((network, index) => <button type="button" className={ssid === network.ssid ? "selected discovery-row" : "discovery-row"} key={`${network.ssid}-${index}`} onClick={() => setSsid(network.ssid)}><Wifi size={16} /><div><strong>{network.ssid || "Hidden network"}</strong><small>Channel {network.channel || "--"} | {network.security || (network.secure ? "Secured" : "Open")}</small></div><span>{network.rssi_dbm ?? "--"} dBm</span></button>)}{!deviceNetworks.length && <p>No device scan results yet.</p>}</div></div><div><strong>Computer radio</strong><div className="discovery-list">{hostNetworks?.networks.map((network, index) => <div className="discovery-row" key={`${network.ssid}-${index}`}><MonitorSmartphone size={16} /><div><strong>{network.ssid || "Hidden network"}</strong><small>{network.authentication || "Security unknown"}</small></div><span>{network.signal_percent ?? "--"}%</span></div>)}{!hostNetworks?.networks.length && <p>Computer radio not scanned yet.</p>}</div></div></div><form className="wifi-form" onSubmit={(event) => { event.preventDefault(); void act("wifi-connect", async () => { const result = await api.configureWifi(ssid, password, remember); setPassword(""); return result.connected ? `${result.ssid} connected at ${result.ip}.` : `${result.ssid}: ${result.status.replaceAll("_", " ")}.`; }); }}><label>Network name<input required maxLength={32} value={ssid} onChange={(event) => setSsid(event.target.value)} placeholder="Select or enter an SSID" /></label><label>Password<span className="password-input"><input type={showPassword ? "text" : "password"} maxLength={63} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" /><button type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((value) => !value)}>{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></span></label><label className="remember"><input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} />Remember on selected device</label><button className="primary" type="submit" disabled={!live || !ssid || Boolean(busy)}><PlugZap size={15} />{busy === "wifi-connect" ? "Connecting..." : "Connect device"}</button></form></>}
    </div>}
    {!live && (hasBle || hasWifi) && <p className="compatibility-note">Radio hardware is identified, but device-side controls require the selected interface to expose the compatible bench protocol. Computer-side BLE and Wi-Fi scans remain available.</p>}
    <ActionMessage text={message} />
  </section>;
}
