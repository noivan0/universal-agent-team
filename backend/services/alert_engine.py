"""Alert Engine for cycle time anomaly detection.

This module detects and creates alerts for cycle time anomalies.
Monitors cycle times and generates alerts when:
- Cycle time exceeds max_cycle_time (too_long)
- Cycle time falls below min_cycle_time (too_short)

Algorithm:
1. Receive completed cycle with duration and thresholds
2. Compare duration to min/max thresholds
3. Determine severity based on how far outside thresholds
4. Create and persist Alert record if anomalous
5. Log alert for monitoring

Severity Calculation:
- Critical if duration < min * 0.8 or > max * 1.2
- Warning if just outside thresholds
- No alert if within normal range
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from backend.models import Alert, CycleLabel, CycleConfiguration, Equipment
from config.constants import ALERT_SEVERITY_CRITICAL_FACTOR

logger = logging.getLogger(__name__)


class AlertEngine:
    """
    Detects and creates alerts for cycle time anomalies.

    Monitors cycle times and generates alerts when:
    - Cycle time exceeds max_cycle_time (too_long)
    - Cycle time falls below min_cycle_time (too_short)
    """

    @staticmethod
    def check_cycle_and_create_alert(
        cycle: CycleLabel,
        config: CycleConfiguration,
        db: Session
    ) -> Optional[Alert]:
        """
        Check a completed cycle for anomalies and create alert if needed.

        Args:
            cycle: The completed cycle to check
            config: The cycle configuration with thresholds
            db: Database session

        Returns:
            Alert object if anomaly detected, None otherwise
        """
        # Determine if cycle is anomalous
        if cycle.cycle_duration < config.min_cycle_time:
            alert_type = "cycle_too_short"
            # Critical if significantly below minimum (< min * 0.8)
            critical_threshold = config.min_cycle_time * (1.0 / ALERT_SEVERITY_CRITICAL_FACTOR)
            severity = "critical" if cycle.cycle_duration < critical_threshold else "warning"
            message = (
                f"Cycle time too short: {cycle.cycle_duration:.1f}s "
                f"(minimum: {config.min_cycle_time}s)"
            )

        elif cycle.cycle_duration > config.max_cycle_time:
            alert_type = "cycle_too_long"
            # Critical if significantly above maximum (> max * 1.2)
            critical_threshold = config.max_cycle_time * ALERT_SEVERITY_CRITICAL_FACTOR
            severity = "critical" if cycle.cycle_duration > critical_threshold else "warning"
            message = (
                f"Cycle time too long: {cycle.cycle_duration:.1f}s "
                f"(maximum: {config.max_cycle_time}s)"
            )

        else:
            # Cycle is within normal range
            logger.debug(
                f"Cycle {cycle.id} is normal: {cycle.cycle_duration:.1f}s "
                f"(range: {config.min_cycle_time}-{config.max_cycle_time}s)"
            )
            return None

        # Create alert
        alert = Alert(
            equipment_id=cycle.equipment_id,
            cycle_label_id=cycle.id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            cycle_time=cycle.cycle_duration,
            threshold_min=config.min_cycle_time,
            threshold_max=config.max_cycle_time,
            is_acknowledged=False
        )

        db.add(alert)
        db.commit()
        db.refresh(alert)

        logger.warning(
            f"Alert created: {alert_type} for equipment {cycle.equipment_id}, "
            f"severity {severity}, cycle duration {cycle.cycle_duration:.1f}s"
        )

        return alert

    @staticmethod
    def check_batch_cycles(
        cycles: list[CycleLabel],
        config: CycleConfiguration,
        db: Session
    ) -> list[Alert]:
        """
        Check multiple cycles and create alerts for anomalies.

        Args:
            cycles: List of cycles to check
            config: The cycle configuration with thresholds
            db: Database session

        Returns:
            List of created alerts
        """
        alerts = []

        for cycle in cycles:
            alert = AlertEngine.check_cycle_and_create_alert(cycle, config, db)
            if alert:
                alerts.append(alert)

        logger.info(f"Created {len(alerts)} alerts from {len(cycles)} cycles")
        return alerts

    @staticmethod
    def get_unacknowledged_alerts_for_equipment(
        equipment_id: int,
        db: Session
    ) -> list[Alert]:
        """
        Get all unacknowledged alerts for an equipment.

        Args:
            equipment_id: Equipment ID
            db: Database session

        Returns:
            List of unacknowledged alerts
        """
        return db.query(Alert).filter(
            Alert.equipment_id == equipment_id,
            Alert.is_acknowledged == False
        ).order_by(Alert.created_at.desc()).all()

    @staticmethod
    def acknowledge_alert(
        alert_id: int,
        acknowledged_by: str,
        db: Session
    ) -> Optional[Alert]:
        """
        Mark an alert as acknowledged.

        Args:
            alert_id: Alert ID to acknowledge
            acknowledged_by: User/system that acknowledged the alert
            db: Database session

        Returns:
            Updated alert or None if not found
        """
        from datetime import datetime, timezone

        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            logger.warning(f"Alert {alert_id} not found for acknowledgment")
            return None

        alert.is_acknowledged = True
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = acknowledged_by

        db.commit()
        db.refresh(alert)

        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return alert

    @staticmethod
    def get_critical_alerts(db: Session) -> list[Alert]:
        """
        Get all unacknowledged critical alerts.

        Args:
            db: Database session

        Returns:
            List of critical unacknowledged alerts
        """
        return db.query(Alert).filter(
            Alert.severity == "critical",
            Alert.is_acknowledged == False
        ).order_by(Alert.created_at.desc()).all()
