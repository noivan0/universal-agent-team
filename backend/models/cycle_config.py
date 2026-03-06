"""CycleConfiguration ORM model."""

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime
from backend.core.database import Base


class CycleConfiguration(Base):
    """Equipment-ProductType specific cycle time configuration."""

    __tablename__ = "cycle_configurations"

    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=False)

    # Cycle time thresholds (in seconds)
    target_cycle_time = Column(Float, nullable=False)  # Expected cycle time
    min_cycle_time = Column(Float, nullable=False)     # Minimum allowed
    max_cycle_time = Column(Float, nullable=False)     # Maximum allowed

    # Signal-based detection
    cycle_start_signal = Column(String(100), nullable=True)
    cycle_end_signal = Column(String(100), nullable=True)

    # Pattern-based detection
    pattern_detection_enabled = Column(Boolean, default=True)
    pattern_threshold = Column(Float, default=0.8)  # Similarity threshold 0-1

    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("equipment_id", "product_type_id", name="uq_equipment_product"),
    )

    def __repr__(self) -> str:
        return f"<CycleConfiguration(id={self.id}, equipment_id={self.equipment_id}, product_type_id={self.product_type_id})>"
