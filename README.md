# raspi-iot-server

Raspberry Pi を IoT サーバーとして運用するためのモノレポ。  
ESP32 などのデバイスからデータを収集・保存し、Web ダッシュボードでモニタリングする。

## 構成

```
raspi-iot-server/
├── server/          # FastAPI + SQLite バックエンド
│   ├── main.py
│   ├── serial_reader.py   # ESP32 USB シリアル読み取り
│   ├── database.py
│   ├── schemas.py
│   ├── routes/
│   └── static/            # Web ダッシュボード
├── deploy/          # systemd サービス、セットアップスクリプト
└── .github/         # Issue / PR テンプレート
```

## 開発ルール

詳細は [CONTRIBUTING.md](./CONTRIBUTING.md) を参照。

- **Issue 駆動**: 作業開始前に必ず Issue を作成する
- **スモール PR**: 1 PR = 1 機能 or 1 修正
- **Conventional Commits**: コミットメッセージ形式に従う

## セットアップ (Raspberry Pi)

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# ESP32 のシリアルポートを確認して設定
export SERIAL_PORT=/dev/ttyUSB0   # または /dev/ttyACM0
uvicorn main:app --host 0.0.0.0 --port 8000
```

## ESP32 側のデータ形式

シリアルポートへ改行区切り JSON を送信する:

```json
{"temperature": 25.3, "humidity": 60.5}
{"temperature": 25.4, "humidity": 60.3, "device_id": "esp32-room1"}
```
