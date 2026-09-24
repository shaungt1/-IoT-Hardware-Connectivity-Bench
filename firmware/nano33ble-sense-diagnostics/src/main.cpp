#include <Arduino.h>
#include <Arduino_APDS9960.h>
#include <Arduino_HTS221.h>
#include <Arduino_LPS22HB.h>
#include <Arduino_LSM9DS1.h>
#include <PDM.h>
#include <Wire.h>

namespace {
bool imuReady = false;
bool apdsReady = false;
bool htsReady = false;
bool baroReady = false;
bool microphoneReady = false;
volatile int microphonePeak = 0;
volatile unsigned long microphoneSamples = 0;
short microphoneBuffer[256];
String commandBuffer;
unsigned long lastBannerAt = 0;

void onPdmData() {
  const int bytes = PDM.available();
  if (bytes <= 0) return;
  const int read = PDM.read(microphoneBuffer, min(bytes, static_cast<int>(sizeof(microphoneBuffer))));
  for (int index = 0; index < read / static_cast<int>(sizeof(short)); ++index) {
    microphonePeak = max(microphonePeak, abs(static_cast<int>(microphoneBuffer[index])));
    microphoneSamples += 1;
  }
}

void printBoolean(bool value) { Serial.print(value ? "true" : "false"); }

void printManifest(const char* prefix) {
  Serial.print(prefix);
  Serial.print(" {\"protocol\":\"iot-bench-sensors/1\",\"board\":\"Arduino Nano 33 BLE Sense (original)\",\"sensors\":{");
  Serial.print("\"lsm9ds1\":"); printBoolean(imuReady);
  Serial.print(",\"apds9960\":"); printBoolean(apdsReady);
  Serial.print(",\"hts221\":"); printBoolean(htsReady);
  Serial.print(",\"lps22hb\":"); printBoolean(baroReady);
  Serial.print(",\"mp34dt05\":"); printBoolean(microphoneReady);
  Serial.println("}}");
}

void printUnavailable(const String& sensor) {
  Serial.print("BENCH_RESULT {\"sensor\":\"");
  Serial.print(sensor);
  Serial.println("\",\"passed\":false,\"error\":\"sensor did not initialize\"}");
}

void testImu() {
  if (!imuReady) return printUnavailable("lsm9ds1");
  float ax = 0, ay = 0, az = 0, gx = 0, gy = 0, gz = 0, mx = 0, my = 0, mz = 0;
  const bool acceleration = IMU.accelerationAvailable() && IMU.readAcceleration(ax, ay, az);
  const bool gyroscope = IMU.gyroscopeAvailable() && IMU.readGyroscope(gx, gy, gz);
  const bool magnetic = IMU.magneticFieldAvailable() && IMU.readMagneticField(mx, my, mz);
  Serial.print("BENCH_RESULT {\"sensor\":\"lsm9ds1\",\"passed\":"); printBoolean(acceleration || gyroscope || magnetic);
  Serial.print(",\"acceleration_g\":["); Serial.print(ax, 4); Serial.print(','); Serial.print(ay, 4); Serial.print(','); Serial.print(az, 4);
  Serial.print("],\"gyroscope_dps\":["); Serial.print(gx, 3); Serial.print(','); Serial.print(gy, 3); Serial.print(','); Serial.print(gz, 3);
  Serial.print("],\"magnetic_uT\":["); Serial.print(mx, 3); Serial.print(','); Serial.print(my, 3); Serial.print(','); Serial.print(mz, 3); Serial.println("]}");
}

void testApds() {
  if (!apdsReady) return printUnavailable("apds9960");
  int red = 0, green = 0, blue = 0, clear = 0;
  int proximity = -1;
  bool colorAvailable = false;
  bool proximityAvailable = false;
  const unsigned long deadline = millis() + 1200;
  while (!colorAvailable && !proximityAvailable && millis() < deadline) {
    colorAvailable = APDS.colorAvailable();
    proximityAvailable = APDS.proximityAvailable();
    if (!colorAvailable && !proximityAvailable) delay(10);
  }
  const bool color = colorAvailable && APDS.readColor(red, green, blue, clear);
  if (proximityAvailable) proximity = APDS.readProximity();
  Serial.print("BENCH_RESULT {\"sensor\":\"apds9960\",\"passed\":"); printBoolean(color || proximity >= 0);
  Serial.print(",\"color_ready\":"); printBoolean(color);
  Serial.print(",\"proximity_ready\":"); printBoolean(proximity >= 0);
  Serial.print(",\"color\":["); Serial.print(red); Serial.print(','); Serial.print(green); Serial.print(','); Serial.print(blue); Serial.print(','); Serial.print(clear);
  Serial.print("],\"proximity\":"); Serial.print(proximity); Serial.println("}");
}

void testHts() {
  if (!htsReady) return printUnavailable("hts221");
  Serial.print("BENCH_RESULT {\"sensor\":\"hts221\",\"passed\":true,\"temperature_c\":");
  Serial.print(HTS.readTemperature(), 2); Serial.print(",\"humidity_percent\":"); Serial.print(HTS.readHumidity(), 2); Serial.println("}");
}

void testBarometer() {
  if (!baroReady) return printUnavailable("lps22hb");
  Serial.print("BENCH_RESULT {\"sensor\":\"lps22hb\",\"passed\":true,\"pressure_kpa\":");
  Serial.print(BARO.readPressure(), 3); Serial.println("}");
}

void testMicrophone() {
  if (!microphoneReady) return printUnavailable("mp34dt05");
  noInterrupts();
  const int peak = microphonePeak;
  const unsigned long samples = microphoneSamples;
  microphonePeak = 0;
  microphoneSamples = 0;
  interrupts();
  Serial.print("BENCH_RESULT {\"sensor\":\"mp34dt05\",\"passed\":"); printBoolean(samples > 0);
  Serial.print(",\"sample_count\":"); Serial.print(samples); Serial.print(",\"peak\":"); Serial.print(peak); Serial.println("}");
}

void testI2c() {
  byte addresses[112];
  int count = 0;
  for (byte address = 0x08; address <= 0x77; ++address) {
    Wire.beginTransmission(address);
    if (Wire.endTransmission() == 0 && count < 112) addresses[count++] = address;
  }
  Serial.print("BENCH_RESULT {\"sensor\":\"i2c\",\"passed\":true,\"addresses\":[");
  for (int index = 0; index < count; ++index) {
    if (index) Serial.print(',');
    Serial.print(addresses[index]);
  }
  Serial.print("],\"count\":"); Serial.print(count); Serial.println("}");
}

void handleCommand(String command) {
  command.trim();
  command.toLowerCase();
  if (command == "hello" || command == "list") return printManifest("BENCH_MANIFEST");
  if (command == "test lsm9ds1") return testImu();
  if (command == "test apds9960") return testApds();
  if (command == "test hts221") return testHts();
  if (command == "test lps22hb") return testBarometer();
  if (command == "test mp34dt05") return testMicrophone();
  if (command == "test i2c") return testI2c();
  Serial.println("BENCH_ERROR {\"error\":\"unsupported command\"}");
}
}  // namespace

void setup() {
  Serial.begin(115200);
  const unsigned long waitUntil = millis() + 2500;
  while (!Serial && millis() < waitUntil) delay(10);
  imuReady = IMU.begin();
  apdsReady = APDS.begin();
  htsReady = HTS.begin();
  baroReady = BARO.begin();
  Wire.begin();
  PDM.onReceive(onPdmData);
  microphoneReady = PDM.begin(1, 16000);
  printManifest("BENCH_READY");
}

void loop() {
  while (Serial.available()) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\n' || value == '\r') {
      if (commandBuffer.length()) handleCommand(commandBuffer);
      commandBuffer = "";
    } else if (commandBuffer.length() < 80) {
      commandBuffer += value;
    }
  }
  if (millis() - lastBannerAt > 2000) {
    lastBannerAt = millis();
    printManifest("BENCH_READY");
  }
  delay(5);
}
