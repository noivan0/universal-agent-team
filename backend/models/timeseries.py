"""TimeseriesData ORM model."""

from sqlalchemy import Column, BigInteger, Integer, Float, String, DateTime, ForeignKey, JSON
from datetime import datetime
from backend.core.database import Base


class TimeseriesData(Base):
    """Time series sensor data from equipment."""

    __tablename__ = "timeseries_data"

    id = Column(BigInteger, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False, index=True)

    timestamp = Column(DateTime, nullable=False, index=True)
    data_point = Column(Float, nullable=False)

    # Signal information
    signal_name = Column(String(100), nullable=True)
    signal_value = Column(Float, nullable=True)

    # Additional metadata
    metadata = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        # Index for common query patterns
        # CREATE INDEX idx_equipment_timestamp ON timeseries_data(equipment_id, timestamp);
    )

    def __repr__(self) -> str:
        return f"<TimeseriesData(id={self.id}, equipment_id={self.equipment_id}, timestamp={self.timestamp}, data_point={self.data_point})>"
