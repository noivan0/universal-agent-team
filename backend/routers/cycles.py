"""Cycle Label API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from backend.core.database import get_db
from backend.schemas import CycleLabelResponse
from backend.models import CycleLabel, Equipment
from backend.services.cycle_detector import CycleDetector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cycles", tags=["cycles"])


@router.get("/{equipment_id}", response_model=List[CycleLabelResponse])
def get_cycles(
    equipment_id: int,
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    status: Optional[str] = Query(None, description="Filter by status: normal, too_long, too_short"),
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db)
):
    """
    Get cycles for a specific equipment.

    Optional filters:
    - start_time: Filter cycles starting after this time
    - end_time: Filter cycles starting before this time
    - status: Filter by cycle status (normal, too_long, too_short)
    """
    # Verify equipment exists
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail=f"Equipment {equipment_id} not found")

    # Build query
    query = db.query(CycleLabel).filter(CycleLabel.equipment_id == equipment_id)

    if start_time:
        query = query.filter(CycleLabel.start_time >= start_time)

    if end_time:
        query = query.filter(CycleLabel.start_time <= end_time)

    if status:
        query = query.filter(CycleLabel.status == status)

    cycles = query.order_by(CycleLabel.start_time.desc()).limit(limit).all()

    logger.info(f"Retrieved {len(cycles)} cycles for equipment {equipment_id}")
    return cycles


@router.get("/{equipment_id}/statistics")
def get_cycle_statistics(
    equipment_id: int,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get cycle time statistics for an equipment.

    Returns:
    - total_cycles: Total number of cycles
    - normal_cycles: Cycles within acceptable range
    - too_long_cycles: Cycles exceeding max time
    - too_short_cycles: Cycles below min time
    - avg_cycle_time: Average cycle duration
    - min_cycle_time: Minimum cycle duration
    - max_cycle_time: Maximum cycle duration
    - std_dev: Standard deviation
    """
    # Verify equipment exists
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail=f"Equipment {equipment_id} not found")

    # Build query
    query = db.query(CycleLabel).filter(CycleLabel.equipment_id == equipment_id)

    if start_time:
        query = query.filter(CycleLabel.start_time >= start_time)

    if end_time:
        query = query.filter(CycleLabel.start_time <= end_time)

    cycles = query.all()

    if not cycles:
        return {
            "total_cycles": 0,
            "normal_cycles": 0,
            "too_long_cycles": 0,
            "too_short_cycles": 0,
            "avg_cycle_time": None,
            "min_cycle_time": None,
            "max_cycle_time": None,
            "std_dev": None
        }

    # Calculate statistics
    import numpy as np

    durations = [c.cycle_duration for c in cycles]
    normal = sum(1 for c in cycles if c.status == "normal")
    too_long = sum(1 for c in cycles if c.status == "too_long")
    too_short = sum(1 for c in cycles if c.status == "too_short")

    return {
        "total_cycles": len(cycles),
        "normal_cycles": normal,
        "too_long_cycles": too_long,
        "too_short_cycles": too_short,
        "avg_cycle_time": float(np.mean(durations)) if durations else None,
        "min_cycle_time": float(np.min(durations)) if durations else None,
        "max_cycle_time": float(np.max(durations)) if durations else None,
        "std_dev": float(np.std(durations)) if durations else None
    }
