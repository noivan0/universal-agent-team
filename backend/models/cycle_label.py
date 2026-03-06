"""CycleLabel ORM model for labeled cycle periods."""

from sqlalchemy import Column, BigInteger, Integer, Float, String, DateTime, ForeignKey
from datetime import datetime
from backend.core.database import Base


class CycleLabel(Base):
    """Labeled cycle period with start/end times and metadata."""

    __tablename__ = "cycle_labels"

    id = Column(BigInteger, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False, index=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=True)

    # Cycle time period
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    cycle_duration = Column(Float, nullable=False)  # in seconds

    # Detection method
    detection_method = Column(String(50), nullable=True)  # 'signal' or 'pattern'
    confidence = Column(Float, nullable=True)  # 0-1 for pattern-based

    # Status
    status = Column(String(20), nullable=True)  # 'normal', 'too_long', 'too_short'

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<CycleLabel(id={self.id}, equipment_id={self.equipment_id}, duration={self.cycle_duration}s, status={self.status})>"
