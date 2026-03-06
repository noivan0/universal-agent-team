"""Equipment ORM model."""

from sqlalchemy import Column, Integer, String, Text, DateTime, func
from datetime import datetime
from backend.core.database import Base


class Equipment(Base):
    """Equipment entity representing manufacturing equipment/machines."""

    __tablename__ = "equipments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="active")  # active, inactive, maintenance
    location = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Equipment(id={self.id}, name='{self.name}', status='{self.status}')>"
