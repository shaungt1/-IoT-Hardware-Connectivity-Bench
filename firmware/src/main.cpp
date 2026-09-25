#include <Arduino.h>
#include <NimBLEDevice.h>
#include <Preferences.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <esp_http_server.h>
#include <esp_timer.h>

#include "camera_pins.h"

namespace {

constexpr char kFirmwareVersion[] = "iot-bench-0.6.1";
constexpr char kBoardId[] = "seeed_xiao_esp32s3_sense";
constexpr char kBoardModel[] = "Seeed Studio XIAO ESP32-S3 Sense";
constexpr char kMcuModel[] = "Espressif ESP32-S3R8";
constexpr char kPinMapVersion[] = "seeed-xiao-esp32s3-sense-v1";
constexpr char kBleServiceUuid[] = "8f7a0001-6e7d-4a44-9f9d-10a1b2c3d401";
constexpr char kBleStatusUuid[] = "8f7a0002-6e7d-4a44-9f9d-10a1b2c3d401";
constexpr char kPreferencesNamespace[] = "iot-bench";
constexpr uint32_t kTelemetryIntervalMs = 1000;
constexpr uint32_t kFrameIntervalMs = 25;
constexpr uint8_t kPacketTelemetry = 1;
constexpr uint8_t kPacketJpeg = 2;
constexpr uint8_t kPacketMagic[] = {'I', 'O', 'T', 'B'};

Preferences preferences;
NimBLECharacteristic* statusCharacteristic = nullptr;
NimBLEServer* bleServer = nullptr;
NimBLEAdvertising* bleAdvertisingController = nullptr;
SemaphoreHandle_t cameraMutex = nullptr;
httpd_handle_t cameraServer = nullptr;

String deviceName;
String apName;
String apPassword;
String commandBuffer;
bool cameraReady = false;
bool usbStreamEnabled = false;
bool bleAdvertising = false;
bool bleAdvertisementConfigured = false;
String bleAdvertisementError;
bool wifiApActive = false;
String stationTargetSsid;
String wifiNetworks = "[]";
String wifiScanError;
uint32_t wifiScanId = 0;
uint32_t wifiJoinId = 0;
uint32_t packetSequence = 0;
uint32_t frameSequence = 0;
uint32_t lastTelemetryAt = 0;
uint32_t lastFrameAt = 0;
uint32_t fpsWindowAt = 0;
uint32_t fpsWindowFrames = 0;
float measuredFps = 0.0f;
int8_t cameraBrightness = 0;
int8_t cameraContrast = 0;
int8_t cameraSaturation = 0;
int8_t cameraSharpness = 0;
int8_t cameraAeLevel = 0;
uint8_t cameraJpegQuality = 12;
uint32_t bleConnectionsTotal = 0;
uint32_t bleLastConnectionAt = 0;
bool internetReachable = false;
String internetProbeStatus = "not_tested";
uint32_t internetProbeId = 0;
uint32_t internetProbeLatencyMs = 0;
uint32_t internetLastProbeAt = 0;
uint32_t internetTestsSuccessful = 0;
uint64_t internetBytesSent = 0;
uint64_t internetBytesReceived = 0;
uint32_t controlSequence = 0;
String controlLastAction;
String controlLastPin;
String controlLastError;
int32_t controlLastValue = 0;
bool controlLastOk = false;

const IPAddress kAccessPointIp(192, 168, 91, 1);
const IPAddress kAccessPointSubnet(255, 255, 255, 0);

class BleServerCallbacks final : public NimBLEServerCallbacks {
 public:
  void onConnect(NimBLEServer*, NimBLEConnInfo&) override {
    bleAdvertising = false;
    bleConnectionsTotal++;
    bleLastConnectionAt = millis();
  }

  void onDisconnect(NimBLEServer*, NimBLEConnInfo&, int) override {
    bleAdvertising = true;
  }
};

BleServerCallbacks bleServerCallbacks;

void sendPacket(uint8_t type, const uint8_t* payload, uint32_t length) {
  Serial.write(kPacketMagic, sizeof(kPacketMagic));
  Serial.write(type);
  Serial.write(reinterpret_cast<const uint8_t*>(&length), sizeof(length));
  const uint32_t sequence = packetSequence++;
  Serial.write(reinterpret_cast<const uint8_t*>(&sequence), sizeof(sequence));
  if (length > 0) {
    Serial.write(payload, length);
  }
}

String jsonEscape(const String& input) {
  String result;
  result.reserve(input.length() + 8);
  for (const char character : input) {
    if (character == '\\' || character == '"') {
      result += '\\';
    }
    result += character;
  }
  return result;
}

const char* wifiStatusName(wl_status_t status) {
  switch (status) {
    case WL_IDLE_STATUS:
      return "connecting";
    case WL_NO_SSID_AVAIL:
      return "network_not_found";
    case WL_SCAN_COMPLETED:
      return "scan_complete";
    case WL_CONNECTED:
      return "connected";
    case WL_CONNECT_FAILED:
      return "connection_failed";
    case WL_CONNECTION_LOST:
      return "connection_lost";
    case WL_DISCONNECTED:
      return stationTargetSsid.isEmpty() ? "not_configured" : "disconnected";
    default:
      return "unknown";
  }
}

String makeTelemetry() {
  if (bleAdvertisingController != nullptr) {
    bleAdvertising = bleAdvertisingController->isAdvertising();
  }
  const bool stationConnected = WiFi.status() == WL_CONNECTED;
  const int32_t wifiRssi = stationConnected ? WiFi.RSSI() : 0;
  const String stationIp = stationConnected ? WiFi.localIP().toString() : "";
  const String gatewayIp = stationConnected ? WiFi.gatewayIP().toString() : "";
  const String dnsIp = stationConnected ? WiFi.dnsIP().toString() : "";
  const String stationSsid = stationConnected ? WiFi.SSID() : stationTargetSsid;
  const int8_t cameraSensorPid = cameraReady && esp_camera_sensor_get()
      ? static_cast<int8_t>(esp_camera_sensor_get()->id.PID)
      : -1;
  const uint8_t bleClientCount = bleServer == nullptr ? 0 : bleServer->getConnectedCount();

  String json = "{";
  json += "\"device\":\"" + jsonEscape(deviceName) + "\",";
  json += "\"board_id\":\"" + String(kBoardId) + "\",";
  json += "\"board_model\":\"" + String(kBoardModel) + "\",";
  json += "\"mcu\":\"" + String(kMcuModel) + "\",";
  json += "\"architecture\":\"Xtensa LX7 dual-core\",";
  json += "\"pin_map_version\":\"" + String(kPinMapVersion) + "\",";
  json += "\"control_protocol\":\"iot-bench-control/1\",";
  json += "\"control_capabilities\":[\"gpio_read\",\"gpio_write\",\"adc_read\"],";
  json += "\"control_sequence\":" + String(controlSequence) + ",";
  json += "\"control_last_action\":\"" + jsonEscape(controlLastAction) + "\",";
  json += "\"control_last_pin\":\"" + jsonEscape(controlLastPin) + "\",";
  json += "\"control_last_value\":" + String(controlLastValue) + ",";
  json += "\"control_last_ok\":" + String(controlLastOk ? "true" : "false") + ",";
  json += "\"control_last_error\":\"" + jsonEscape(controlLastError) + "\",";
  json += "\"firmware\":\"" + String(kFirmwareVersion) + "\",";
  json += "\"uptime_ms\":" + String(millis()) + ",";
  json += "\"free_heap_bytes\":" + String(ESP.getFreeHeap()) + ",";
  json += "\"psram_bytes\":" + String(ESP.getPsramSize()) + ",";
  json += "\"camera_ready\":" + String(cameraReady ? "true" : "false") + ",";
  json += "\"camera_sensor_pid\":" + String(cameraSensorPid) + ",";
  json += "\"camera_fps\":" + String(measuredFps, 1) + ",";
  json += "\"camera_brightness\":" + String(cameraBrightness) + ",";
  json += "\"camera_contrast\":" + String(cameraContrast) + ",";
  json += "\"camera_saturation\":" + String(cameraSaturation) + ",";
  json += "\"camera_sharpness\":" + String(cameraSharpness) + ",";
  json += "\"camera_ae_level\":" + String(cameraAeLevel) + ",";
  json += "\"camera_jpeg_quality\":" + String(cameraJpegQuality) + ",";
  json += "\"frames_sent\":" + String(frameSequence) + ",";
  json += "\"usb_streaming\":" + String(usbStreamEnabled ? "true" : "false") + ",";
  json += "\"ble_advertising\":" + String(bleAdvertising ? "true" : "false") + ",";
  json += "\"ble_advertisement_configured\":" + String(bleAdvertisementConfigured ? "true" : "false") + ",";
  json += "\"ble_advertisement_error\":\"" + jsonEscape(bleAdvertisementError) + "\",";
  json += "\"ble_connected\":" + String(bleClientCount > 0 ? "true" : "false") + ",";
  json += "\"ble_client_count\":" + String(bleClientCount) + ",";
  json += "\"ble_connections_total\":" + String(bleConnectionsTotal) + ",";
  json += "\"ble_last_connection_ms\":" + String(bleLastConnectionAt) + ",";
  json += "\"ble_service_uuid\":\"" + String(kBleServiceUuid) + "\",";
  json += "\"ble_device_address\":\"" + String(NimBLEDevice::getAddress().toString().c_str()) + "\",";
  json += "\"wifi_ap_active\":" + String(wifiApActive ? "true" : "false") + ",";
  json += "\"wifi_ap_configured\":" + String(apPassword.length() >= 8 ? "true" : "false") + ",";
  json += "\"wifi_ap_ssid\":\"" + jsonEscape(apName) + "\",";
  json += "\"wifi_ap_ip\":\"" + String(wifiApActive ? WiFi.softAPIP().toString() : "") + "\",";
  json += "\"wifi_ap_clients\":" + String(wifiApActive ? WiFi.softAPgetStationNum() : 0) + ",";
  json += "\"wifi_station_connected\":" + String(stationConnected ? "true" : "false") + ",";
  json += "\"wifi_station_status\":\"" + String(wifiStatusName(WiFi.status())) + "\",";
  json += "\"wifi_station_ssid\":\"" + jsonEscape(stationSsid) + "\",";
  json += "\"wifi_station_ip\":\"" + stationIp + "\",";
  json += "\"wifi_gateway_ip\":\"" + gatewayIp + "\",";
  json += "\"wifi_dns_ip\":\"" + dnsIp + "\",";
  json += "\"wifi_rssi_dbm\":" + String(stationConnected ? wifiRssi : 0) + ",";
  json += "\"wifi_join_id\":" + String(wifiJoinId) + ",";
  json += "\"wifi_scan_id\":" + String(wifiScanId) + ",";
  json += "\"wifi_scan_error\":\"" + jsonEscape(wifiScanError) + "\",";
  json += "\"internet_reachable\":" + String(internetReachable ? "true" : "false") + ",";
  json += "\"internet_probe_status\":\"" + jsonEscape(internetProbeStatus) + "\",";
  json += "\"internet_probe_id\":" + String(internetProbeId) + ",";
  json += "\"internet_probe_latency_ms\":" + String(internetProbeLatencyMs) + ",";
  json += "\"internet_last_probe_ms\":" + String(internetLastProbeAt) + ",";
  json += "\"internet_tests_successful\":" + String(internetTestsSuccessful) + ",";
  json += "\"internet_bytes_sent\":" + String(internetBytesSent) + ",";
  json += "\"internet_bytes_received\":" + String(internetBytesReceived) + ",";
  json += "\"wifi_networks\":" + wifiNetworks;
  json += "}";
  return json;
}

void publishTelemetry() {
  const String payload = makeTelemetry();
  sendPacket(kPacketTelemetry, reinterpret_cast<const uint8_t*>(payload.c_str()), payload.length());
  if (statusCharacteristic != nullptr) {
    statusCharacteristic->setValue(payload.c_str());
    statusCharacteristic->notify();
  }
}

int8_t externalPin(const String& name) {
  static constexpr int8_t pins[] = {1, 2, 3, 4, 5, 6, 43, 44, 7, 8, 9};
  if (name.length() < 2 || name[0] != 'D') {
    return -1;
  }
  const int index = name.substring(1).toInt();
  return index >= 0 && index < 11 && name == String("D") + String(index) ? pins[index] : -1;
}

void finishControl(const String& action, const String& pin, bool ok, int32_t value, const String& error = "") {
  controlSequence++;
  controlLastAction = action;
  controlLastPin = pin;
  controlLastOk = ok;
  controlLastValue = value;
  controlLastError = error;
  publishTelemetry();
}

void processControlCommand(const String& command) {
  const int first = command.indexOf('\t');
  const int second = command.indexOf('\t', first + 1);
  const String action = first > 0 ? command.substring(0, first) : command;
  const String pinName = first > 0 ? (second > first ? command.substring(first + 1, second) : command.substring(first + 1)) : "";
  const int8_t pin = externalPin(pinName);
  if (pin < 0) {
    finishControl(action, pinName, false, 0, "Pin is not an exposed D0-D10 terminal");
    return;
  }
  if (action == "GPIO READ") {
    pinMode(pin, INPUT);
    finishControl(action, pinName, true, digitalRead(pin));
    return;
  }
  if (action == "ADC READ") {
    if (pinName != "D0" && pinName != "D1" && pinName != "D2" && pinName != "D3" && pinName != "D4" && pinName != "D5") {
      finishControl(action, pinName, false, 0, "ADC is available only on D0-D5");
      return;
    }
    pinMode(pin, INPUT);
    finishControl(action, pinName, true, analogRead(pin));
    return;
  }
  if (action == "GPIO WRITE" && second > first) {
    const String requested = command.substring(second + 1);
    if (requested != "0" && requested != "1") {
      finishControl(action, pinName, false, 0, "GPIO value must be 0 or 1");
      return;
    }
    const int value = requested == "1" ? HIGH : LOW;
    pinMode(pin, OUTPUT);
    digitalWrite(pin, value);
    finishControl(action, pinName, true, value == HIGH ? 1 : 0);
    return;
  }
  finishControl(action, pinName, false, 0, "Unsupported control command");
}

bool initCamera() {
  camera_config_t config{};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = psramFound() ? 3 : 1;
  config.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  config.grab_mode = CAMERA_GRAB_LATEST;

  if (esp_camera_init(&config) != ESP_OK) {
    return false;
  }

  sensor_t* sensor = esp_camera_sensor_get();
  if (sensor != nullptr) {
    sensor->set_framesize(sensor, FRAMESIZE_VGA);
    sensor->set_quality(sensor, cameraJpegQuality);
  }
  return true;
}

esp_err_t statusHandler(httpd_req_t* request) {
  const String payload = makeTelemetry();
  httpd_resp_set_type(request, "application/json");
  httpd_resp_set_hdr(request, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(request, payload.c_str(), payload.length());
}

esp_err_t captureHandler(httpd_req_t* request) {
  if (!cameraReady || xSemaphoreTake(cameraMutex, pdMS_TO_TICKS(1000)) != pdTRUE) {
    httpd_resp_set_status(request, "503 Service Unavailable");
    return httpd_resp_send(request, "Camera busy", HTTPD_RESP_USE_STRLEN);
  }
  camera_fb_t* frame = esp_camera_fb_get();
  if (frame == nullptr) {
    xSemaphoreGive(cameraMutex);
    return httpd_resp_send_err(request, HTTPD_500_INTERNAL_SERVER_ERROR, "Capture failed");
  }
  httpd_resp_set_type(request, "image/jpeg");
  httpd_resp_set_hdr(request, "Access-Control-Allow-Origin", "*");
  const esp_err_t result = httpd_resp_send(request, reinterpret_cast<const char*>(frame->buf), frame->len);
  esp_camera_fb_return(frame);
  xSemaphoreGive(cameraMutex);
  return result;
}

esp_err_t streamHandler(httpd_req_t* request) {
  static constexpr char kBoundary[] = "\r\n--iot-bench-frame\r\n";
  static constexpr char kHeader[] = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";
  httpd_resp_set_type(request, "multipart/x-mixed-replace;boundary=iot-bench-frame");
  httpd_resp_set_hdr(request, "Access-Control-Allow-Origin", "*");

  while (true) {
    if (xSemaphoreTake(cameraMutex, pdMS_TO_TICKS(1000)) != pdTRUE) {
      continue;
    }
    camera_fb_t* frame = esp_camera_fb_get();
    if (frame == nullptr) {
      xSemaphoreGive(cameraMutex);
      return ESP_FAIL;
    }
    char header[96];
    const size_t headerLength = snprintf(header, sizeof(header), kHeader, frame->len);
    esp_err_t result = httpd_resp_send_chunk(request, kBoundary, strlen(kBoundary));
    if (result == ESP_OK) {
      result = httpd_resp_send_chunk(request, header, headerLength);
    }
    if (result == ESP_OK) {
      result = httpd_resp_send_chunk(request, reinterpret_cast<const char*>(frame->buf), frame->len);
    }
    esp_camera_fb_return(frame);
    xSemaphoreGive(cameraMutex);
    if (result != ESP_OK) {
      return result;
    }
    frameSequence++;
    fpsWindowFrames++;
    taskYIELD();
  }
}

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.max_uri_handlers = 8;
  config.stack_size = 8192;
  if (httpd_start(&cameraServer, &config) != ESP_OK) {
    return;
  }
  const httpd_uri_t statusUri{.uri = "/status", .method = HTTP_GET, .handler = statusHandler, .user_ctx = nullptr};
  const httpd_uri_t captureUri{.uri = "/capture.jpg", .method = HTTP_GET, .handler = captureHandler, .user_ctx = nullptr};
  const httpd_uri_t streamUri{.uri = "/stream", .method = HTTP_GET, .handler = streamHandler, .user_ctx = nullptr};
  httpd_register_uri_handler(cameraServer, &statusUri);
  httpd_register_uri_handler(cameraServer, &captureUri);
  httpd_register_uri_handler(cameraServer, &streamUri);
}

void connectStoredWifi() {
  if (!preferences.begin(kPreferencesNamespace, false)) {
    return;
  }
  const String ssid = preferences.isKey("ssid") ? preferences.getString("ssid", "") : "";
  const String password = preferences.isKey("password") ? preferences.getString("password", "") : "";
  preferences.end();
  if (!ssid.isEmpty()) {
    stationTargetSsid = ssid;
    WiFi.begin(ssid.c_str(), password.c_str());
  }
}

void loadDeviceConfiguration(const String& defaultName) {
  deviceName = defaultName;
  apName = defaultName;
  apPassword = "";
  if (!preferences.begin(kPreferencesNamespace, false)) {
    return;
  }
  if (preferences.isKey("device_name")) {
    deviceName = preferences.getString("device_name", defaultName);
    apName = deviceName;
  }
  if (preferences.isKey("ap_password")) {
    const String storedPassword = preferences.getString("ap_password", "");
    if (storedPassword.length() >= 8) {
      apPassword = storedPassword;
    }
  }
  preferences.end();
}

void configureWifi(const String& ssid, const String& password, bool remember) {
  if (remember) {
    if (!preferences.begin(kPreferencesNamespace, false)) {
      return;
    }
    preferences.putString("ssid", ssid);
    preferences.putString("password", password);
    preferences.end();
  }
  stationTargetSsid = ssid;
  wifiJoinId++;
  WiFi.disconnect(false, false);
  delay(100);
  WiFi.begin(ssid.c_str(), password.c_str());
}

void scanWifiNetworks() {
  wifiScanError = "";
  const bool resumeStation = WiFi.status() != WL_CONNECTED && !stationTargetSsid.isEmpty();
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.disconnect(false, false);
    delay(250);
  }
  const int count = WiFi.scanNetworks(false, true);
  String networks = "[";
  if (count < 0) {
    wifiScanError = "scan_failed_" + String(count);
  } else {
    const int limit = min(count, 20);
    for (int index = 0; index < limit; index++) {
      if (index > 0) {
        networks += ',';
      }
      networks += "{\"ssid\":\"" + jsonEscape(WiFi.SSID(index)) + "\",";
      networks += "\"rssi_dbm\":" + String(WiFi.RSSI(index)) + ",";
      networks += "\"channel\":" + String(WiFi.channel(index)) + ",";
      networks += "\"secure\":" + String(WiFi.encryptionType(index) == WIFI_AUTH_OPEN ? "false" : "true") + "}";
    }
  }
  networks += ']';
  wifiNetworks = networks;
  wifiScanId++;
  WiFi.scanDelete();
  if (resumeStation) {
    WiFi.reconnect();
  }
}

void testInternetConnection() {
  internetProbeId++;
  internetLastProbeAt = millis();
  internetProbeLatencyMs = 0;
  internetReachable = false;
  if (WiFi.status() != WL_CONNECTED) {
    internetProbeStatus = "wifi_not_connected";
    return;
  }

  IPAddress resolvedAddress;
  const uint32_t startedAt = millis();
  if (!WiFi.hostByName("connectivitycheck.gstatic.com", resolvedAddress)) {
    internetProbeStatus = "dns_failed";
    internetProbeLatencyMs = millis() - startedAt;
    return;
  }

  WiFiClient client;
  if (!client.connect(resolvedAddress, 80, 4000)) {
    internetProbeStatus = "internet_host_unreachable";
    internetProbeLatencyMs = millis() - startedAt;
    return;
  }

  static constexpr char kRequest[] =
      "GET /generate_204 HTTP/1.1\r\n"
      "Host: connectivitycheck.gstatic.com\r\n"
      "Connection: close\r\n\r\n";
  internetBytesSent += client.write(reinterpret_cast<const uint8_t*>(kRequest), strlen(kRequest));

  String statusLine;
  uint32_t receivedThisProbe = 0;
  const uint32_t responseDeadline = millis() + 5000;
  while (millis() < responseDeadline && (client.connected() || client.available())) {
    while (client.available()) {
      const char character = static_cast<char>(client.read());
      receivedThisProbe++;
      if (statusLine.length() < 80 && character != '\r' && character != '\n') {
        statusLine += character;
      }
      if (character == '\n' && !statusLine.isEmpty()) {
        break;
      }
    }
    if (!statusLine.isEmpty()) {
      break;
    }
    delay(5);
  }
  client.stop();
  internetBytesReceived += receivedThisProbe;
  internetProbeLatencyMs = millis() - startedAt;
  internetReachable = statusLine.startsWith("HTTP/1.1 204") || statusLine.startsWith("HTTP/1.0 204");
  internetProbeStatus = internetReachable ? "verified" : (statusLine.isEmpty() ? "no_response" : "unexpected_response");
  if (internetReachable) {
    internetTestsSuccessful++;
  }
}

bool configureBleAdvertisement() {
  if (bleAdvertisingController == nullptr) {
    bleAdvertisementError = "BLE advertising controller unavailable";
    return false;
  }

  bleAdvertisingController->reset();
  bleAdvertisingController->enableScanResponse(true);
  bleAdvertisingController->setConnectableMode(BLE_GAP_CONN_MODE_UND);
  bleAdvertisingController->setDiscoverableMode(BLE_GAP_DISC_MODE_GEN);
  bleAdvertisingController->setMinInterval(0x20);
  bleAdvertisingController->setMaxInterval(0x40);

  NimBLEAdvertisementData advertisementData;
  NimBLEAdvertisementData scanResponseData;
  const bool flagsOk = advertisementData.setFlags(BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP);
  const bool serviceOk = advertisementData.addServiceUUID(kBleServiceUuid);
  const bool powerOk = advertisementData.addTxPower();
  const bool nameOk = scanResponseData.setName(deviceName.c_str());
  const bool advertisementOk = bleAdvertisingController->setAdvertisementData(advertisementData);
  const bool scanResponseOk = bleAdvertisingController->setScanResponseData(scanResponseData);
  bleAdvertisementConfigured = flagsOk && serviceOk && powerOk && nameOk && advertisementOk && scanResponseOk;
  bleAdvertisementError = bleAdvertisementConfigured ? "" : "BLE advertisement payload configuration failed";
  return bleAdvertisementConfigured;
}

void setBleAdvertising(bool enabled) {
  if (statusCharacteristic == nullptr || bleAdvertisingController == nullptr) {
    return;
  }
  if (enabled) {
    if (!bleAdvertisementConfigured) {
      configureBleAdvertisement();
    }
    bleAdvertising = bleAdvertisementConfigured && bleAdvertisingController->start();
    bleAdvertising = bleAdvertising && bleAdvertisingController->isAdvertising();
    if (!bleAdvertising && bleAdvertisementError.isEmpty()) {
      bleAdvertisementError = "BLE controller did not enter advertising state";
    }
  } else {
    bleAdvertisingController->stop();
    bleAdvertising = false;
  }
}

void setWifiAccessPoint(bool enabled) {
  if (enabled) {
    if (apPassword.length() < 8) {
      wifiApActive = false;
      return;
    }
    const bool addressConfigured = WiFi.softAPConfig(kAccessPointIp, kAccessPointIp, kAccessPointSubnet);
    wifiApActive = addressConfigured && WiFi.softAP(apName.c_str(), apPassword.c_str());
  } else {
    WiFi.softAPdisconnect(true);
    wifiApActive = false;
  }
}

void configureDeviceAccess(const String& name, const String& password) {
  if (!preferences.begin(kPreferencesNamespace, false)) {
    return;
  }
  preferences.putString("device_name", name);
  if (password.length() >= 8) {
    preferences.putString("ap_password", password);
  }
  preferences.end();

  deviceName = name;
  apName = name;
  if (password.length() >= 8) {
    apPassword = password;
  }

  const bool restartAp = wifiApActive;
  if (restartAp) {
    WiFi.softAPdisconnect(true);
    delay(150);
    setWifiAccessPoint(true);
  }

  const bool restartBle = bleAdvertising;
  bleAdvertisingController->stop();
  NimBLEDevice::setDeviceName(deviceName.c_str());
  configureBleAdvertisement();
  bleAdvertising = restartBle && bleAdvertisementConfigured && bleAdvertisingController->start();
}

bool setCameraControl(const String& setting, int value) {
  sensor_t* sensor = esp_camera_sensor_get();
  if (!cameraReady || sensor == nullptr) {
    return false;
  }
  if (setting == "brightness" && value >= -2 && value <= 2) {
    cameraBrightness = value;
    return sensor->set_brightness(sensor, value) == 0;
  }
  if (setting == "contrast" && value >= -2 && value <= 2) {
    cameraContrast = value;
    return sensor->set_contrast(sensor, value) == 0;
  }
  if (setting == "saturation" && value >= -2 && value <= 2) {
    cameraSaturation = value;
    return sensor->set_saturation(sensor, value) == 0;
  }
  if (setting == "sharpness" && value >= -2 && value <= 2) {
    cameraSharpness = value;
    return sensor->set_sharpness(sensor, value) == 0;
  }
  if (setting == "exposure" && value >= -2 && value <= 2) {
    cameraAeLevel = value;
    return sensor->set_ae_level(sensor, value) == 0;
  }
  if (setting == "quality" && value >= 4 && value <= 63) {
    cameraJpegQuality = value;
    return sensor->set_quality(sensor, value) == 0;
  }
  return false;
}

void processCommand(const String& rawCommand) {
  String command = rawCommand;
  command.trim();
  if (command == "STREAM ON") {
    usbStreamEnabled = true;
    return;
  }
  if (command == "STREAM OFF") {
    usbStreamEnabled = false;
    return;
  }
  if (command == "STATUS") {
    publishTelemetry();
    return;
  }
  if (command.startsWith("GPIO READ\t") || command.startsWith("GPIO WRITE\t") || command.startsWith("ADC READ\t")) {
    processControlCommand(command);
    return;
  }
  if (command == "BLE ON") {
    setBleAdvertising(true);
    publishTelemetry();
    return;
  }
  if (command == "BLE OFF") {
    setBleAdvertising(false);
    publishTelemetry();
    return;
  }
  if (command == "WIFI AP ON") {
    setWifiAccessPoint(true);
    publishTelemetry();
    return;
  }
  if (command == "WIFI AP OFF") {
    setWifiAccessPoint(false);
    publishTelemetry();
    return;
  }
  if (command == "WIFI SCAN") {
    scanWifiNetworks();
    publishTelemetry();
    return;
  }
  if (command == "INTERNET TEST") {
    testInternetConnection();
    publishTelemetry();
    return;
  }
  if (command.startsWith("CAMERA\t")) {
    const int separator = command.indexOf('\t', 7);
    if (separator > 7) {
      setCameraControl(command.substring(7, separator), command.substring(separator + 1).toInt());
      publishTelemetry();
    }
    return;
  }
  if (command.startsWith("DEVICE\t")) {
    const int separator = command.indexOf('\t', 7);
    if (separator > 7) {
      configureDeviceAccess(command.substring(7, separator), command.substring(separator + 1));
      publishTelemetry();
    }
    return;
  }
  if (command.startsWith("NAME\t") && command.length() > 5) {
    configureDeviceAccess(command.substring(5), apPassword);
    publishTelemetry();
    return;
  }
  if (command.startsWith("WIFI ONCE\t")) {
    const int separator = command.indexOf('\t', 10);
    if (separator > 10) {
      configureWifi(command.substring(10, separator), command.substring(separator + 1), false);
      publishTelemetry();
    }
    return;
  }
  if (command.startsWith("WIFI\t")) {
    const int separator = command.indexOf('\t', 5);
    if (separator > 5) {
      configureWifi(command.substring(5, separator), command.substring(separator + 1), true);
      publishTelemetry();
    }
  }
}

void readCommands() {
  while (Serial.available() > 0) {
    const char character = static_cast<char>(Serial.read());
    if (character == '\n') {
      processCommand(commandBuffer);
      commandBuffer = "";
    } else if (character != '\r' && commandBuffer.length() < 256) {
      commandBuffer += character;
    }
  }
}

void streamUsbFrame() {
  if (!cameraReady || !usbStreamEnabled || xSemaphoreTake(cameraMutex, 0) != pdTRUE) {
    return;
  }
  camera_fb_t* frame = esp_camera_fb_get();
  if (frame != nullptr) {
    sendPacket(kPacketJpeg, frame->buf, frame->len);
    esp_camera_fb_return(frame);
    frameSequence++;
    fpsWindowFrames++;
  }
  xSemaphoreGive(cameraMutex);
}

void updateFps() {
  const uint32_t now = millis();
  const uint32_t elapsed = now - fpsWindowAt;
  if (elapsed >= 2000) {
    measuredFps = fpsWindowFrames * 1000.0f / elapsed;
    fpsWindowFrames = 0;
    fpsWindowAt = now;
  }
}

void startBle() {
  NimBLEDevice::init(deviceName.c_str());
  NimBLEDevice::setPower(9);
  bleServer = NimBLEDevice::createServer();
  bleServer->setCallbacks(&bleServerCallbacks, false);
  bleServer->advertiseOnDisconnect(true);
  NimBLEService* service = bleServer->createService(kBleServiceUuid);
  statusCharacteristic = service->createCharacteristic(
      kBleStatusUuid,
      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
  statusCharacteristic->setValue(makeTelemetry().c_str());
  bleServer->start();
  bleAdvertisingController = NimBLEDevice::getAdvertising();
  configureBleAdvertisement();
  bleAdvertising = bleAdvertisementConfigured && bleAdvertisingController->start();
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(800);

  const uint64_t mac = ESP.getEfuseMac();
  char suffix[5];
  snprintf(suffix, sizeof(suffix), "%04X", static_cast<uint16_t>(mac & 0xFFFF));
  loadDeviceConfiguration("XIAO-ESP32S3-SENSE-" + String(suffix));

  cameraMutex = xSemaphoreCreateMutex();
  cameraReady = initCamera();

  WiFi.mode(WIFI_AP_STA);
  WiFi.setSleep(false);
  setWifiAccessPoint(true);
  connectStoredWifi();
  startBle();
  if (cameraReady) {
    startCameraServer();
  }

  fpsWindowAt = millis();
  publishTelemetry();
}

void loop() {
  readCommands();
  const uint32_t now = millis();
  if (now - lastFrameAt >= kFrameIntervalMs) {
    lastFrameAt = now;
    streamUsbFrame();
  }
  updateFps();
  if (now - lastTelemetryAt >= kTelemetryIntervalMs) {
    lastTelemetryAt = now;
    publishTelemetry();
  }
  delay(2);
}
