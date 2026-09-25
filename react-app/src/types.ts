export type Status = "verified" | "detected" | "expected" | "declared" | "unavailable" | "unknown";

export interface Hardware {
  id: string;
  kind: "serial" | "usb_network" | "usb_identity" | "ssh_target";
  device?: string;
  interface?: string;
  ip_address?: string;
  name: string;
  description?: string;
  vid?: string;
  pid?: string;
  transport: string;
  classification?: string;
  device_category?: string;
  confidence?: number;
  is_esp32?: boolean;
  is_lichee?: boolean;
}

export interface Evidence { source: string; claim: string; status: Status }
export interface Capability { id: string; name: string; status: Status; source: string }
export interface Component { id: string; name: string; type: string; bus?: string; status: Status; source: string; variant?: string }
export interface Service { name: string; address?: string; port?: number; url?: string; status: Status }
export interface DeviceTest { id: string; action?: "deep_probe" | "bus_scan" | "wireless_test"; name: string; risk: string; available: boolean; description: string }
export interface TestHistoryRecord { sequence: number; identifier: string; test_id: string; passed: boolean; result: Record<string, unknown>; recorded_at: string }
export interface EvidenceHistory { identifier: string | null; retention_per_device: number; inspections: Array<Record<string, unknown>>; tests: TestHistoryRecord[] }
export interface Resource { title: string; url: string; provider: string; kind: string }
export interface ConnectionInterface { id: string; name: string; status: Status; adapter?: string; limitation: string }
export interface IdentityLayer { id: string; layer: string; name: string; status: Status; source: string }
export interface HardwareDefinition { format: "cmsis-svd" | "zephyr-devicetree" | "kicad-schematic" | "fritzing-part"; scope: "mcu_internal" | "board_topology" | "design_evidence" | "component_definition"; source_name: string; source_sha256: string; device?: string; vendor?: string; counts: Record<string, number>; provenance: { kind: string; confidence: string } }
export interface EvidenceGraph { schema_version: string; root: string; nodes: Array<{ id: string; kind: string; name: string; status: Status; provenance: { source: string }; attributes: Record<string, unknown> }>; edges: Array<{ id: string; source: string; target: string; relation: string; status: Status; provenance: { source: string } }>; counts: Record<string, number> }
export interface DiscoveryReport {
  schema_version: "1.0";
  identifier: string;
  phases: Array<{ id: string; label: string; status: Status; summary: string }>;
  coverage: Array<{ id: string; label: string; status: Status; count: number; source: string; detail: string }>;
  unresolved: Array<{ id: string; label: string; reason: string; next_step: string; required_evidence: string[] }>;
  adapter_attempts: Array<{ adapter_id: string; name: string; status: "completed" | "no_evidence" | "failed"; error?: string }>;
  graph: { nodes: number; edges: number };
  safety: { unknown_pins_driven: boolean; blind_serial_bytes_sent: boolean; automatic_brute_force: boolean; physical_limit: string };
}
export interface ControlProfile { schema_version: string; identifier: string; connected: boolean; mapped: boolean; control_ready: boolean; protocol?: string; adapter?: string; capabilities: Array<{ id: string; available: boolean; risk: string; reason: string }>; safety: { unknown_pins_may_be_driven: boolean; write_requires_explicit_approval: boolean; prototype_wire_implies_physical_control: boolean } }
export interface ProbeMatrix {
  schema_version: "1.0";
  identifier: string;
  connected: boolean;
  probes: Array<{ id: string; label: string; status: "available" | "locked" | "instrument_required"; can_run: boolean; test_id?: string; risk: string; adapter?: string; detects: string; reason: string; route: string }>;
  available_count: number;
  locked_count: number;
  instrument_required_count: number;
  safety: { unknown_pins_driven: boolean; automatic_brute_force: boolean; reason: string };
}
export interface PinKnowledge { id: string; canonical: string; category: string; summary: string; caution: string }
export interface PinAttachment { pin: string; component_name: string; component_type: string; interface: string; notes: string; status: "declared"; source: string }
export interface DevicePin { name: string; aliases: string[]; group: string; functions: string[]; status: Status; source: string; attachment?: PinAttachment; knowledge?: PinKnowledge[]; electrical?: { logic_voltage_v?: number; nominal_voltage_v?: number; absolute_input_max_v?: number; five_volt_tolerant?: boolean; characterized_source_ma?: number; characterized_sink_ma?: number; rail?: string; caution?: string; source?: string } }
export interface AttachedPeripheral { id: string; name: string; bus: string; status: Status; address: string; candidates: string[]; source: string }
export interface RuntimeTelemetry {
  firmware?: string;
  runtime_adapter?: string;
  storage_mount?: string;
  storage_total_bytes?: number;
  storage_free_bytes?: number;
  code_files?: string[];
  imports?: string[];
  libraries?: string[];
  free_heap_bytes?: number;
  cpu_frequency_hz?: number;
  cpu_frequency?: string;
  processor?: string;
  flash_size?: string;
  radio_capabilities?: string[];
}

export interface Inspection {
  identifier: string;
  interface?: string;
  identity?: string;
  model: string;
  family?: string;
  classification: string;
  confidence: number;
  manufacturer?: string;
  mcu?: string;
  architecture?: string;
  runtime?: string;
  candidates: string[];
  evidence: Evidence[];
  capabilities: Capability[];
  components: Component[];
  services: Service[];
  connection_interfaces: ConnectionInterface[];
  tests: DeviceTest[];
  resources: Resource[];
  limitations: string[];
  pins?: DevicePin[];
  attached_peripherals?: AttachedPeripheral[];
  adapter?: { id: string; name: string; mode: string };
  telemetry?: RuntimeTelemetry;
  identity_layers?: IdentityLayer[];
  definitions?: HardwareDefinition[];
  evidence_graph?: EvidenceGraph;
  discovery?: DiscoveryReport;
  user_pin_attachments?: PinAttachment[];
  visual_evidence?: Array<{ sequence: number; image_sha256: string; marking: string; role: string; confidence: number; source_text: string; confirmed_at: string }>;
}

export interface UsbInventory { count: number; devices: Array<{ name: string; usb_identity: string; class_name: string; pnp_class?: string; classification?: string; bus: number; address: number; development_candidate: boolean }> }
export interface HostInventory { hostname: string; interfaces: Array<{ name: string; up: boolean; speed_mbps?: number; addresses: Array<{ family: string; address: string }> }> }
export interface ToolRegistry { available_count: number; tools: Array<{ id: string; name: string; category: string; risk: string; available: boolean; version?: string; path?: string; capability: string; diagnostic_supported: boolean; documentation_url?: string }> }
export interface ToolDiagnostic { tool: ToolRegistry["tools"][number]; available: boolean; diagnostic_ran: boolean; exit_code?: number; output: string; duration_ms: number; physical_hardware_changed: boolean; route: string }
export interface InstrumentReport { schema_version: "1.0"; connected_count: number; fixtures: Array<{ id: string; name: string; kind: string; status: "connected" | "tool_ready" | "unavailable"; tools: string[]; devices: Array<Record<string, string>>; fixture_count: number; target_wiring_confirmed: boolean; next_step: string }>; safety: { target_opened: boolean; target_wiring_confirmed: boolean; signals_driven: boolean; reason: string } }
export interface ProviderRegistry { available_count: number; providers: Array<{ id: string; name: string; scope: string; available: boolean; requires_key: boolean; mode: string }> }
export interface AdapterRegistry { count: number; adapters: Array<{ id: string; name: string; version: string; transports: string[]; families: string[]; inspection_modes: string[]; timeout_seconds: number; safety: string }> }
export interface ServiceDiscovery { count: number; services: Array<{ name: string; type: string; addresses: string[]; server: string; port: number }> }
export interface NetworkService { name: string; port: number; protocol: string; url?: string; status: Status }
export interface NetworkDevice { address: string; mac_address?: string; source: string; services: NetworkService[] }
export interface NetworkDiscovery { mode: "standard" | "deep"; scope: string[]; count: number; devices: NetworkDevice[]; limits: { private_subnets_only: boolean; maximum_prefix: number; ports: number[]; writes_sent: boolean } }
export interface DeviceCommandResult { command_id: string; label: string; target: string; output: string; risk: string }
export interface OperationCapability { id: string; label: string; risk: string; description: string; available: boolean; reason: string; project?: string }
export interface OperationPlan { plan_id: string; identifier: string; operation_id: string; label: string; risk: string; description: string; preview: string; requires_approval: boolean; expires_in_seconds: number; approval_token?: string }
export interface OperationResult { plan_id: string; operation_id: string; passed: boolean; status: string; output: string; duration_ms: number }
export interface OperationEvent { sequence: number; plan_id: string; identifier: string; operation_id: string; risk: string; status: string; preview: string; output: string; recorded_at: string }
export interface ActiveOperation { plan_id: string; identifier: string; operation_id: string; label: string; started_at: number; updated_at: number; output: string }
export interface WorkspaceInventory { roots: Array<{ id: string; name: string; writable: boolean; source: string }>; files: Array<{ root_id: string; path: string; name: string; size: number; writable: boolean }> }
export interface WorkspaceFile { root_id: string; path: string; content: string; sha256: string; size: number }
export interface FirmwareAnalysis {
  schema_version: "1.0";
  filename: string;
  size_bytes: number;
  sha256: string;
  entropy_bits_per_byte: number;
  format: string;
  architecture?: string;
  format_details: Record<string, unknown>;
  strings: string[];
  urls: string[];
  engines: Array<{ id: string; name: string; purpose: string; available: boolean; invoked: boolean }>;
  evidence: Evidence[];
  safety: { uploaded_bytes_executed: boolean; external_engines_invoked: boolean; maximum_input_bytes: number };
}
export interface EmulationCatalog {
  engine: "renode";
  installed: boolean;
  version?: string;
  count?: number;
  identity?: string;
  exact_match?: EmulationPlatform;
  platforms: EmulationPlatform[];
  limitation?: string;
}
export interface EmulationPlatform { id: string; label: string; definition: string; match_score: number; source: string }
export interface EmulationVerification {
  engine: "renode";
  version: string;
  platform: EmulationPlatform;
  loaded: boolean;
  peripheral_count: number;
  peripherals: Array<{ name: string; model: string }>;
  architectures: string[];
  firmware_executed: boolean;
  physical_hardware_changed: boolean;
}
export interface EmulationRun {
  engine: "renode";
  version: string;
  platform: EmulationPlatform;
  firmware: { filename: string; sha256: string; format: string; architecture: string; size_bytes: number };
  runtime_ms: number;
  firmware_loaded: boolean;
  firmware_executed: boolean;
  execution_proven: boolean;
  proof: { address?: string; expected?: string; observed?: string };
  trace: string[];
  physical_hardware_changed: boolean;
  safety: { platform_allowlisted: boolean; architecture_checked: boolean; runtime_bounded: boolean; process_timeout_seconds: number; guest_file_deleted: boolean };
}
export interface VisualAnalysis {
  schema_version: "1.0";
  filename: string;
  sha256: string;
  input_bytes: number;
  input_dimensions: { width: number; height: number };
  normalized_dimensions: { width: number; height: number };
  ocr_engine: string;
  lines: Array<{ text: string; confidence: number; box: number[][] }>;
  candidates: Array<{ id: string; marking: string; suggested_role: string; ocr_confidence: number; status: "unconfirmed" | "confirmed"; source_text: string }>;
  needs_review: boolean;
  limitations: string[];
  privacy: { image_persisted: boolean; image_bytes_returned: boolean; local_processing: boolean };
}

export interface BleDevice {
  name: string;
  address: string;
  rssi_dbm: number;
  service_uuids: string[];
  is_compatible: boolean;
}

export interface BleStatus {
  detected: boolean;
  name?: string;
  address?: string;
  rssi_dbm?: number;
  service_uuids: string[];
  connection_verified: boolean;
  devices: BleDevice[];
  error?: string | null;
}

export interface LiveTelemetry {
  device?: string;
  board_id?: string;
  board_model?: string;
  mcu?: string;
  architecture?: string;
  pin_map_version?: string;
  firmware?: string;
  uptime_ms?: number;
  free_heap_bytes?: number;
  psram_bytes?: number;
  camera_ready?: boolean;
  camera_status?: string;
  camera_sensor_pid?: number;
  camera_fps?: number;
  camera_brightness?: number;
  camera_contrast?: number;
  camera_saturation?: number;
  camera_sharpness?: number;
  camera_ae_level?: number;
  camera_jpeg_quality?: number;
  frames_sent?: number;
  usb_streaming?: boolean;
  ble_advertising?: boolean;
  ble_advertisement_configured?: boolean;
  ble_advertisement_error?: string;
  ble_connected?: boolean;
  ble_client_count?: number;
  ble_connections_total?: number;
  ble_service_uuid?: string;
  ble_device_address?: string;
  wifi_ap_active?: boolean;
  wifi_ap_configured?: boolean;
  wifi_ap_ssid?: string;
  wifi_ap_ip?: string;
  wifi_ap_clients?: number;
  wifi_station_connected?: boolean;
  wifi_station_status?: string;
  wifi_station_ssid?: string;
  wifi_station_ip?: string;
  wifi_gateway_ip?: string;
  wifi_dns_ip?: string;
  wifi_rssi_dbm?: number;
  wifi_networks?: WifiNetwork[];
  internet_reachable?: boolean;
  internet_probe_status?: string;
  internet_probe_latency_ms?: number;
  internet_tests_successful?: number;
  internet_bytes_sent?: number;
  internet_bytes_received?: number;
}

export interface BenchStatus {
  connected: boolean;
  port?: string | null;
  error?: string | null;
  telemetry: LiveTelemetry;
  frame_sequence: number;
  measured_fps: number;
  bytes_received: number;
  packets_received: number;
  bridge_uptime_seconds: number;
  ble: BleStatus;
  operations?: { active_identifiers: string[]; active: ActiveOperation[]; disconnected_identifiers: string[]; pending_plans: number };
  runtime?: { rss_bytes: number; threads: number; open_handles?: number | null };
  device_state?: {
    revision: number;
    hardware: Hardware[];
    events: Array<{ revision: number; action: "connected" | "disconnected" | "changed"; identifier: string; name: string; interface?: string; observed_at: number }>;
  };
}

export interface WifiNetwork {
  ssid: string;
  rssi_dbm?: number;
  channel?: number;
  secure?: boolean;
  security?: string;
}

export interface HostWifiNetwork {
  ssid: string;
  signal_percent?: number;
  authentication?: string;
  encryption?: string;
}

export interface HostWifiScan {
  available: boolean;
  adapter?: string;
  networks: HostWifiNetwork[];
  error?: string | null;
}

export interface PrototypePin {
  id: string;
  label: string;
  functions: string[];
  voltage?: number;
  direction: "input" | "output" | "bidirectional" | "power" | "unknown";
}
export interface PrototypeNode {
  id: string;
  kind: "controller" | "sensor" | "output" | "passive" | "instrument" | "custom";
  label: string;
  mode: "physical" | "simulated" | "hybrid" | "disconnected" | "user_defined";
  position: { x: number; y: number };
  component_id?: string;
  target_identifier?: string;
  pins: PrototypePin[];
  properties: Record<string, unknown>;
  state: Record<string, unknown>;
}
export interface PrototypeEdge {
  id: string;
  source: string;
  source_pin: string;
  target: string;
  target_pin: string;
  signal: string;
  state_source: "physical" | "simulated" | "hybrid" | "user_defined";
  validation: "valid" | "warning" | "invalid" | "unknown";
  message: string;
}
export interface PrototypeProject {
  schema_version: "1.0";
  revision: number;
  identifier: string;
  name: string;
  nodes: PrototypeNode[];
  edges: PrototypeEdge[];
  updated_at?: string;
}
export interface SimulationReport {
  schema_version: "1.0";
  engine: "ngspice";
  analysis: string;
  passed: boolean;
  node_voltages: Record<string, number>;
  endpoint_nets: Record<string, string>;
  warnings: string[];
  netlist: string;
  safety: { physical_hardware_changed: boolean; subprocess_timeout_seconds: number };
}
