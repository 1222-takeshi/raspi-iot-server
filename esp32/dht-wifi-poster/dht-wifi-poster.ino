/**
 * ESP32 温湿度センサー (DHT22) → Raspi IoT Server
 *
 * 必要ライブラリ (Arduino Library Manager からインストール):
 *   - DHT sensor library (Adafruit)
 *   - Adafruit Unified Sensor
 *
 * 接続:
 *   DHT22 DATA → GPIO 4
 *   DHT22 VCC  → 3.3V
 *   DHT22 GND  → GND
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "DHT.h"

// ── 設定: ここを変更してください ────────────────────────────────────────────

const char* WIFI_SSID     = "your-wifi-ssid";
const char* WIFI_PASSWORD = "your-wifi-password";

// Raspi サーバーの URL (raspi-server.local または IP アドレス)
const char* SERVER_URL    = "http://raspi-server.local:8000/api/sensors/reading";

// このデバイスの名前 (ダッシュボードに表示される)
const char* DEVICE_ID     = "living-room";

// 送信間隔 (ミリ秒)
const unsigned long INTERVAL_MS = 10000;  // 10秒

// DHT センサーの設定
#define DHT_PIN  4
#define DHT_TYPE DHT22  // DHT11 の場合は DHT11 に変更

// ── ここより下は変更不要 ──────────────────────────────────────────────────────

DHT dht(DHT_PIN, DHT_TYPE);
unsigned long lastSentAt = 0;

void setup() {
  Serial.begin(115200);
  dht.begin();

  Serial.printf("\n[IoT] Device: %s\n", DEVICE_ID);
  Serial.printf("[IoT] Connecting to WiFi: %s\n", WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\n[IoT] WiFi connected. IP: %s\n", WiFi.localIP().toString().c_str());
}

void loop() {
  unsigned long now = millis();
  if (now - lastSentAt < INTERVAL_MS) return;
  lastSentAt = now;

  // センサー読み取り
  float humidity    = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("[IoT] DHT read failed, skipping");
    return;
  }

  Serial.printf("[IoT] temp=%.1f°C  humi=%.1f%%\n", temperature, humidity);

  // WiFi 再接続
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[IoT] WiFi lost, reconnecting...");
    WiFi.reconnect();
    return;
  }

  // HTTP POST
  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<128> doc;
  doc["device_id"]   = DEVICE_ID;
  doc["temperature"] = temperature;
  doc["humidity"]    = humidity;

  String body;
  serializeJson(doc, body);

  int code = http.POST(body);
  if (code == 201) {
    Serial.printf("[IoT] POST ok (201)\n");
  } else {
    Serial.printf("[IoT] POST failed: %d\n", code);
  }
  http.end();
}
