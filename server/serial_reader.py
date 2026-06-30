"""
ESP32 serial reader — runs as a background asyncio task.

ESP32 side should send newline-terminated JSON, e.g.:
  {"temperature": 25.3, "humidity": 60.5}
  {"temperature": 25.4, "humidity": 60.3, "device_id": "esp32-kitchen"}

Optional fields:
  device_id  — defaults to "esp32"
"""

import asyncio
import json
import logging
import os
from datetime import datetime

import serial
import serial.tools.list_ports
from sqlalchemy import insert

from database import AsyncSessionLocal, SensorReading

logger = logging.getLogger(__name__)

SERIAL_PORT = os.getenv("SERIAL_PORT", "")
BAUD_RATE = int(os.getenv("BAUD_RATE", "115200"))
READ_INTERVAL = float(os.getenv("READ_INTERVAL", "1.0"))


def detect_esp32_port() -> str | None:
    """Auto-detect the first USB-serial device (CH340, CP210x, FTDI)."""
    known_vid_pids = {
        (0x1A86, 0x7523),  # CH340
        (0x10C4, 0xEA60),  # CP2102
        (0x0403, 0x6001),  # FTDI FT232R
        (0x0403, 0x6015),  # FTDI FT231X
        (0x239A, None),    # Adafruit / ESP32-S2
        (0x303A, None),    # Espressif native USB
    }
    for port in serial.tools.list_ports.comports():
        for vid, pid in known_vid_pids:
            if port.vid == vid and (pid is None or port.pid == pid):
                logger.info("Auto-detected ESP32 on %s", port.device)
                return port.device
    return None


def parse_line(raw: str) -> dict | None:
    """Parse a JSON line from ESP32. Returns dict with temperature/humidity or None."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if "temperature" in data and "humidity" in data:
            return {
                "device_id": str(data.get("device_id", "esp32")),
                "temperature": float(data["temperature"]),
                "humidity": float(data["humidity"]),
            }
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.debug("Skipping unparseable line %r: %s", raw, exc)
    return None


# Shared in-memory latest reading for quick access without a DB query
latest_reading: dict | None = None


async def serial_reader_task(broadcast_fn=None):
    """
    Long-running asyncio task that reads from the ESP32 serial port,
    persists every reading to SQLite, and optionally broadcasts via WebSocket.

    broadcast_fn: async callable(dict) — called with each new reading.
    """
    global latest_reading

    port = SERIAL_PORT or detect_esp32_port()
    if not port:
        logger.warning(
            "No ESP32 port found. Set SERIAL_PORT env var or connect the device. "
            "Retrying in 10 s…"
        )
        await asyncio.sleep(10)
        return

    logger.info("Opening serial port %s @ %d baud", port, BAUD_RATE)
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=2)
    except serial.SerialException as exc:
        logger.error("Cannot open serial port %s: %s", port, exc)
        await asyncio.sleep(10)
        return

    try:
        while True:
            try:
                # Non-blocking readline via thread executor to keep event loop free
                raw = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ser.readline().decode("utf-8", errors="replace")
                )
                parsed = parse_line(raw)
                if parsed is None:
                    continue

                parsed["timestamp"] = datetime.utcnow()
                latest_reading = parsed

                async with AsyncSessionLocal() as session:
                    await session.execute(insert(SensorReading).values(**parsed))
                    await session.commit()

                logger.debug("Stored reading: %s", parsed)

                if broadcast_fn:
                    await broadcast_fn(parsed)

            except serial.SerialException as exc:
                logger.error("Serial read error: %s — reconnecting in 5 s", exc)
                await asyncio.sleep(5)
                break

            await asyncio.sleep(READ_INTERVAL)
    finally:
        ser.close()
