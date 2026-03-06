"""Cycle Configuration API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from backend.core.database import get_db
from backend.schemas import CycleConfigurationCreate, CycleConfigurationUpdate, CycleConfigurationResponse
from backend.models import CycleConfiguration, Equipment, ProductType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cycle-configs", tags=["cycle-configs"])


@router.get("", response_model=List[CycleConfigurationResponse])
def list_cycle_configurations(
    equipment_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List cycle configurations, optionally filtered by equipment."""
    query = db.query(CycleConfiguration)

    if equipment_id:
        query = query.filter(CycleConfiguration.equipment_id == equipment_id)

    configs = query.offset(skip).limit(limit).all()
    return configs


@router.post("", response_model=CycleConfigurationResponse, status_code=201)
def create_cycle_configuration(
    config: CycleConfigurationCreate,
    db: Session = Depends(get_db)
):
    """Create a new cycle configuration."""
    # Verify equipment exists
    equipment = db.query(Equipment).filter(Equipment.id == config.equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail=f"Equipment {config.equipment_id} not found")

    # Verify product type exists
    product_type = db.query(ProductType).filter(ProductType.id == config.product_type_id).first()
    if not product_type:
        raise HTTPException(status_code=404, detail=f"Product type {config.product_type_id} not found")

    # Check if configuration already exists
    existing = db.query(CycleConfiguration).filter(
        CycleConfiguration.equipment_id == config.equipment_id,
        CycleConfiguration.product_type_id == config.product_type_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Configuration already exists for equipment {config.equipment_id} and product type {config.product_type_id}"
        )

    # Validate thresholds
    if config.min_cycle_time > config.target_cycle_time:
        raise HTTPException(status_code=400, detail="min_cycle_time cannot be greater than target_cycle_time")
    if config.max_cycle_time < config.target_cycle_time:
        raise HTTPException(status_code=400, detail="max_cycle_time cannot be less than target_cycle_time")

    new_config = CycleConfiguration(**config.model_dump())
    db.add(new_config)
    db.commit()
    db.refresh(new_config)

    logger.info(f"Created cycle configuration: {new_config.id} for equipment {new_config.equipment_id}")
    return new_config


@router.get("/{config_id}", response_model=CycleConfigurationResponse)
def get_cycle_configuration(config_id: int, db: Session = Depends(get_db)):
    """Get cycle configuration by ID."""
    config = db.query(CycleConfiguration).filter(CycleConfiguration.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
    return config


@router.put("/{config_id}", response_model=CycleConfigurationResponse)
def update_cycle_configuration(
    config_id: int,
    config_update: CycleConfigurationUpdate,
    db: Session = Depends(get_db)
):
    """Update cycle configuration."""
    config = db.query(CycleConfiguration).filter(CycleConfiguration.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")

    update_data = config_update.model_dump(exclude_unset=True)

    # Validate thresholds if provided
    target = update_data.get('target_cycle_time') or config.target_cycle_time
    min_time = update_data.get('min_cycle_time') or config.min_cycle_time
    max_time = update_data.get('max_cycle_time') or config.max_cycle_time

    if min_time > target:
        raise HTTPException(status_code=400, detail="min_cycle_time cannot be greater than target_cycle_time")
    if max_time < target:
        raise HTTPException(status_code=400, detail="max_cycle_time cannot be less than target_cycle_time")

    for field, value in update_data.items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)

    logger.info(f"Updated cycle configuration: {config_id}")
    return config


@router.delete("/{config_id}", status_code=204)
def delete_cycle_configuration(config_id: int, db: Session = Depends(get_db)):
    """Delete cycle configuration."""
    config = db.query(CycleConfiguration).filter(CycleConfiguration.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")

    db.delete(config)
    db.commit()

    logger.info(f"Deleted cycle configuration: {config_id}")
