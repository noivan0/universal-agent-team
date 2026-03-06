"""Alert API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from backend.core.database import get_db
from backend.schemas import AlertResponse, AlertAcknowledge
from backend.models import Alert, Equipment
from backend.services.alert_engine import AlertEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=List[AlertResponse])
def list_alerts(
    equipment_id: Optional[int] = Query(None),
    alert_type: Optional[str] = Query(None, description="filter: cycle_too_long, cycle_too_short"),
    severity: Optional[str] = Query(None, description="filter: critical, warning, info"),
    acknowledged: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    List alerts with optional filtering.

    Filters:
    - equipment_id: Filter by specific equipment
    - alert_type: Filter by alert type
    - severity: Filter by severity level
    - acknowledged: Filter by acknowledgment status (True/False)
    """
    query = db.query(Alert)

    if equipment_id is not None:
        query = query.filter(Alert.equipment_id == equipment_id)

    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)

    if severity:
        query = query.filter(Alert.severity == severity)

    if acknowledged is not None:
        query = query.filter(Alert.is_acknowledged == acknowledged)

    alerts = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()
    return alerts


@router.get("/equipment/{equipment_id}", response_model=List[AlertResponse])
def get_equipment_alerts(
    equipment_id: int,
    unacknowledged_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Get all alerts for a specific equipment.

    Args:
        equipment_id: Equipment ID
        unacknowledged_only: If True, return only unacknowledged alerts
    """
    # Verify equipment exists
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail=f"Equipment {equipment_id} not found")

    if unacknowledged_only:
        alerts = AlertEngine.get_unacknowledged_alerts_for_equipment(equipment_id, db)
    else:
        alerts = db.query(Alert).filter(
            Alert.equipment_id == equipment_id
        ).order_by(Alert.created_at.desc()).all()

    return alerts


@router.get("/unacknowledged-count")
def get_unacknowledged_count(
    db: Session = Depends(get_db)
):
    """
    Get count of unacknowledged alerts globally.
    """
    count = db.query(Alert).filter(Alert.is_acknowledged == False).count()
    return {"unacknowledged_count": count}


@router.get("/critical")
def get_critical_alerts(
    db: Session = Depends(get_db)
):
    """
    Get all unacknowledged critical alerts.
    """
    alerts = AlertEngine.get_critical_alerts(db)
    return alerts


@router.put("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    payload: AlertAcknowledge,
    db: Session = Depends(get_db)
):
    """
    Mark an alert as acknowledged by a user.
    """
    alert = AlertEngine.acknowledge_alert(alert_id, payload.acknowledged_by, db)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    logger.info(f"Alert {alert_id} acknowledged by {payload.acknowledged_by}")
    return alert


@router.delete("/{alert_id}")
def dismiss_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete/dismiss an alert.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    db.delete(alert)
    db.commit()

    logger.info(f"Alert {alert_id} dismissed")
    return {"message": "Alert dismissed"}


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific alert by ID.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    return alert
