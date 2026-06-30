from datetime import datetime, timedelta, timezone
from typing import Optional

JST = timezone(timedelta(hours=9))

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import SensorReading, get_db
from schemas import SensorReadingIn, SensorReadingOut, DeviceInfo

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


# ── Ingest ────────────────────────────────────────────────────────────────────

@router.post("/reading", response_model=SensorReadingOut, status_code=201)
async def post_reading(
    payload: SensorReadingIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Receive a sensor reading from an ESP32 device over WiFi.

    ESP32 should POST JSON:
        {"device_id": "living-room", "temperature": 25.3, "humidity": 60.5}
    """
    reading = SensorReading(
        device_id=payload.device_id,
        temperature=payload.temperature,
        humidity=payload.humidity,
        timestamp=datetime.now(tz=JST),
    )
    db.add(reading)
    await db.commit()
    await db.refresh(reading)

    # Broadcast to WebSocket clients
    from main import get_manager
    manager = get_manager()
    await manager.broadcast({
        "id": reading.id,
        "device_id": reading.device_id,
        "temperature": reading.temperature,
        "humidity": reading.humidity,
        "timestamp": reading.timestamp.isoformat(),
    })

    return reading


# ── Query ─────────────────────────────────────────────────────────────────────

@router.get("/devices", response_model=list[DeviceInfo])
async def get_devices(db: AsyncSession = Depends(get_db)):
    """List all registered devices with last seen time and reading count."""
    result = await db.execute(
        select(
            SensorReading.device_id,
            func.max(SensorReading.timestamp).label("last_seen"),
            func.count(SensorReading.id).label("reading_count"),
        ).group_by(SensorReading.device_id)
        .order_by(func.max(SensorReading.timestamp).desc())
    )
    return [
        DeviceInfo(device_id=row.device_id, last_seen=row.last_seen, reading_count=row.reading_count)
        for row in result.all()
    ]


@router.get("/latest", response_model=Optional[SensorReadingOut])
async def get_latest(
    device_id: str = Query(..., description="Device name, e.g. 'living-room'"),
    db: AsyncSession = Depends(get_db),
):
    """Return the most recent reading for a device."""
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.device_id == device_id)
        .order_by(SensorReading.timestamp.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/history", response_model=list[SensorReadingOut])
async def get_history(
    device_id: str = Query(..., description="Device name"),
    minutes: int = Query(60, ge=1, le=1440),
    db: AsyncSession = Depends(get_db),
):
    """Return readings within the last N minutes (default 60, max 1440)."""
    since = datetime.now(tz=JST) - timedelta(minutes=minutes)
    result = await db.execute(
        select(SensorReading)
        .where(
            SensorReading.device_id == device_id,
            SensorReading.timestamp >= since,
        )
        .order_by(SensorReading.timestamp.asc())
    )
    return result.scalars().all()


@router.get("/stats")
async def get_stats(
    device_id: str = Query(..., description="Device name"),
    minutes: int = Query(60, ge=1, le=1440),
    db: AsyncSession = Depends(get_db),
):
    """Return min/max/avg for temperature and humidity over the last N minutes."""
    since = datetime.now(tz=JST) - timedelta(minutes=minutes)
    result = await db.execute(
        select(
            func.min(SensorReading.temperature).label("temp_min"),
            func.max(SensorReading.temperature).label("temp_max"),
            func.avg(SensorReading.temperature).label("temp_avg"),
            func.min(SensorReading.humidity).label("humi_min"),
            func.max(SensorReading.humidity).label("humi_max"),
            func.avg(SensorReading.humidity).label("humi_avg"),
            func.count(SensorReading.id).label("count"),
        ).where(
            SensorReading.device_id == device_id,
            SensorReading.timestamp >= since,
        )
    )
    row = result.one()
    return {
        "device_id": device_id,
        "period_minutes": minutes,
        "temperature": {
            "min": row.temp_min,
            "max": row.temp_max,
            "avg": round(row.temp_avg, 2) if row.temp_avg else None,
        },
        "humidity": {
            "min": row.humi_min,
            "max": row.humi_max,
            "avg": round(row.humi_avg, 2) if row.humi_avg else None,
        },
        "count": row.count,
    }
