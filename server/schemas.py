from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SensorReadingIn(BaseModel):
    """Payload sent by ESP32 via HTTP POST."""
    device_id: str = Field(..., description="Unique device name, e.g. 'living-room'")
    temperature: float = Field(..., description="Temperature in Celsius")
    humidity: float = Field(..., ge=0, le=100, description="Relative humidity in %")


class SensorReadingOut(BaseModel):
    id: int
    device_id: str
    temperature: float
    humidity: float
    timestamp: datetime

    model_config = {"from_attributes": True}


class DeviceInfo(BaseModel):
    device_id: str
    last_seen: Optional[datetime]
    reading_count: int
