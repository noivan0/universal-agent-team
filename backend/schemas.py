"""Pydantic schemas for request/response serialization."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Equipment Schemas
class EquipmentCreate(BaseModel):
    """Schema for creating equipment."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    location: Optional[str] = None
    model: Optional[str] = None


class EquipmentUpdate(BaseModel):
    """Schema for updating equipment."""
    description: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    model: Optional[str] = None


class EquipmentResponse(BaseModel):
    """Schema for equipment response."""
    id: int
    name: str
    description: Optional[str]
    status: str
    location: Optional[str]
    model: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ProductType Schemas
class ProductTypeCreate(BaseModel):
    """Schema for creating product type."""
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class ProductTypeResponse(BaseModel):
    """Schema for product type response."""
    id: int
    code: str
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# CycleConfiguration Schemas
class CycleConfigurationCreate(BaseModel):
    """Schema for creating cycle configuration."""
    equipment_id: int
    product_type_id: int
    target_cycle_time: float = Field(..., gt=0)
    min_cycle_time: float = Field(..., gt=0)
    max_cycle_time: float = Field(..., gt=0)
    cycle_start_signal: Optional[str] = None
    cycle_end_signal: Optional[str] = None
    pattern_detection_enabled: bool = True
    pattern_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class CycleConfigurationUpdate(BaseModel):
    """Schema for updating cycle configuration."""
    target_cycle_time: Optional[float] = Field(None, gt=0)
    min_cycle_time: Optional[float] = Field(None, gt=0)
    max_cycle_time: Optional[float] = Field(None, gt=0)
    cycle_start_signal: Optional[str] = None
    cycle_end_signal: Optional[str] = None
    pattern_detection_enabled: Optional[bool] = None
    pattern_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: Optional[str] = None


class CycleConfigurationResponse(BaseModel):
    """Schema for cycle configuration response."""
    id: int
    equipment_id: int
    product_type_id: int
    target_cycle_time: float
    min_cycle_time: float
    max_cycle_time: float
    cycle_start_signal: Optional[str]
    cycle_end_signal: Optional[str]
    pattern_detection_enabled: bool
    pattern_threshold: float
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# TimeseriesData Schemas
class TimeseriesDataPoint(BaseModel):
    """Schema for a single timeseries data point."""
    timestamp: datetime
    data_point: float
    signal_name: Optional[str] = None
    signal_value: Optional[float] = None
    metadata: Optional[dict] = None


class TimeseriesDataCreate(BaseModel):
    """Schema for creating timeseries data (single or batch)."""
    data_points: List[TimeseriesDataPoint]
    equipment_id: int


class TimeseriesDataResponse(BaseModel):
    """Schema for timeseries data response."""
    id: int
    equipment_id: int
    timestamp: datetime
    data_point: float
    signal_name: Optional[str]
    signal_value: Optional[float]
    metadata: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


# CycleLabel Schemas
class CycleLabelResponse(BaseModel):
    """Schema for cycle label response."""
    id: int
    equipment_id: int
    product_type_id: Optional[int]
    start_time: datetime
    end_time: datetime
    cycle_duration: float
    detection_method: Optional[str]
    confidence: Optional[float]
    status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Alert Schemas
class AlertResponse(BaseModel):
    """Schema for alert response."""
    id: int
    equipment_id: int
    cycle_label_id: Optional[int]
    alert_type: str
    severity: Optional[str]
    message: Optional[str]
    cycle_time: Optional[float]
    threshold_min: Optional[float]
    threshold_max: Optional[float]
    is_acknowledged: bool
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert."""
    acknowledged_by: str = Field(..., min_length=1)


# Dashboard Schemas
class EquipmentSummary(BaseModel):
    """Summary statistics for a single equipment."""
    equipment_id: int
    equipment_name: str
    status: str
    total_cycles_today: int
    normal_cycles: int
    too_long_cycles: int
    too_short_cycles: int
    avg_cycle_time: Optional[float]
    min_cycle_time: Optional[float]
    max_cycle_time: Optional[float]
    active_alerts: int


class DashboardSummary(BaseModel):
    """Overall dashboard summary."""
    total_equipments: int
    active_equipments: int
    total_alerts: int
    unacknowledged_alerts: int
    equipments: List[EquipmentSummary]
