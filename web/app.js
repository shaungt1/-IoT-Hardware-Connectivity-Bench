const byId = (id) => document.getElementById(id);
const state = {
  currentPort: null,
  currentHardwareId: null,
  selectedHardware: null,
  deviceInspection: null,
  testResults: {},
  workspace: "host",
  networkProbe: null,
  savedPort: null,
  ports: [],
  savedWireless: [],
  telemetry: {},
  selectedBleAddress: null,
  bleDevicesSignature: "",
  wifiNetworks: [],
  lastFrameSequence: 0,
  lastFrameChange: 0,
  lastCameraRetry: 0,
  cameraExpected: false,
  operationCount: 0,
  inspectionRequest: null,
  consoleEvents: [],
  pinProbeIds: { deep: null, bus: null },
  firmwareInventory: null,
  firmwareFile: null,
  firmwareOriginalContent: "",
};
const cameraFeed = byId("camera-feed");

function icon(path, alt = "") {
  const image = document.createElement("img");
  image.src = `/icons/${path}.svg`;
  image.alt = alt;
  return image;
}

function reconnectCamera(force = false) {
  if (!state.cameraExpected) return;
  const now = Date.now();
  if (!force && now - state.lastCameraRetry < 1500) return;
  state.lastCameraRetry = now;
  cameraFeed.src = `${cameraFeed.dataset.streamSrc}?started=${now}`;
}

cameraFeed.addEventListener("error", () => {
  cameraFeed.parentElement.classList.remove("receiving");
  if (state.cameraExpected) setTimeout(reconnectCamera, 1200);
});

function formatBytes(value = 0) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 ** 2).toFixed(1)} MB`;
}

function formatUptime(milliseconds = 0) {
  const seconds = Math.floor(milliseconds / 1000);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m ${seconds % 60}s`;
}

function signalQuality(rssi) {
  if (!Number.isFinite(rssi) || rssi === 0) return "No signal measurement";
  if (rssi >= -55) return "Excellent";
  if (rssi >= -67) return "Good";
  if (rssi >= -75) return "Usable";
  return "Weak";
}

function setState(element, label, className = "") {
  element.textContent = label;
  element.className = `state-label ${className}`.trim();
}

function setBadge(element, label, className = "") {
  element.textContent = label;
  element.className = `status-badge ${className}`.trim();
}

function setDirectionStatus(dotId, stateId, label, tone) {
  byId(dotId).className = `mini-dot ${tone}`.trim();
  byId(stateId).textContent = label;
}

function setProgress(id, active) {
  const progress = byId(id);
  progress.hidden = !active;
  progress.setAttribute("aria-busy", String(active));
}

function logEvent(channel, message, tone = "") {
  state.consoleEvents.push({ at: new Date().toLocaleTimeString(), channel, message, tone });
  state.consoleEvents = state.consoleEvents.slice(-200);
  byId("console-event-count").textContent = `${state.consoleEvents.length} events`;
  const output = byId("console-output");
  output.replaceChildren();
  for (const event of state.consoleEvents) {
    const row = document.createElement("div");
    row.className = event.tone;
    const at = document.createElement("span");
    const label = document.createElement("b");
    const copy = document.createElement("pre");
    at.textContent = event.at;
    label.textContent = event.channel;
    copy.textContent = event.message;
    row.append(at, label, copy);
    output.append(row);
  }
  output.scrollTop = output.scrollHeight;
}

function beginOperation(label) {
  state.operationCount += 1;
  byId("global-progress").classList.add("active");
  logEvent("bench", label);
}

function endOperation() {
  state.operationCount = Math.max(0, state.operationCount - 1);
  byId("global-progress").classList.toggle("active", state.operationCount > 0);
}

async function apiJson(path, options) {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}

function switchWorkspace(workspace) {
  state.workspace = workspace;
  document.querySelectorAll("[data-workspace]").forEach((section) => {
    section.hidden = section.dataset.workspace !== workspace;
  });
  document.querySelectorAll("[data-workspace-tab]").forEach((button) => {
    const active = button.dataset.workspaceTab === workspace;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  window.scrollTo({ top: 0, behavior: "auto" });
  if ((workspace === "device" || workspace === "pins" || workspace === "tests") && state.selectedHardware?.id) {
    loadDeviceInspection().catch((error) => {
      byId("intelligence-message").textContent = error.message;
      logEvent("device", `Live inspection refresh failed: ${error.message}`, "error");
    });
  }
  if (workspace === "firmware") loadFirmwareWorkspace();
}

async function loadFirmwareWorkspace() {
  const identifier = state.selectedHardware?.id || state.currentHardwareId;
  const message = byId("firmware-message");
  if (!identifier) {
    message.textContent = "Select and inspect a device before opening firmware tools.";
    return;
  }
  beginOperation("Refreshing target firmware workspace...");
  try {
    const query = encodeURIComponent(identifier);
    const [inventory, operationResult, historyResult] = await Promise.all([
      apiJson(`/api/workspace?identifier=${query}`),
      apiJson(`/api/device/operations?identifier=${query}`),
      apiJson(`/api/operations/history?identifier=${query}`),
    ]);
    state.firmwareInventory = inventory;
    message.textContent = `${inventory.files.length} editable source/configuration files and ${operationResult.operations.filter((item) => item.available).length} ready operations.`;
    renderFirmwareOperations(operationResult.operations);
    renderFirmwareFiles(inventory);
    renderFirmwareHistory(historyResult.events);
  } catch (error) {
    message.textContent = error.message;
    logEvent("firmware", error.message, "error");
  } finally {
    endOperation();
  }
}

function renderFirmwareOperations(operations) {
  const target = byId("firmware-operations");
  target.replaceChildren();
  for (const operation of operations) {
    const card = document.createElement("article");
    card.className = "firmware-operation";
    const detail = document.createElement("div");
    const title = document.createElement("strong");
    const description = document.createElement("p");
    const badge = document.createElement("span");
    const limitation = document.createElement("small");
    const button = document.createElement("button");
    title.textContent = operation.label;
    description.textContent = operation.description;
    badge.className = `risk-badge risk-${operation.risk}`;
    badge.textContent = operation.risk;
    limitation.textContent = operation.available ? "Ready for a target-bound operation plan." : operation.reason;
    button.className = "tool-button";
    button.type = "button";
    button.disabled = !operation.available;
    button.textContent = operation.available ? "Plan & run" : "Unavailable";
    button.addEventListener("click", () => runFirmwareOperation(operation, button));
    detail.append(title, description, badge, limitation);
    card.append(detail, button);
    target.append(card);
  }
}

function renderFirmwareFiles(inventory) {
  const target = byId("firmware-file-list");
  target.replaceChildren();
  for (const root of inventory.roots) {
    const group = document.createElement("div");
    group.className = "firmware-file-root";
    const title = document.createElement("strong");
    const source = document.createElement("small");
    title.textContent = root.name;
    source.textContent = root.source;
    group.append(title, source);
    for (const file of inventory.files.filter((item) => item.root_id === root.id)) {
      const button = document.createElement("button");
      const name = document.createElement("span");
      const size = document.createElement("small");
      name.textContent = file.path;
      size.textContent = `${file.size} B`;
      button.append(name, size);
      button.addEventListener("click", () => openFirmwareFile(file, button));
      group.append(button);
    }
    target.append(group);
  }
}

function renderFirmwareHistory(events) {
  const body = byId("firmware-history-body");
  body.replaceChildren();
  for (const event of events.slice(0, 25)) {
    const row = document.createElement("tr");
    for (const value of [new Date(event.recorded_at).toLocaleString(), event.operation_id, event.risk, event.status, event.output || event.preview]) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    body.append(row);
  }
  if (!events.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.textContent = "No operations recorded for this target.";
    row.append(cell);
    body.append(row);
  }
}

async function openFirmwareFile(file, button) {
  const identifier = state.selectedHardware?.id || state.currentHardwareId;
  beginOperation(`Opening ${file.path}...`);
  try {
    const opened = await apiJson(`/api/workspace/file?identifier=${encodeURIComponent(identifier)}&root_id=${encodeURIComponent(file.root_id)}&path=${encodeURIComponent(file.path)}`);
    state.firmwareFile = opened;
    state.firmwareOriginalContent = opened.content;
    byId("firmware-file-name").textContent = opened.path;
    byId("firmware-file-hash").textContent = `sha256 ${opened.sha256.slice(0, 12)}`;
    byId("firmware-file-content").disabled = false;
    byId("firmware-file-content").value = opened.content;
    byId("firmware-save").disabled = true;
    document.querySelectorAll(".firmware-file-root button").forEach((item) => item.classList.toggle("active", item === button));
  } catch (error) {
    byId("firmware-message").textContent = error.message;
  } finally {
    endOperation();
  }
}

async function runFirmwareOperation(operation, button) {
  const identifier = state.selectedHardware?.id || state.currentHardwareId;
  button.disabled = true;
  beginOperation(`Planning ${operation.label}...`);
  try {
    const plan = await apiJson("/api/operations/plan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ identifier, operation_id: operation.id, parameters: {} }) });
    let token = null;
    if (plan.requires_approval) {
      if (!window.confirm(`${plan.preview}\n\nRisk: ${plan.risk}. Approval expires in ${plan.expires_in_seconds} seconds. Continue?`)) return;
      const approval = await apiJson(`/api/operations/${encodeURIComponent(plan.plan_id)}/approve`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ identifier }) });
      token = approval.approval_token;
    }
    const result = await apiJson(`/api/operations/${encodeURIComponent(plan.plan_id)}/execute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ identifier, approval_token: token }) });
    byId("firmware-message").textContent = result.output;
    logEvent("operation", `${operation.label}: ${result.output}`, result.passed ? "ok" : "error");
    await loadFirmwareWorkspace();
  } catch (error) {
    byId("firmware-message").textContent = error.message;
    logEvent("operation", error.message, "error");
  } finally {
    button.disabled = !operation.available;
    endOperation();
  }
}

async function saveFirmwareFile() {
  const identifier = state.selectedHardware?.id || state.currentHardwareId;
  if (!identifier || !state.firmwareFile) return;
  const content = byId("firmware-file-content").value;
  const button = byId("firmware-save");
  button.disabled = true;
  beginOperation(`Reviewing ${state.firmwareFile.path} update...`);
  try {
    const plan = await apiJson("/api/workspace/write-plan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ identifier, root_id: state.firmwareFile.root_id, path: state.firmwareFile.path, content, expected_sha256: state.firmwareFile.sha256 }) });
    if (!window.confirm(`${plan.preview}\n\nSave this change?`)) return;
    const approval = await apiJson(`/api/operations/${encodeURIComponent(plan.plan_id)}/approve`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ identifier }) });
    const result = await apiJson(`/api/operations/${encodeURIComponent(plan.plan_id)}/execute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ identifier, approval_token: approval.approval_token }) });
    byId("firmware-message").textContent = result.output;
    logEvent("workspace", result.output, result.passed ? "ok" : "error");
    if (result.passed) await loadFirmwareWorkspace();
  } catch (error) {
    byId("firmware-message").textContent = error.message;
    logEvent("workspace", error.message, "error");
  } finally {
    endOperation();
  }
}

function renderPinWorkspace(inspection) {
  const telemetry = inspection.telemetry || {};
  const adapter = inspection.adapter;
  const pins = inspection.pins || [];
  const peripherals = inspection.attached_peripherals || [];
  const runtimeTest = (inspection.tests || []).find((test) => test.action === "deep_probe");
  const i2cTest = (inspection.tests || []).find((test) => test.action === "bus_scan");
  state.pinProbeIds = { deep: runtimeTest?.id || null, bus: i2cTest?.id || null };

  byId("pin-adapter").textContent = adapter?.name || "No adapter";
  byId("pin-adapter").className = `status-badge${adapter ? " online" : ""}`;
  byId("pins-message").textContent = adapter
    ? `${inspection.model}: ${pins.filter((pin) => pin.status === "verified").length} runtime-verified and ${pins.filter((pin) => pin.status !== "verified").length} documented pins.`
    : "No pin adapter is available for this device profile.";
  byId("runtime-firmware").textContent = telemetry.firmware || inspection.runtime || "--";
  byId("runtime-storage").textContent = telemetry.storage_mount || "--";
  byId("runtime-storage-free").textContent = Number.isFinite(telemetry.storage_free_bytes) ? formatBytes(telemetry.storage_free_bytes) : "--";
  byId("runtime-heap").textContent = Number.isFinite(telemetry.free_heap_bytes) ? formatBytes(telemetry.free_heap_bytes) : "Run probe";
  byId("runtime-frequency").textContent = Number.isFinite(telemetry.cpu_frequency_hz) ? `${(telemetry.cpu_frequency_hz / 1_000_000).toFixed(2)} MHz` : telemetry.cpu_frequency || "Run probe";
  byId("runtime-code").textContent = telemetry.code_files?.join(", ") || "--";

  const artifacts = byId("runtime-artifacts");
  artifacts.replaceChildren();
  const artifactNames = [
    ...(telemetry.imports || []).map((name) => `import: ${name}`),
    ...(telemetry.libraries || []).map((name) => `library: ${name}`),
  ];
  for (const name of artifactNames) {
    const chip = document.createElement("span");
    chip.textContent = name;
    artifacts.append(chip);
  }
  if (!artifactNames.length) {
    const empty = document.createElement("span");
    empty.textContent = "No runtime modules reported.";
    artifacts.append(empty);
  }

  byId("runtime-probe").disabled = !runtimeTest?.available;
  byId("i2c-probe").disabled = !i2cTest?.available;
  byId("i2c-probe").hidden = !i2cTest;
  byId("probe-boundary").textContent = runtimeTest?.description || (adapter ? "This adapter has no deeper target-identification action." : "No compatible runtime adapter detected.");

  const grouped = new Map();
  for (const pin of pins) {
    const group = pin.group || "Other";
    if (!grouped.has(group)) grouped.set(group, []);
    grouped.get(group).push(pin);
  }
  const pinGroups = byId("pin-groups");
  pinGroups.replaceChildren();
  for (const [group, groupPins] of grouped) {
    const section = document.createElement("section");
    section.className = "pin-group";
    const header = document.createElement("header");
    const title = document.createElement("strong");
    const count = document.createElement("span");
    title.textContent = group;
    count.textContent = `${groupPins.length} pins`;
    header.append(title, count);
    const grid = document.createElement("div");
    grid.className = "pin-grid";
    for (const pin of groupPins) {
      const card = document.createElement("article");
      card.className = "pin-card";
      const heading = document.createElement("div");
      const name = document.createElement("strong");
      name.textContent = [pin.name, ...(pin.aliases || [])].join(" / ");
      heading.append(name, createStatusLabel(pin.status));
      const functions = document.createElement("small");
      functions.textContent = (pin.functions || []).join(" | ");
      const source = document.createElement("small");
      source.textContent = pin.source || "Device profile";
      card.append(heading, functions, source);
      grid.append(card);
    }
    section.append(header, grid);
    pinGroups.append(section);
  }
  if (!pins.length) fillEmpty(pinGroups, "No pin map is available for this device profile.");
  byId("pin-count").textContent = `${pins.length} pins`;

  const peripheralList = byId("attached-peripherals");
  peripheralList.replaceChildren();
  for (const peripheral of peripherals) {
    const card = document.createElement("article");
    card.className = "peripheral-card";
    const heading = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = peripheral.name;
    heading.append(name, createStatusLabel(peripheral.status));
    const candidates = document.createElement("small");
    candidates.textContent = `Candidates: ${(peripheral.candidates || []).join("; ")}`;
    const source = document.createElement("small");
    source.textContent = `${peripheral.bus} ${peripheral.address} | ${peripheral.source}`;
    card.append(heading, candidates, source);
    peripheralList.append(card);
  }
  if (!peripherals.length) fillEmpty(peripheralList, "No responding external bus address has been detected.");
  byId("peripheral-count").textContent = `${peripherals.length} detected`;
}

function createStatusLabel(status = "unknown") {
  const label = document.createElement("span");
  label.className = `evidence-status ${status}`;
  label.textContent = status;
  return label;
}

function createInspectionRow(title, detail, status = "unknown") {
  const row = document.createElement("div");
  row.className = "inspection-row";
  const copy = document.createElement("div");
  const strong = document.createElement("strong");
  const small = document.createElement("small");
  strong.textContent = title;
  small.textContent = detail || "No additional detail";
  copy.append(strong, small);
  row.append(copy, createStatusLabel(status));
  return row;
}

function createServiceRow(service) {
  if (!service.url) return createInspectionRow(service.name, `${service.address}:${service.port}`, service.status);
  const link = document.createElement("a");
  link.className = "resource-row service-resource";
  link.href = service.url;
  link.target = "_blank";
  link.rel = "noreferrer";
  const title = document.createElement("strong");
  const detail = document.createElement("small");
  title.textContent = service.name;
  detail.textContent = service.url;
  link.append(title, detail);
  return link;
}

function fillEmpty(container, message) {
  const empty = document.createElement("p");
  empty.textContent = message;
  container.append(empty);
}

function renderDeviceInspection(inspection) {
  state.deviceInspection = inspection;
  renderPinWorkspace(inspection);
  byId("intelligence-model").textContent = inspection.model || "Unidentified hardware";
  byId("intelligence-class").textContent = (inspection.classification || "Unknown").replaceAll("_", " ");
  byId("intelligence-mcu").textContent = [inspection.mcu, inspection.architecture].filter(Boolean).join(" | ") || "Unknown";
  byId("intelligence-runtime").textContent = inspection.runtime || "Unknown";
  byId("intelligence-confidence").textContent = `${Math.round((inspection.confidence || 0) * 100)}%`;
  byId("intelligence-message").textContent = `${inspection.interface || inspection.identifier} inspected. Claims below show whether they are verified, detected, expected, or unavailable.`;

  const modelForm = byId("device-model-form");
  const modelSelect = byId("device-model-select");
  modelSelect.replaceChildren();
  modelForm.hidden = !(inspection.candidates || []).length;
  for (const candidate of inspection.candidates || []) {
    const option = document.createElement("option");
    option.value = candidate;
    option.textContent = candidate;
    option.selected = candidate === inspection.model;
    modelSelect.append(option);
  }

  const layerWrap = byId("identity-layers-wrap");
  const layerBody = byId("identity-layers-body");
  layerBody.replaceChildren();
  for (const layer of inspection.identity_layers || []) {
    const row = document.createElement("tr");
    const layerName = document.createElement("td");
    const hardware = document.createElement("td");
    const source = document.createElement("td");
    const status = document.createElement("td");
    layerName.textContent = layer.layer;
    hardware.textContent = layer.name;
    source.textContent = layer.source;
    status.append(createStatusLabel(layer.status));
    row.append(layerName, hardware, source, status);
    layerBody.append(row);
  }
  layerWrap.hidden = !(inspection.identity_layers || []).length;

  const capabilityIds = new Set((inspection.capabilities || []).map((item) => item.id));
  const hasBle = capabilityIds.has("ble");
  const hasWifi = capabilityIds.has("wifi_24") || capabilityIds.has("wifi_5");
  const bleTab = document.querySelector('[data-radio-tab="ble"]');
  const wifiTab = document.querySelector('[data-radio-tab="wifi"]');
  bleTab.hidden = !hasBle;
  wifiTab.hidden = !hasWifi;
  byId("wireless-capability-message").textContent = hasBle && hasWifi
    ? "Select a supported wireless connection"
    : hasWifi
      ? "This device reports Wi-Fi only"
      : hasBle
        ? "This device reports Bluetooth (BLE) only"
        : "No wireless capability has been verified for this device";
  if (hasWifi && !hasBle) wifiTab.click();
  if (hasBle && !hasWifi) bleTab.click();
  if (!hasBle && !hasWifi) {
    byId("ble-panel").hidden = true;
    byId("wifi-panel").hidden = true;
    byId("active-radio-label").textContent = "No verified radio";
  }

  const evidence = byId("device-evidence");
  evidence.replaceChildren();
  for (const item of inspection.evidence || []) evidence.append(createInspectionRow(item.claim, item.source, item.status));
  if (!inspection.evidence?.length) fillEmpty(evidence, "No evidence collected");
  byId("evidence-count").textContent = `${inspection.evidence?.length || 0} claims`;

  const components = byId("device-components");
  components.replaceChildren();
  for (const component of inspection.components || []) {
    const card = document.createElement("article");
    card.className = "component-card";
    const heading = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = component.name;
    heading.append(name, createStatusLabel(component.status));
    const details = document.createElement("small");
    details.textContent = [component.type, component.bus, component.variant].filter(Boolean).join(" | ");
    const source = document.createElement("small");
    source.textContent = `Source: ${component.source}`;
    card.append(heading, details, source);
    components.append(card);
  }
  if (!inspection.components?.length) fillEmpty(components, "No onboard components can be inferred from the current evidence.");
  byId("component-count").textContent = `${inspection.components?.length || 0} items`;

  const capabilities = byId("device-capabilities");
  capabilities.replaceChildren();
  for (const capability of inspection.capabilities || []) capabilities.append(createInspectionRow(capability.name, capability.source, capability.status));
  const services = byId("device-services");
  services.replaceChildren();
  for (const service of inspection.services || []) services.append(createServiceRow(service));
  if (!inspection.capabilities?.length && !inspection.services?.length) fillEmpty(capabilities, "No capabilities or services identified.");
  byId("capability-count").textContent = `${(inspection.capabilities?.length || 0) + (inspection.services?.length || 0)} items`;

  const connectionInterfaces = byId("device-connection-interfaces");
  connectionInterfaces.replaceChildren();
  for (const connection of inspection.connection_interfaces || []) {
    connectionInterfaces.append(createInspectionRow(connection.name, [connection.adapter, connection.limitation].filter(Boolean).join(" | "), connection.status));
  }
  if (!inspection.connection_interfaces?.length) fillEmpty(connectionInterfaces, "No externally enumerable bus was identified for this profile.");
  byId("connection-interface-count").textContent = `${inspection.connection_interfaces?.length || 0} interfaces`;

  const tests = byId("device-tests");
  tests.replaceChildren();
  for (const test of inspection.tests || []) {
    const row = document.createElement("div");
    row.className = "test-row";
    const copy = document.createElement("div");
    const name = document.createElement("strong");
    const details = document.createElement("small");
    name.textContent = test.name;
    details.textContent = `${test.description} Risk: ${test.risk}.`;
    copy.append(name, details);
    const button = document.createElement("button");
    button.type = "button";
    button.className = test.available ? "tool-button" : "tool-button";
    button.textContent = test.available ? "Run test" : "Unavailable";
    button.disabled = !test.available;
    button.title = test.available ? `Run ${test.name}` : test.description;
    button.addEventListener("click", () => runDeviceTest(test, row));
    row.append(copy, button);
    const priorResult = state.testResults[test.id];
    if (priorResult) {
      const resultLine = document.createElement("small");
      resultLine.className = `test-result evidence-status ${priorResult.tone || ""}`.trim();
      resultLine.textContent = priorResult.text;
      row.append(resultLine);
      if (priorResult.running) button.disabled = true;
    }
    tests.append(row);
  }
  if (!inspection.tests?.length) fillEmpty(tests, "No tests available for this interface.");
  byId("test-count").textContent = `${inspection.tests?.filter((test) => test.available).length || 0} ready`;

  const resources = byId("device-resources");
  resources.replaceChildren();
  for (const resource of inspection.resources || []) {
    const link = document.createElement("a");
    link.className = "resource-row";
    link.href = resource.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    const title = document.createElement("strong");
    const detail = document.createElement("small");
    title.textContent = resource.title;
    detail.textContent = `${resource.provider} | ${resource.kind}`;
    link.append(title, detail);
    resources.append(link);
  }
  if (!inspection.resources?.length) fillEmpty(resources, "No documentation matched this device.");
  byId("resource-count").textContent = `${inspection.resources?.length || 0} links`;

  const camera = (inspection.components || []).find((component) => component.type === "camera");
  state.cameraExpected = Boolean(camera || state.selectedHardware?.is_esp32);
  byId("camera-empty-message").textContent = !state.cameraExpected
    ? "No camera detected for selected hardware"
    : camera?.status === "unavailable"
      ? `${camera.name} is configured but not detected`
      : "Camera detected; waiting for frames";
  if (!state.cameraExpected) {
    cameraFeed.removeAttribute("src");
    cameraFeed.parentElement.classList.remove("receiving");
  }
}

async function loadDeviceInspection(identifier = state.selectedHardware?.id) {
  if (!identifier) {
    byId("intelligence-message").textContent = "Select a detected interface before inspecting it.";
    return null;
  }
  if (state.inspectionRequest) return state.inspectionRequest;
  byId("intelligence-message").textContent = "Collecting identity evidence and compatible provider data...";
  beginOperation("Collecting device identity and capability evidence...");
  state.inspectionRequest = (async () => {
    const response = await fetch("/api/device/inspect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Device inspection failed");
    renderDeviceInspection(result.inspection);
    if (result.live && state.selectedHardware?.kind === "usb_network") state.networkProbe = result.live;
    logEvent("device", `${result.inspection.model} inspected at ${Math.round((result.inspection.confidence || 0) * 100)}% identity confidence.`, "ok");
    return result;
  })();
  try {
    return await state.inspectionRequest;
  } finally {
    state.inspectionRequest = null;
    endOperation();
  }
}

async function runDeviceTest(test, row) {
  const button = row.querySelector("button");
  button.disabled = true;
  let resultLine = row.querySelector(".test-result");
  if (!resultLine) {
    resultLine = document.createElement("small");
    resultLine.className = "test-result";
    row.append(resultLine);
  }
  resultLine.textContent = `Running ${test.name}...`;
  state.testResults[test.id] = { text: resultLine.textContent, running: true, tone: "" };
  beginOperation(`Running ${test.name}...`);
  try {
    const response = await fetch("/api/device/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: state.selectedHardware.id, test_id: test.id }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Test failed");
    resultLine.textContent = result.summary;
    state.testResults[test.id] = { text: result.summary, running: false, tone: result.passed ? "verified" : "unavailable" };
    await loadDeviceInspection();
    logEvent("test", result.summary, result.passed ? "ok" : "error");
    resultLine.className = `test-result evidence-status ${result.passed ? "verified" : "unavailable"}`;
  } catch (error) {
    resultLine.textContent = error.message;
    state.testResults[test.id] = { text: error.message, running: false, tone: "unavailable" };
    if (state.deviceInspection) renderDeviceInspection(state.deviceInspection);
    resultLine.className = "test-result evidence-status unavailable";
  } finally {
    button.disabled = false;
    endOperation();
  }
}

async function runPinProbe(testId) {
  if (!state.selectedHardware?.id || !state.deviceInspection) return;
  const test = (state.deviceInspection.tests || []).find((item) => item.id === testId);
  if (!test?.available) return;
  const confirmed = window.confirm(`${test.description} Continue?`);
  if (!confirmed) return;
  const buttons = [byId("runtime-probe"), byId("i2c-probe")];
  buttons.forEach((button) => { button.disabled = true; });
  byId("pins-message").textContent = `Running ${test.name}...`;
  beginOperation(`Running ${test.name}...`);
  try {
    const response = await fetch("/api/device/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: state.selectedHardware.id, test_id: testId }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Probe failed");
    await loadDeviceInspection();
    byId("pins-message").textContent = result.summary;
    logEvent("probe", result.summary, result.passed ? "ok" : "error");
  } catch (error) {
    byId("pins-message").textContent = error.message;
    logEvent("probe", error.message, "error");
  } finally {
    const tests = state.deviceInspection?.tests || [];
    byId("runtime-probe").disabled = !tests.find((item) => item.action === "deep_probe")?.available;
    byId("i2c-probe").disabled = !tests.find((item) => item.action === "bus_scan")?.available;
    endOperation();
  }
}

function render(data) {
  const usingNetworkDevice = state.selectedHardware?.kind === "usb_network" && state.networkProbe;
  const usingCompatibleSerial = state.selectedHardware?.kind === "serial" && state.selectedHardware?.is_esp32 && data.port === state.selectedHardware.device;
  const usingGenericDevice = state.selectedHardware && !usingNetworkDevice && !usingCompatibleSerial;
  const telemetry = usingNetworkDevice
    ? (state.networkProbe.telemetry || {})
    : usingCompatibleSerial
      ? (data.telemetry || {})
      : usingGenericDevice
        ? (state.deviceInspection?.telemetry || {})
        : {};
  const ble = data.ble || {};
  state.telemetry = telemetry;
  const selectedPresent = Boolean(state.selectedHardware && state.ports.some((item) => item.id === state.selectedHardware.id));
  const hardwareOnline = usingNetworkDevice ? Boolean(state.networkProbe.online) : usingCompatibleSerial ? Boolean(data.connected) : selectedPresent;
  const protocolCompatible = usingCompatibleSerial && Boolean(telemetry.device && telemetry.firmware);
  const capabilityIds = new Set((state.deviceInspection?.capabilities || []).map((item) => item.id));
  const identityInspected = Boolean(state.deviceInspection);
  const hasBleHardware = capabilityIds.has("ble");
  const hasWifiHardware = capabilityIds.has("wifi_24") || capabilityIds.has("wifi_5");
  const selectedDeviceName = usingNetworkDevice ? state.networkProbe.name : (telemetry.device || state.selectedHardware?.name || state.selectedHardware?.device);

  byId("overall-dot").classList.toggle("online", hardwareOnline);
  byId("overall-label").textContent = hardwareOnline ? "Hardware online" : state.selectedHardware ? "Hardware unavailable" : "Waiting for selection";
  byId("device-name").textContent = selectedDeviceName || "Select a detected interface";
  byId("link-device-name").textContent = selectedDeviceName || "Waiting for a selected interface";
  byId("usb-port").textContent = usingNetworkDevice ? state.networkProbe.ip_address : (state.selectedHardware?.device || (usingCompatibleSerial ? data.port : "No port"));
  if (usingCompatibleSerial) state.currentPort = data.port || state.currentPort;
  setState(byId("usb-state"), hardwareOnline ? "Online" : "Offline", hardwareOnline ? "online" : "");
  byId("packets").textContent = usingNetworkDevice ? "USB IP" : usingCompatibleSerial ? (data.packets_received || 0).toLocaleString() : "--";
  byId("bytes").textContent = usingNetworkDevice ? state.networkProbe.interface : usingCompatibleSerial ? formatBytes(data.bytes_received) : "--";
  byId("protocol-state").textContent = usingNetworkDevice ? "SSH + HTTP" : protocolCompatible ? "Compatible" : usingGenericDevice ? "Identity only" : "Waiting";
  byId("device-wifi-capability").textContent = protocolCompatible
    ? "Reported by device: 2.4 GHz"
    : hasWifiHardware
      ? "Wi-Fi hardware verified; runtime controls require compatible firmware"
      : identityInspected
        ? "Wi-Fi not reported by this device"
        : "Inspect the selected device to identify radio hardware";

  const bleAdvertising = Boolean(telemetry.ble_advertising);
  const bleConnected = Boolean(telemetry.ble_connected);
  byId("ble-broadcast-name").textContent = telemetry.device || "Unavailable";
  byId("ble-client-count").textContent = telemetry.ble_client_count ?? 0;
  byId("ble-connections-total").textContent = telemetry.ble_connections_total ?? 0;
  byId("ble-device-address").textContent = telemetry.ble_device_address || "--";
  byId("ble-service-id").textContent = telemetry.ble_service_uuid || "--";
  byId("ble-power").dataset.enabled = String(bleAdvertising);
  byId("ble-power").disabled = !protocolCompatible;
  byId("ble-settings").disabled = !protocolCompatible;
  byId("ble-power").querySelector("span").textContent = bleAdvertising ? "Stop BLE broadcast" : "Start BLE broadcast";
  setBadge(
    byId("ble-broadcast-status"),
    bleConnected ? "Client connected" : ble.detected ? "Signal detected" : bleAdvertising ? "Controller on" : "Off",
    bleConnected || ble.detected ? "online" : bleAdvertising ? "warning" : "danger",
  );
  const bleUnavailableLabel = identityInspected && !hasBleHardware ? "Not supported" : "Unknown";
  setDirectionStatus("ble-out-dot", "ble-out-state", protocolCompatible ? (bleAdvertising ? "On" : "Off") : bleUnavailableLabel, protocolCompatible ? (bleAdvertising ? "online pulse" : "danger") : "warning");
  setDirectionStatus("ble-in-dot", "ble-in-state", protocolCompatible ? (bleConnected ? `${telemetry.ble_client_count} connected` : "Waiting") : bleUnavailableLabel, protocolCompatible && bleConnected ? "online" : "warning");
  setDirectionStatus("ble-read-dot", "ble-read-state", identityInspected && !hasBleHardware ? "Not supported" : ble.connection_verified ? "Verified" : "None", ble.connection_verified ? "online" : "warning");
  byId("ble-address").textContent = protocolCompatible
    ? (ble.detected ? `${ble.name} detected by computer` : `${telemetry.device} ${bleAdvertising ? "controller on" : "broadcast off"}`)
    : identityInspected && !hasBleHardware
      ? "Bluetooth is not present in the identified hardware"
      : "No compatible telemetry";
  byId("ble-quality").textContent = ble.detected
    ? `${ble.name} received by this computer at ${ble.rssi_dbm} dBm${ble.connection_verified ? "; GATT verified" : ""}`
    : telemetry.ble_advertisement_error || ble.error || (bleAdvertising ? `BLE controller is active at ${telemetry.ble_device_address || "unknown address"}; over-air reception has not been verified.` : "BLE broadcast is disabled.");
  renderBleDevices(ble.devices || []);

  const stationConnected = Boolean(telemetry.wifi_station_connected);
  const apActive = Boolean(telemetry.wifi_ap_active);
  const stationStatus = telemetry.wifi_station_status || "not_configured";
  const stationName = telemetry.wifi_station_ssid || "";
  const internetVerified = Boolean(telemetry.internet_reachable);
  const probeStatus = telemetry.internet_probe_status || "not_tested";
  byId("wifi-power").dataset.enabled = String(apActive);
  byId("wifi-power").disabled = !protocolCompatible;
  byId("wifi-toggle").disabled = !protocolCompatible;
  byId("wifi-refresh").disabled = !protocolCompatible;
  byId("wifi-power").querySelector("span").textContent = apActive ? "Stop Wi-Fi broadcast" : "Start Wi-Fi broadcast";
  byId("wifi-broadcast-name").textContent = telemetry.wifi_ap_ssid || "Unavailable";
  byId("wifi-client-count").textContent = telemetry.wifi_ap_clients ?? 0;
  byId("wifi-ap-address").textContent = apActive ? telemetry.wifi_ap_ip || "Starting" : "Off";
  setBadge(byId("wifi-broadcast-status"), apActive ? "Broadcasting" : "Off", apActive ? "warning" : "");
  const wifiEvidenceLabel = hasWifiHardware ? "Hardware verified" : identityInspected ? "Not reported" : "Unknown";
  setDirectionStatus("wifi-out-dot", "wifi-out-state", protocolCompatible ? (apActive ? "On" : "Off") : wifiEvidenceLabel, protocolCompatible ? (apActive ? "online pulse" : "danger") : hasWifiHardware ? "online" : "warning");
  setDirectionStatus("wifi-client-dot", "wifi-client-state", protocolCompatible ? (telemetry.wifi_ap_clients > 0 ? `${telemetry.wifi_ap_clients} connected` : "Waiting") : wifiEvidenceLabel, protocolCompatible && telemetry.wifi_ap_clients > 0 ? "online" : hasWifiHardware ? "online" : "warning");
  setDirectionStatus("wifi-in-dot", "wifi-in-state", protocolCompatible ? (stationConnected ? "Connected" : "Offline") : wifiEvidenceLabel, protocolCompatible && stationConnected ? "online" : hasWifiHardware ? "online" : "warning");
  byId("wifi-network").textContent = protocolCompatible
    ? (stationConnected ? `${stationName} internet link` : apActive ? `${telemetry.wifi_ap_ssid} broadcasting` : "Wi-Fi broadcast off")
    : hasWifiHardware
      ? "Wi-Fi hardware detected; live state requires compatible firmware"
      : "No compatible telemetry";
  byId("wifi-current-name").textContent = stationName || "Not connected";
  byId("wifi-detail").textContent = stationConnected
    ? `${telemetry.wifi_station_ip} | ${telemetry.wifi_rssi_dbm} dBm | ${signalQuality(telemetry.wifi_rssi_dbm)}`
    : stationName ? `Last result: ${stationStatus.replaceAll("_", " ")}` : "No router has been selected";
  setBadge(
    byId("wifi-current-status"),
    stationConnected ? "Connected" : stationName ? stationStatus.replaceAll("_", " ") : "Offline",
    stationConnected ? "online" : stationName ? "danger" : "",
  );
  byId("wifi-gateway").textContent = telemetry.wifi_gateway_ip || "--";
  byId("wifi-dns").textContent = telemetry.wifi_dns_ip || "--";
  byId("internet-latency").textContent = telemetry.internet_probe_id ? `${telemetry.internet_probe_latency_ms || 0} ms` : "--";
  byId("internet-traffic").textContent = `${formatBytes(telemetry.internet_bytes_sent || 0)} out / ${formatBytes(telemetry.internet_bytes_received || 0)} in`;
  byId("internet-test").disabled = !protocolCompatible || !stationConnected;
  setBadge(byId("internet-probe-status"), internetVerified ? "Verified" : probeStatus.replaceAll("_", " "), internetVerified ? "online" : telemetry.internet_probe_id ? "danger" : "");
  byId("internet-probe-detail").textContent = internetVerified
    ? `Outbound Internet traffic verified; ${telemetry.internet_tests_successful || 0} successful test${telemetry.internet_tests_successful === 1 ? "" : "s"}.`
    : stationConnected ? `Router connected; Internet result: ${probeStatus.replaceAll("_", " ")}.` : "Connect the device to a 2.4 GHz router before testing.";

  if (telemetry.camera_ready || telemetry.camera_status) state.cameraExpected = true;
  byId("camera-empty-message").textContent = !state.cameraExpected
    ? "No camera detected for selected hardware"
    : telemetry.camera_ready
      ? "Camera detected; waiting for frames"
      : telemetry.camera_status || "Camera detected; waiting for frames";
  byId("fps").textContent = Number(data.measured_fps || telemetry.camera_fps || 0).toFixed(1);
  byId("frames").textContent = (telemetry.frames_sent || 0).toLocaleString();
  const newFrame = data.frame_sequence && data.frame_sequence !== state.lastFrameSequence;
  if (newFrame) {
    state.lastFrameSequence = data.frame_sequence;
    state.lastFrameChange = Date.now();
    if (state.cameraExpected && cameraFeed.naturalWidth === 0) reconnectCamera();
  }
  cameraFeed.parentElement.classList.toggle("receiving", Date.now() - state.lastFrameChange < 2500);
  byId("firmware").textContent = telemetry.firmware || "--";
  byId("camera-status").textContent = telemetry.camera_ready ? (telemetry.camera_sensor_pid ? `Ready | PID ${telemetry.camera_sensor_pid}` : "Ready") : telemetry.camera_status || "Unavailable";
  byId("heap").textContent = telemetry.free_heap_bytes ? formatBytes(telemetry.free_heap_bytes) : "--";
  byId("psram").textContent = telemetry.psram_bytes ? formatBytes(telemetry.psram_bytes) : "--";
  byId("uptime").textContent = telemetry.uptime_ms ? formatUptime(telemetry.uptime_ms) : "--";
  byId("ap-clients").textContent = telemetry.wifi_ap_clients ?? "--";
  byId("updated-at").textContent = telemetry.uptime_ms || telemetry.firmware ? `Updated ${new Date().toLocaleTimeString()}` : "No compatible data received";
  byId("bridge-uptime").textContent = `Bridge uptime ${Math.floor(data.bridge_uptime_seconds || 0)}s`;
}

function createDiscoveryRow(iconName, title, subtitle, meta) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "discovery-item";
  const symbol = document.createElement("span");
  symbol.className = "radio-symbol";
  symbol.append(icon(iconName));
  const copy = document.createElement("span");
  copy.className = "discovery-item-copy";
  const strong = document.createElement("strong");
  strong.textContent = title;
  const detail = document.createElement("span");
  detail.textContent = subtitle;
  copy.append(strong, detail);
  const metadata = document.createElement("span");
  metadata.className = "discovery-meta";
  metadata.textContent = meta;
  button.append(symbol, copy, metadata, icon("chevron-right"));
  return button;
}

function renderBleDevices(devices = []) {
  const saved = new Set(state.savedWireless.filter((item) => item.kind === "ble").map((item) => item.identifier));
  const signature = JSON.stringify(devices.map((device) => [device.address, device.rssi_dbm, saved.has(device.address), state.selectedBleAddress]));
  if (signature === state.bleDevicesSignature) return;
  state.bleDevicesSignature = signature;
  const list = byId("ble-devices");
  list.replaceChildren();
  if (!devices.length) {
    const empty = document.createElement("p");
    empty.textContent = "No BLE advertisements detected";
    list.append(empty);
    return;
  }
  for (const device of devices) {
    const row = createDiscoveryRow(
      "bluetooth",
      device.name,
      `${device.address} | ${device.rssi_dbm} dBm | ${signalQuality(device.rssi_dbm)}`,
      saved.has(device.address) ? "Saved" : device.is_compatible ? "IoT Bench" : "Nearby",
    );
    row.classList.toggle("selected", state.selectedBleAddress === device.address);
    row.addEventListener("click", () => {
      state.selectedBleAddress = device.address;
      byId("ble-connect").disabled = !device.is_compatible;
      byId("ble-rssi").textContent = device.is_compatible
        ? `${device.name} selected; ready for GATT verification`
        : `${device.name} selected; discovery only because it does not expose a compatible IoT Bench test service`;
      state.bleDevicesSignature = "";
      renderBleDevices(devices);
    });
    list.append(row);
  }
}

function selectWifiNetwork(network) {
  byId("wifi-form").hidden = false;
  byId("wifi-form-network").textContent = network.ssid || "Hidden network";
  byId("wifi-ssid").value = network.ssid || "";
  byId("wifi-password").value = "";
  byId("wifi-message").textContent = network.rssi_dbm <= -80 ? "Signal is weak; the connection may fail until the antenna or device position improves." : "";
  (network.ssid ? byId("wifi-password") : byId("wifi-ssid")).focus();
  document.querySelectorAll("#wifi-networks .discovery-item").forEach((row) => row.classList.toggle("selected", row.dataset.ssid === network.ssid));
}

function renderWifiNetworks(networks = []) {
  state.wifiNetworks = networks;
  const saved = new Map(state.savedWireless.filter((item) => item.kind === "wifi").map((item) => [item.identifier, item]));
  const list = byId("wifi-networks");
  list.replaceChildren();
  if (!networks.length) {
    const empty = document.createElement("p");
    empty.textContent = "The selected device did not report any 2.4 GHz networks";
    list.append(empty);
    return;
  }
  for (const network of networks) {
    const title = network.ssid || "Hidden network";
    const profile = saved.get(network.ssid);
    const row = createDiscoveryRow(
      "wifi",
      title,
      `2.4 GHz | ${network.rssi_dbm} dBm | channel ${network.channel} | ${signalQuality(network.rssi_dbm)}`,
      profile ? `Saved | ${profile.status.replaceAll("_", " ")}` : network.secure ? "Secured" : "Open",
    );
    row.dataset.ssid = network.ssid;
    row.addEventListener("click", () => selectWifiNetwork(network));
    list.append(row);
  }
}

function renderHostWifi(result) {
  const list = byId("host-wifi-networks");
  list.replaceChildren();
  if (!result.available) {
    byId("host-wifi-capability").textContent = "Unavailable; install a dual-band Wi-Fi adapter";
    const empty = document.createElement("p");
    empty.textContent = result.error || "Computer Wi-Fi scanner unavailable";
    list.append(empty);
    return;
  }
  byId("host-wifi-capability").textContent = "2.4/5 GHz host scanning available";
  if (!result.networks.length) {
    const empty = document.createElement("p");
    empty.textContent = "No networks received by the computer radio";
    list.append(empty);
    return;
  }
  for (const network of result.networks) {
    const connectable = network.band === "2.4 GHz";
    const row = createDiscoveryRow("monitor-smartphone", network.ssid, `${network.band} | channel ${network.channel} | signal ${network.signal_percent}%`, connectable ? "Device can join" : "Computer only");
    row.addEventListener("click", () => {
      if (connectable) selectWifiNetwork({ ssid: network.ssid, rssi_dbm: 0, channel: network.channel, secure: network.security !== "Open" });
      else byId("wifi-rssi").textContent = `${network.ssid} is ${network.band}; the computer can see it, but the selected device reports 2.4 GHz only.`;
    });
    list.append(row);
  }
}

async function loadPorts() {
  beginOperation("Refreshing connected ports and USB network interfaces...");
  try {
  const [portsResponse, profilesResponse] = await Promise.all([fetch("/api/hardware"), fetch("/api/profiles")]);
  const ports = await portsResponse.json();
  const profiles = await profilesResponse.json();
  state.savedPort = profiles.selected_port || state.savedPort;
  state.currentHardwareId = state.currentHardwareId || profiles.selected_hardware;
  state.savedWireless = profiles.wireless_profiles || [];
  state.ports = ports;
  if (state.wifiNetworks.length) renderWifiNetworks(state.wifiNetworks);
  state.bleDevicesSignature = "";
  const body = byId("ports-body");
  const select = byId("port-select");
  body.replaceChildren();
  select.replaceChildren();
  const selectedStillPresent = state.selectedHardware && ports.some((port) => port.id === state.selectedHardware.id);
  if (state.selectedHardware && !selectedStillPresent) {
    state.selectedHardware = null;
    state.networkProbe = null;
    state.currentHardwareId = null;
    state.currentPort = null;
    state.deviceInspection = null;
    state.testResults = {};
    byId("network-device-services").hidden = true;
    byId("port-message").textContent = "The selected hardware was disconnected. Live state has been cleared.";
  }
  if (!ports.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.textContent = "No USB serial or network devices detected";
    row.append(cell);
    body.append(row);
    byId("profile-name").textContent = "No device selected";
    byId("profile-transport").textContent = "--";
    byId("profile-usb").textContent = "--";
    byId("profile-role").textContent = "--";
    logEvent("host", "No USB serial or USB network interfaces detected.");
    return;
  }
  for (const port of ports) {
    const interfaceName = port.device || port.interface || port.ip_address || port.id;
    const option = document.createElement("option");
    option.value = port.id;
    option.textContent = `${interfaceName} - ${port.name || port.description}`;
    select.append(option);
  }
  const categories = ["Circuit, controller, or compute target", "Programming or debug interface", "Unresolved serial target", "Host peripheral"];
  for (const category of categories) {
    const members = ports.filter((port) => (port.device_category || "Host peripheral") === category);
    if (!members.length) continue;
    const groupRow = document.createElement("tr");
    groupRow.className = "device-group";
    const groupCell = document.createElement("td");
    groupCell.colSpan = 5;
    groupCell.textContent = `${category} (${members.length})`;
    groupRow.append(groupCell);
    body.append(groupRow);
    for (const port of members) {
    const interfaceName = port.device || port.interface || port.ip_address || port.id;
    const row = document.createElement("tr");
    for (const value of [interfaceName, port.name || port.description, `${port.vid || "----"}:${port.pid || "----"}`, port.transport]) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    const action = document.createElement("td");
    const label = document.createElement("span");
    label.className = "row-select";
    label.textContent = "Select";
    action.append(label);
    row.append(action);
    row.dataset.port = port.id;
    row.tabIndex = 0;
    row.setAttribute("role", "button");
    row.setAttribute("aria-label", `Load ${port.name || port.device} connection profile`);
    row.addEventListener("click", () => selectPortProfile(port.id, true));
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectPortProfile(port.id, true);
      }
    });
    body.append(row);
    }
  }
  const desired = state.currentHardwareId || ports.find((port) => port.kind === "usb_network")?.id || ports.find((port) => port.is_esp32)?.id || ports[0]?.id;
  if (desired && ports.some((port) => port.id === desired)) {
    selectPortProfile(desired);
  }
  logEvent("host", `${ports.length} selectable interface${ports.length === 1 ? "" : "s"} detected.`, "ok");
  } finally {
    endOperation();
  }
}

function appendCells(row, values) {
  for (const value of values) {
    const cell = document.createElement("td");
    if (value instanceof Node) cell.append(value);
    else cell.textContent = value;
    row.append(cell);
  }
}

async function loadDiagnostics() {
  beginOperation("Refreshing passive host, USB, tool, and provider inventory...");
  try {
  const message = byId("diagnostics-message");
  message.textContent = "Refreshing passive USB, host, and tool inventory...";
  const fetchJson = async (path) => {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`${path} returned ${response.status}`);
    return response.json();
  };
  const [usbResult, hostResult, toolsResult, providersResult] = await Promise.allSettled([
    fetchJson("/api/inventory/usb"),
    fetchJson("/api/inventory/host"),
    fetchJson("/api/tools"),
    fetchJson("/api/metadata/providers"),
  ]);
  const usb = usbResult.status === "fulfilled" ? usbResult.value : { count: 0, devices: [] };
  const host = hostResult.status === "fulfilled" ? hostResult.value : { hostname: "this host", interfaces: [] };
  const registry = toolsResult.status === "fulfilled" ? toolsResult.value : { available_count: 0, tools: [], risk_levels: {} };
  const providerRegistry = providersResult.status === "fulfilled" ? providersResult.value : { available_count: 0, providers: [] };

  const usbBody = byId("usb-inventory-body");
  usbBody.replaceChildren();
  const visibleUsb = usb.devices.filter((device) => device.classification !== "usb_hub");
  byId("usb-inventory-summary").textContent = `${visibleUsb.length} physical USB devices shown; inspectable circuit targets are labeled separately`;
  for (const device of visibleUsb) {
    const row = document.createElement("tr");
    appendCells(row, [device.name, device.usb_identity, (device.classification || device.pnp_class || device.class_name).replaceAll("_", " "), `${device.bus}:${device.address}`]);
    usbBody.append(row);
  }
  if (!visibleUsb.length) {
    const row = document.createElement("tr");
    appendCells(row, ["No physical USB identities detected", "--", "--", "--"]);
    usbBody.append(row);
  }

  const hostBody = byId("host-inventory-body");
  hostBody.replaceChildren();
  const activeInterfaces = host.interfaces.filter((networkInterface) => networkInterface.up);
  byId("host-inventory-summary").textContent = `${activeInterfaces.length} active of ${host.interfaces.length} host interfaces`;
  for (const networkInterface of activeInterfaces) {
    const addresses = document.createElement("span");
    addresses.className = "inventory-addresses";
    addresses.textContent = networkInterface.addresses.filter((address) => address.family !== "MAC").map((address) => address.address).join(", ") || "No IP address";
    const row = document.createElement("tr");
    appendCells(row, [networkInterface.name, "Active", networkInterface.speed_mbps ? `${networkInterface.speed_mbps} Mbps` : "Unknown", addresses]);
    hostBody.append(row);
  }

  const toolBody = byId("tool-registry-body");
  toolBody.replaceChildren();
  byId("tool-summary").textContent = `${registry.available_count} of ${registry.tools.length} registered tools available`;
  for (const tool of registry.tools) {
    const risk = document.createElement("span");
    risk.className = `risk-${tool.risk}`;
    risk.textContent = tool.risk;
    risk.title = registry.risk_levels[tool.risk];
    const row = document.createElement("tr");
    appendCells(row, [tool.name, tool.category, risk, tool.available ? tool.version || "Available" : "Not installed"]);
    toolBody.append(row);
  }

  const providerGrid = byId("metadata-providers");
  providerGrid.replaceChildren();
  byId("provider-summary").textContent = `${providerRegistry.available_count} of ${providerRegistry.providers.length} sources ready`;
  for (const provider of providerRegistry.providers) {
    const card = document.createElement("article");
    card.className = `provider-card ${provider.available ? "available" : ""}`.trim();
    const heading = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = provider.name;
    heading.append(name, createStatusLabel(provider.available ? "verified" : "unavailable"));
    const purpose = document.createElement("small");
    purpose.textContent = provider.scope;
    const status = document.createElement("small");
    status.textContent = `${provider.mode} | ${provider.available ? "ready" : provider.requires_key ? "API credentials not configured" : "unavailable"}`;
    card.append(heading, purpose, status);
    providerGrid.append(card);
  }
  const failed = [usbResult, hostResult, toolsResult, providersResult].filter((result) => result.status === "rejected").length;
  message.textContent = failed
    ? `Host inventory loaded with ${failed} unavailable provider${failed === 1 ? "" : "s"}. Working sections remain usable.`
    : `Passive inventory refreshed for ${host.hostname}. No target interfaces were claimed or changed.`;
  logEvent("host", message.textContent, failed ? "error" : "ok");
  } finally {
    endOperation();
  }
}

async function scanLocalServices() {
  const button = byId("service-scan");
  button.disabled = true;
  beginOperation("Listening for local service advertisements...");
  byId("service-summary").textContent = "Listening for local service advertisements...";
  try {
    const response = await fetch("/api/discovery/services", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timeout_seconds: 2.5 }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Service scan failed");
    const list = byId("service-results");
    list.replaceChildren();
    byId("service-summary").textContent = `${result.count} HTTP, SSH, camera, or MQTT services advertised`;
    if (!result.services.length) {
      const empty = document.createElement("p");
      empty.textContent = "No matching local services advertised during this scan";
      list.append(empty);
    }
    for (const service of result.services) {
      const type = service.type.toLowerCase();
      const scheme = type.includes("_https") ? "https" : type.includes("_http") ? "http" : null;
      const host = service.addresses[0] || service.server.replace(/\.$/, "");
      let row;
      if (scheme && host) {
        const defaultPort = (scheme === "http" && service.port === 80) || (scheme === "https" && service.port === 443);
        row = document.createElement("a");
        row.className = "resource-row service-resource";
        row.href = `${scheme}://${host}${defaultPort ? "" : `:${service.port}`}`;
        row.target = "_blank";
        row.rel = "noreferrer";
        const title = document.createElement("strong");
        const detail = document.createElement("small");
        title.textContent = service.name;
        detail.textContent = `${service.type} | ${host} | port ${service.port}`;
        row.append(title, detail);
      } else {
        row = createDiscoveryRow("monitor-smartphone", service.name, `${service.type} | ${service.addresses.join(", ") || service.server} | port ${service.port}`, "Advertised");
      }
      list.append(row);
    }
    logEvent("network", `${result.count} advertised local service${result.count === 1 ? "" : "s"} found.`, "ok");
  } catch (error) {
    byId("service-summary").textContent = error.message;
    logEvent("network", error.message, "error");
  } finally {
    button.disabled = false;
    endOperation();
  }
}

function renderNetworkDiscovery(result) {
  byId("network-discovery-summary").textContent = `${result.count} device${result.count === 1 ? "" : "s"} found | ${result.mode}`;
  const list = byId("network-discovery-results");
  list.replaceChildren();
  if (!result.devices.length) {
    fillEmpty(list, "No responding or cached devices found inside the allowed private-network scope.");
    return;
  }
  for (const device of result.devices) {
    const card = document.createElement("article");
    card.className = "network-device";
    const identity = document.createElement("div");
    const address = document.createElement("strong");
    const detail = document.createElement("small");
    address.textContent = device.address;
    detail.textContent = `${device.mac_address || "MAC unavailable"} | ${device.source}`;
    identity.append(address, detail);
    const services = document.createElement("div");
    services.className = "network-services";
    for (const service of device.services) {
      const item = document.createElement(service.url ? "a" : "span");
      item.textContent = `${service.name} :${service.port}`;
      if (service.url) {
        item.href = service.url;
        item.target = "_blank";
        item.rel = "noreferrer";
        item.title = `Open ${service.url}`;
      }
      services.append(item);
    }
    if (!device.services.length) {
      const cached = document.createElement("span");
      cached.textContent = "Seen in local neighbor cache";
      services.append(cached);
    }
    card.append(identity, services);
    list.append(card);
  }
}

async function scanNetwork(mode) {
  if (mode === "deep" && !window.confirm("Deep discovery checks a fixed list of TCP service ports on private local /24 networks. It sends connection attempts but no application data. Continue?")) return;
  const buttons = [byId("network-scan"), byId("network-deep-scan")];
  buttons.forEach((button) => { button.disabled = true; });
  beginOperation(`${mode === "deep" ? "Deep" : "Standard"} private-network discovery started...`);
  try {
    const response = await fetch("/api/discovery/network", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode, target: byId("network-target").value.trim() || null }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Network discovery failed");
    renderNetworkDiscovery(result);
    logEvent("network", `Found ${result.count} device(s) across ${result.scope.join(", ") || "no eligible private subnet"}.`, "ok");
  } catch (error) {
    byId("network-discovery-summary").textContent = error.message;
    logEvent("network", error.message, "error");
  } finally {
    buttons.forEach((button) => { button.disabled = false; });
    endOperation();
  }
}

function selectPortProfile(device, announce = false) {
  const port = state.ports.find((item) => item.id === device);
  if (!port) return;
  if (state.selectedHardware?.id !== port.id) state.testResults = {};
  state.selectedHardware = port;
  byId("port-select").value = device;
  byId("profile-name").textContent = `${port.device || port.interface || port.ip_address || port.id} | ${port.name || port.description}`;
  byId("profile-transport").textContent = port.kind === "usb_network" ? `${port.transport} via ${port.interface}` : port.is_esp32 ? "USB serial + camera" : port.transport || "USB serial";
  byId("profile-usb").textContent = `${port.vid || "----"}:${port.pid || "----"}`;
  byId("profile-role").textContent = (port.classification || (port.is_lichee ? "Linux single-board computer" : port.is_esp32 ? "Microcontroller board" : "Unclassified device")).replaceAll("_", " ");
  byId("port-connect").querySelector("span").textContent = "Inspect IoT device";
  byId("network-device-services").hidden = true;
  document.querySelectorAll("#ports-body tr").forEach((row) => {
    const selected = row.dataset.port === device;
    row.classList.toggle("selected", selected);
    row.setAttribute("aria-selected", String(selected));
    const label = row.querySelector(".row-select");
    if (label) label.textContent = selected ? "Selected" : "Select";
  });
  if (announce) byId("port-message").textContent = `${port.name || port.device} selected. Press Inspect to collect device-specific evidence.`;
  const consoleCompatible = port.kind === "usb_network" && port.is_lichee;
  byId("console-command").disabled = !consoleCompatible;
  byId("console-run").disabled = !consoleCompatible;
  byId("console-note").textContent = consoleCompatible
    ? `Read-only target diagnostics are available at ${port.ip_address}.`
    : "This interface has no compatible authenticated operating-system adapter. Bench events remain available.";
}

async function connectSelectedPort() {
  const button = byId("port-connect");
  const message = byId("port-message");
  const identifier = byId("port-select").value;
  const profile = state.ports.find((item) => item.id === identifier);
  button.disabled = true;
  beginOperation(`Inspecting ${profile?.name || identifier} without changing firmware...`);
  message.textContent = `Inspecting ${profile?.name || identifier} without changing its firmware...`;
  try {
    const response = await fetch("/api/hardware/select", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ identifier }) });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Port connection failed");
    state.currentHardwareId = identifier;
    state.selectedHardware = body.hardware;
    if (profile?.kind === "usb_network") {
      state.networkProbe = body.hardware;
      const services = body.hardware.services || {};
      const camera = body.hardware.telemetry?.camera_status || "Camera status unavailable";
      message.textContent = body.confirmed ? `${body.hardware.name} verified at ${body.hardware.ip_address}. ${camera}.` : body.error;
      byId("network-device-services").hidden = false;
      byId("network-service-status").textContent = `SSH ${services.ssh ? "online" : "offline"} | Web UI ${services.web ? "online" : "offline"}`;
      byId("network-web-link").href = body.hardware.web_url || "#";
      render({ connected: false, telemetry: {}, ble: {}, bridge_uptime_seconds: 0 });
    } else {
      state.networkProbe = null;
      state.currentPort = body.hardware.device;
      state.savedPort = body.hardware.device;
      message.textContent = body.confirmed
        ? `${body.hardware.device} protocol verified and saved.`
        : `${body.hardware.device} identified from host and provider evidence. No serial protocol was opened.`;
      if (body.hardware.is_esp32) reconnectCamera();
      const statusResponse = await fetch("/api/status", { cache: "no-store" });
      if (statusResponse.ok) render(await statusResponse.json());
    }
    await loadDeviceInspection(identifier);
    switchWorkspace("device");
    logEvent("device", message.textContent, body.confirmed ? "ok" : "");
  } catch (error) {
    message.textContent = error.message;
    logEvent("device", error.message, "error");
  } finally {
    button.disabled = false;
    endOperation();
  }
}

async function scanBle() {
  const button = byId("rescan-button");
  button.disabled = true;
  setProgress("ble-progress", true);
  byId("ble-command-status").textContent = "Scanning from this computer for nearby BLE advertisements...";
  try {
    const response = await fetch("/api/ble/scan", { method: "POST" });
    const body = await response.json();
    byId("ble-command-status").textContent = body.detected ? `${body.name} received at ${body.rssi_dbm} dBm.` : `${(body.devices || []).length} nearby devices found; the selected device's BLE advertisement was not received.`;
  } catch (error) {
    byId("ble-command-status").textContent = error.message;
  } finally {
    button.disabled = false;
    setProgress("ble-progress", false);
  }
}

async function verifyBle() {
  const button = byId("ble-connect");
  button.disabled = true;
  setProgress("ble-progress", true);
  byId("ble-command-status").textContent = "Opening the selected IoT Bench GATT service and reading status...";
  try {
    const response = await fetch("/api/ble/connect", { method: "POST" });
    const body = await response.json();
    byId("ble-command-status").textContent = body.verified ? `GATT data exchange verified with ${body.address}; profile saved.` : body.error || "Connection failed.";
    if (body.verified) await loadPorts();
  } finally {
    button.disabled = false;
    setProgress("ble-progress", false);
  }
}

async function setRadioPower(endpoint, button, enabled, message) {
  button.disabled = true;
  message.textContent = `${enabled ? "Enabling" : "Disabling"} radio...`;
  try {
    const response = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled }) });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Device command failed");
    message.textContent = body.confirmed ? `Radio ${enabled ? "enabled" : "disabled"} and confirmed.` : "Command sent but not confirmed.";
    const statusResponse = await fetch("/api/status", { cache: "no-store" });
    if (statusResponse.ok) render(await statusResponse.json());
  } catch (error) {
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function scanEspWifi() {
  const button = byId("wifi-refresh");
  button.disabled = true;
  setProgress("wifi-progress", true);
  byId("wifi-rssi").textContent = "Selected device is scanning its supported 2.4 GHz channels...";
  try {
    const response = await fetch("/api/wifi/scan", { method: "POST" });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Wi-Fi scan failed");
    renderWifiNetworks(body.networks || []);
    byId("wifi-rssi").textContent = body.networks.length ? `${body.networks.length} compatible 2.4 GHz signals found by the selected device.` : "Scan completed; the selected device received no 2.4 GHz signals.";
  } catch (error) {
    byId("wifi-rssi").textContent = error.message;
  } finally {
    button.disabled = false;
    setProgress("wifi-progress", false);
  }
}

async function scanHostWifi() {
  const button = byId("host-wifi-refresh");
  button.disabled = true;
  byId("host-wifi-capability").textContent = "Scanning computer radio...";
  try {
    const response = await fetch("/api/host/wifi/scan", { method: "POST" });
    renderHostWifi(await response.json());
  } catch (error) {
    renderHostWifi({ available: false, networks: [], error: error.message });
  } finally {
    button.disabled = false;
  }
}

function togglePassword(inputId, buttonId) {
  const input = byId(inputId);
  const button = byId(buttonId);
  const reveal = input.type === "password";
  input.type = reveal ? "text" : "password";
  button.setAttribute("aria-pressed", String(reveal));
  button.setAttribute("aria-label", reveal ? "Hide password" : "Show password");
  button.title = reveal ? "Hide password" : "Show password";
  button.querySelector("img").src = reveal ? "/icons/eye-off.svg" : "/icons/eye.svg";
}

function openAccessDialog() {
  byId("access-name").value = state.telemetry.device || "";
  byId("access-password").value = "";
  byId("access-message").textContent = "";
  byId("access-dialog").showModal();
}

document.querySelectorAll("[data-radio-tab]").forEach((button) => button.addEventListener("click", () => {
  const radio = button.dataset.radioTab;
  document.querySelectorAll("[data-radio-tab]").forEach((item) => {
    const selected = item === button;
    item.classList.toggle("active", selected);
    item.setAttribute("aria-selected", String(selected));
  });
  byId("ble-panel").hidden = radio !== "ble";
  byId("wifi-panel").hidden = radio !== "wifi";
  byId("active-radio-label").textContent = radio === "ble" ? "Bluetooth (BLE)" : "Wi-Fi";
}));

document.querySelectorAll("[data-mode-group]").forEach((button) => button.addEventListener("click", () => {
  const group = button.dataset.modeGroup;
  const mode = button.dataset.mode;
  document.querySelectorAll(`[data-mode-group="${group}"]`).forEach((item) => item.classList.toggle("active", item === button));
  byId(`${group}-access`).hidden = mode !== "access";
  byId(`${group}-nearby`).hidden = mode !== "nearby";
  if (group === "wifi" && mode === "nearby") {
    scanEspWifi();
    scanHostWifi();
  }
}));

byId("camera-refresh").addEventListener("click", () => reconnectCamera(true));
byId("pins-refresh").addEventListener("click", async () => {
  const button = byId("pins-refresh");
  button.disabled = true;
  try {
    await loadDeviceInspection();
  } catch (error) {
    byId("pins-message").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
byId("runtime-probe").addEventListener("click", () => state.pinProbeIds.deep && runPinProbe(state.pinProbeIds.deep));
byId("i2c-probe").addEventListener("click", () => state.pinProbeIds.bus && runPinProbe(state.pinProbeIds.bus));
document.querySelectorAll("[data-workspace-tab]").forEach((button) => button.addEventListener("click", () => switchWorkspace(button.dataset.workspaceTab)));
byId("firmware-refresh").addEventListener("click", loadFirmwareWorkspace);
byId("firmware-file-content").addEventListener("input", (event) => {
  byId("firmware-save").disabled = !state.firmwareFile || event.target.value === state.firmwareOriginalContent;
});
byId("firmware-save").addEventListener("click", saveFirmwareFile);
byId("tests-refresh").addEventListener("click", async () => {
  const button = byId("tests-refresh");
  button.disabled = true;
  try {
    await loadDeviceInspection();
  } catch (error) {
    logEvent("device", `Test availability refresh failed: ${error.message}`, "error");
  } finally {
    button.disabled = false;
  }
});
byId("port-select").addEventListener("change", (event) => selectPortProfile(event.target.value));
byId("port-connect").addEventListener("click", connectSelectedPort);
byId("device-inspect-refresh").addEventListener("click", async () => {
  const button = byId("device-inspect-refresh");
  button.disabled = true;
  try {
    await loadDeviceInspection();
  } catch (error) {
    byId("intelligence-message").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
byId("device-model-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = event.submitter;
  submit.disabled = true;
  try {
    const response = await fetch("/api/device/model", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: state.selectedHardware.id, model: byId("device-model-select").value }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Model selection failed");
    await loadDeviceInspection();
    byId("intelligence-message").textContent = `${result.model} saved for this physical interface. Sensor entries remain expected until tested.`;
  } catch (error) {
    byId("intelligence-message").textContent = error.message;
  } finally {
    submit.disabled = false;
  }
});
byId("hardware-refresh").addEventListener("click", async () => {
  const button = byId("hardware-refresh");
  button.disabled = true;
  byId("port-message").textContent = "Scanning USB serial and network devices...";
  try {
    await loadPorts();
    byId("port-message").textContent = `${state.ports.length} hardware interface${state.ports.length === 1 ? "" : "s"} detected.`;
  } catch (error) {
    byId("port-message").textContent = `Hardware scan failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
});
byId("diagnostics-refresh").addEventListener("click", async () => {
  const button = byId("diagnostics-refresh");
  button.disabled = true;
  try {
    await loadDiagnostics();
  } catch (error) {
    byId("diagnostics-message").textContent = `Passive inventory failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
});
byId("tools-refresh").addEventListener("click", async () => {
  const button = byId("tools-refresh");
  button.disabled = true;
  try {
    await loadDiagnostics();
  } catch (error) {
    byId("diagnostics-message").textContent = `Tool refresh failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
});
byId("service-scan").addEventListener("click", scanLocalServices);
byId("rescan-button").addEventListener("click", scanBle);
byId("ble-connect").addEventListener("click", verifyBle);
byId("ble-power").addEventListener("click", () => setRadioPower("/api/ble/power", byId("ble-power"), byId("ble-power").dataset.enabled !== "true", byId("ble-quality")));
byId("wifi-power").addEventListener("click", () => setRadioPower("/api/wifi/ap", byId("wifi-power"), byId("wifi-power").dataset.enabled !== "true", byId("wifi-command-status")));
byId("wifi-refresh").addEventListener("click", scanEspWifi);
byId("internet-test").addEventListener("click", async () => {
  const button = byId("internet-test");
  button.disabled = true;
  byId("internet-test-message").textContent = "Sending test traffic from the selected device...";
  try {
    const response = await fetch("/api/wifi/internet-test", { method: "POST" });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Internet test failed");
    byId("internet-test-message").textContent = body.reachable
      ? `Internet verified in ${body.latency_ms} ms; ${formatBytes(body.bytes_sent)} sent and ${formatBytes(body.bytes_received)} received.`
      : `Internet test failed: ${(body.status || "unknown").replaceAll("_", " ")}.`;
  } catch (error) {
    byId("internet-test-message").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
byId("host-wifi-refresh").addEventListener("click", scanHostWifi);
byId("network-scan").addEventListener("click", () => scanNetwork("standard"));
byId("network-deep-scan").addEventListener("click", () => scanNetwork("deep"));
byId("wifi-hidden").addEventListener("click", () => selectWifiNetwork({ ssid: "", rssi_dbm: 0, channel: 0, secure: true }));
byId("wifi-cancel").addEventListener("click", () => { byId("wifi-form").hidden = true; });
byId("password-toggle").addEventListener("click", () => togglePassword("wifi-password", "password-toggle"));
byId("access-password-toggle").addEventListener("click", () => togglePassword("access-password", "access-password-toggle"));
byId("ble-settings").addEventListener("click", openAccessDialog);
byId("wifi-toggle").addEventListener("click", openAccessDialog);
byId("access-close").addEventListener("click", () => byId("access-dialog").close());
byId("access-cancel").addEventListener("click", () => byId("access-dialog").close());
byId("console-toggle").addEventListener("click", () => {
  const body = byId("console-body");
  body.hidden = !body.hidden;
  byId("diagnostic-console").classList.toggle("open", !body.hidden);
});
byId("console-clear").addEventListener("click", () => {
  state.consoleEvents = [];
  byId("console-event-count").textContent = "0 events";
  byId("console-output").replaceChildren(Object.assign(document.createElement("p"), { textContent: "No bench events yet." }));
});
byId("console-run").addEventListener("click", async () => {
  const button = byId("console-run");
  if (!state.selectedHardware) return;
  button.disabled = true;
  beginOperation(`Running ${byId("console-command").selectedOptions[0].textContent} on ${state.selectedHardware.ip_address || state.selectedHardware.device}...`);
  try {
    const response = await fetch("/api/device/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: state.selectedHardware.id, command_id: byId("console-command").value }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Target diagnostic failed");
    logEvent("target", `${result.label} @ ${result.target}\n${result.output}`, "ok");
  } catch (error) {
    logEvent("target", error.message, "error");
  } finally {
    button.disabled = false;
    endOperation();
  }
});

byId("access-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = event.submitter;
  submit.disabled = true;
  byId("access-message").textContent = "Applying and restarting BLE/Wi-Fi broadcasts...";
  try {
    const newPassword = byId("access-password").value;
    const response = await fetch("/api/device/access", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: byId("access-name").value, password: newPassword }) });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Settings update failed");
    byId("access-message").textContent = body.confirmed ? `${body.name} confirmed; ${newPassword ? "password updated" : "current password kept"}.` : "Settings sent but not confirmed.";
    if (body.confirmed) setTimeout(() => byId("access-dialog").close(), 650);
  } catch (error) {
    byId("access-message").textContent = error.message;
  } finally {
    submit.disabled = false;
  }
});

byId("wifi-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = byId("wifi-connect");
  const ssid = byId("wifi-ssid").value;
  button.disabled = true;
  setProgress("wifi-progress", true);
  byId("wifi-message").textContent = `Sending credentials over ${state.currentPort || "USB"} and waiting for an address...`;
  try {
    const response = await fetch("/api/wifi", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ssid, password: byId("wifi-password").value, remember: byId("wifi-remember").checked }) });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Connection failed");
    byId("wifi-rssi").textContent = body.connected ? `${body.ssid} connected at ${body.ip}.` : `${body.ssid} failed: ${(body.status || "timed out").replaceAll("_", " ")}.`;
    byId("wifi-form").hidden = true;
    byId("wifi-password").value = "";
    if (body.connected) await loadPorts();
  } catch (error) {
    byId("wifi-message").textContent = error.message;
  } finally {
    button.disabled = false;
    setProgress("wifi-progress", false);
  }
});

function connectWebSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${location.host}/ws`);
  socket.addEventListener("message", (event) => render(JSON.parse(event.data)));
  socket.addEventListener("close", () => setTimeout(connectWebSocket, 1500));
}

loadPorts()
  .then(() => state.selectedHardware?.id ? loadDeviceInspection() : null)
  .catch((error) => logEvent("device", `Initial inspection failed: ${error.message}`, "error"));
loadDiagnostics().catch((error) => { byId("diagnostics-message").textContent = error.message; });
scanHostWifi();
setInterval(() => loadPorts().catch(() => {}), 30000);
connectWebSocket();
