"""Timeseries Data API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging

from backend.core.database import get_db
from backend.schemas import TimeseriesDataCreate, TimeseriesDataResponse
from backend.models import TimeseriesData, Equipment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/timeseries", tags=["timeseries"])


@router.post("", status_code=201)
def create_timeseries_data(
    data: TimeseriesDataCreate,
    db: Session = Depends(get_db)
):
    """Create timeseries data (single or batch)."""
    # Verify equipment exists
    equipment = db.query(Equipment).filter(Equipment.id == data.equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail=f"Equipment {data.equipment_id} not found")

    # Bulk insert data points
    timeseries_records = []
    for point in data.data_points:
        record = TimeseriesData(
            equipment_id=data.equipment_id,
            timestamp=point.timestamp,
            data_point=point.data_point,
            signal_name=point.signal_name,
            signal_value=point.signal_value,
            metadata=point.metadata or {}
        )
        timeseries_records.append(record)

    db.add_all(timeseries_records)
    db.commit()

    logger.info(f"Created {len(timeseries_records)} timeseries records for equipment {data.equipment_id}")
    return {
        "message": f"Created {len(timeseries_records)} records",
        "equipment_id": data.equipment_id,
        "count": len(timeseries_records)
    }


@router.get("/{equipment_id}", response_model=List[TimeseriesDataResponse])
def get_timeseries_data(
    equipment_id: int,
    start_time: datetime = Query(..., description="Start time (ISO format)"),
    end_time: datetime = Query(..., description="End time (ISO format)"),
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db)
):
    """Get timeseries data for an equipment within a time range."""
    # Verify equipment exists
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail=f"Equipment {equipment_id} not found")

    # Query data within time range
    data = db.query(TimeseriesData).filter(
        TimeseriesData.equipment_id == equipment_id,
        TimeseriesData.timestamp >= start_time,
        TimeseriesData.timestamp <= end_time
    ).order_by(TimeseriesData.timestamp.asc()).limit(limit).all()

    return data


@router.get("/{equipment_id}/latest", response_model=TimeseriesDataResponse)
def get_latest_timeseries_data(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    """Get the latest timeseries data point for an equipment."""
    # Verify equipment exists
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail=f"Equipment {equipment_id} not found")

    # Get latest data point
    data = db.query(TimeseriesData).filter(
        TimeseriesData.equipment_id == equipment_id
    ).order_by(TimeseriesData.timestamp.desc()).first()

    if not data:
        raise HTTPException(status_code=404, detail=f"No timeseries data found for equipment {equipment_id}")

    return data
