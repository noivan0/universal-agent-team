"""Product Type API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import logging

from backend.core.database import get_db
from backend.schemas import ProductTypeCreate, ProductTypeResponse
from backend.models import ProductType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/product-types", tags=["product-types"])


@router.get("", response_model=List[ProductTypeResponse])
def list_product_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all product types."""
    types = db.query(ProductType).offset(skip).limit(limit).all()
    return types


@router.post("", response_model=ProductTypeResponse, status_code=201)
def create_product_type(
    product_type: ProductTypeCreate,
    db: Session = Depends(get_db)
):
    """Create a new product type."""
    # Check if product type already exists
    existing = db.query(ProductType).filter(ProductType.code == product_type.code).first()
    if existing:
        logger.warning(f"Product type with code '{product_type.code}' already exists")
        raise HTTPException(status_code=400, detail=f"Product type code '{product_type.code}' already exists")

    new_type = ProductType(**product_type.model_dump())
    db.add(new_type)
    db.commit()
    db.refresh(new_type)

    logger.info(f"Created product type: {new_type.id} - {new_type.code}")
    return new_type


@router.get("/{product_type_id}", response_model=ProductTypeResponse)
def get_product_type(product_type_id: int, db: Session = Depends(get_db)):
    """Get product type by ID."""
    product_type = db.query(ProductType).filter(ProductType.id == product_type_id).first()
    if not product_type:
        logger.warning(f"Product type {product_type_id} not found")
        raise HTTPException(status_code=404, detail=f"Product type {product_type_id} not found")
    return product_type
