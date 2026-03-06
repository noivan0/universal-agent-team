"""ProductType ORM model."""

from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from backend.core.database import Base


class ProductType(Base):
    """Product type/model entity."""

    __tablename__ = "product_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<ProductType(id={self.id}, code='{self.code}', name='{self.name}')>"
