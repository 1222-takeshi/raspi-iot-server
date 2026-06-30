# raspi-iot-server

Raspberry Pi を IoT サーバーとして運用するためのモノレポ。  
WiFi に接続した ESP32 がデータを HTTP POST し、Raspi が収集・保存。Web ダッシュボードでリアルタイムモニタリングする。

## アーキテクチャ

```
ESP32 (room-a) ──┐
ESP32 (room-b) ──┼── WiFi → POST /api/sensors/reading → Raspi FastAPI + SQLite
ESP32 (room-c) ──┘                                              │
                                                     Browser ← WebSocket push
```

## 構成

```
raspi-iot-server/
├── server/          # FastAPI + SQLite バックエンド
│   ├── main.py
│   ├── database.py
│   ├── schemas.py
│   ├── routes/sensors.py      # REST API + POST ingest
│   └── static/                # Web ダッシュボード
├── esp32/
│   └── dht-wifi-poster/       # Arduino サンプルスケッチ (DHT22)
├── deploy/          # systemd サービス、セットアップスクリプト
└── .github/         # Issue / PR テンプレート
```

## 開発ルール

詳細は [CONTRIBUTING.md](./CONTRIBUTING.md) を参照。

## API

| Method | Path | 説明 |
|--------|------|------|
| `POST` | `/api/sensors/reading` | ESP32からデータ受信 |
| `GET`  | `/api/sensors/devices` | デバイス一覧 |
| `GET`  | `/api/sensors/latest?device_id=<name>` | 最新値 |
| `GET`  | `/api/sensors/history?device_id=<name>&minutes=60` | 履歴 |
| `GET`  | `/api/sensors/stats?device_id=<name>&minutes=60` | 統計 |
| `WS`   | `/ws` | リアルタイムプッシュ |

## ESP32 側の設定

`esp32/dht-wifi-poster/dht-wifi-poster.ino` を Arduino IDE で開き、以下を編集:

```cpp
const char* WIFI_SSID  = "your-wifi-ssid";
const char* WIFI_PASSWORD = "your-wifi-password";
const char* SERVER_URL = "http://raspi-server.local:8000/api/sensors/reading";
const char* DEVICE_ID  = "living-room";  // ← 好きな名前をつける
```

POSTするJSONフォーマット:
```json
{"device_id": "living-room", "temperature": 25.3, "humidity": 60.5}
```

## セットアップ (Raspberry Pi)

```bash
git clone https://github.com/1222-takeshi/raspi-iot-server.git
cd raspi-iot-server
bash deploy/setup.sh
sudo systemctl start raspi-iot-server

# ブラウザで確認
# http://raspi-server.local:8000
```

