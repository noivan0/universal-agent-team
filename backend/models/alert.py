"""Alert ORM model for cycle time anomalies."""

from sqlalchemy import Column, BigInteger, Integer, Float, String, Boolean, DateTime, ForeignKey, Text
from datetime import datetime
from backend.core.database import Base


class Alert(Base):
    """Alert record for cycle time anomalies (too long/too short)."""

    __tablename__ = "alerts"

    id = Column(BigInteger, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False, index=True)
    cycle_label_id = Column(BigInteger, ForeignKey("cycle_labels.id"), nullable=True)

    # Alert information
    alert_type = Column(String(50), nullable=False)  # 'cycle_too_long', 'cycle_too_short'
    severity = Column(String(20), nullable=True)  # 'info', 'warning', 'critical'
    message = Column(Text, nullable=True)

    # Detailed data
    cycle_time = Column(Float, nullable=True)
    threshold_min = Column(Float, nullable=True)
    threshold_max = Column(Float, nullable=True)

    # Processing status
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, equipment_id={self.equipment_id}, alert_type={self.alert_type}, severity={self.severity})>"


class AlertNotification(Base):
    """Notification delivery record for alerts."""

    __tablename__ = "alert_notifications"

    id = Column(BigInteger, primary_key=True, index=True)
    alert_id = Column(BigInteger, ForeignKey("alerts.id"), nullable=False)

    notification_method = Column(String(50), nullable=False)  # 'email', 'push', 'sms'
    recipient = Column(String(200), nullable=False)
    status = Column(String(20), default="pending")  # 'pending', 'sent', 'failed'
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<AlertNotification(id={self.id}, alert_id={self.alert_id}, method={self.notification_method}, status={self.status})>"
