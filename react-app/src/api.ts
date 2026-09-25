import type { AdapterRegistry, BenchStatus, BleStatus, ControlProfile, DeviceCommandResult, EmulationCatalog, EmulationRun, EmulationVerification, EvidenceHistory, FirmwareAnalysis, Hardware, HostInventory, HostWifiScan, Inspection, InstrumentReport, NetworkDiscovery, OperationCapability, OperationEvent, OperationPlan, OperationResult, ProbeMatrix, PrototypeProject, ProviderRegistry, ServiceDiscovery, SimulationReport, ToolDiagnostic, ToolRegistry, UsbInventory, VisualAnalysis, WifiNetwork, WorkspaceFile, WorkspaceInventory } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new Error("Hardware API is unavailable on 127.0.0.1:8765. From the repository root run .\\start.ps1 react.");
  }
  const text = await response.text();
  let body: Record<string, unknown> = {};
  try { body = text ? JSON.parse(text) as Record<string, unknown> : {}; }
  catch {
    if (!response.ok) throw new Error(`Hardware API request failed (${response.status}). From the repository root run .\\start.ps1 react.`);
    throw new Error("Hardware API returned an invalid response.");
  }
  if (!response.ok) throw new Error(String(body.detail || `Request failed (${response.status})`));
  return body as T;
}

export const api = {
  status: () => request<BenchStatus>("/api/status", { cache: "no-store" }),
  hardware: (force = false) => request<Hardware[]>(`/api/hardware${force ? "?force=true" : ""}`),
  usbInventory: (force = false) => request<UsbInventory>(`/api/inventory/usb${force ? "?force=true" : ""}`),
  hostInventory: () => request<HostInventory>("/api/inventory/host"),
  tools: () => request<ToolRegistry>("/api/tools"),
  diagnoseTool: (toolId: string) => request<ToolDiagnostic>(`/api/tools/${encodeURIComponent(toolId)}/diagnose`),
  instruments: () => request<InstrumentReport>("/api/instruments"),
  analyzeFirmware: (filename: string, contentBase64: string) => request<FirmwareAnalysis>("/api/firmware/analyze", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ filename, content_base64: contentBase64 }),
  }),
  analyzeBoardImage: (filename: string, contentBase64: string) => request<VisualAnalysis>("/api/visual/analyze", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ filename, content_base64: contentBase64 }),
  }),
  confirmVisualEvidence: (identifier: string, analysis: VisualAnalysis, candidate: VisualAnalysis["candidates"][number]) => request<{ confirmed: boolean; marking: string; role: string; image_persisted: boolean }>("/api/device/visual-evidence/confirm", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ identifier, image_sha256: analysis.sha256, marking: candidate.marking, role: candidate.suggested_role, confidence: candidate.ocr_confidence, source_text: candidate.source_text, confirm: true }),
  }),
  emulationPlatforms: (identity = "") => request<EmulationCatalog>(`/api/emulation/platforms?identity=${encodeURIComponent(identity)}`),
  verifyEmulationPlatform: (platformId: string) => request<EmulationVerification>("/api/emulation/platform/verify", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ platform_id: platformId }),
  }),
  runEmulatedFirmware: (platformId: string, filename: string, contentBase64: string, runtimeMs = 50) => request<EmulationRun>("/api/emulation/firmware/run", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ platform_id: platformId, filename, content_base64: contentBase64, runtime_ms: runtimeMs }),
  }),
  providers: () => request<ProviderRegistry>("/api/metadata/providers"),
  adapters: () => request<AdapterRegistry>("/api/adapters"),
  probeSsh: (host: string, port: number) => request<{ host: string; port: number; algorithm: string; fingerprint: string; requires_confirmation: boolean }>("/api/ssh/probe", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ host, port }),
  }),
  enrollSsh: (host: string, port: number, username: string, password: string, expectedFingerprint: string) => request<{ enrolled: boolean; identifier: string; fingerprint: string; credential_storage: string }>("/api/ssh/enroll", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ host, port, username, password, expected_fingerprint: expectedFingerprint }),
  }),
  scanServices: () => request<ServiceDiscovery>("/api/discovery/services", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ timeout_seconds: 2.5 }),
  }),
  scanNetwork: (mode: "standard" | "deep", target?: string) => request<NetworkDiscovery>("/api/discovery/network", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, target: target || null }),
  }),
  inspect: (identifier: string) => request<{ hardware: Hardware; inspection: Inspection; live?: unknown }>("/api/device/inspect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier }),
  }),
  select: (identifier: string) => request<{ hardware: Hardware; inspection?: Inspection; confirmed: boolean }>("/api/hardware/select", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier }),
  }),
  saveModel: (identifier: string, model: string) => request<{ saved: boolean; model: string }>("/api/device/model", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, model }),
  }),
  savePinAttachment: (identifier: string, pin: string, componentName: string, componentType: string, connectionInterface: string, notes: string) => request<{ saved: boolean; evidence_status: "declared" }>("/api/device/pin-attachments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, pin, component_name: componentName, component_type: componentType, interface: connectionInterface, notes }),
  }),
  deletePinAttachment: (identifier: string, pin: string) => request<{ deleted: boolean }>("/api/device/pin-attachments", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, pin }),
  }),
  importDefinition: (identifier: string, format: "cmsis-svd" | "zephyr-devicetree" | "kicad-schematic" | "fritzing-part" | "fritzing-bundle", sourceName: string, content: string) => request<{ count: number }>("/api/device/definitions/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, format, source_name: sourceName, content }),
  }),
  runTest: (identifier: string, testId: string) => request<{ passed: boolean; summary: string }>("/api/device/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, test_id: testId }),
  }),
  evidenceHistory: (identifier: string, limit = 50) => request<EvidenceHistory>(`/api/history?identifier=${encodeURIComponent(identifier)}&limit=${limit}`),
  exportEvidenceHistory: (identifier: string) => request<Record<string, unknown>>(`/api/history/export?identifier=${encodeURIComponent(identifier)}`),
  runCommand: (identifier: string, commandId: string) => request<DeviceCommandResult>("/api/device/command", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, command_id: commandId }),
  }),
  operations: (identifier: string) => request<{ identifier: string; operations: OperationCapability[] }>(`/api/device/operations?identifier=${encodeURIComponent(identifier)}`),
  operationHistory: (identifier: string) => request<{ identifier: string; events: OperationEvent[] }>(`/api/operations/history?identifier=${encodeURIComponent(identifier)}`),
  planOperation: (identifier: string, operationId: string) => request<OperationPlan>("/api/operations/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, operation_id: operationId, parameters: {} }),
  }),
  approveOperation: (identifier: string, planId: string) => request<OperationPlan>(`/api/operations/${encodeURIComponent(planId)}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier }),
  }),
  executeOperation: (identifier: string, planId: string, approvalToken?: string) => request<OperationResult>(`/api/operations/${encodeURIComponent(planId)}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, approval_token: approvalToken || null }),
  }),
  cancelOperation: (identifier: string) => request<{ identifier: string; plans_cancelled: number; process_terminated: boolean }>("/api/operations/cancel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier }),
  }),
  workspace: (identifier: string) => request<WorkspaceInventory>(`/api/workspace?identifier=${encodeURIComponent(identifier)}`),
  workspaceFile: (identifier: string, rootId: string, path: string) => request<WorkspaceFile>(`/api/workspace/file?identifier=${encodeURIComponent(identifier)}&root_id=${encodeURIComponent(rootId)}&path=${encodeURIComponent(path)}`),
  planWorkspaceWrite: (identifier: string, file: WorkspaceFile) => request<OperationPlan>("/api/workspace/write-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, root_id: file.root_id, path: file.path, content: file.content, expected_sha256: file.sha256 }),
  }),
  prototype: (identifier: string) => request<PrototypeProject>(`/api/prototype?identifier=${encodeURIComponent(identifier)}`),
  controlProfile: (identifier: string) => request<ControlProfile>(`/api/device/control-profile?identifier=${encodeURIComponent(identifier)}`),
  probeMatrix: (identifier: string) => request<ProbeMatrix>(`/api/device/probe-matrix?identifier=${encodeURIComponent(identifier)}`),
  savePrototype: (project: PrototypeProject) => request<PrototypeProject>("/api/prototype", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(project),
  }),
  simulatePrototype: (project: PrototypeProject) => request<SimulationReport>("/api/prototype/simulate", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(project),
  }),
  refreshDeviceStatus: () => request<{ accepted: boolean }>("/api/device/status", { method: "POST" }),
  setCameraControl: (setting: "brightness" | "contrast" | "saturation" | "sharpness" | "exposure" | "quality", value: number) => request<{ accepted: boolean; confirmed: boolean; setting: string; value: number; error?: string }>("/api/camera/control", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ setting, value }),
  }),
  setCameraTransport: (mode: "direct" | "websocket") => request<{ mode: "direct" | "websocket"; confirmed: boolean; direct_url: string | null; usb_streaming: boolean }>("/api/camera/transport", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode }),
  }),
  scanBle: () => request<BleStatus>("/api/ble/scan", { method: "POST" }),
  verifyBle: () => request<{ verified: boolean; address?: string; error?: string }>("/api/ble/connect", { method: "POST" }),
  setBlePower: (enabled: boolean) => request<{ accepted: boolean; confirmed: boolean; enabled: boolean; error?: string }>("/api/ble/power", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled }),
  }),
  setWifiAccessPoint: (enabled: boolean) => request<{ accepted: boolean; confirmed: boolean; enabled: boolean; ip?: string; error?: string }>("/api/wifi/ap", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled }),
  }),
  scanDeviceWifi: () => request<{ accepted: boolean; confirmed: boolean; networks: WifiNetwork[]; error?: string }>("/api/wifi/scan", { method: "POST" }),
  scanHostWifi: () => request<HostWifiScan>("/api/host/wifi/scan", { method: "POST" }),
  testDeviceInternet: () => request<{ accepted: boolean; confirmed: boolean; reachable: boolean; status: string; latency_ms: number; bytes_sent: number; bytes_received: number }>("/api/wifi/internet-test", { method: "POST" }),
  configureWifi: (ssid: string, password: string, remember: boolean) => request<{ accepted: boolean; attempted: boolean; saved: boolean; connected: boolean; ssid: string; status: string; ip?: string }>("/api/wifi", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ssid, password, remember }),
  }),
  configureDeviceAccess: (name: string, password: string) => request<{ accepted: boolean; confirmed: boolean; name?: string; ap_active?: boolean; ble_advertising?: boolean }>("/api/device/access", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, password }),
  }),
};
