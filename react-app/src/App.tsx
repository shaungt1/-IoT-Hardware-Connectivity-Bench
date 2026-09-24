import * as Accordion from "@radix-ui/react-accordion";
import * as Tooltip from "@radix-ui/react-tooltip";
import {
  Activity,
  Bluetooth,
  CircuitBoard,
  ChevronDown,
  CircleDot,
  Cpu,
  Database,
  ExternalLink,
  FileCode2,
  HardDrive,
  Hammer,
  Network,
  Play,
  RadioTower,
  Radar,
  RefreshCw,
  Search,
  Save,
  ShieldCheck,
  SquareTerminal,
  TestTube2,
  Usb,
  Wifi,
  Wrench,
} from "lucide-react";
import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { Hardware, HostInventory, Inspection, NetworkDiscovery, OperationCapability, OperationEvent, ProviderRegistry, ServiceDiscovery, Status, ToolRegistry, UsbInventory, WorkspaceFile, WorkspaceInventory } from "./types";

type Workspace = "host" | "device" | "pins" | "tests" | "firmware" | "tools";

const steps: Array<{ id: Workspace; label: string; hint: string; icon: typeof Usb }> = [
  { id: "host", label: "Host & devices", hint: "Discover interfaces", icon: Usb },
  { id: "device", label: "Selected device", hint: "Identify hardware", icon: Cpu },
  { id: "pins", label: "Pins & buses", hint: "Inspect connections", icon: CircuitBoard },
  { id: "tests", label: "Tests", hint: "Verify capabilities", icon: TestTube2 },
  { id: "firmware", label: "Firmware & files", hint: "Build, edit and flash", icon: FileCode2 },
  { id: "tools", label: "Tools & sources", hint: "Inspect providers", icon: Wrench },
];

function statusClass(status: Status | string) {
  return `status status-${status}`;
}

function formatBytes(value?: number) {
  if (!Number.isFinite(value)) return "--";
  if ((value || 0) < 1024) return `${value} B`;
  if ((value || 0) < 1024 ** 2) return `${((value || 0) / 1024).toFixed(1)} KB`;
  return `${((value || 0) / 1024 ** 2).toFixed(1)} MB`;
}

function advertisedServiceUrl(service: ServiceDiscovery["services"][number]) {
  const type = service.type.toLowerCase();
  const scheme = type.includes("_https") ? "https" : type.includes("_http") ? "http" : null;
  const host = service.addresses[0] || service.server.replace(/\.$/, "");
  if (!scheme || !host) return null;
  const defaultPort = (scheme === "http" && service.port === 80) || (scheme === "https" && service.port === 443);
  return `${scheme}://${host}${defaultPort ? "" : `:${service.port}`}`;
}

function Label({ children }: { children: React.ReactNode }) {
  return <p className="eyebrow">{children}</p>;
}

function SectionHeading({ label, title, action }: { label: string; title: string; action?: React.ReactNode }) {
  return <div className="section-heading"><div><Label>{label}</Label><h2>{title}</h2></div>{action}</div>;
}

function IconButton({ label, onClick, busy = false }: { label: string; onClick: () => void; busy?: boolean }) {
  return <Tooltip.Root><Tooltip.Trigger asChild><button className="icon-button" type="button" aria-label={label} disabled={busy} onClick={onClick}><RefreshCw className={busy ? "spin" : ""} size={17} /></button></Tooltip.Trigger><Tooltip.Portal><Tooltip.Content className="tooltip" sideOffset={7}>{label}<Tooltip.Arrow className="tooltip-arrow" /></Tooltip.Content></Tooltip.Portal></Tooltip.Root>;
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="empty">{children}</p>;
}

function DataAccordion({ value, title, count, children, open = false }: { value: string; title: string; count: string; children: React.ReactNode; open?: boolean }) {
  return (
    <Accordion.Item className="accordion-item" value={value}>
      <Accordion.Header>
        <Accordion.Trigger className="accordion-trigger"><ChevronDown size={15} /><strong>{title}</strong><span>{count}</span></Accordion.Trigger>
      </Accordion.Header>
      <Accordion.Content className="accordion-content" data-open-default={open}>{children}</Accordion.Content>
    </Accordion.Item>
  );
}

type LogEvent = { at: string; channel: string; message: string; tone?: "ok" | "warn" | "error" };

function HostView({ hardware, selectedId, loading, message, usb, host, onRefresh, onSelect, onInspect, onLog }: {
  hardware: Hardware[];
  selectedId: string | null;
  loading: boolean;
  message: string;
  usb: UsbInventory | null;
  host: HostInventory | null;
  onRefresh: () => void;
  onSelect: (hardware: Hardware) => void;
  onInspect: () => void;
  onLog: (channel: string, message: string, tone?: LogEvent["tone"]) => void;
}) {
  const [services, setServices] = useState<ServiceDiscovery | null>(null);
  const [scanningServices, setScanningServices] = useState(false);
  const [network, setNetwork] = useState<NetworkDiscovery | null>(null);
  const [networkTarget, setNetworkTarget] = useState("");
  const [scanningNetwork, setScanningNetwork] = useState(false);
  const scanServices = async () => {
    setScanningServices(true);
    try { const result = await api.scanServices(); setServices(result); onLog("host", `Advertised-service scan found ${result.count} service(s).`, "ok"); }
    catch (error) { setServices({ count: 0, services: [] }); onLog("host", error instanceof Error ? error.message : "Advertised-service scan failed", "error"); }
    finally { setScanningServices(false); }
  };
  const scanNetwork = async (mode: "standard" | "deep") => {
    if (mode === "deep" && !window.confirm("Deep discovery checks a fixed list of TCP service ports on private local /24 networks. It sends connection attempts but no application data. Continue?")) return;
    setScanningNetwork(true);
    onLog("network", `${mode === "deep" ? "Deep" : "Standard"} private-network discovery started.`);
    try {
      const result = await api.scanNetwork(mode, networkTarget.trim() || undefined);
      setNetwork(result);
      onLog("network", `Found ${result.count} network device(s) across ${result.scope.join(", ") || "no eligible private subnet"}.`, "ok");
    } catch (error) { onLog("network", error instanceof Error ? error.message : "Network discovery failed", "error"); }
    finally { setScanningNetwork(false); }
  };
  const selected = hardware.find((item) => item.id === selectedId);
  const hardwareGroups = ["Circuit, controller, or compute target", "Programming or debug interface", "Unresolved serial target", "Host peripheral"].map((category) => ({ category, items: hardware.filter((item) => (item.device_category || "Host peripheral") === category) })).filter((group) => group.items.length);
  const visibleUsb = usb?.devices.filter((item) => item.classification !== "usb_hub") || [];
  const activeNetworks = host?.interfaces.filter((item) => item.up) || [];
  return <div className="workspace-content">
    <section>
      <SectionHeading label="Host hardware" title="Detected devices and interfaces" action={<div className="actions"><IconButton label="Refresh ports and devices" onClick={onRefresh} busy={loading} /><button className="primary inspect-button" type="button" disabled={!selected || loading} onClick={onInspect}><Search size={17} />Inspect IoT device</button></div>} />
      <p className="message" role="status">{message}</p>
      {selected && <div className="selected-summary"><div><span>Selected interface</span><strong>{selected.device || selected.interface || selected.ip_address}</strong></div><div><span>Identity</span><strong>{selected.vid || "----"}:{selected.pid || "----"}</strong></div><div><span>Classification</span><strong>{(selected.classification || "Unclassified").replaceAll("_", " ")}</strong></div><div><span>Transport</span><strong>{selected.transport}</strong></div></div>}
      <div className="table-wrap"><table><thead><tr><th>Interface</th><th>Device</th><th>USB identity</th><th>Transport</th><th>Status</th></tr></thead><tbody>{hardwareGroups.map((group) => <Fragment key={group.category}><tr className="device-group"><td colSpan={5}>{group.category}<span>{group.items.length}</span></td></tr>{group.items.map((item) => <tr key={item.id} className={item.id === selectedId ? "selected" : ""} tabIndex={0} onClick={() => onSelect(item)} onKeyDown={(event) => (event.key === "Enter" || event.key === " ") && onSelect(item)}><td>{item.device || item.interface || item.ip_address}</td><td>{item.name}</td><td>{item.vid || "----"}:{item.pid || "----"}</td><td>{item.transport}</td><td><span className={statusClass(item.classification ? "detected" : "unknown")}>{item.id === selectedId ? "Selected" : item.classification ? "Identified" : "Detected"}</span></td></tr>)}</Fragment>)}</tbody></table>{!hardware.length && <Empty>No serial or USB network interfaces detected.</Empty>}</div>
    </section>
    <section>
      <SectionHeading label="Passive host inspection" title="Computer, USB and network inventory" />
      <Accordion.Root className="accordion-root" type="multiple" defaultValue={["usb"]}>
        <DataAccordion value="usb" title="USB identities" count={usb ? `${visibleUsb.length} physical devices shown` : "Loading"} open>
          <div className="table-wrap"><table><thead><tr><th>Device</th><th>Identity</th><th>Category</th><th>Bus</th></tr></thead><tbody>{visibleUsb.map((item) => <tr key={`${item.bus}:${item.address}`}><td>{item.name}</td><td>{item.usb_identity}</td><td>{(item.classification || item.pnp_class || item.class_name).replaceAll("_", " ")}</td><td>{item.bus}:{item.address}</td></tr>)}</tbody></table></div>
        </DataAccordion>
        <DataAccordion value="networks" title="Host network interfaces" count={host ? `${activeNetworks.length} active of ${host.interfaces.length}` : "Loading"}>
          <div className="table-wrap"><table><thead><tr><th>Interface</th><th>State</th><th>Speed</th><th>Addresses</th></tr></thead><tbody>{activeNetworks.map((item) => <tr key={item.name}><td>{item.name}</td><td>Active</td><td>{item.speed_mbps ? `${item.speed_mbps} Mbps` : "Unknown"}</td><td className="wrap">{item.addresses.filter((address) => address.family !== "MAC").map((address) => address.address).join(", ") || "No IP address"}</td></tr>)}</tbody></table></div>
        </DataAccordion>
        <DataAccordion value="services" title="Local advertised services" count={services ? `${services.count} found` : "Not scanned"}>
          <div className="sub-actions"><p>Bounded scan for advertised HTTP, SSH, camera, and MQTT services.</p><button className="tool-button" type="button" disabled={scanningServices} onClick={() => void scanServices()}><Network size={15} />{scanningServices ? "Scanning..." : "Scan local services"}</button></div>
          {services && <div className="item-list service-list">{services.services.map((service) => { const url = advertisedServiceUrl(service); const body = <><div><strong>{service.name}</strong><small>{service.type} | {service.addresses.join(", ") || service.server} | port {service.port}</small></div>{url ? <ExternalLink size={15} /> : <span className={statusClass("detected")}>Advertised</span>}</>; return url ? <a className="resource" href={url} target="_blank" rel="noreferrer" key={`${service.type}-${service.server}-${service.port}`}>{body}</a> : <div className="item-row" key={`${service.type}-${service.server}-${service.port}`}>{body}</div>; })}{!services.services.length && <Empty>No matching local services advertised during this scan.</Empty>}</div>}
        </DataAccordion>
        <DataAccordion value="network-devices" title="Devices on private local networks" count={network ? `${network.count} found` : "Not scanned"}>
          <div className="network-scan-controls"><label htmlFor="network-target">Optional exact IPv4 target<input id="network-target" value={networkTarget} onChange={(event) => setNetworkTarget(event.target.value)} placeholder="192.168.5.178" /></label><button className="tool-button" type="button" disabled={scanningNetwork} onClick={() => void scanNetwork("standard")}><Radar size={15} />{scanningNetwork ? "Scanning..." : "Scan known devices"}</button><button className="tool-button danger-action" type="button" disabled={scanningNetwork} onClick={() => void scanNetwork("deep")}><Search size={15} />Deep local scan</button></div>
          <p className="scan-boundary">Private local networks only. Deep mode is capped to /24 and checks a fixed service-port list without sending application payloads.</p>
          {network && <div className="network-device-list">{network.devices.map((device) => <article className="network-device" key={device.address}><div><strong>{device.address}</strong><small>{device.mac_address || "MAC unavailable"} | {device.source}</small></div><div className="service-chips">{device.services.map((service) => service.url ? <a href={service.url} target="_blank" rel="noreferrer" key={`${device.address}-${service.port}`}>{service.name} :{service.port}<ExternalLink size={12} /></a> : <span key={`${device.address}-${service.port}`}>{service.name} :{service.port}</span>)}{!device.services.length && <span>Seen on local neighbor cache</span>}</div></article>)}{!network.devices.length && <Empty>No responding or cached devices found inside the allowed scope.</Empty>}</div>}
        </DataAccordion>
      </Accordion.Root>
    </section>
  </div>;
}

function DeviceView({ inspection, onRefresh, onSaveModel }: { inspection: Inspection | null; onRefresh: () => void; onSaveModel: (model: string) => void }) {
  const [model, setModel] = useState(inspection?.model || "");
  useEffect(() => setModel(inspection?.model || ""), [inspection]);
  if (!inspection) return <Empty>Select and inspect a connected interface from Host & devices.</Empty>;
  return <div className="workspace-content"><section>
    <SectionHeading label="Evidence-based inspection" title="Device identity and capabilities" action={<IconButton label="Refresh device evidence" onClick={onRefresh} />} />
    <div className="identity-grid"><div><span>Identified model</span><strong>{inspection.model}</strong></div><div><span>Device class</span><strong>{inspection.classification.replaceAll("_", " ")}</strong></div><div><span>MCU / SoC</span><strong>{inspection.mcu || "Unknown"}</strong></div><div><span>Architecture</span><strong>{inspection.architecture || "Unknown"}</strong></div><div><span>Runtime / OS</span><strong>{inspection.runtime || "Unknown"}</strong></div><div><span>Confidence</span><strong>{Math.round(inspection.confidence * 100)}%</strong></div></div>
    {!!inspection.identity_layers?.length && <div className="table-wrap identity-layer-table"><table><thead><tr><th>Layer</th><th>Identified hardware</th><th>Evidence</th><th>Status</th></tr></thead><tbody>{inspection.identity_layers.map((item) => <tr key={item.id}><td>{item.layer}</td><td><strong>{item.name}</strong></td><td>{item.source}</td><td><span className={statusClass(item.status)}>{item.status}</span></td></tr>)}</tbody></table></div>}
    {!!inspection.candidates.length && <form className="model-picker" onSubmit={(event) => { event.preventDefault(); onSaveModel(model); }}><label htmlFor="model">Exact board model</label><div><select id="model" value={model} onChange={(event) => setModel(event.target.value)}>{inspection.candidates.map((candidate) => <option key={candidate}>{candidate}</option>)}</select><button className="primary" type="submit"><ShieldCheck size={16} />Save model</button></div><small>Model selection filters expected components. Hardware tests are still required before a sensor is marked verified.</small></form>}
    <Accordion.Root className="accordion-root two-columns" type="multiple" defaultValue={["evidence", "components"]}>
      <DataAccordion value="evidence" title="Evidence" count={`${inspection.evidence.length} claims`} open><div className="item-list">{inspection.evidence.map((item, index) => <div className="item-row" key={`${item.source}-${index}`}><div><strong>{item.claim}</strong><small>{item.source}</small></div><span className={statusClass(item.status)}>{item.status}</span></div>)}</div></DataAccordion>
      <DataAccordion value="components" title="Components and sensors" count={`${inspection.components.length} items`} open><div className="card-grid">{inspection.components.map((item) => <article className="data-card" key={item.id}><div><strong>{item.name}</strong><span className={statusClass(item.status)}>{item.status}</span></div><small>{[item.type, item.bus, item.variant].filter(Boolean).join(" | ")}</small><small>Source: {item.source}</small></article>)}</div></DataAccordion>
      <DataAccordion value="capabilities" title="Capabilities and services" count={`${inspection.capabilities.length + inspection.services.length} items`}><div className="item-list">{inspection.capabilities.map((item) => <div className="item-row" key={item.id}><div><strong>{item.name}</strong><small>{item.source}</small></div><span className={statusClass(item.status)}>{item.status}</span></div>)}{inspection.services.map((item) => item.url ? <a className="resource service-link" href={item.url} target="_blank" rel="noreferrer" key={`${item.name}-${item.port}`}><div><strong>{item.name}</strong><small>{item.url}</small></div><ExternalLink size={15} /></a> : <div className="item-row" key={`${item.name}-${item.port}`}><div><strong>{item.name}</strong><small>{item.address}:{item.port}</small></div><span className={statusClass(item.status)}>{item.status}</span></div>)}</div></DataAccordion>
      <DataAccordion value="connections" title="External buses and terminal connections" count={`${inspection.connection_interfaces?.length || 0} interfaces`}><div className="item-list">{inspection.connection_interfaces?.map((item) => <div className="item-row connection-row" key={item.id}><div><strong>{item.name}</strong><small>{item.adapter || item.limitation}</small>{item.adapter && <small>{item.limitation}</small>}</div><span className={statusClass(item.status)}>{item.status}</span></div>)}{!inspection.connection_interfaces?.length && <Empty>No externally enumerable bus was identified for this profile.</Empty>}</div></DataAccordion>
      <DataAccordion value="resources" title="Documentation and sources" count={`${inspection.resources.length} links`}><div className="item-list">{inspection.resources.map((item) => <a className="resource" href={item.url} target="_blank" rel="noreferrer" key={item.url}><div><strong>{item.title}</strong><small>{item.provider} | {item.kind}</small></div><ExternalLink size={15} /></a>)}</div></DataAccordion>
    </Accordion.Root>
  </section></div>;
}

function PinsView({ inspection, onRefresh, onLog }: { inspection: Inspection | null; onRefresh: () => Promise<void>; onLog: (channel: string, message: string, tone?: LogEvent["tone"]) => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState("");
  if (!inspection) return <Empty>Inspect a device before viewing its pins and buses.</Empty>;
  const pins = inspection.pins || [];
  const peripherals = inspection.attached_peripherals || [];
  const telemetry = inspection.telemetry || {};
  const groups = new Map<string, typeof pins>();
  for (const pin of pins) {
    const group = pin.group || "Other";
    groups.set(group, [...(groups.get(group) || []), pin]);
  }
  const runtimeProbe = inspection.tests.find((test) => test.action === "deep_probe");
  const i2cProbe = inspection.tests.find((test) => test.action === "bus_scan");
  const runProbe = async (testId: string) => {
    const test = inspection.tests.find((item) => item.id === testId);
    if (!test?.available) return;
    if (!window.confirm(`${test.description} Continue?`)) return;
    setBusy(testId); setResult(`Running ${test.name}...`);
    try {
      const response = await api.runTest(inspection.identifier, testId);
      setResult(response.summary); onLog("probe", response.summary, response.passed ? "ok" : "error");
      await onRefresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Probe failed";
      setResult(message); onLog("probe", message, "error");
    } finally { setBusy(null); }
  };
  const artifacts = [
    ...(telemetry.imports || []).map((name) => `import: ${name}`),
    ...(telemetry.libraries || []).map((name) => `library: ${name}`),
  ];
  return <div className="workspace-content"><section>
    <SectionHeading label="Board connection map" title={`Pins, buses and attached peripherals for ${inspection.model}`} action={<div className="actions"><span className={statusClass(inspection.adapter ? "verified" : "unavailable")}>{inspection.adapter?.name || "No adapter"}</span><IconButton label="Refresh pin and bus evidence" onClick={() => void onRefresh()} busy={Boolean(busy)} /></div>} />
    <p className="intro">{result || (inspection.adapter ? `${pins.filter((pin) => pin.status === "verified").length} runtime-verified and ${pins.filter((pin) => pin.status !== "verified").length} documented pins.` : "No pin adapter is available for this device profile.")}</p>
    <div className="runtime-grid"><div><span>Runtime</span><strong>{telemetry.firmware || inspection.runtime || "--"}</strong></div><div><span>Processor</span><strong>{telemetry.processor || inspection.mcu || "--"}</strong></div><div><span>Storage</span><strong>{telemetry.storage_mount || telemetry.flash_size || "--"}</strong></div><div><span>Free heap</span><strong>{formatBytes(telemetry.free_heap_bytes)}</strong></div><div><span>CPU clock</span><strong>{telemetry.cpu_frequency_hz ? `${(telemetry.cpu_frequency_hz / 1_000_000).toFixed(2)} MHz` : telemetry.cpu_frequency || "--"}</strong></div><div><span>Program</span><strong>{telemetry.code_files?.join(", ") || "--"}</strong></div></div>
    <div className="runtime-artifacts">{artifacts.length ? artifacts.map((item) => <span key={item}>{item}</span>) : <span>No runtime modules reported.</span>}</div>
    <div className="probe-toolbar"><div><strong>Controlled device probe</strong><small>{runtimeProbe?.description || (inspection.adapter ? "This adapter has no deeper target-identification action." : "No compatible runtime adapter detected.")}</small></div><button className="tool-button danger-action" type="button" disabled={!runtimeProbe?.available || Boolean(busy)} onClick={() => runtimeProbe && void runProbe(runtimeProbe.id)}><Activity size={15} />{busy === runtimeProbe?.id ? "Probing..." : "Run deep probe"}</button><button className="tool-button" type="button" hidden={!i2cProbe} disabled={!i2cProbe?.available || Boolean(busy)} onClick={() => i2cProbe && void runProbe(i2cProbe.id)}><Search size={15} />{busy === i2cProbe?.id ? "Scanning..." : "Scan I2C bus"}</button></div>
    <div className="pin-layout"><div><div className="subsection-heading"><h3>Board pins</h3><span>{pins.length} pins</span></div><div className="pin-groups">{[...groups].map(([group, groupPins]) => <section className="pin-group" key={group}><header><strong>{group}</strong><span>{groupPins.length} pins</span></header><div className="pin-grid">{groupPins.map((pin) => <article className="pin-card" key={`${group}-${pin.name}`}><div><strong>{[pin.name, ...pin.aliases].join(" / ")}</strong><span className={statusClass(pin.status)}>{pin.status}</span></div><small>{pin.functions.join(" | ")}</small><small>{pin.source}</small></article>)}</div></section>)}{!pins.length && <Empty>No pin map is available for this device profile.</Empty>}</div></div><div><div className="subsection-heading"><h3>Attached peripherals</h3><span>{peripherals.length} detected</span></div><div className="peripheral-list">{peripherals.map((peripheral) => <article className="peripheral-card" key={peripheral.id}><div><strong>{peripheral.name}</strong><span className={statusClass(peripheral.status)}>{peripheral.status}</span></div><small>Candidates: {peripheral.candidates.join("; ")}</small><small>{peripheral.bus} {peripheral.address} | {peripheral.source}</small></article>)}{!peripherals.length && <Empty>No responding external bus address has been detected.</Empty>}</div></div></div>
  </section></div>;
}

function DiagnosticConsole({ selected, events, onClear, onLog }: { selected: Hardware | null; events: LogEvent[]; onClear: () => void; onLog: (channel: string, message: string, tone?: LogEvent["tone"]) => void }) {
  const [open, setOpen] = useState(false);
  const [command, setCommand] = useState("system_summary");
  const [busy, setBusy] = useState(false);
  const compatible = Boolean(selected?.kind === "usb_network" && selected.is_lichee);
  const run = async () => {
    if (!selected) return;
    setBusy(true); setOpen(true); onLog("target", `Running ${command} on ${selected.ip_address || selected.device}...`);
    try { const result = await api.runCommand(selected.id, command); onLog("target", `${result.label} @ ${result.target}\n${result.output}`, "ok"); }
    catch (error) { onLog("target", error instanceof Error ? error.message : "Target diagnostic failed", "error"); }
    finally { setBusy(false); }
  };
  return <aside className={`diagnostic-console ${open ? "open" : ""}`} aria-label="Diagnostic console"><button className="console-toggle" type="button" onClick={() => setOpen((value) => !value)}><SquareTerminal size={15} /><strong>Diagnostic console</strong><span>{events.length} events</span><ChevronDown size={15} /></button>{open && <div className="console-body"><div className="console-toolbar"><select aria-label="Read-only target diagnostic" value={command} disabled={!compatible || busy} onChange={(event) => setCommand(event.target.value)}><option value="system_summary">System summary</option><option value="network_interfaces">Network interfaces</option><option value="usb_devices">USB devices</option><option value="i2c_adapters">I2C adapters</option><option value="media_devices">Media devices</option></select><button className="tool-button" type="button" disabled={!compatible || busy} onClick={() => void run()}><Play size={14} />{busy ? "Running..." : "Run read-only command"}</button><button className="tool-button" type="button" onClick={onClear}>Clear</button></div>{!compatible && <p className="console-note">Select an inspected target with a compatible authenticated operating-system adapter to enable commands. Bench events remain visible for every device.</p>}<div className="console-output" role="log" aria-live="polite">{events.map((event, index) => <div className={event.tone || ""} key={`${event.at}-${index}`}><span>{event.at}</span><b>{event.channel}</b><pre>{event.message}</pre></div>)}{!events.length && <p>No bench events yet.</p>}</div></div>}</aside>;
}

function TestsView({ inspection, onRefresh }: { inspection: Inspection | null; onRefresh: () => void | Promise<void> }) {
  const [results, setResults] = useState<Record<string, string>>({});
  const run = async (testId: string) => {
    if (!inspection) return;
    setResults((old) => ({ ...old, [testId]: "Running..." }));
    try {
      const result = await api.runTest(inspection.identifier, testId);
      setResults((old) => ({ ...old, [testId]: result.summary }));
      await onRefresh();
    } catch (error) {
      setResults((old) => ({ ...old, [testId]: error instanceof Error ? error.message : "Test failed" }));
    }
  };
  if (!inspection) return <Empty>Inspect a device before running tests.</Empty>;
  const capabilityIds = new Set(inspection.capabilities.map((item) => item.id));
  const hasBle = capabilityIds.has("ble");
  const hasWifi = capabilityIds.has("wifi_24") || capabilityIds.has("wifi_5");
  return <div className="workspace-content"><section><SectionHeading label="Controlled verification" title={`Tests for ${inspection.model}`} action={<IconButton label="Refresh live test availability" onClick={onRefresh} />} /><div className="test-grid">{inspection.tests.map((test) => <article className="test-card" key={test.id}><div className="test-icon"><Activity size={18} /></div><div><strong>{test.name}</strong><p>{test.description}</p><span className={`risk risk-${test.risk}`}>{test.risk}</span>{results[test.id] && <small className="test-result">{results[test.id]}</small>}</div><button className="tool-button" type="button" disabled={!test.available || results[test.id] === "Running..."} onClick={() => run(test.id)}><Play size={15} />{test.available ? "Run" : "Unavailable"}</button></article>)}</div><div className="test-context">{hasBle && <div><Bluetooth size={18} /><strong>Bluetooth (BLE)</strong><span>Available on this selected hardware profile.</span></div>}{hasWifi && <div><Wifi size={18} /><strong>Wi-Fi</strong><span>Available on this selected hardware profile; live broadcast state still requires compatible firmware telemetry.</span></div>}<div><RadioTower size={18} /><strong>Signals</strong><span>Unknown pins and buses are never driven until a compatible protocol or board map is established.</span></div></div></section></div>;
}

function FirmwareView({ selected, inspection, onLog }: { selected: Hardware | null; inspection: Inspection | null; onLog: (channel: string, message: string, tone?: LogEvent["tone"]) => void }) {
  const [inventory, setInventory] = useState<WorkspaceInventory | null>(null);
  const [capabilities, setCapabilities] = useState<OperationCapability[]>([]);
  const [history, setHistory] = useState<OperationEvent[]>([]);
  const [file, setFile] = useState<WorkspaceFile | null>(null);
  const [originalContent, setOriginalContent] = useState("");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const identifier = selected?.id || inspection?.identifier;

  const refresh = useCallback(async () => {
    if (!identifier) return;
    setBusy("refresh");
    try {
      const [nextInventory, nextOperations, nextHistory] = await Promise.all([
        api.workspace(identifier), api.operations(identifier), api.operationHistory(identifier),
      ]);
      setInventory(nextInventory); setCapabilities(nextOperations.operations); setHistory(nextHistory.events);
      setMessage(`${nextInventory.files.length} editable source/configuration files and ${nextOperations.operations.filter((item) => item.available).length} ready operations.`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Firmware workspace could not be loaded"); }
    finally { setBusy(""); }
  }, [identifier]);

  useEffect(() => { setFile(null); setOriginalContent(""); void refresh(); }, [refresh]);

  const openFile = async (rootId: string, path: string) => {
    if (!identifier) return;
    setBusy(`file:${rootId}:${path}`);
    try { const next = await api.workspaceFile(identifier, rootId, path); setFile(next); setOriginalContent(next.content); }
    catch (error) { setMessage(error instanceof Error ? error.message : "File could not be opened"); }
    finally { setBusy(""); }
  };

  const runOperation = async (operation: OperationCapability) => {
    if (!identifier || !operation.available) return;
    setBusy(operation.id); setMessage(`Planning ${operation.label}...`);
    try {
      const plan = await api.planOperation(identifier, operation.id);
      let token: string | undefined;
      if (plan.requires_approval) {
        const approved = window.confirm(`${plan.preview}\n\nRisk: ${plan.risk}. This approval expires in ${plan.expires_in_seconds} seconds. Continue?`);
        if (!approved) { setMessage("Operation cancelled before approval."); return; }
        token = (await api.approveOperation(identifier, plan.plan_id)).approval_token;
      }
      const result = await api.executeOperation(identifier, plan.plan_id, token);
      setMessage(result.output); onLog("operation", `${operation.label}: ${result.output}`, result.passed ? "ok" : "error");
      await refresh();
    } catch (error) { const text = error instanceof Error ? error.message : "Operation failed"; setMessage(text); onLog("operation", text, "error"); }
    finally { setBusy(""); }
  };

  const saveFile = async () => {
    if (!identifier || !file || file.content === originalContent) return;
    setBusy("save");
    try {
      const plan = await api.planWorkspaceWrite(identifier, file);
      if (!window.confirm(`${plan.preview}\n\nSave this change?`)) { setMessage("File save cancelled."); return; }
      const approved = await api.approveOperation(identifier, plan.plan_id);
      const result = await api.executeOperation(identifier, plan.plan_id, approved.approval_token);
      setMessage(result.output); onLog("workspace", result.output, result.passed ? "ok" : "error");
      if (result.passed) { const next = await api.workspaceFile(identifier, file.root_id, file.path); setFile(next); setOriginalContent(next.content); }
      await refresh();
    } catch (error) { const text = error instanceof Error ? error.message : "File save failed"; setMessage(text); onLog("workspace", text, "error"); }
    finally { setBusy(""); }
  };

  if (!identifier) return <Empty>Select and inspect hardware before opening firmware tools.</Empty>;
  return <div className="workspace-content"><section>
    <SectionHeading label="Controlled target workspace" title={`Firmware and files for ${inspection?.model || selected?.name || "selected hardware"}`} action={<IconButton label="Refresh firmware workspace" busy={busy === "refresh"} onClick={() => void refresh()} />} />
    <p className="intro">{message || "Builds are local. Device writes require a target-bound, short-lived approval and create an audit receipt."}</p>
    <div className="operation-grid">{capabilities.map((operation) => <article className="operation-card" key={operation.id}><div className="test-icon">{operation.risk === "destructive" ? <ShieldCheck size={18} /> : <Hammer size={18} />}</div><div><strong>{operation.label}</strong><p>{operation.description}</p><span className={`risk risk-${operation.risk}`}>{operation.risk}</span>{!operation.available && <small>{operation.reason}</small>}</div><button className="tool-button" type="button" disabled={!operation.available || Boolean(busy)} onClick={() => void runOperation(operation)}><Play size={15} />{busy === operation.id ? "Running..." : operation.available ? "Plan & run" : "Unavailable"}</button></article>)}</div>
  </section><section>
    <SectionHeading label="Allowlisted source access" title="Project and mounted-device files" action={file && <button className="tool-button" type="button" disabled={file.content === originalContent || Boolean(busy)} onClick={() => void saveFile()}><Save size={15} />{busy === "save" ? "Saving..." : "Review & save"}</button>} />
    <div className="file-workspace"><aside>{inventory?.roots.map((root) => <div className="file-root" key={root.id}><strong>{root.name}</strong><small>{root.source}</small>{inventory.files.filter((item) => item.root_id === root.id).map((item) => <button type="button" className={file?.root_id === item.root_id && file.path === item.path ? "active" : ""} key={`${item.root_id}:${item.path}`} onClick={() => void openFile(item.root_id, item.path)}><FileCode2 size={13} /><span>{item.path}</span><small>{item.size} B</small></button>)}</div>)}</aside><div className="code-editor">{file ? <><header><strong>{file.path}</strong><span>sha256 {file.sha256.slice(0, 12)}</span></header><textarea aria-label={`Edit ${file.path}`} spellCheck={false} value={file.content} onChange={(event) => setFile({ ...file, content: event.target.value })} /></> : <Empty>Select a source or configuration file to inspect it. Binary firmware images are intentionally excluded from the editor.</Empty>}</div></div>
  </section><section>
    <SectionHeading label="Immutable evidence trail" title="Operation receipts" />
    <div className="table-wrap"><table><thead><tr><th>Time</th><th>Operation</th><th>Risk</th><th>Status</th><th>Evidence</th></tr></thead><tbody>{history.slice(0, 25).map((event) => <tr key={event.sequence}><td>{new Date(event.recorded_at).toLocaleString()}</td><td>{event.operation_id}</td><td><span className={`risk risk-${event.risk}`}>{event.risk}</span></td><td>{event.status}</td><td className="wrap">{event.output || event.preview}</td></tr>)}{!history.length && <tr><td colSpan={5}>No operations have been planned for this target.</td></tr>}</tbody></table></div>
  </section></div>;
}

function ToolsView({ registry, providers, onRefresh }: { registry: ToolRegistry | null; providers: ProviderRegistry | null; onRefresh: () => void }) {
  return <div className="workspace-content"><section><SectionHeading label="Extensible discovery engine" title="Tools and metadata sources" action={<IconButton label="Refresh tools and providers" onClick={onRefresh} />} /><p className="intro">Providers enrich identity and documentation. Local evidence remains authoritative for connected hardware and verified capabilities.</p><Accordion.Root className="accordion-root" type="multiple" defaultValue={["providers", "tools"]}><DataAccordion value="providers" title="Metadata providers" count={providers ? `${providers.available_count} of ${providers.providers.length} ready` : "Loading"} open><div className="card-grid">{providers?.providers.map((provider) => <article className={`data-card ${provider.available ? "available" : ""}`} key={provider.id}><div><strong>{provider.name}</strong><span className={statusClass(provider.available ? "verified" : "unavailable")}>{provider.available ? "ready" : "not configured"}</span></div><small>{provider.scope}</small><small>{provider.mode}{provider.requires_key ? " | optional credentials" : ""}</small></article>)}</div></DataAccordion><DataAccordion value="tools" title="Command-line tools" count={registry ? `${registry.available_count} of ${registry.tools.length} available` : "Loading"} open><div className="table-wrap"><table><thead><tr><th>Tool</th><th>Purpose</th><th>Risk</th><th>Status</th></tr></thead><tbody>{registry?.tools.map((tool) => <tr key={tool.id}><td>{tool.name}</td><td>{tool.category}</td><td><span className={`risk risk-${tool.risk}`}>{tool.risk}</span></td><td>{tool.available ? tool.version || "Available" : "Planned"}</td></tr>)}</tbody></table></div></DataAccordion></Accordion.Root></section></div>;
}

export default function App() {
  const [workspace, setWorkspace] = useState<Workspace>("host");
  const [hardware, setHardware] = useState<Hardware[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [usb, setUsb] = useState<UsbInventory | null>(null);
  const [host, setHost] = useState<HostInventory | null>(null);
  const [registry, setRegistry] = useState<ToolRegistry | null>(null);
  const [providers, setProviders] = useState<ProviderRegistry | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("Scanning this computer for connected hardware...");
  const [events, setEvents] = useState<LogEvent[]>([]);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [workspace]);

  const log = useCallback((channel: string, eventMessage: string, tone?: LogEvent["tone"]) => {
    setEvents((current) => [...current.slice(-199), { at: new Date().toLocaleTimeString(), channel, message: eventMessage, tone }]);
  }, []);

  const selected = useMemo(() => hardware.find((item) => item.id === selectedId) || null, [hardware, selectedId]);
  const loadHost = useCallback(async () => {
    setLoading(true);
    try {
      const [nextHardware, nextUsb, nextHost] = await Promise.all([api.hardware(), api.usbInventory(), api.hostInventory()]);
      setHardware(nextHardware); setUsb(nextUsb); setHost(nextHost);
      setSelectedId((current) => nextHardware.some((item) => item.id === current) ? current : nextHardware.find((item) => item.classification)?.id || nextHardware[0]?.id || null);
      const nextMessage = `${nextHardware.length} selectable interfaces found on ${nextHost.hostname}. No target was opened or changed.`;
      setMessage(nextMessage); log("host", nextMessage, "ok");
    } catch (error) { const nextMessage = error instanceof Error ? error.message : "Host scan failed"; setMessage(nextMessage); log("host", nextMessage, "error"); }
    finally { setLoading(false); }
  }, [log]);
  const loadTools = useCallback(async () => { const [nextRegistry, nextProviders] = await Promise.all([api.tools(), api.providers()]); setRegistry(nextRegistry); setProviders(nextProviders); }, []);
  const inspect = useCallback(async () => { if (!selectedId) return; setLoading(true); setMessage("Collecting device evidence..."); log("device", "Collecting identity, interface, and provider evidence..."); try { await api.select(selectedId); const result = await api.inspect(selectedId); setInspection(result.inspection); setWorkspace("device"); setMessage(`${result.inspection.model} inspected.`); log("device", `${result.inspection.model} inspected at ${Math.round(result.inspection.confidence * 100)}% identity confidence.`, "ok"); } catch (error) { const nextMessage = error instanceof Error ? error.message : "Inspection failed"; setMessage(nextMessage); log("device", nextMessage, "error"); } finally { setLoading(false); } }, [selectedId, log]);
  const refreshInspection = useCallback(async () => { if (!selectedId) return; const result = await api.inspect(selectedId); setInspection(result.inspection); }, [selectedId]);
  const saveModel = useCallback(async (model: string) => { if (!selectedId) return; await api.saveModel(selectedId, model); await refreshInspection(); }, [selectedId, refreshInspection]);

  useEffect(() => { void loadHost(); void loadTools(); }, [loadHost, loadTools]);
  useEffect(() => { const timer = window.setInterval(() => void loadHost(), 30_000); return () => window.clearInterval(timer); }, [loadHost]);
  useEffect(() => { if (selectedId && inspection?.identifier !== selectedId) setInspection(null); }, [selectedId, inspection?.identifier]);

  return <div className="app-shell">
    <div className={`global-progress ${loading ? "active" : ""}`} role="progressbar" aria-label="Bench operation in progress" />
    <header><div className="brand"><span /><div><h1>IoT Hardware Connectivity Bench</h1><p>Cross-vendor discovery, inspection and acceptance testing</p></div></div><div className="host-status"><CircleDot size={16} /><div><strong>{selected ? "Hardware selected" : "Waiting for hardware"}</strong><span>{selected?.name || "No target interface"}</span></div></div></header>
    <nav className="workflow" aria-label="Hardware bench workflow">{steps.map((step, index) => { const Icon = step.icon; return <button key={step.id} type="button" title={`${step.label}: ${step.hint}`} className={workspace === step.id ? "active" : ""} aria-current={workspace === step.id ? "step" : undefined} onClick={() => { setWorkspace(step.id); if ((step.id === "device" || step.id === "pins" || step.id === "tests" || step.id === "firmware") && selectedId) void refreshInspection(); }}><span className="step-number">{index + 1}</span><Icon size={16} /><span><strong>{step.label}</strong><small>{step.hint}</small></span></button>; })}</nav>
    <main>
      {workspace === "host" && <HostView hardware={hardware} selectedId={selectedId} loading={loading} message={message} usb={usb} host={host} onRefresh={() => void loadHost()} onSelect={(item) => { setSelectedId(item.id); log("host", `Selected ${item.name} on ${item.device || item.interface || item.ip_address}.`); }} onInspect={() => void inspect()} onLog={log} />}
      {workspace === "device" && <DeviceView inspection={inspection} onRefresh={() => void refreshInspection()} onSaveModel={(model) => void saveModel(model)} />}
      {workspace === "pins" && <PinsView inspection={inspection} onRefresh={refreshInspection} onLog={log} />}
      {workspace === "tests" && <TestsView inspection={inspection} onRefresh={refreshInspection} />}
      {workspace === "firmware" && <FirmwareView selected={selected} inspection={inspection} onLog={log} />}
      {workspace === "tools" && <ToolsView registry={registry} providers={providers} onRefresh={() => void loadTools()} />}
    </main>
    <footer><span>React client 0.2</span><a href="http://127.0.0.1:8765">Open HTML validation client <ExternalLink size={12} /></a></footer>
    <DiagnosticConsole selected={selected} events={events} onClear={() => setEvents([])} onLog={log} />
  </div>;
}
