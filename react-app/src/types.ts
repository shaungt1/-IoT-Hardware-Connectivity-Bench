export type Status = "verified" | "detected" | "expected" | "declared" | "unavailable" | "unknown";

export interface Hardware {
  id: string;
  kind: "serial" | "usb_network" | "usb_identity";
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
export interface Resource { title: string; url: string; provider: string; kind: string }
export interface ConnectionInterface { id: string; name: string; status: Status; adapter?: string; limitation: string }
export interface IdentityLayer { id: string; layer: string; name: string; status: Status; source: string }
export interface DevicePin { name: string; aliases: string[]; group: string; functions: string[]; status: Status; source: string }
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
}

export interface UsbInventory { count: number; devices: Array<{ name: string; usb_identity: string; class_name: string; pnp_class?: string; classification?: string; bus: number; address: number; development_candidate: boolean }> }
export interface HostInventory { hostname: string; interfaces: Array<{ name: string; up: boolean; speed_mbps?: number; addresses: Array<{ family: string; address: string }> }> }
export interface ToolRegistry { available_count: number; tools: Array<{ id: string; name: string; category: string; risk: string; available: boolean; version?: string; capability: string }> }
export interface ProviderRegistry { available_count: number; providers: Array<{ id: string; name: string; scope: string; available: boolean; requires_key: boolean; mode: string }> }
export interface ServiceDiscovery { count: number; services: Array<{ name: string; type: string; addresses: string[]; server: string; port: number }> }
export interface NetworkService { name: string; port: number; protocol: string; url?: string; status: Status }
export interface NetworkDevice { address: string; mac_address?: string; source: string; services: NetworkService[] }
export interface NetworkDiscovery { mode: "standard" | "deep"; scope: string[]; count: number; devices: NetworkDevice[]; limits: { private_subnets_only: boolean; maximum_prefix: number; ports: number[]; writes_sent: boolean } }
export interface DeviceCommandResult { command_id: string; label: string; target: string; output: string; risk: string }
export interface OperationCapability { id: string; label: string; risk: string; description: string; available: boolean; reason: string; project?: string }
export interface OperationPlan { plan_id: string; identifier: string; operation_id: string; label: string; risk: string; description: string; preview: string; requires_approval: boolean; expires_in_seconds: number; approval_token?: string }
export interface OperationResult { plan_id: string; operation_id: string; passed: boolean; status: string; output: string; duration_ms: number }
export interface OperationEvent { sequence: number; plan_id: string; identifier: string; operation_id: string; risk: string; status: string; preview: string; output: string; recorded_at: string }
export interface WorkspaceInventory { roots: Array<{ id: string; name: string; writable: boolean; source: string }>; files: Array<{ root_id: string; path: string; name: string; size: number; writable: boolean }> }
export interface WorkspaceFile { root_id: string; path: string; content: string; sha256: string; size: number }
