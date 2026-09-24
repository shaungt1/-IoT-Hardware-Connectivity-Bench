import type { DeviceCommandResult, Hardware, HostInventory, Inspection, NetworkDiscovery, OperationCapability, OperationEvent, OperationPlan, OperationResult, ProviderRegistry, ServiceDiscovery, ToolRegistry, UsbInventory, WorkspaceFile, WorkspaceInventory } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body as T;
}

export const api = {
  hardware: () => request<Hardware[]>("/api/hardware"),
  usbInventory: () => request<UsbInventory>("/api/inventory/usb"),
  hostInventory: () => request<HostInventory>("/api/inventory/host"),
  tools: () => request<ToolRegistry>("/api/tools"),
  providers: () => request<ProviderRegistry>("/api/metadata/providers"),
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
  runTest: (identifier: string, testId: string) => request<{ passed: boolean; summary: string }>("/api/device/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, test_id: testId }),
  }),
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
  workspace: (identifier: string) => request<WorkspaceInventory>(`/api/workspace?identifier=${encodeURIComponent(identifier)}`),
  workspaceFile: (identifier: string, rootId: string, path: string) => request<WorkspaceFile>(`/api/workspace/file?identifier=${encodeURIComponent(identifier)}&root_id=${encodeURIComponent(rootId)}&path=${encodeURIComponent(path)}`),
  planWorkspaceWrite: (identifier: string, file: WorkspaceFile) => request<OperationPlan>("/api/workspace/write-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, root_id: file.root_id, path: file.path, content: file.content, expected_sha256: file.sha256 }),
  }),
};
