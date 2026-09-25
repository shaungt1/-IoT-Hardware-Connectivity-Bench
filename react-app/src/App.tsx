import * as Accordion from "@radix-ui/react-accordion";
import * as Tooltip from "@radix-ui/react-tooltip";
import {
  Activity,
  Bluetooth,
  Boxes,
  CircuitBoard,
  ChevronDown,
  CircleDot,
  CircleHelp,
  Cpu,
  Database,
  ExternalLink,
  FileCode2,
  HardDrive,
  Hammer,
  ImageUp,
  Network,
  PencilLine,
  Play,
  RadioTower,
  Radar,
  RefreshCw,
  Search,
  Save,
  ShieldCheck,
  Square,
  SquareTerminal,
  TestTube2,
  Trash2,
  Upload,
  Usb,
  Wifi,
  Wrench,
  X,
} from "lucide-react";
import { Fragment, Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { api } from "./api";
import { useConfirmation } from "./ConfirmDialog";
import { DeviceLivePanel, WirelessControls } from "./LiveDevicePanels";
import type { ActiveOperation, AdapterRegistry, BenchStatus, DevicePin, EmulationCatalog, EmulationRun, EmulationVerification, EvidenceHistory, FirmwareAnalysis, Hardware, HostInventory, Inspection, InstrumentReport, NetworkDiscovery, OperationCapability, OperationEvent, ProbeMatrix, ProviderRegistry, ServiceDiscovery, Status, ToolDiagnostic, ToolRegistry, UsbInventory, VisualAnalysis, WorkspaceFile, WorkspaceInventory } from "./types";

const Editor = lazy(() => import("@monaco-editor/react").then((module) => ({ default: module.default })));
const PrototypeView = lazy(() => import("./PrototypeView").then((module) => ({ default: module.PrototypeView })));

type Workspace = "host" | "device" | "pins" | "connections" | "prototype" | "tests" | "firmware" | "tools";

const workspaceIds: Workspace[] = ["host", "device", "pins", "connections", "tests", "firmware", "prototype", "tools"];
function editorLanguage(path: string) {
  const extension = path.toLowerCase().split(".").pop();
  return ({ c: "c", cc: "cpp", cpp: "cpp", h: "cpp", hpp: "cpp", ino: "cpp", py: "python", json: "json", md: "markdown", yaml: "yaml", yml: "yaml", toml: "ini", ini: "ini", cfg: "ini" } as Record<string, string>)[extension || ""] || "plaintext";
}
function restoredWorkspace(): Workspace {
  const saved = window.localStorage.getItem("iot-bench.workspace") as Workspace | null;
  return saved && workspaceIds.includes(saved) ? saved : "host";
}
function restoredSelectedId(): string | null {
  const saved = window.localStorage.getItem("iot-bench.selected-id");
  return saved && saved.length <= 512 ? saved : null;
}

const steps: Array<{ id: Workspace; label: string; hint: string; icon: typeof Usb }> = [
  { id: "host", label: "Host & devices", hint: "Discover interfaces", icon: Usb },
  { id: "device", label: "Selected device", hint: "Identify hardware", icon: Cpu },
  { id: "pins", label: "Pins & buses", hint: "Inspect connections", icon: CircuitBoard },
  { id: "connections", label: "Connections", hint: "Configure radios", icon: RadioTower },
  { id: "tests", label: "Tests", hint: "Verify capabilities", icon: TestTube2 },
  { id: "firmware", label: "Firmware & files", hint: "Build, edit and flash", icon: FileCode2 },
  { id: "prototype", label: "Prototype", hint: "Wire physical + virtual", icon: Boxes },
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
  const [sshHost, setSshHost] = useState("");
  const [sshPort, setSshPort] = useState(22);
  const [sshUser, setSshUser] = useState("");
  const [sshPassword, setSshPassword] = useState("");
  const [sshFingerprint, setSshFingerprint] = useState("");
  const [sshBusy, setSshBusy] = useState(false);
  const confirmation = useConfirmation();
  const scanServices = async () => {
    setScanningServices(true);
    try { const result = await api.scanServices(); setServices(result); onLog("host", `Advertised-service scan found ${result.count} service(s).`, "ok"); }
    catch (error) { setServices({ count: 0, services: [] }); onLog("host", error instanceof Error ? error.message : "Advertised-service scan failed", "error"); }
    finally { setScanningServices(false); }
  };
  const scanNetwork = async (mode: "standard" | "deep") => {
    if (mode === "deep" && !await confirmation.request({ title: "Run deep local discovery?", message: "This checks a fixed list of TCP service ports on private local /24 networks. It sends connection attempts but no application data.", confirmLabel: "Run deep scan", risk: "Active network connection attempts" })) return;
    setScanningNetwork(true);
    onLog("network", `${mode === "deep" ? "Deep" : "Standard"} private-network discovery started.`);
    try {
      const result = await api.scanNetwork(mode, networkTarget.trim() || undefined);
      setNetwork(result);
      onLog("network", `Found ${result.count} network device(s) across ${result.scope.join(", ") || "no eligible private subnet"}.`, "ok");
    } catch (error) { onLog("network", error instanceof Error ? error.message : "Network discovery failed", "error"); }
    finally { setScanningNetwork(false); }
  };
  const probeSsh = async () => {
    setSshBusy(true); setSshFingerprint("");
    try { const result = await api.probeSsh(sshHost.trim(), sshPort); setSshFingerprint(result.fingerprint); onLog("ssh", `Observed ${result.algorithm} host key ${result.fingerprint}. Confirm it before enrollment.`, "warn"); }
    catch (error) { onLog("ssh", error instanceof Error ? error.message : "SSH host-key probe failed", "error"); }
    finally { setSshBusy(false); }
  };
  const enrollSsh = async () => {
    setSshBusy(true);
    try { await api.enrollSsh(sshHost.trim(), sshPort, sshUser.trim(), sshPassword, sshFingerprint); setSshPassword(""); setSshFingerprint(""); onRefresh(); onLog("ssh", `Enrolled ${sshHost}:${sshPort} with a pinned host key. Credentials remain in API memory only.`, "ok"); }
    catch (error) { onLog("ssh", error instanceof Error ? error.message : "SSH enrollment failed", "error"); }
    finally { setSshBusy(false); }
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
        <DataAccordion value="ssh-target" title="Linux board enrollment" count="Pinned SSH">
          <div className="ssh-enrollment">
            <label>Host<input value={sshHost} onChange={(event) => { setSshHost(event.target.value); setSshFingerprint(""); }} placeholder="192.168.4.49" /></label>
            <label>Port<input type="number" min={1} max={65535} value={sshPort} onChange={(event) => { setSshPort(Number(event.target.value)); setSshFingerprint(""); }} /></label>
            <label>Username<input value={sshUser} onChange={(event) => setSshUser(event.target.value)} autoComplete="username" /></label>
            <label>Password<input type="password" value={sshPassword} onChange={(event) => setSshPassword(event.target.value)} autoComplete="current-password" /></label>
            <button className="tool-button" type="button" disabled={sshBusy || !sshHost.trim()} onClick={() => void probeSsh()}><ShieldCheck size={15} />Read host key</button>
            <button className="primary" type="button" disabled={sshBusy || !sshFingerprint || !sshUser.trim() || !sshPassword} onClick={() => void enrollSsh()}><Network size={15} />Enroll board</button>
          </div>
          {sshFingerprint && <div className="host-key-confirm"><strong>Verify this host key</strong><code>{sshFingerprint}</code><small>Enrollment pins this key. A later key change is refused. The password is held only in API process memory.</small></div>}
        </DataAccordion>
      </Accordion.Root>
    </section>
    {confirmation.dialog}
  </div>;
}

function DeviceView({ selected, inspection, status, onRefresh, onSaveModel, onLog }: { selected: Hardware | null; inspection: Inspection | null; status: BenchStatus | null; onRefresh: () => void | Promise<void>; onSaveModel: (model: string) => void; onLog: (channel: string, message: string, tone?: LogEvent["tone"]) => void }) {
  const [model, setModel] = useState(inspection?.model || "");
  const [definitionBusy, setDefinitionBusy] = useState(false);
  const [definitionMessage, setDefinitionMessage] = useState("");
  const [visualBusy, setVisualBusy] = useState("");
  const [visualMessage, setVisualMessage] = useState("");
  const [visualPreview, setVisualPreview] = useState("");
  const [visualAnalysis, setVisualAnalysis] = useState<VisualAnalysis | null>(null);
  useEffect(() => setModel(inspection?.model || ""), [inspection]);
  if (!inspection) return <Empty>Select and inspect a connected interface from Host & devices.</Empty>;
  const importDefinition = async (file: File) => {
    const extension = file.name.toLowerCase().split(".").pop();
    const format = extension === "svd" || extension === "xml" ? "cmsis-svd" : extension === "dts" || extension === "dtsi" ? "zephyr-devicetree" : extension === "kicad_sch" ? "kicad-schematic" : extension === "fzp" ? "fritzing-part" : extension === "fzpz" ? "fritzing-bundle" : null;
    if (!format) { setDefinitionMessage("Choose a .svd, .xml, .dts, .dtsi, .kicad_sch, .fzp, or .fzpz definition file."); return; }
    setDefinitionBusy(true); setDefinitionMessage(`Importing ${file.name}...`);
    try {
      const content = format === "fritzing-bundle" ? await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => { const dataUrl = String(reader.result); resolve(dataUrl.slice(dataUrl.indexOf(",") + 1)); }; reader.onerror = () => reject(reader.error || new Error("Fritzing bundle could not be read")); reader.readAsDataURL(file); }) : await file.text();
      const result = await api.importDefinition(inspection.identifier, format, file.name, content);
      setDefinitionMessage(`${file.name} imported. ${result.count} definition source(s) now bound to this device.`);
      onLog("definitions", `${file.name} imported for ${inspection.model}.`, "ok");
      await onRefresh();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Definition import failed";
      setDefinitionMessage(detail); onLog("definitions", detail, "error");
    } finally { setDefinitionBusy(false); }
  };
  const analyzePhoto = async (file: File) => {
    if (file.size > 12 * 1024 * 1024) { setVisualMessage("Board photos are limited to 12 MiB."); return; }
    setVisualBusy("analyze"); setVisualMessage(`Reading markings from ${file.name} locally...`);
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = () => reject(reader.error || new Error("Photo could not be read")); reader.readAsDataURL(file); });
      const report = await api.analyzeBoardImage(file.name, dataUrl.slice(dataUrl.indexOf(",") + 1));
      setVisualPreview(dataUrl); setVisualAnalysis(report); setVisualMessage(`${report.lines.length} text region(s), ${report.candidates.length} reviewable marking candidate(s). No image bytes were saved.`);
      onLog("visual", `${file.name}: ${report.candidates.length} OCR marking candidates`, report.candidates.length ? "ok" : "warn");
    } catch (error) { const detail = error instanceof Error ? error.message : "Board photo analysis failed"; setVisualMessage(detail); onLog("visual", detail, "error"); }
    finally { setVisualBusy(""); }
  };
  const confirmPhotoCandidate = async (candidate: VisualAnalysis["candidates"][number]) => {
    if (!visualAnalysis) return;
    setVisualBusy(candidate.id);
    try {
      await api.confirmVisualEvidence(inspection.identifier, visualAnalysis, candidate);
      setVisualAnalysis({ ...visualAnalysis, candidates: visualAnalysis.candidates.map((item) => item.id === candidate.id ? { ...item, status: "confirmed" } : item) });
      setVisualMessage(`${candidate.marking} confirmed as ${candidate.suggested_role.replaceAll("_", " ")}. The photo itself was not stored.`);
      onLog("visual", `${candidate.marking} confirmed from board photo`, "ok");
      await onRefresh();
    } catch (error) { const detail = error instanceof Error ? error.message : "Candidate confirmation failed"; setVisualMessage(detail); onLog("visual", detail, "error"); }
    finally { setVisualBusy(""); }
  };
  return <div className="workspace-content"><section>
    <DeviceLivePanel selected={selected} inspection={inspection} status={status} onRefresh={onRefresh} onLog={onLog} />
    <SectionHeading label="Evidence-based inspection" title="Device identity and capabilities" action={<IconButton label="Refresh device evidence" onClick={onRefresh} />} />
    <div className="identity-grid"><div><span>Identified model</span><strong>{inspection.model}</strong></div><div><span>Device class</span><strong>{inspection.classification.replaceAll("_", " ")}</strong></div><div><span>MCU / SoC</span><strong>{inspection.mcu || "Unknown"}</strong></div><div><span>Architecture</span><strong>{inspection.architecture || "Unknown"}</strong></div><div><span>Runtime / OS</span><strong>{inspection.runtime || "Unknown"}</strong></div><div><span>Confidence</span><strong>{Math.round(inspection.confidence * 100)}%</strong></div></div>
    {!!inspection.identity_layers?.length && <div className="table-wrap identity-layer-table"><table><thead><tr><th>Layer</th><th>Identified hardware</th><th>Evidence</th><th>Status</th></tr></thead><tbody>{inspection.identity_layers.map((item) => <tr key={item.id}><td>{item.layer}</td><td><strong>{item.name}</strong></td><td>{item.source}</td><td><span className={statusClass(item.status)}>{item.status}</span></td></tr>)}</tbody></table></div>}
    {!!inspection.candidates.length && <form className="model-picker" onSubmit={(event) => { event.preventDefault(); onSaveModel(model); }}><label htmlFor="model">Exact board model</label><div><select id="model" value={model} onChange={(event) => setModel(event.target.value)}>{inspection.candidates.map((candidate) => <option key={candidate}>{candidate}</option>)}</select><button className="primary" type="submit"><ShieldCheck size={16} />Save model</button></div><small>Model selection filters expected components. Hardware tests are still required before a sensor is marked verified.</small></form>}
    <div className="visual-intelligence"><div className="visual-intelligence-heading"><div><span>Board photo intelligence</span><strong>Read chip and module markings locally</strong></div><label className={`tool-button upload-control ${visualBusy ? "disabled" : ""}`}><ImageUp size={15} />{visualBusy === "analyze" ? "Reading..." : "Analyze photo"}<input type="file" accept="image/jpeg,image/png,image/webp" disabled={Boolean(visualBusy)} onChange={(event) => { const photo = event.target.files?.[0]; if (photo) void analyzePhoto(photo); event.currentTarget.value = ""; }} /></label></div>{visualMessage && <p className="control-message" role="status">{visualMessage}</p>}{visualAnalysis && <div className="visual-review">{visualPreview && <img src={visualPreview} alt="Uploaded circuit board under local OCR review" />}<div className="visual-candidates">{visualAnalysis.candidates.map((candidate) => <div key={candidate.id}><span><strong>{candidate.marking}</strong><small>{candidate.suggested_role.replaceAll("_", " ")} | {Math.round(candidate.ocr_confidence * 100)}% OCR</small></span><button className="tool-button" type="button" disabled={Boolean(visualBusy) || candidate.status === "confirmed"} onClick={() => void confirmPhotoCandidate(candidate)}><ShieldCheck size={14} />{candidate.status === "confirmed" ? "Confirmed" : "Confirm"}</button></div>)}{!visualAnalysis.candidates.length && <Empty>No reliable chip-like marking was found. Try a sharper, closer photo with the text upright.</Empty>}</div></div>}<small>OCR candidates do not prove hidden topology, pin connections, or component function. Confirmation records only the marking and image hash.</small></div>
    <Accordion.Root className="accordion-root two-columns" type="multiple" defaultValue={["evidence", "components"]}>
      <DataAccordion value="discovery" title="Progressive identification coverage" count={`${inspection.discovery?.coverage.filter((item) => item.count > 0).length || 0} areas resolved`} open><div className="sub-actions"><p>Discover, identify, decompose, trace, enrich, and verify remain separate so an interface or USB bridge is never presented as the complete board.</p></div><div className="item-list">{inspection.discovery?.phases.map((phase) => <div className="item-row" key={phase.id}><div><strong>{phase.label}</strong><small>{phase.summary}</small></div><span className={statusClass(phase.status)}>{phase.status}</span></div>)}{!inspection.discovery && <Empty>No progressive discovery report is available.</Empty>}</div></DataAccordion>
      <DataAccordion value="coverage" title="Hardware trace coverage" count={`${inspection.discovery?.unresolved.length || 0} unresolved`}><div className="card-grid">{inspection.discovery?.coverage.map((item) => <article className="data-card" key={item.id}><div><strong>{item.label}</strong><span className={statusClass(item.status)}>{item.count || item.status}</span></div><small>{item.detail}</small><small>Source: {item.source}</small></article>)}</div>{!!inspection.discovery?.unresolved.length && <div className="item-list discovery-gaps">{inspection.discovery.unresolved.map((item) => <div className="item-row" key={item.id}><div><strong>{item.label} remains unresolved</strong><small>{item.next_step}</small><small>Evidence routes: {item.required_evidence.join(", ")}</small></div><span className={statusClass("unknown")}>unknown</span></div>)}</div>}<p className="compatibility-note">{inspection.discovery?.safety.physical_limit}</p></DataAccordion>
      <DataAccordion value="evidence" title="Evidence" count={`${inspection.evidence.length} claims`} open><div className="item-list">{inspection.evidence.map((item, index) => <div className="item-row" key={`${item.source}-${index}`}><div><strong>{item.claim}</strong><small>{item.source}</small></div><span className={statusClass(item.status)}>{item.status}</span></div>)}</div></DataAccordion>
      <DataAccordion value="evidence-graph" title="Evidence graph" count={`${inspection.evidence_graph?.nodes.length || 0} nodes`}><div className="sub-actions"><p>Normalized identities, components, pins, attached peripherals, and imported definitions. Every relationship retains its evidence status and source.</p></div><div className="item-list">{inspection.evidence_graph?.edges.slice(0, 24).map((edge) => { const source = inspection.evidence_graph?.nodes.find((node) => node.id === edge.source); const target = inspection.evidence_graph?.nodes.find((node) => node.id === edge.target); return <div className="item-row" key={edge.id}><div><strong>{source?.name || edge.source} {edge.relation.replaceAll("_", " ")} {target?.name || edge.target}</strong><small>{edge.provenance.source}</small></div><span className={statusClass(edge.status)}>{edge.status}</span></div>; })}{!inspection.evidence_graph?.edges.length && <Empty>No normalized relationships are available.</Empty>}</div></DataAccordion>
      <DataAccordion value="components" title="Components and sensors" count={`${inspection.components.length} items`} open><div className="card-grid">{inspection.components.map((item) => <article className="data-card" key={item.id}><div><strong>{item.name}</strong><span className={statusClass(item.status)}>{item.status}</span></div><small>{[item.type, item.bus, item.variant].filter(Boolean).join(" | ")}</small><small>Source: {item.source}</small></article>)}</div></DataAccordion>
      <DataAccordion value="capabilities" title="Capabilities and services" count={`${inspection.capabilities.length + inspection.services.length} items`}><div className="item-list">{inspection.capabilities.map((item) => <div className="item-row" key={item.id}><div><strong>{item.name}</strong><small>{item.source}</small></div><span className={statusClass(item.status)}>{item.status}</span></div>)}{inspection.services.map((item) => item.url ? <a className="resource service-link" href={item.url} target="_blank" rel="noreferrer" key={`${item.name}-${item.port}`}><div><strong>{item.name}</strong><small>{item.url}</small></div><ExternalLink size={15} /></a> : <div className="item-row" key={`${item.name}-${item.port}`}><div><strong>{item.name}</strong><small>{item.address}:{item.port}</small></div><span className={statusClass(item.status)}>{item.status}</span></div>)}</div></DataAccordion>
      <DataAccordion value="connections" title="External buses and terminal connections" count={`${inspection.connection_interfaces?.length || 0} interfaces`}><div className="item-list">{inspection.connection_interfaces?.map((item) => <div className="item-row connection-row" key={item.id}><div><strong>{item.name}</strong><small>{item.adapter || item.limitation}</small>{item.adapter && <small>{item.limitation}</small>}</div><span className={statusClass(item.status)}>{item.status}</span></div>)}{!inspection.connection_interfaces?.length && <Empty>No externally enumerable bus was identified for this profile.</Empty>}</div></DataAccordion>
      <DataAccordion value="definitions" title="MCU, board and design definitions" count={`${inspection.definitions?.length || 0} imported`}><div className="sub-actions"><p>CMSIS-SVD maps registers, DeviceTree maps topology, KiCad adds design evidence, and Fritzing adds visual part connectors.</p><label className={`tool-button ${definitionBusy ? "disabled" : ""}`}><Upload size={15} />{definitionBusy ? "Importing..." : "Import definition"}<input hidden type="file" disabled={definitionBusy} accept=".svd,.xml,.dts,.dtsi,.kicad_sch,.fzp,.fzpz" onChange={(event) => { const file = event.target.files?.[0]; if (file) void importDefinition(file); event.currentTarget.value = ""; }} /></label></div>{definitionMessage && <p className="control-message" role="status">{definitionMessage}</p>}<div className="item-list">{inspection.definitions?.map((item) => <div className="item-row" key={item.source_sha256}><div><strong>{item.source_name}</strong><small>{item.format} | {item.scope.replaceAll("_", " ")} | {Object.entries(item.counts).map(([key, value]) => `${value} ${key}`).join(", ")}</small></div><span className={statusClass("verified")}>definition</span></div>)}{!inspection.definitions?.length && <Empty>No SVD, DeviceTree, KiCad, or Fritzing definition is bound to this hardware yet.</Empty>}</div></DataAccordion>
      <DataAccordion value="resources" title="Documentation and sources" count={`${inspection.resources.length} links`}><div className="item-list">{inspection.resources.map((item) => <a className="resource" href={item.url} target="_blank" rel="noreferrer" key={item.url}><div><strong>{item.title}</strong><small>{item.provider} | {item.kind}</small></div><ExternalLink size={15} /></a>)}</div></DataAccordion>
    </Accordion.Root>
  </section></div>;
}

function PinAttachmentControl({ identifier, pin, onSaved, onLog }: { identifier: string; pin: DevicePin; onSaved: () => Promise<void>; onLog: (channel: string, message: string, tone?: LogEvent["tone"]) => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(pin.attachment?.component_name || "");
  const [type, setType] = useState(pin.attachment?.component_type || "sensor");
  const [connectionInterface, setConnectionInterface] = useState(pin.attachment?.interface || "direct_pin");
  const [notes, setNotes] = useState(pin.attachment?.notes || "");
  const [busy, setBusy] = useState(false);
  const openEditor = () => {
    setName(pin.attachment?.component_name || "");
    setType(pin.attachment?.component_type || "sensor");
    setConnectionInterface(pin.attachment?.interface || "direct_pin");
    setNotes(pin.attachment?.notes || "");
    setOpen(true);
  };
  const save = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try {
      await api.savePinAttachment(identifier, pin.name, name.trim(), type, connectionInterface, notes.trim());
      await onSaved();
      onLog("pins", `${name.trim()} recorded on ${pin.name} as user-declared evidence.`, "ok");
      setOpen(false);
    } catch (error) { onLog("pins", error instanceof Error ? error.message : "Attachment could not be saved", "error"); }
    finally { setBusy(false); }
  };
  const remove = async () => {
    setBusy(true);
    try {
      await api.deletePinAttachment(identifier, pin.name);
      await onSaved();
      onLog("pins", `User-declared attachment removed from ${pin.name}.`, "warn");
      setOpen(false);
    } catch (error) { onLog("pins", error instanceof Error ? error.message : "Attachment could not be removed", "error"); }
    finally { setBusy(false); }
  };
  return <>
    {pin.attachment && <div className="pin-attachment-summary"><span className={statusClass("declared")}>user declared</span><strong>{pin.attachment.component_name}</strong><small>{pin.attachment.interface.replaceAll("_", " ")}</small></div>}
    <button className="pin-attachment-button" type="button" onClick={openEditor}><PencilLine size={13} />{pin.attachment ? "Edit attachment" : "Record attachment"}</button>
    {open && <div className="approval-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setOpen(false)}><section className="approval-dialog pin-attachment-dialog" role="dialog" aria-modal="true" aria-labelledby={`pin-attachment-${pin.name}`}><header><div><p className="eyebrow">User-confirmed evidence</p><h2 id={`pin-attachment-${pin.name}`}>Attachment on {pin.name}</h2></div><button className="icon-button" type="button" aria-label="Close attachment editor" onClick={() => setOpen(false)}><X size={17} /></button></header><p>Record what you physically observed. This remains declared evidence and is never presented as an automatic electrical detection.</p><div className="pin-attachment-fields"><label>Component or sensor name<input autoFocus value={name} maxLength={128} onChange={(event) => setName(event.target.value)} placeholder="Water temperature sensor" /></label><label>Component type<select value={type} onChange={(event) => setType(event.target.value)}><option value="sensor">Sensor</option><option value="led">LED or light</option><option value="switch">Switch</option><option value="power">Power or battery</option><option value="display">Display</option><option value="camera">Camera</option><option value="controller">Controller or board</option><option value="passive">Passive component</option><option value="user_defined">Other</option></select></label><label>Connection interface<select value={connectionInterface} onChange={(event) => setConnectionInterface(event.target.value)}><option value="direct_pin">Direct pin</option><option value="gpio">GPIO</option><option value="analog">Analog</option><option value="pwm">PWM</option><option value="i2c">I2C</option><option value="spi">SPI</option><option value="uart">UART</option><option value="one_wire">1-Wire</option><option value="power">Power rail</option></select></label><label>Observation notes<textarea value={notes} maxLength={512} onChange={(event) => setNotes(event.target.value)} placeholder="Part marking, wire color, board location, or measurement evidence" /></label></div><footer>{pin.attachment ? <button className="tool-button danger-action" type="button" disabled={busy} onClick={() => void remove()}><Trash2 size={14} />Remove</button> : <span />}<button className="tool-button" type="button" disabled={busy} onClick={() => setOpen(false)}>Cancel</button><button className="primary" type="button" disabled={busy || !name.trim()} onClick={() => void save()}><Save size={14} />{busy ? "Saving..." : "Save evidence"}</button></footer></section></div>}
  </>;
}

function PinsView({ inspection, connected, onRefresh, onLog }: { inspection: Inspection | null; connected: boolean; onRefresh: () => Promise<void>; onLog: (channel: string, message: string, tone?: LogEvent["tone"]) => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState("");
  const [probeMatrix, setProbeMatrix] = useState<ProbeMatrix | null>(null);
  const confirmation = useConfirmation();
  useEffect(() => {
    let current = true;
    setProbeMatrix(null);
    if (!inspection?.identifier) return () => { current = false; };
    void api.probeMatrix(inspection.identifier)
      .then((matrix) => { if (current) setProbeMatrix(matrix); })
      .catch((error) => { if (current) onLog("probe", error instanceof Error ? error.message : "Probe coverage unavailable", "error"); });
    return () => { current = false; };
  }, [inspection?.identifier, connected, onLog]);
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
    if (!connected) return;
    const test = inspection.tests.find((item) => item.id === testId);
    if (!test?.available) return;
    if (!await confirmation.request({ title: test.name, message: test.description, confirmLabel: "Run probe", risk: test.risk })) return;
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
    <div className="probe-toolbar"><div><strong>Controlled device probe</strong><small>{!connected ? "The selected interface is disconnected. Last-known evidence remains visible, but live probes are locked." : runtimeProbe?.description || (inspection.adapter ? "This adapter has no deeper target-identification action." : "No compatible runtime adapter detected.")}</small></div><button className="tool-button danger-action" type="button" disabled={!connected || !runtimeProbe?.available || Boolean(busy)} onClick={() => runtimeProbe && void runProbe(runtimeProbe.id)}><Activity size={15} />{busy === runtimeProbe?.id ? "Probing..." : "Run deep probe"}</button><button className="tool-button" type="button" hidden={!i2cProbe} disabled={!connected || !i2cProbe?.available || Boolean(busy)} onClick={() => i2cProbe && void runProbe(i2cProbe.id)}><Search size={15} />{busy === i2cProbe?.id ? "Scanning..." : "Scan I2C bus"}</button></div>
    <div className="probe-coverage"><div className="subsection-heading"><h3>Probe coverage</h3><span>{probeMatrix ? `${probeMatrix.available_count} available | ${probeMatrix.instrument_required_count} instrument` : "Loading"}</span></div><div className="table-wrap"><table><thead><tr><th>Interface</th><th>Detects</th><th>Route</th><th>Status</th><th>Action</th></tr></thead><tbody>{probeMatrix?.probes.map((probe) => <tr key={probe.id}><td><strong>{probe.label}</strong><small>{probe.reason}</small></td><td>{probe.detects}</td><td>{probe.route}</td><td><span className={statusClass(probe.status === "available" ? "verified" : probe.status === "locked" ? "unavailable" : "expected")}>{probe.status.replaceAll("_", " ")}</span></td><td>{probe.can_run && probe.test_id ? <button className="tool-button" type="button" disabled={Boolean(busy)} onClick={() => void runProbe(probe.test_id!)}><Play size={14} />Run</button> : <span className="muted">{probe.adapter || "External fixture"}</span>}</td></tr>)}{!probeMatrix && <tr><td colSpan={5}>Loading safe probe coverage...</td></tr>}</tbody></table></div>{probeMatrix && <p className="compatibility-note">{probeMatrix.safety.reason}</p>}</div>
    <div className="pin-layout"><div><div className="subsection-heading"><h3>Board pins</h3><span>{pins.length} pins</span></div><div className="pin-groups">{[...groups].map(([group, groupPins]) => <section className="pin-group" key={group}><header><strong>{group}</strong><span>{groupPins.length} pins</span></header><div className="pin-grid">{groupPins.map((pin) => <article className="pin-card" key={`${group}-${pin.name}`}><div><strong>{[pin.name, ...pin.aliases].join(" / ")}</strong><span className={statusClass(pin.status)}>{pin.status}</span></div><small>{pin.functions.join(" | ")}</small>{pin.electrical && <small>{pin.electrical.rail || `${pin.electrical.logic_voltage_v} V logic`} {pin.electrical.absolute_input_max_v ? `| ${pin.electrical.absolute_input_max_v} V absolute max` : ""}{pin.electrical.five_volt_tolerant === false ? " | not 5 V tolerant" : ""}</small>}<small>{pin.source}</small>{!!pin.knowledge?.length && <div className="pin-knowledge">{pin.knowledge.map((knowledge) => <Tooltip.Root key={knowledge.id}><Tooltip.Trigger asChild><button type="button" aria-label={`Explain ${knowledge.canonical}`}><CircleHelp size={13} />{knowledge.canonical}</button></Tooltip.Trigger><Tooltip.Portal><Tooltip.Content className="tooltip pin-tooltip" sideOffset={7}><strong>{knowledge.canonical}</strong><span>{knowledge.summary}</span><em>{knowledge.caution}</em><Tooltip.Arrow className="tooltip-arrow" /></Tooltip.Content></Tooltip.Portal></Tooltip.Root>)}</div>}<PinAttachmentControl identifier={inspection.identifier} pin={pin} onSaved={onRefresh} onLog={onLog} /></article>)}</div></section>)}{!pins.length && <Empty>No pin map is available for this device profile.</Empty>}</div></div><div><div className="subsection-heading"><h3>Attached peripherals</h3><span>{peripherals.length} mapped</span></div><div className="peripheral-list">{peripherals.map((peripheral) => <article className="peripheral-card" key={peripheral.id}><div><strong>{peripheral.name}</strong><span className={statusClass(peripheral.status)}>{peripheral.status}</span></div><small>Candidates: {peripheral.candidates.join("; ")}</small><small>{peripheral.bus} {peripheral.address} | {peripheral.source}</small></article>)}{!peripherals.length && <Empty>No responding or user-declared external attachment has been mapped.</Empty>}</div></div></div>
  </section>{confirmation.dialog}</div>;
}

function DiagnosticConsole({ selected, inspection, events, onClear, onLog }: { selected: Hardware | null; inspection: Inspection | null; events: LogEvent[]; onClear: () => void; onLog: (channel: string, message: string, tone?: LogEvent["tone"]) => void }) {
  const [open, setOpen] = useState(false);
  const [command, setCommand] = useState("test:presence");
  const [busy, setBusy] = useState(false);
  const safeTests = (inspection?.tests || []).filter((test) => test.available && (test.risk === "passive" || test.risk === "read-only"));
  const operatingSystemCommands = Boolean(selected?.kind === "usb_network" && selected.is_lichee);
  const compatible = Boolean(selected && (safeTests.length || operatingSystemCommands));
  useEffect(() => {
    if (safeTests.length && !safeTests.some((test) => `test:${test.id}` === command) && command.startsWith("test:")) setCommand(`test:${safeTests[0].id}`);
  }, [inspection?.identifier, safeTests, command]);
  const run = async () => {
    if (!selected) return;
    setBusy(true); setOpen(true); onLog("target", `Running ${command} on ${selected.ip_address || selected.device}...`);
    try {
      if (command.startsWith("test:")) {
        const result = await api.runTest(selected.id, command.slice(5));
        onLog("test-profile", result.summary, result.passed ? "ok" : "error");
      } else {
        const result = await api.runCommand(selected.id, command);
        onLog("target", `${result.label} @ ${result.target}\n${result.output}`, "ok");
      }
    }
    catch (error) { onLog("target", error instanceof Error ? error.message : "Target diagnostic failed", "error"); }
    finally { setBusy(false); }
  };
  return <aside className={`diagnostic-console ${open ? "open" : ""}`} aria-label="Diagnostic console"><button className="console-toggle" type="button" onClick={() => setOpen((value) => !value)}><SquareTerminal size={15} /><strong>Diagnostic console</strong><span>{events.length} events</span><ChevronDown size={15} /></button>{open && <div className="console-body"><div className="console-toolbar"><select aria-label="Read-only target diagnostic profile" value={command} disabled={!compatible || busy} onChange={(event) => setCommand(event.target.value)}>{safeTests.length > 0 && <optgroup label="Selected-device test profiles">{safeTests.map((test) => <option key={test.id} value={`test:${test.id}`}>{test.name}</option>)}</optgroup>}{operatingSystemCommands && <optgroup label="Read-only operating-system diagnostics"><option value="system_summary">System summary</option><option value="network_interfaces">Network interfaces</option><option value="usb_devices">USB devices</option><option value="i2c_adapters">I2C adapters</option><option value="media_devices">Media devices</option></optgroup>}</select><button className="tool-button" type="button" disabled={!compatible || busy} onClick={() => void run()}><Play size={14} />{busy ? "Running..." : "Run profile"}</button><button className="tool-button" type="button" onClick={onClear}>Clear</button></div>{!compatible && <p className="console-note">Inspect a connected target to load its advertised passive and read-only profiles. Arbitrary shell input is intentionally unavailable.</p>}<div className="console-output" role="log" aria-live="polite">{events.map((event, index) => <div className={event.tone || ""} key={`${event.at}-${index}`}><span>{event.at}</span><b>{event.channel}</b><pre>{event.message}</pre></div>)}{!events.length && <p>No bench events yet.</p>}</div></div>}</aside>;
}

function ConnectionsView({ selected, inspection, status, onLog }: { selected: Hardware | null; inspection: Inspection | null; status: BenchStatus | null; onLog: (channel: string, message: string, tone?: LogEvent["tone"]) => void }) {
  if (!inspection) return <Empty>Inspect a device before configuring Bluetooth or Wi-Fi.</Empty>;
  return <div className="workspace-content"><WirelessControls selected={selected} inspection={inspection} status={status} onLog={onLog} /></div>;
}

function TestsView({ selected, inspection, onRefresh }: { selected: Hardware | null; inspection: Inspection | null; onRefresh: () => void | Promise<void> }) {
  const [results, setResults] = useState<Record<string, string>>({});
  const [history, setHistory] = useState<EvidenceHistory | null>(null);
  const loadHistory = useCallback(async () => {
    if (!inspection) return;
    setHistory(await api.evidenceHistory(inspection.identifier));
  }, [inspection]);
  useEffect(() => { void loadHistory(); }, [loadHistory]);
  const run = async (testId: string) => {
    if (!inspection || !selected) return;
    setResults((old) => ({ ...old, [testId]: "Running..." }));
    try {
      const result = await api.runTest(inspection.identifier, testId);
      setResults((old) => ({ ...old, [testId]: result.summary }));
      await onRefresh();
      await loadHistory();
    } catch (error) {
      setResults((old) => ({ ...old, [testId]: error instanceof Error ? error.message : "Test failed" }));
    }
  };
  const exportHistory = async () => {
    if (!inspection) return;
    const payload = await api.exportEvidenceHistory(inspection.identifier);
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `iot-bench-${inspection.identifier.replace(/[^a-z0-9]+/gi, "-")}-history.json`;
    link.click();
    URL.revokeObjectURL(url);
  };
  if (!inspection) return <Empty>Inspect a device before running tests.</Empty>;
  const capabilityIds = new Set(inspection.capabilities.map((item) => item.id));
  const hasBle = capabilityIds.has("ble");
  const hasWifi = capabilityIds.has("wifi_24") || capabilityIds.has("wifi_5");
  return <div className="workspace-content"><section><SectionHeading label="Controlled verification" title={`Tests for ${inspection.model}`} action={<IconButton label="Refresh live test availability" onClick={onRefresh} />} />{!selected && <p className="compatibility-note">The selected interface is disconnected. Last results remain visible; live tests are locked until it reconnects.</p>}<div className="test-grid">{inspection.tests.map((test) => <article className="test-card" key={test.id}><div className="test-icon"><Activity size={18} /></div><div><strong>{test.name}</strong><p>{test.description}</p><span className={`risk risk-${test.risk}`}>{test.risk}</span>{results[test.id] && <small className="test-result">{results[test.id]}</small>}</div><button className="tool-button" type="button" disabled={!selected || !test.available || results[test.id] === "Running..."} onClick={() => run(test.id)}><Play size={15} />{!selected ? "Disconnected" : test.available ? "Run" : "Unavailable"}</button></article>)}</div><div className="test-context">{hasBle && <div><Bluetooth size={18} /><strong>Bluetooth (BLE)</strong><span>Available on this selected hardware profile.</span></div>}{hasWifi && <div><Wifi size={18} /><strong>Wi-Fi</strong><span>Available on this selected hardware profile.</span></div>}<div><RadioTower size={18} /><strong>Signals</strong><span>Unknown pins and buses are never driven until a compatible protocol or board map is established.</span></div></div></section><section><SectionHeading label="Evidence history" title="Recorded test results" action={<div className="actions"><IconButton label="Refresh recorded test results" onClick={() => void loadHistory()} /><button className="tool-button" type="button" disabled={!history?.tests.length} onClick={() => void exportHistory()}><Database size={15} />Export JSON</button></div>} /><p className="intro">Redacted results survive reloads and are retained up to {history?.retention_per_device || 100} entries per selected device.</p><div className="table-wrap"><table><thead><tr><th>Time</th><th>Test</th><th>Result</th><th>Summary</th></tr></thead><tbody>{history?.tests.map((record) => <tr key={record.sequence}><td>{new Date(record.recorded_at).toLocaleString()}</td><td>{record.test_id}</td><td><span className={statusClass(record.passed ? "verified" : "unavailable")}>{record.passed ? "Passed" : "Failed"}</span></td><td className="wrap">{String(record.result.summary || "No summary recorded")}</td></tr>)}{!history?.tests.length && <tr><td colSpan={4}>No tests have been recorded for this target.</td></tr>}</tbody></table></div></section></div>;
}

function FirmwareView({ selected, inspection, activeOperations, onLog }: { selected: Hardware | null; inspection: Inspection | null; activeOperations: ActiveOperation[]; onLog: (channel: string, message: string, tone?: LogEvent["tone"]) => void }) {
  const [inventory, setInventory] = useState<WorkspaceInventory | null>(null);
  const [capabilities, setCapabilities] = useState<OperationCapability[]>([]);
  const [history, setHistory] = useState<OperationEvent[]>([]);
  const [file, setFile] = useState<WorkspaceFile | null>(null);
  const [analysis, setAnalysis] = useState<FirmwareAnalysis | null>(null);
  const [emulation, setEmulation] = useState<EmulationCatalog | null>(null);
  const [emulationPlatform, setEmulationPlatform] = useState("");
  const [emulationVerification, setEmulationVerification] = useState<EmulationVerification | null>(null);
  const [emulationRun, setEmulationRun] = useState<EmulationRun | null>(null);
  const [firmwareUpload, setFirmwareUpload] = useState<{ filename: string; contentBase64: string } | null>(null);
  const [originalContent, setOriginalContent] = useState("");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const confirmation = useConfirmation();
  const identifier = selected?.id || inspection?.identifier;
  const activeOperation = activeOperations.find((operation) => operation.identifier === identifier);

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
  useEffect(() => {
    if (!identifier) return;
    let cancelled = false;
    void api.emulationPlatforms(inspection?.model || selected?.name || "").then((catalog) => {
      if (cancelled) return;
      setEmulation(catalog);
      setEmulationPlatform(catalog.exact_match?.id || catalog.platforms[0]?.id || "");
      setEmulationVerification(null);
    }).catch(() => !cancelled && setEmulation(null));
    return () => { cancelled = true; };
  }, [identifier, inspection?.model, selected?.name]);

  const openFile = async (rootId: string, path: string) => {
    if (!identifier) return;
    setBusy(`file:${rootId}:${path}`);
    try { const next = await api.workspaceFile(identifier, rootId, path); setFile(next); setOriginalContent(next.content); }
    catch (error) { setMessage(error instanceof Error ? error.message : "File could not be opened"); }
    finally { setBusy(""); }
  };

  const runOperation = async (operation: OperationCapability) => {
    if (!identifier || !selected || !operation.available) return;
    setBusy(operation.id); setMessage(`Planning ${operation.label}...`);
    try {
      const plan = await api.planOperation(identifier, operation.id);
      let token: string | undefined;
      if (plan.requires_approval) {
        const approved = await confirmation.request({ title: `Approve ${operation.label}?`, message: `${plan.preview} This approval expires in ${plan.expires_in_seconds} seconds.`, confirmLabel: "Approve and run", risk: plan.risk });
        if (!approved) { setMessage("Operation cancelled before approval."); return; }
        token = (await api.approveOperation(identifier, plan.plan_id)).approval_token;
      }
      const result = await api.executeOperation(identifier, plan.plan_id, token);
      setMessage(result.output); onLog("operation", `${operation.label}: ${result.output}`, result.passed ? "ok" : "error");
      await refresh();
    } catch (error) { const text = error instanceof Error ? error.message : "Operation failed"; setMessage(text); onLog("operation", text, "error"); }
    finally { setBusy(""); }
  };

  const cancelOperation = async () => {
    if (!identifier) return;
    setMessage("Cancelling the active operation...");
    try {
      const result = await api.cancelOperation(identifier);
      if (!result.process_terminated && !result.plans_cancelled) setMessage("No active operation was found for this target.");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Operation cancellation failed";
      setMessage(text); onLog("operation", text, "error");
    }
  };

  const saveFile = async () => {
    if (!identifier || !selected || !file || file.content === originalContent) return;
    setBusy("save");
    try {
      const plan = await api.planWorkspaceWrite(identifier, file);
      if (!await confirmation.request({ title: "Save firmware file change?", message: plan.preview, confirmLabel: "Approve and save", risk: plan.risk })) { setMessage("File save cancelled."); return; }
      const approved = await api.approveOperation(identifier, plan.plan_id);
      const result = await api.executeOperation(identifier, plan.plan_id, approved.approval_token);
      setMessage(result.output); onLog("workspace", result.output, result.passed ? "ok" : "error");
      if (result.passed) { const next = await api.workspaceFile(identifier, file.root_id, file.path); setFile(next); setOriginalContent(next.content); }
      await refresh();
    } catch (error) { const text = error instanceof Error ? error.message : "File save failed"; setMessage(text); onLog("workspace", text, "error"); }
    finally { setBusy(""); }
  };

  const analyzeBinary = async (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    event.target.value = "";
    if (!selectedFile) return;
    if (selectedFile.size > 16 * 1024 * 1024) { setMessage("Firmware analysis is limited to 16 MiB per file."); return; }
    setBusy("analyze"); setMessage(`Analyzing ${selectedFile.name} without executing it...`);
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = () => reject(reader.error || new Error("Firmware file could not be read"));
        reader.readAsDataURL(selectedFile);
      });
      const report = await api.analyzeFirmware(selectedFile.name, dataUrl.slice(dataUrl.indexOf(",") + 1));
      const contentBase64 = dataUrl.slice(dataUrl.indexOf(",") + 1);
      setAnalysis(report); setFirmwareUpload({ filename: selectedFile.name, contentBase64 }); setEmulationRun(null); setMessage(`${report.filename} identified as ${report.format}; uploaded bytes were not executed.`);
      onLog("firmware", `${report.filename}: ${report.format}, ${report.size_bytes} bytes`, "ok");
    } catch (error) { const text = error instanceof Error ? error.message : "Firmware analysis failed"; setMessage(text); onLog("firmware", text, "error"); }
    finally { setBusy(""); }
  };

  const verifyVirtualPlatform = async () => {
    if (!emulationPlatform) return;
    setBusy("emulation"); setEmulationVerification(null); setMessage(`Loading ${emulationPlatform} in Renode...`);
    try {
      const report = await api.verifyEmulationPlatform(emulationPlatform);
      setEmulationVerification(report); setMessage(`Renode loaded ${report.platform.label} with ${report.peripheral_count} modeled peripherals. No guest firmware ran.`);
      onLog("emulation", `Verified ${report.platform.id} in Renode ${report.version}`, "ok");
    } catch (error) { const text = error instanceof Error ? error.message : "Renode platform verification failed"; setMessage(text); onLog("emulation", text, "error"); }
    finally { setBusy(""); }
  };

  const runVirtualFirmware = async () => {
    if (!emulationPlatform || !firmwareUpload || analysis?.format !== "elf") return;
    setBusy("emulation-run"); setEmulationRun(null); setMessage(`Running ${firmwareUpload.filename} for 50 ms on the isolated ${emulationPlatform} model...`);
    try {
      const report = await api.runEmulatedFirmware(emulationPlatform, firmwareUpload.filename, firmwareUpload.contentBase64, 50);
      setEmulationRun(report); setMessage(`${report.firmware.filename} ran for ${report.runtime_ms} ms on ${report.platform.label}; physical hardware was not changed.`);
      onLog("emulation", `${report.firmware.filename} ran on ${report.platform.id} in Renode ${report.version}`, "ok");
    } catch (error) { const text = error instanceof Error ? error.message : "Renode firmware execution failed"; setMessage(text); onLog("emulation", text, "error"); }
    finally { setBusy(""); }
  };

  if (!identifier) return <Empty>Select and inspect hardware before opening firmware tools.</Empty>;
  return <div className="workspace-content"><section>
    <SectionHeading label="Controlled target workspace" title={`Firmware and files for ${inspection?.model || selected?.name || "selected hardware"}`} action={<IconButton label="Refresh firmware workspace" busy={busy === "refresh"} onClick={() => void refresh()} />} />
    <p className="intro">{message || "Builds are local. Device writes require a target-bound, short-lived approval and create an audit receipt."}</p>
    {activeOperation && <div className="operation-live" role="log" aria-live="polite"><header><span><Activity size={15} />{activeOperation.label}</span><small>Live process output</small></header><pre>{activeOperation.output || "Process started; waiting for output..."}</pre></div>}
    <div className="operation-grid">{capabilities.map((operation) => <article className="operation-card" key={operation.id}><div className="test-icon">{operation.risk === "destructive" ? <ShieldCheck size={18} /> : <Hammer size={18} />}</div><div><strong>{operation.label}</strong><p>{operation.description}</p><span className={`risk risk-${operation.risk}`}>{operation.risk}</span>{!operation.available && <small>{operation.reason}</small>}</div><button className={`tool-button ${busy === operation.id ? "danger-action" : ""}`} type="button" disabled={!selected || !operation.available || (Boolean(busy) && busy !== operation.id)} onClick={() => void (busy === operation.id ? cancelOperation() : runOperation(operation))}>{busy === operation.id ? <Square size={15} /> : <Play size={15} />}{!selected ? "Disconnected" : busy === operation.id ? "Cancel" : operation.available ? "Plan & run" : "Unavailable"}</button></article>)}</div>
  </section><section>
    <SectionHeading label="Firmware intelligence" title="Inspect a binary without executing it" action={<label className={`tool-button upload-control ${busy === "analyze" ? "disabled" : ""}`}><Upload size={15} />{busy === "analyze" ? "Analyzing..." : "Analyze firmware"}<input type="file" accept=".bin,.elf,.axf,.uf2,.hex,.img,.rom,.fw,application/octet-stream" disabled={Boolean(busy)} onChange={(event) => void analyzeBinary(event)} /></label>} />
    <p className="intro">Static inspection verifies hashes, format structure, entropy, strings, URLs, and architecture metadata when the file proves it. External reverse-engineering engines are never launched by this upload action.</p>
    {analysis ? <div className="firmware-analysis"><div className="runtime-grid firmware-metrics"><div><small>Format</small><strong>{analysis.format}</strong></div><div><small>Architecture</small><strong>{analysis.architecture || "Unproven"}</strong></div><div><small>Size</small><strong>{analysis.size_bytes.toLocaleString()} B</strong></div><div><small>Entropy</small><strong>{analysis.entropy_bits_per_byte} bits/B</strong></div><div><small>SHA-256</small><strong title={analysis.sha256}>{analysis.sha256.slice(0, 16)}</strong></div><div><small>Execution</small><strong>{analysis.safety.uploaded_bytes_executed ? "Unsafe" : "Never executed"}</strong></div></div><div className="firmware-analysis-grid"><article><strong>Verified structure</strong><pre>{JSON.stringify(analysis.format_details, null, 2)}</pre></article><article><strong>Optional analysis engines</strong>{analysis.engines.map((engine) => <div className="engine-row" key={engine.id}><span>{engine.name}<small>{engine.purpose}</small></span><span className={statusClass(engine.available ? "detected" : "unavailable")}>{engine.available ? "available" : "not installed"}</span></div>)}</article><article><strong>Extracted indicators</strong>{analysis.urls.map((url) => <code key={url}>{url}</code>)}{analysis.strings.slice(0, 20).map((value, index) => <code key={`${index}:${value}`}>{value}</code>)}{!analysis.strings.length && <small>No printable strings found.</small>}</article></div></div> : <Empty>Select an ELF, UF2, Intel HEX, Espressif image, or raw firmware file for bounded static inspection.</Empty>}
  </section><section>
    <SectionHeading label="Firmware emulation" title="Verified virtual board platforms" action={<div className="actions"><button className="tool-button" type="button" disabled={!emulation?.installed || !emulationPlatform || Boolean(busy)} onClick={() => void verifyVirtualPlatform()}><Play size={15} />{busy === "emulation" ? "Loading..." : "Verify platform"}</button><button className="tool-button" type="button" disabled={!emulation?.installed || !emulationPlatform || !firmwareUpload || analysis?.format !== "elf" || Boolean(busy)} onClick={() => void runVirtualFirmware()}><Activity size={15} />{busy === "emulation-run" ? "Running..." : "Run ELF"}</button></div>} />
    <p className="intro">Renode board models are isolated virtual targets. ELF execution is architecture-checked and time-bounded; it never identifies or changes the connected physical device.</p>
    <div className="emulation-picker"><label>Renode platform<select value={emulationPlatform} disabled={!emulation?.installed || Boolean(busy)} onChange={(event) => { setEmulationPlatform(event.target.value); setEmulationVerification(null); }}>{emulation?.platforms.map((platform) => <option value={platform.id} key={platform.id}>{platform.label}{platform.match_score ? ` (${platform.match_score} identity tokens)` : ""}</option>)}</select></label><div><small>Engine</small><strong>{emulation?.installed ? `Renode ${emulation.version}` : "Not installed"}</strong></div><div><small>Identity match</small><strong>{emulation?.exact_match?.label || "Exact platform unresolved"}</strong></div><div><small>Model count</small><strong>{emulation?.count || 0}</strong></div></div>
    {emulationVerification && <div className="emulation-result"><strong>{emulationVerification.platform.label}</strong><span className={statusClass("verified")}>{emulationVerification.peripheral_count} peripherals loaded</span><div>{emulationVerification.peripherals.map((peripheral) => <code key={`${peripheral.name}:${peripheral.model}`}>{peripheral.name} <small>{peripheral.model}</small></code>)}</div></div>}
    {emulationRun && <div className="emulation-result"><strong>{emulationRun.firmware.filename}</strong><span className={statusClass(emulationRun.firmware_executed ? "verified" : "unavailable")}>{emulationRun.firmware_executed ? `${emulationRun.runtime_ms} ms guest run complete` : "Execution not confirmed"}</span><div>{emulationRun.trace.map((line) => <code key={line}>{line}</code>)}</div><small>Allowlisted platform, architecture checked, temporary guest deleted, physical hardware unchanged.</small></div>}
  </section><section>
    <SectionHeading label="Allowlisted source access" title="Project and mounted-device files" action={file && <button className="tool-button" type="button" disabled={!selected || file.content === originalContent || Boolean(busy)} onClick={() => void saveFile()}><Save size={15} />{busy === "save" ? "Saving..." : "Review & save"}</button>} />
    <div className="file-workspace" aria-busy={busy === "refresh" || busy.startsWith("file:")}>{(busy === "refresh" || busy.startsWith("file:")) && <div className="workspace-loading" role="status"><RefreshCw className="spin" size={22} /><strong>{busy === "refresh" ? "Indexing allowed source roots" : "Opening and hashing source file"}</strong></div>}<aside>{inventory?.roots.map((root) => <div className="file-root" key={root.id}><strong>{root.name}</strong><small>{root.source}</small>{inventory.files.filter((item) => item.root_id === root.id).map((item) => <button type="button" className={file?.root_id === item.root_id && file.path === item.path ? "active" : ""} key={`${item.root_id}:${item.path}`} onClick={() => void openFile(item.root_id, item.path)}><FileCode2 size={13} /><span>{item.path}</span><small>{item.size} B</small></button>)}</div>)}</aside><div className="code-editor">{file ? <><header><strong>{file.path}</strong><span>sha256 {file.sha256.slice(0, 12)}</span></header><Suspense fallback={<Empty>Loading editor...</Empty>}><Editor height="100%" language={editorLanguage(file.path)} theme="vs-dark" value={file.content} onChange={(content) => setFile({ ...file, content: content || "" })} options={{ automaticLayout: true, fontSize: 12, lineNumbersMinChars: 3, minimap: { enabled: false }, scrollBeyondLastLine: false, tabSize: 2, wordWrap: "off", ariaLabel: `Edit ${file.path}` }} /></Suspense></> : <Empty>Select a source or configuration file to inspect it. Binary firmware images are intentionally excluded from the editor.</Empty>}</div></div>
  </section><section>
    <SectionHeading label="Immutable evidence trail" title="Operation receipts" />
    <div className="table-wrap"><table><thead><tr><th>Time</th><th>Operation</th><th>Risk</th><th>Status</th><th>Evidence</th></tr></thead><tbody>{history.slice(0, 25).map((event) => <tr key={event.sequence}><td>{new Date(event.recorded_at).toLocaleString()}</td><td>{event.operation_id}</td><td><span className={`risk risk-${event.risk}`}>{event.risk}</span></td><td>{event.status}</td><td className="wrap">{event.output || event.preview}</td></tr>)}{!history.length && <tr><td colSpan={5}>No operations have been planned for this target.</td></tr>}</tbody></table></div>
  </section>{confirmation.dialog}</div>;
}

function ToolsView({ registry, providers, adapters, onRefresh }: { registry: ToolRegistry | null; providers: ProviderRegistry | null; adapters: AdapterRegistry | null; onRefresh: () => void }) {
  const [diagnostic, setDiagnostic] = useState<ToolDiagnostic | null>(null);
  const [instruments, setInstruments] = useState<InstrumentReport | null>(null);
  const [busy, setBusy] = useState("");
  const diagnose = async (toolId: string) => {
    setBusy(toolId); setDiagnostic(null);
    try { setDiagnostic(await api.diagnoseTool(toolId)); }
    catch (error) { setDiagnostic({ tool: registry!.tools.find((item) => item.id === toolId)!, available: false, diagnostic_ran: false, output: error instanceof Error ? error.message : "Diagnostic failed", duration_ms: 0, physical_hardware_changed: false, route: "Tools & sources" }); }
    finally { setBusy(""); }
  };
  const scanInstruments = async () => {
    setBusy("instruments");
    try { setInstruments(await api.instruments()); }
    finally { setBusy(""); }
  };
  return <div className="workspace-content"><section>
    <SectionHeading label="Extensible discovery engine" title="Tools and metadata sources" action={<div className="actions"><button className="tool-button" type="button" disabled={Boolean(busy)} onClick={() => void scanInstruments()}><Radar className={busy === "instruments" ? "spin" : ""} size={15} />{busy === "instruments" ? "Scanning..." : "Scan fixtures"}</button><IconButton label="Refresh tools and providers" onClick={onRefresh} /></div>} />
    <p className="intro">Providers enrich identity and documentation. Local evidence remains authoritative for connected hardware and verified capabilities.</p>
    {instruments && <div className="instrument-report" role="status"><div className="subsection-heading"><h3>Connected bench fixtures</h3><span>{instruments.connected_count} connected</span></div><div className="item-list">{instruments.fixtures.map((fixture) => <div className="item-row" key={fixture.id}><div><strong>{fixture.name}</strong><small>{fixture.fixture_count ? fixture.devices.map((device) => device.description || device.product || device.unique_id).join(", ") : fixture.next_step}</small><small>{fixture.tools.length ? `Tools: ${fixture.tools.join(", ")}` : "No compatible local tool"} | target wiring not confirmed</small></div><span className={statusClass(fixture.status === "connected" ? "verified" : fixture.status === "tool_ready" ? "detected" : "unavailable")}>{fixture.status.replaceAll("_", " ")}</span></div>)}</div><p className="compatibility-note">{instruments.safety.reason}</p></div>}
    <Accordion.Root className="accordion-root" type="multiple" defaultValue={["adapters", "providers", "tools"]}>
      <DataAccordion value="adapters" title="Installed hardware adapters" count={adapters ? `${adapters.count} active contracts` : "Loading"} open><div className="card-grid">{adapters?.adapters.map((adapter) => <article className="data-card available" key={adapter.id}><div><strong>{adapter.name}</strong><span className={statusClass("verified")}>v{adapter.version}</span></div><small>{adapter.families.join(", ")}</small><small>{adapter.transports.join(" | ")} | {adapter.inspection_modes.join(", ")}</small><small>{adapter.safety}</small></article>)}</div></DataAccordion>
      <DataAccordion value="providers" title="Metadata providers" count={providers ? `${providers.available_count} of ${providers.providers.length} ready` : "Loading"} open><div className="card-grid">{providers?.providers.map((provider) => <article className={`data-card ${provider.available ? "available" : ""}`} key={provider.id}><div><strong>{provider.name}</strong><span className={statusClass(provider.available ? "verified" : "unavailable")}>{provider.available ? "ready" : "not configured"}</span></div><small>{provider.scope}</small><small>{provider.mode}{provider.requires_key ? " | optional credentials" : ""}</small></article>)}</div></DataAccordion>
      <DataAccordion value="tools" title="Command-line tools" count={registry ? `${registry.available_count} of ${registry.tools.length} available` : "Loading"} open>{diagnostic && <div className="tool-diagnostic" role="status"><div><strong>{diagnostic.tool.name}</strong><span className={statusClass(diagnostic.available ? "verified" : "unavailable")}>{diagnostic.available ? "available" : "unavailable"}</span></div><pre>{diagnostic.output || "Path verified."}</pre><small>{diagnostic.duration_ms} ms | physical hardware unchanged | continue in {diagnostic.route}</small></div>}<div className="table-wrap"><table><thead><tr><th>Tool</th><th>Purpose</th><th>Risk</th><th>Status</th><th>Actions</th></tr></thead><tbody>{registry?.tools.map((tool) => <tr key={tool.id}><td>{tool.name}</td><td>{tool.category}</td><td><span className={`risk risk-${tool.risk}`}>{tool.risk}</span></td><td>{tool.available ? tool.version || "Available" : "Not installed"}</td><td><div className="table-actions"><button className="icon-button" type="button" title={`Diagnose ${tool.name}`} aria-label={`Diagnose ${tool.name}`} disabled={busy === tool.id} onClick={() => void diagnose(tool.id)}><CircleHelp className={busy === tool.id ? "spin" : ""} size={15} /></button>{tool.documentation_url && <a className="icon-button" title={`${tool.name} documentation`} aria-label={`${tool.name} documentation`} href={tool.documentation_url} target="_blank" rel="noreferrer"><ExternalLink size={15} /></a>}</div></td></tr>)}</tbody></table></div></DataAccordion>
    </Accordion.Root>
  </section></div>;
}

export default function App() {
  const [workspace, setWorkspace] = useState<Workspace>(restoredWorkspace);
  const [hardware, setHardware] = useState<Hardware[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(restoredSelectedId);
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [usb, setUsb] = useState<UsbInventory | null>(null);
  const [host, setHost] = useState<HostInventory | null>(null);
  const [registry, setRegistry] = useState<ToolRegistry | null>(null);
  const [providers, setProviders] = useState<ProviderRegistry | null>(null);
  const [adapters, setAdapters] = useState<AdapterRegistry | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingLabel, setLoadingLabel] = useState("Scanning connected hardware");
  const [message, setMessage] = useState("Scanning this computer for connected hardware...");
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [benchStatus, setBenchStatus] = useState<BenchStatus | null>(null);
  const [apiConnected, setApiConnected] = useState(false);
  const deviceRevision = useRef(0);
  const selectedIdRef = useRef<string | null>(selectedId);
  const inspectionRequest = useRef(0);
  const restorationAttempted = useRef(false);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
    window.localStorage.setItem("iot-bench.workspace", workspace);
  }, [workspace]);
  useEffect(() => {
    if (selectedId) window.localStorage.setItem("iot-bench.selected-id", selectedId);
    else window.localStorage.removeItem("iot-bench.selected-id");
  }, [selectedId]);

  const log = useCallback((channel: string, eventMessage: string, tone?: LogEvent["tone"]) => {
    setEvents((current) => [...current.slice(-199), { at: new Date().toLocaleTimeString(), channel, message: eventMessage, tone }]);
  }, []);

  const selected = useMemo(() => hardware.find((item) => item.id === selectedId) || null, [hardware, selectedId]);
  const loadHost = useCallback(async (force = false) => {
    setLoadingLabel("Scanning connected hardware");
    setLoading(true);
    try {
      const [nextHardware, nextUsb, nextHost] = await Promise.all([api.hardware(force), api.usbInventory(false), api.hostInventory()]);
      setApiConnected(true);
      setHardware(nextHardware); setUsb(nextUsb); setHost(nextHost);
      setSelectedId((current) => (current && nextHardware.some((item) => item.id === current) ? current : nextHardware.find((item) => item.classification)?.id || nextHardware[0]?.id || null));
      const nextMessage = `${nextHardware.length} selectable interfaces found on ${nextHost.hostname}. No target was opened or changed.`;
      setMessage(nextMessage); log("host", nextMessage, "ok");
    } catch (error) { setApiConnected(false); const nextMessage = error instanceof Error ? error.message : "Host scan failed"; setMessage(nextMessage); log("host", nextMessage, "error"); }
    finally { setLoading(false); }
  }, [log]);
  const loadTools = useCallback(async () => { const [nextRegistry, nextProviders, nextAdapters] = await Promise.all([api.tools(), api.providers(), api.adapters()]); setRegistry(nextRegistry); setProviders(nextProviders); setAdapters(nextAdapters); }, []);
  const inspect = useCallback(async () => { if (!selectedId) return; const identifier = selectedId; const request = ++inspectionRequest.current; setLoadingLabel("Inspecting selected IoT hardware"); setLoading(true); setMessage("Collecting device evidence..."); log("device", "Collecting identity, interface, and provider evidence..."); try { await api.select(identifier); const result = await api.inspect(identifier); if (request !== inspectionRequest.current || selectedIdRef.current !== identifier) return; setInspection(result.inspection); setWorkspace("device"); setMessage(`${result.inspection.model} inspected.`); log("device", `${result.inspection.model} inspected at ${Math.round(result.inspection.confidence * 100)}% identity confidence.`, "ok"); } catch (error) { if (request !== inspectionRequest.current) return; const nextMessage = error instanceof Error ? error.message : "Inspection failed"; setMessage(nextMessage); log("device", nextMessage, "error"); } finally { if (request === inspectionRequest.current) setLoading(false); } }, [selectedId, log]);
  const refreshInspection = useCallback(async () => { if (!selectedId) return; const identifier = selectedId; const request = ++inspectionRequest.current; const result = await api.inspect(identifier); if (request === inspectionRequest.current && selectedIdRef.current === identifier) setInspection(result.inspection); }, [selectedId]);
  const saveModel = useCallback(async (model: string) => { if (!selectedId) return; await api.saveModel(selectedId, model); await refreshInspection(); }, [selectedId, refreshInspection]);

  useEffect(() => { void loadHost(false); void loadTools(); }, [loadHost, loadTools]);
  useEffect(() => { selectedIdRef.current = selectedId; inspectionRequest.current += 1; }, [selectedId]);
  useEffect(() => { if (selectedId && inspection?.identifier !== selectedId) setInspection(null); }, [selectedId, inspection?.identifier]);
  useEffect(() => {
    if (restorationAttempted.current || workspace === "host" || !selected || inspection) return;
    restorationAttempted.current = true;
    void refreshInspection();
  }, [workspace, selected, inspection, refreshInspection]);
  useEffect(() => {
    let active = true;
    let reconnectTimer = 0;
    let socket: WebSocket | null = null;
    const connect = () => {
      if (!active) return;
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${protocol}://${window.location.host}/ws`);
      socket.onopen = () => setApiConnected(true);
      socket.onmessage = (event) => {
        try {
          const next = JSON.parse(event.data) as BenchStatus;
          setBenchStatus(next);
          const state = next.device_state;
          if (state && state.revision > deviceRevision.current) {
            const previousRevision = deviceRevision.current;
            deviceRevision.current = state.revision;
            setHardware(state.hardware);
            state.events.filter((item) => item.revision > previousRevision).forEach((item) => {
              log("hardware", `${item.name} ${item.action}${item.interface ? ` at ${item.interface}` : ""}.`, item.action === "disconnected" ? "warn" : "ok");
              if (item.identifier === selectedIdRef.current && item.action === "disconnected") {
                inspectionRequest.current += 1;
                setMessage(`${item.name} disconnected. Live probes, tests, camera, and firmware operations are locked.`);
              }
              if (item.identifier === selectedIdRef.current && item.action === "connected") {
                setMessage(`${item.name} reconnected. Refreshing current device evidence...`);
                void refreshInspection().catch(() => undefined);
              }
            });
          }
        } catch { /* Keep the last valid live sample. */ }
      };
      socket.onclose = () => { setApiConnected(false); if (active) reconnectTimer = window.setTimeout(connect, 1500); };
      socket.onerror = () => socket?.close();
    };
    void api.status().then((next) => { if (active) { setBenchStatus(next); setApiConnected(true); } }).catch(() => active && setApiConnected(false));
    connect();
    return () => { active = false; window.clearTimeout(reconnectTimer); socket?.close(); };
  }, [log, refreshInspection]);

  return <div className="app-shell">
    <div className={`global-progress ${loading ? "active" : ""}`} role="progressbar" aria-label="Bench operation in progress" />
    {!apiConnected && <div className="api-offline" role="alert"><strong>Hardware API offline</strong><span>From the repository root run <code>.\start.ps1 react</code>. React cannot discover or inspect devices without port 8765.</span></div>}
    {loading && <div className="inspection-overlay" role="status" aria-live="assertive" aria-label={loadingLabel}><div className="inspection-symbols" aria-hidden="true"><Cpu /><Wifi /><CircuitBoard /></div><RefreshCw className="spin" size={28} /><strong>{loadingLabel}</strong><span>Collecting current host, interface, and device evidence</span></div>}
    <header><div className="brand"><span /><div><h1>IoT Hardware Connectivity Bench</h1><p>Cross-vendor discovery, inspection and acceptance testing</p></div></div><div className={`host-status ${inspection && !selected ? "disconnected" : ""}`}><CircleDot size={16} /><div><strong>{selected ? "Hardware selected" : inspection ? "Hardware disconnected" : "Waiting for hardware"}</strong><span>{selected?.name || inspection?.model || "No target interface"}</span></div></div></header>
    <nav className="workflow" aria-label="Hardware bench workflow">{steps.map((step, index) => { const Icon = step.icon; return <button key={step.id} type="button" disabled={loading} title={`${step.label}: ${step.hint}`} className={workspace === step.id ? "active" : ""} aria-current={workspace === step.id ? "step" : undefined} onClick={() => { setWorkspace(step.id); if ((step.id === "device" || step.id === "pins" || step.id === "connections" || step.id === "tests" || step.id === "firmware") && selectedId) void refreshInspection(); }}><span className="step-number">{index + 1}</span><Icon size={16} /><span><strong>{step.label}</strong><small>{step.hint}</small></span></button>; })}</nav>
    {inspection && !selected && <div className="device-disconnected-banner" role="alert"><Usb size={17} /><div><strong>Selected hardware disconnected</strong><span>{inspection.model} is no longer present. Last-known evidence remains visible; all live actions are locked until the interface reconnects.</span></div></div>}
    <main>
      {workspace === "host" && <HostView hardware={hardware} selectedId={selectedId} loading={loading} message={message} usb={usb} host={host} onRefresh={() => void loadHost(true)} onSelect={(item) => { setSelectedId(item.id); log("host", `Selected ${item.name} on ${item.device || item.interface || item.ip_address}.`); }} onInspect={() => void inspect()} onLog={log} />}
      {workspace === "device" && <DeviceView selected={selected} inspection={inspection} status={benchStatus} onRefresh={refreshInspection} onSaveModel={(model) => void saveModel(model)} onLog={log} />}
      {workspace === "pins" && <PinsView inspection={inspection} connected={Boolean(selected)} onRefresh={refreshInspection} onLog={log} />}
      {workspace === "connections" && <ConnectionsView selected={selected} inspection={inspection} status={benchStatus} onLog={log} />}
      {workspace === "prototype" && <Suspense fallback={<Empty>Loading prototype workspace...</Empty>}><PrototypeView inspection={inspection} connected={Boolean(selected)} onLog={log} /></Suspense>}
      {workspace === "tests" && <TestsView selected={selected} inspection={inspection} onRefresh={refreshInspection} />}
      {workspace === "firmware" && <FirmwareView selected={selected} inspection={inspection} activeOperations={benchStatus?.operations?.active || []} onLog={log} />}
      {workspace === "tools" && <ToolsView registry={registry} providers={providers} adapters={adapters} onRefresh={() => void loadTools()} />}
    </main>
    <footer><span>React client 0.1</span><span>{apiConnected ? "Local hardware API connected" : "Local hardware API disconnected"}</span></footer>
    <DiagnosticConsole selected={selected} inspection={inspection} events={events} onClear={() => setEvents([])} onLog={log} />
  </div>;
}
