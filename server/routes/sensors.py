from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import SensorReading, get_db
from schemas import SensorReadingOut
import serial_reader as sr

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.get("/latest", response_model=Optional[SensorReadingOut])
async def get_latest(
    device_id: str = Query("esp32"),
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
    device_id: str = Query("esp32"),
    minutes: int = Query(60, ge=1, le=1440),
    db: AsyncSession = Depends(get_db),
):
    """Return readings within the last N minutes (default 60, max 1440)."""
    since = datetime.utcnow() - timedelta(minutes=minutes)
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
    device_id: str = Query("esp32"),
    minutes: int = Query(60, ge=1, le=1440),
    db: AsyncSession = Depends(get_db),
):
    """Return min/max/avg for temperature and humidity over the last N minutes."""
    since = datetime.utcnow() - timedelta(minutes=minutes)
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


@router.get("/devices")
async def get_devices(db: AsyncSession = Depends(get_db)):
    """List all known device IDs."""
    result = await db.execute(
        select(SensorReading.device_id).distinct()
    )
    return [row[0] for row in result.all()]


@router.get("/status")
async def get_status():
    """Return serial reader status and latest in-memory reading."""
    return {
        "latest": sr.latest_reading,
        "serial_port": sr.SERIAL_PORT or "auto-detect",
        "baud_rate": sr.BAUD_RATE,
    }
