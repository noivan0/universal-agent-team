"""Equipment API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import logging

from backend.core.database import get_db
from backend.schemas import EquipmentCreate, EquipmentUpdate, EquipmentResponse
from backend.repositories.equipment_repo import EquipmentRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/equipments", tags=["equipments"])


@router.get("", response_model=List[EquipmentResponse])
def list_equipments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all equipments with pagination."""
    equipments = EquipmentRepository.get_all(db, skip=skip, limit=limit)
    return equipments


@router.post("", response_model=EquipmentResponse, status_code=201)
def create_equipment(
    equipment: EquipmentCreate,
    db: Session = Depends(get_db)
):
    """Create a new equipment."""
    # Check if equipment already exists
    existing = EquipmentRepository.get_by_name(db, equipment.name)
    if existing:
        logger.warning(f"Equipment with name '{equipment.name}' already exists")
        raise HTTPException(status_code=400, detail=f"Equipment '{equipment.name}' already exists")

    new_equipment = EquipmentRepository.create(db, equipment)
    logger.info(f"Created equipment: {new_equipment.id} - {new_equipment.name}")
    return new_equipment


@router.get("/{equipment_id}", response_model=EquipmentResponse)
def get_equipment(equipment_id: int, db: Session = Depends(get_db)):
    """Get equipment by ID."""
    equipment = EquipmentRepository.get_by_id(db, equipment_id)
    if not equipment:
        logger.warning(f"Equipment {equipment_id} not found")
        raise HTTPException(status_code=404, detail=f"Equipment {equipment_id} not found")
    return equipment


@router.put("/{equipment_id}", response_model=EquipmentResponse)
def update_equipment(
    equipment_id: int,
    equipment_update: EquipmentUpdate,
    db: Session = Depends(get_db)
):
    """Update equipment."""
    equipment = EquipmentRepository.update(db, equipment_id, equipment_update)
    if not equipment:
        logger.warning(f"Equipment {equipment_id} not found")
        raise HTTPException(status_code=404, detail=f"Equipment {equipment_id} not found")

    logger.info(f"Updated equipment: {equipment_id}")
    return equipment


@router.delete("/{equipment_id}", status_code=204)
def delete_equipment(equipment_id: int, db: Session = Depends(get_db)):
    """Delete equipment."""
    success = EquipmentRepository.delete(db, equipment_id)
    if not success:
        logger.warning(f"Equipment {equipment_id} not found")
        raise HTTPException(status_code=404, detail=f"Equipment {equipment_id} not found")

    logger.info(f"Deleted equipment: {equipment_id}")
