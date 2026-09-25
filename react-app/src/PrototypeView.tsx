import {
  Background, BackgroundVariant, ConnectionMode, Controls, Handle, MiniMap, Panel, Position, ReactFlow,
  addEdge, useEdgesState, useNodesState, type Connection, type Edge, type Node, type NodeProps, type ReactFlowInstance,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "@wokwi/elements";
import { Activity, Cable, ChevronLeft, ChevronRight, CircleGauge, Cpu, PanelLeftClose, PanelLeftOpen, Save, Search, Trash2, TriangleAlert } from "lucide-react";
import { createElement, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { componentCatalog, visualForComponent, type CatalogPart } from "./componentCatalog";
import type { ControlProfile, Inspection, PrototypeEdge, PrototypeNode, PrototypePin, PrototypeProject, SimulationReport } from "./types";

type PrototypeNodeData = Record<string, unknown> & { component: PrototypeNode; connected: boolean; onVirtualValue: (id: string, value: number) => void };
type FlowNode = Node<PrototypeNodeData>;
type FlowEdge = Edge<{ prototype: PrototypeEdge }>;
type WokwiPinInfo = { name: string; x: number; y: number };
type WokwiElement = HTMLElement & { pinInfo?: WokwiPinInfo[] };

function pinIsGround(pin: PrototypePin) {
  return pin.functions.some((item) => item.toLowerCase() === "ground") || /(^|[-_])gnd/i.test(pin.id);
}

function validateWire(source: PrototypePin, target: PrototypePin): Pick<PrototypeEdge, "signal" | "validation" | "message"> {
  const common = source.functions.find((item) => target.functions.includes(item));
  const signal = common || source.functions[0] || target.functions[0] || "signal";
  const sourceGround = pinIsGround(source);
  const targetGround = pinIsGround(target);
  if (sourceGround !== targetGround) {
    const nonGround = sourceGround ? target : source;
    if (nonGround.direction === "output" || (nonGround.direction === "power" && nonGround.voltage !== undefined && nonGround.voltage !== 0)) return { signal, validation: "invalid", message: "Ground cannot be wired directly to a positive rail or driven output." };
  }
  if (sourceGround && targetGround) return { signal: "GND", validation: "valid", message: "Ground reference connection." };
  if (source.direction === "output" && target.direction === "output") return { signal, validation: "invalid", message: "Two driven outputs can contend and must not be connected directly." };
  if (source.direction === "power" && target.direction === "power" && source.voltage !== undefined && target.voltage !== undefined && Math.abs(source.voltage - target.voltage) > 0.25) return { signal: "power", validation: "invalid", message: `${source.voltage} V and ${target.voltage} V rails are incompatible.` };
  const supply = source.direction === "power" ? source : target.direction === "power" ? target : null;
  const load = supply === source ? target : source;
  if (supply?.voltage !== undefined && load.voltage !== undefined && supply.voltage > load.voltage + 0.25) return { signal, validation: "invalid", message: `${supply.voltage} V exceeds the ${load.voltage} V target rating.` };
  if (source.direction === "input" && target.direction === "input") return { signal, validation: "warning", message: "Both endpoints are inputs; this net has no identified driver." };
  if (!common && source.direction !== "power" && target.direction !== "power") return { signal, validation: "warning", message: "Pin functions do not share a known bus or signal role." };
  return { signal, validation: "valid", message: common ? `Compatible ${common} connection.` : "Direction and voltage checks passed." };
}

function PartVisual({ component }: { component: PrototypeNode }) {
  const visual = visualForComponent(component);
  if (!visual) return <div className="unresolved-part"><Cpu size={30} /><span>Visual unavailable</span></div>;
  if (visual.image) return <div className="part-visual" title={visual.accuracy}><img className="board-product-image" src={visual.image} alt={`${component.label} board`} /></div>;
  if (!visual.element) return <div className="unresolved-part"><Cpu size={30} /><span>Visual unavailable</span></div>;
  const attributes: Record<string, unknown> = { class: "wokwi-part", "aria-label": visual.accuracy };
  if (visual.element === "wokwi-led") attributes.value = Boolean(component.state.active);
  if (visual.element === "wokwi-potentiometer") attributes.value = Number(component.state.value ?? 50) / 100;
  return <div className="part-visual" title={visual.accuracy}>{createElement(visual.element, attributes)}</div>;
}

function GenericTerminalVisual({ component }: { component: PrototypeNode }) {
  const midpoint = Math.ceil(component.pins.length / 2);
  const left = component.pins.slice(0, midpoint);
  const right = component.pins.slice(midpoint);
  return <div className="generic-board" data-terminal-count={component.pins.length}>
    <div className="generic-pin-rail">{left.map((terminal) => <div className="generic-terminal" key={terminal.id} title={`${terminal.label}: ${terminal.functions.join(", ") || terminal.direction}`}><Handle id={terminal.id} type="source" position={Position.Left} /><span>{terminal.label}</span></div>)}</div>
    <div className="generic-board-body"><Cpu size={34} /><strong>{component.label}</strong><small>{component.pins.length ? "Generated from inspected terminals" : "No verified terminal map"}</small></div>
    <div className="generic-pin-rail">{right.map((terminal) => <div className="generic-terminal terminal-right" key={terminal.id} title={`${terminal.label}: ${terminal.functions.join(", ") || terminal.direction}`}><span>{terminal.label}</span><Handle id={terminal.id} type="source" position={Position.Right} /></div>)}</div>
  </div>;
}

function WokwiTerminalVisual({ component, element }: { component: PrototypeNode; element: string }) {
  const host = useRef<WokwiElement | null>(null);
  const [terminals, setTerminals] = useState<WokwiPinInfo[]>([]);
  const attach = useCallback((node: Element | null) => { host.current = node as WokwiElement | null; }, []);

  useEffect(() => {
    let cancelled = false;
    void customElements.whenDefined(element).then(() => {
      window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
        if (!cancelled) setTerminals([...(host.current?.pinInfo || [])]);
      }));
    });
    return () => { cancelled = true; };
  }, [element]);

  const known = new Map(component.pins.map((terminal) => [terminal.id, terminal]));
  const unmatched = component.pins.filter((terminal) => !terminals.some((pinInfo) => pinInfo.name === terminal.id));
  const attributes: Record<string, unknown> = { class: "wokwi-part", ref: attach, "aria-label": `${component.label} physical visual` };
  if (element === "wokwi-led") attributes.value = Boolean(component.state.active);
  if (element === "wokwi-potentiometer") attributes.value = Number(component.state.value ?? 50) / 100;

  return <div className="terminal-visual">
    <div className="wokwi-terminal-stage" data-terminal-count={terminals.length}>
      {createElement(element, attributes)}
      {terminals.map((terminal) => {
        const definition = known.get(terminal.name);
        return <Handle
          className={`physical-terminal terminal-${definition?.direction || "unknown"}`}
          data-pin-id={terminal.name}
          id={terminal.name}
          key={terminal.name}
          position={Position.Top}
          style={{ left: terminal.x, top: terminal.y }}
          title={`${definition?.label || terminal.name}: ${definition?.functions.join(", ") || "Unclassified terminal"}`}
          type="source"
        />;
      })}
    </div>
    {unmatched.length > 0 && <div className="unmapped-terminal-rail" aria-label="Terminals without visual coordinates">{unmatched.map((terminal) => <div key={terminal.id}><Handle id={terminal.id} type="source" position={Position.Bottom} /><span>{terminal.label}</span></div>)}</div>}
  </div>;
}

function isXiaoSense(component: PrototypeNode) {
  const identity = `${component.component_id || ""} ${component.label}`.toLowerCase();
  return identity.includes("xiao") && identity.includes("esp32") && identity.includes("sense");
}

function XiaoPin({ pin, side }: { pin: PrototypePin; side: "left" | "right" }) {
  return <div className={`xiao-pin xiao-pin-${side}`} title={`${pin.label}: ${pin.functions.join(", ") || pin.direction}`}>
    {side === "left" && <Handle id={pin.id} type="source" position={Position.Left} />}
    <b>{pin.id}</b><small>{pin.label.replace(`${pin.id} / `, "")}</small>
    {side === "right" && <Handle id={pin.id} type="source" position={Position.Right} />}
  </div>;
}

function XiaoBoard({ component }: { component: PrototypeNode }) {
  const left = component.pins.slice(0, 7);
  const right = component.pins.slice(7, 14);
  return <div className="xiao-board-map" data-board-model="seeed-xiao-esp32s3-sense">
    <div className="xiao-pin-rail">{left.map((pin) => <XiaoPin key={pin.id} pin={pin} side="left" />)}</div>
    <div className="xiao-board-photo"><img src="/boards/seeed-xiao-esp32s3-sense.jpg" alt="Seeed Studio XIAO ESP32-S3 Sense with camera and antenna" /></div>
    <div className="xiao-pin-rail">{right.map((pin) => <XiaoPin key={pin.id} pin={pin} side="right" />)}</div>
  </div>;
}

function HardwareNode({ data, selected }: NodeProps<FlowNode>) {
  const component = data.component;
  const mode = component.mode === "physical" && !data.connected ? "disconnected" : component.mode;
  const value = Number(component.state.value ?? 50);
  const xiao = isXiaoSense(component);
  const visual = visualForComponent(component);
  return <article data-component-id={component.component_id || "unresolved"} data-schema-terminal-count={component.pins.length} className={`prototype-node mode-${mode} ${component.kind === "controller" ? "controller-node" : ""} ${xiao ? "xiao-sense-node" : ""} ${visual?.element === "wokwi-arduino-mega" ? "wide-board-node" : ""} ${selected ? "selected" : ""}`}>
    <header><span>{component.kind}</span><b>{mode}</b></header><strong className="part-name">{component.label}</strong>{xiao ? <XiaoBoard component={component} /> : visual?.element ? <WokwiTerminalVisual component={component} element={visual.element} /> : <GenericTerminalVisual component={component} />}
    {component.kind === "sensor" && component.mode !== "physical" && <label className="virtual-control nodrag nopan nowheel">Virtual stimulus<input className="nodrag nopan nowheel" type="range" min="0" max="100" value={value} onPointerDown={(event) => event.stopPropagation()} onChange={(event) => data.onVirtualValue(component.id, Number(event.target.value))} /><output>{value}</output></label>}
  </article>;
}

const nodeTypes = { hardware: HardwareNode };

function enrichProject(project: PrototypeProject): PrototypeProject {
  return { ...project, nodes: project.nodes.map((component) => {
    if (component.pins.length || component.kind !== "controller") return component;
    const visual = visualForComponent(component);
    const representative = componentCatalog.find((part) => part.element === visual?.element);
    return representative ? { ...component, pins: representative.pins.map((pin) => ({ ...pin, functions: [...pin.functions] })), properties: { ...component.properties, pin_map: `Representative ${representative.label}; exact board model must be confirmed` } } : component;
  }) };
}

function toFlowNodes(project: PrototypeProject, connected: boolean, onVirtualValue: PrototypeNodeData["onVirtualValue"]): FlowNode[] {
  return project.nodes.map((component) => ({ id: component.id, type: "hardware", position: component.position, data: { component, connected, onVirtualValue } }));
}

function toFlowEdges(project: PrototypeProject): FlowEdge[] {
  return project.edges.map((edge) => ({ id: edge.id, source: edge.source, sourceHandle: edge.source_pin, target: edge.target, targetHandle: edge.target_pin, label: edge.signal === "unknown" ? edge.validation : edge.signal, className: `prototype-edge validation-${edge.validation}`, data: { prototype: edge } }));
}

function persistedEdge(edge: FlowEdge): PrototypeEdge {
  return edge.data?.prototype || { id: edge.id, source: edge.source, source_pin: edge.sourceHandle || "unknown", target: edge.target, target_pin: edge.targetHandle || "unknown", signal: "unknown", state_source: "user_defined", validation: "unknown", message: "Connection has not been electrically validated." };
}

function catalogNode(part: CatalogPart, kindIndex: number): PrototypeNode {
  const lane = part.kind === "controller" ? { x: 360, width: 460, height: 620 } : part.kind === "sensor" ? { x: 40, width: 300, height: 330 } : { x: 900, width: 300, height: 300 };
  const columns = part.kind === "controller" ? 2 : 3;
  const position = { x: lane.x + (kindIndex % columns) * lane.width, y: 80 + Math.floor(kindIndex / columns) * lane.height };
  const electrical = part.id === "wokwi-resistor" ? { resistance_ohms: 220 } : part.id === "wokwi-potentiometer" ? { resistance_ohms: 10_000 } : {};
  const visual = part.element ? document.createElement(part.element) as WokwiElement : null;
  const packagePins = part.pins.length ? part.pins : (visual?.pinInfo || []).map((item) => ({ id: item.name, label: item.name, functions: [], direction: "unknown" as const }));
  return { id: `${part.id}-${crypto.randomUUID()}`, kind: part.kind, label: part.label, mode: "simulated", position, component_id: part.id, pins: packagePins.map((item) => ({ ...item, functions: [...item.functions] })), properties: { source: "@wokwi/elements", visual_element: part.element, simulation_engine: "ngspice when supported", terminal_evidence: part.pins.length ? "bench electrical definition" : "@wokwi/elements pinInfo; electrical semantics unresolved", ...electrical }, state: part.kind === "sensor" ? { value: 50, unit: "%", source: "virtual stimulus" } : {} };
}

export function PrototypeView({ inspection, connected, onLog }: { inspection: Inspection | null; connected: boolean; onLog: (channel: string, message: string, tone?: "ok" | "warn" | "error") => void }) {
  const [project, setProject] = useState<PrototypeProject | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<FlowEdge>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);
  const [message, setMessage] = useState("Load a selected device to begin a prototype.");
  const [busy, setBusy] = useState(false);
  const [controlProfile, setControlProfile] = useState<ControlProfile | null>(null);
  const [simulation, setSimulation] = useState<SimulationReport | null>(null);
  const [query, setQuery] = useState("");
  const [libraryOpen, setLibraryOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const flow = useRef<ReactFlowInstance<FlowNode, FlowEdge> | null>(null);
  const edgesRef = useRef<FlowEdge[]>([]);

  useEffect(() => { edgesRef.current = edges; }, [edges]);
  const updateVirtualValue = useCallback((id: string, value: number) => {
    const reachable = new Set([id]);
    const queue = [id];
    while (queue.length) {
      const current = queue.shift() as string;
      for (const edge of edgesRef.current) {
        const next = edge.source === current ? edge.target : edge.target === current ? edge.source : null;
        if (next && !reachable.has(next)) { reachable.add(next); queue.push(next); }
      }
    }
    setNodes((current) => current.map((node) => {
      if (node.id === id) return { ...node, data: { ...node.data, component: { ...node.data.component, state: { ...node.data.component.state, value, source: "virtual stimulus" } } } };
      const component = node.data.component;
      if (!reachable.has(node.id) || component.mode !== "simulated" || component.kind !== "output") return node;
      return { ...node, data: { ...node.data, component: { ...component, state: { ...component.state, value, active: value >= 50, source: `simulated net from ${id}` } } } };
    }));
    setMessage(`Virtual stimulus ${value} propagated to ${Math.max(0, reachable.size - 1)} connected simulated part(s). Physical outputs remain locked.`);
  }, [setNodes]);

  useEffect(() => {
    if (!inspection) { setProject(null); setNodes([]); setEdges([]); return; }
    let cancelled = false; setBusy(true); setMessage("Loading prototype circuit...");
    Promise.all([api.prototype(inspection.identifier), api.controlProfile(inspection.identifier)]).then(([loaded, profile]) => { if (cancelled) return; const enriched = enrichProject(loaded); setProject(enriched); setControlProfile(profile); setNodes(toFlowNodes(enriched, connected, updateVirtualValue)); setEdges(toFlowEdges(enriched)); setMessage(`${enriched.nodes.length} part(s), ${enriched.edges.length} net(s). Physical control is ${profile.control_ready ? "negotiated" : "locked"}.`); }).catch((error) => setMessage(error instanceof Error ? error.message : "Prototype could not be loaded")).finally(() => !cancelled && setBusy(false));
    return () => { cancelled = true; };
  }, [inspection?.identifier, connected, setEdges, setNodes, updateVirtualValue]);

  useEffect(() => { if (!flow.current || !nodes.length) return; const frame = window.requestAnimationFrame(() => void flow.current?.fitView({ padding: 0.16, duration: 200 })); return () => window.cancelAnimationFrame(frame); }, [nodes.length]);

  const selected = useMemo(() => nodes.find((node) => node.id === selectedNode)?.data.component || null, [nodes, selectedNode]);
  const wire = useMemo(() => edges.find((edge) => edge.id === selectedEdge)?.data?.prototype || null, [edges, selectedEdge]);
  const visibleParts = useMemo(() => componentCatalog.filter((part) => `${part.label} ${part.category} ${part.summary}`.toLowerCase().includes(query.toLowerCase())), [query]);
  const groupedParts = useMemo(() => ["Boards", "Sensors", "Inputs", "Outputs", "Displays", "Modules", "Passives"].map((category) => ({ category, parts: visibleParts.filter((part) => part.category === category) })).filter((group) => group.parts.length), [visibleParts]);

  const addPart = (part: CatalogPart) => { const component = catalogNode(part, nodes.filter((node) => node.data.component.kind === part.kind).length); setNodes((current) => [...current, { id: component.id, type: "hardware", position: component.position, data: { component, connected, onVirtualValue: updateVirtualValue } }]); setSelectedNode(component.id); setSelectedEdge(null); };
  const connect = useCallback((connection: Connection) => {
    if (!connection.sourceHandle || !connection.targetHandle) return;
    const sourcePin = nodes.find((node) => node.id === connection.source)?.data.component.pins.find((pin) => pin.id === connection.sourceHandle);
    const targetPin = nodes.find((node) => node.id === connection.target)?.data.component.pins.find((pin) => pin.id === connection.targetHandle);
    if (!sourcePin || !targetPin) return;
    const check = validateWire(sourcePin, targetPin);
    const prototype: PrototypeEdge = { id: `wire-${crypto.randomUUID()}`, source: connection.source, source_pin: connection.sourceHandle, target: connection.target, target_pin: connection.targetHandle, state_source: "user_defined", ...check };
    setEdges((current) => addEdge({ ...connection, id: prototype.id, label: prototype.signal, className: `prototype-edge validation-${prototype.validation}`, data: { prototype } }, current)); setMessage(check.message); onLog("prototype", check.message, check.validation === "valid" ? "ok" : check.validation === "invalid" ? "error" : "warn");
  }, [nodes, onLog, setEdges]);

  const removeSelection = () => {
    if (selectedNode) { const node = nodes.find((item) => item.id === selectedNode); if (node?.data.component.target_identifier) return; setNodes((current) => current.filter((item) => item.id !== selectedNode)); setEdges((current) => current.filter((edge) => edge.source !== selectedNode && edge.target !== selectedNode)); setSelectedNode(null); }
    else if (selectedEdge) { setEdges((current) => current.filter((edge) => edge.id !== selectedEdge)); setSelectedEdge(null); }
  };
  const save = async () => {
    if (!project) return; setBusy(true); setMessage("Saving prototype circuit...");
    const next: PrototypeProject = { ...project, nodes: nodes.map((node) => ({ ...node.data.component, position: node.position })), edges: edges.map(persistedEdge) };
    try { const saved = await api.savePrototype(next); setProject(saved); setEdges(toFlowEdges(saved)); const invalid = saved.edges.filter((edge) => edge.validation === "invalid").length; setMessage(`Saved ${saved.nodes.length} part(s) and ${saved.edges.length} net(s).${invalid ? ` ${invalid} invalid net(s) require correction.` : ""}`); onLog("prototype", `Saved ${saved.name}${invalid ? ` with ${invalid} invalid net(s)` : ""}.`, invalid ? "warn" : "ok"); } catch (error) { const detail = error instanceof Error ? error.message : "Prototype save failed"; setMessage(detail); onLog("prototype", detail, "error"); } finally { setBusy(false); }
  };
  const simulate = async () => {
    if (!project) return;
    setBusy(true); setSimulation(null); setMessage("Running a bounded ngspice DC operating-point analysis...");
    const next: PrototypeProject = { ...project, nodes: nodes.map((node) => ({ ...node.data.component, position: node.position })), edges: edges.map(persistedEdge) };
    try {
      const report = await api.simulatePrototype(next);
      setSimulation(report); setMessage(`${report.engine} solved ${Object.keys(report.node_voltages).length} electrical net(s); physical hardware was not changed.`);
      onLog("simulation", `${report.engine} ${report.passed ? "completed" : "returned no operating point"}`, report.passed ? "ok" : "warn");
    } catch (error) { const detail = error instanceof Error ? error.message : "Electrical simulation failed"; setMessage(detail); onLog("simulation", detail, "error"); }
    finally { setBusy(false); }
  };

  if (!inspection) return <p className="empty">Inspect a device before opening Prototype.</p>;
  return <div className="workspace-content prototype-workspace"><section>
    <div className="section-heading"><div><p className="eyebrow">Hybrid rapid prototyping</p><h2>{project?.name || `${inspection.model} prototype`}</h2></div><div className="actions"><span className={`status status-${controlProfile?.control_ready ? "verified" : connected ? "detected" : "unavailable"}`}>{controlProfile?.control_ready ? "physical control ready" : connected ? "physical target mapped" : "target disconnected"}</span><button className="tool-button" type="button" disabled={busy || !project} onClick={() => void simulate()}><Activity size={16} />Run SPICE</button><button className="primary" type="button" disabled={busy || !project} onClick={() => void save()}><Save size={16} />Save circuit</button></div></div>
    <p className="intro" role="status">{message}</p>
    <div className="prototype-engines"><div><b>Parts</b><strong className="ready">Wokwi Elements ready</strong></div><div><b>Net rules</b><strong className="ready">Backend direction + voltage checks</strong></div><div><b>Physical I/O</b><strong className={controlProfile?.control_ready ? "ready" : ""}>{controlProfile?.control_ready ? controlProfile.protocol : controlProfile?.mapped ? "Mapped, control locked" : "No verified pin map"}</strong></div><div><b>Electrical simulation</b><strong className="ready">ngspice installed</strong></div><div><b>Firmware emulation</b><strong className="ready">Renode installed; platform required</strong></div></div>
    {simulation && <details className="simulation-report" open><summary><span><Activity size={15} />ngspice operating point</span><strong>{Object.keys(simulation.node_voltages).length} nets solved</strong></summary><div><dl>{Object.entries(simulation.node_voltages).map(([net, voltage]) => <div key={net}><dt>{net}</dt><dd>{voltage.toFixed(4)} V</dd></div>)}</dl><pre>{simulation.netlist}</pre>{simulation.warnings.length > 0 && <ul>{simulation.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>}</div></details>}
    <div className={`prototype-shell electronics-studio ${libraryOpen ? "library-open" : "library-closed"} ${inspectorOpen ? "inspector-open" : "inspector-closed"}`}>
      {libraryOpen && <aside className="component-library"><div className="panel-title"><h3>Parts</h3><button className="icon-button" type="button" title="Collapse parts library" aria-label="Collapse parts library" onClick={() => setLibraryOpen(false)}><PanelLeftClose size={16} /></button></div><label className="component-search"><Search size={14} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search boards and parts" /></label>{groupedParts.map((group) => <details className="catalog-group" key={group.category} open><summary>{group.category}<span>{group.parts.length}</span></summary>{group.parts.map((part) => <button type="button" data-component-id={part.id} onClick={() => addPart(part)} key={part.id}><span className="catalog-preview">{part.image ? <img src={part.image} alt="" /> : part.element ? createElement(part.element, { class: "wokwi-library-part" }) : null}</span><span><strong>{part.label}</strong><small>{part.summary}</small></span></button>)}</details>)}</aside>}
      <div className="prototype-canvas" aria-label="Prototype circuit canvas"><ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} onInit={(instance) => { flow.current = instance; }} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={connect} onNodeClick={(_, node) => { setSelectedNode(node.id); setSelectedEdge(null); }} onEdgeClick={(_, edge) => { setSelectedEdge(edge.id); setSelectedNode(null); }} fitView minZoom={0.15} connectionMode={ConnectionMode.Loose}><Background variant={BackgroundVariant.Lines} gap={20} size={1} /><Controls /><MiniMap pannable zoomable maskColor="rgb(4 7 8 / 72%)" style={{ background: "#0e1315" }} nodeColor={(node) => (node.data as PrototypeNodeData).component.mode === "physical" ? "#19d8a6" : "#f0b44d"} /><Panel position="top-left" className="canvas-toolbar">{!libraryOpen && <button type="button" title="Open parts library" aria-label="Open parts library" onClick={() => setLibraryOpen(true)}><PanelLeftOpen size={15} /></button>}<span className="canvas-mode"><Cable size={14} />Circuit topology</span>{!inspectorOpen && <button type="button" title="Open inspector" aria-label="Open inspector" onClick={() => setInspectorOpen(true)}><ChevronLeft size={15} /></button>}</Panel></ReactFlow></div>
      {inspectorOpen && <aside className="prototype-inspector"><div className="panel-title"><h3>Inspector</h3><button className="icon-button" type="button" title="Collapse inspector" aria-label="Collapse inspector" onClick={() => setInspectorOpen(false)}><ChevronRight size={16} /></button></div>{selected ? <><span className={`status status-${selected.mode === "physical" && connected ? "verified" : selected.mode === "simulated" ? "expected" : "unavailable"}`}>{selected.mode}</span><h4>{selected.label}</h4><PartVisual component={selected} /><dl><div><dt>Kind</dt><dd>{selected.kind}</dd></div><div><dt>Pins</dt><dd>{selected.pins.length}</dd></div><div><dt>Visual</dt><dd>{visualForComponent(selected)?.accuracy || "generated terminal map"}</dd></div><div><dt>Source</dt><dd>{String(selected.properties.source || (selected.target_identifier ? "Selected hardware" : "Prototype catalog"))}</dd></div></dl>{selected.kind === "sensor" && <div className="instrument-reading"><CircleGauge size={19} /><span>Virtual stimulus</span><strong>{String(selected.state.value ?? "--")}{String(selected.state.unit ?? "")}</strong></div>}{selected.kind === "output" && selected.mode === "simulated" && <div className="instrument-reading"><CircleGauge size={19} /><span>Simulated output</span><strong>{selected.state.active ? "On" : "Off"}</strong></div>}{!selected.target_identifier && <button className="tool-button danger-action" type="button" onClick={removeSelection}><Trash2 size={14} />Remove part</button>}</> : wire ? <><span className={`status status-${wire.validation === "valid" ? "verified" : wire.validation === "warning" ? "expected" : "unavailable"}`}>{wire.validation}</span><h4>{wire.signal}</h4><p>{wire.message}</p><dl><div><dt>From</dt><dd>{wire.source}.{wire.source_pin}</dd></div><div><dt>To</dt><dd>{wire.target}.{wire.target_pin}</dd></div><div><dt>State source</dt><dd>{wire.state_source}</dd></div></dl><button className="tool-button danger-action" type="button" onClick={removeSelection}><Trash2 size={14} />Remove wire</button></> : <p>Select a board, part, pin net, or wire to inspect its identity and validation state.</p>}{Boolean(selected?.properties.pin_map) && <p className="inspector-warning"><TriangleAlert size={14} />{String(selected?.properties.pin_map)}</p>}</aside>}
    </div>
  </section></div>;
}
