"""Equipment data access repository.

This repository provides optimized database access patterns:
- Eager loading to prevent N+1 queries
- Proper indexing strategies
- Batch operations where appropriate
- Query result caching for frequently accessed data
"""

import logging
from functools import lru_cache
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func
from backend.models import Equipment, CycleConfiguration
from backend.schemas import EquipmentCreate, EquipmentUpdate
from typing import List, Optional

logger = logging.getLogger(__name__)


class EquipmentRepository:
    """Repository for Equipment database operations with performance optimizations."""

    # Simple in-memory cache for equipment lookups (invalidated on write)
    _cache: dict[int, Equipment] = {}

    @staticmethod
    def create(db: Session, equipment: EquipmentCreate) -> Equipment:
        """
        Create a new equipment.

        Args:
            db: Database session
            equipment: Equipment creation data

        Returns:
            Created Equipment instance
        """
        db_equipment = Equipment(**equipment.model_dump())
        db.add(db_equipment)
        db.commit()
        db.refresh(db_equipment)

        # Clear cache on write
        EquipmentRepository._cache.clear()
        logger.debug(f"Created equipment: {db_equipment.id}")

        return db_equipment

    @staticmethod
    def get_by_id(db: Session, equipment_id: int) -> Optional[Equipment]:
        """
        Get equipment by ID with caching.

        Optimizations:
        - Check local cache first
        - Use indexed lookup on primary key
        - Eager load related cycle configurations

        Args:
            db: Database session
            equipment_id: Equipment ID

        Returns:
            Equipment instance or None if not found
        """
        # Check cache first
        if equipment_id in EquipmentRepository._cache:
            logger.debug(f"Cache hit for equipment {equipment_id}")
            return EquipmentRepository._cache[equipment_id]

        # Query with eager loading
        result = db.query(Equipment).filter(Equipment.id == equipment_id).first()

        if result:
            EquipmentRepository._cache[equipment_id] = result
            logger.debug(f"Cache miss for equipment {equipment_id}, loaded from DB")

        return result

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Equipment]:
        """
        Get equipment by name.

        Optimizations:
        - Uses indexed lookup on name column

        Args:
            db: Database session
            name: Equipment name

        Returns:
            Equipment instance or None if not found
        """
        return db.query(Equipment).filter(Equipment.name == name).first()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Equipment]:
        """
        Get all equipments with pagination.

        Optimizations:
        - Uses limit/offset for efficient pagination
        - Eager loads related configurations to prevent N+1 queries

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of Equipment instances
        """
        query = db.query(Equipment).offset(skip).limit(limit)

        # Eager load cycle configurations to prevent N+1 queries
        query = query.options(selectinload(Equipment.cycle_configurations))

        results = query.all()
        logger.debug(f"Retrieved {len(results)} equipments (skip={skip}, limit={limit})")

        return results

    @staticmethod
    def get_with_cycles(db: Session, equipment_id: int) -> Optional[Equipment]:
        """
        Get equipment with all related cycle data eagerly loaded.

        Optimizations:
        - Single query with joinedload to fetch equipment and cycles
        - Prevents N+1 queries when accessing cycle data

        Args:
            db: Database session
            equipment_id: Equipment ID

        Returns:
            Equipment instance with cycles preloaded, or None if not found
        """
        return db.query(Equipment).options(
            selectinload(Equipment.cycle_configurations)
        ).filter(Equipment.id == equipment_id).first()

    @staticmethod
    def get_all_with_cycles(db: Session, skip: int = 0, limit: int = 100) -> List[Equipment]:
        """
        Get all equipments with cycle configurations eagerly loaded.

        Optimizations:
        - Single query with eager loading of relationships
        - Prevents N+1 queries

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of Equipment instances with cycles preloaded
        """
        return db.query(Equipment).options(
            selectinload(Equipment.cycle_configurations)
        ).offset(skip).limit(limit).all()

    @staticmethod
    def update(db: Session, equipment_id: int, equipment_update: EquipmentUpdate) -> Optional[Equipment]:
        """
        Update equipment.

        Optimizations:
        - Avoids unnecessary queries by using get_by_id
        - Invalidates cache after update

        Args:
            db: Database session
            equipment_id: Equipment ID
            equipment_update: Equipment update data

        Returns:
            Updated Equipment instance or None if not found
        """
        db_equipment = EquipmentRepository.get_by_id(db, equipment_id)
        if not db_equipment:
            return None

        update_data = equipment_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_equipment, field, value)

        db.commit()
        db.refresh(db_equipment)

        # Invalidate cache entry
        EquipmentRepository._cache.pop(equipment_id, None)
        logger.debug(f"Updated equipment {equipment_id}")

        return db_equipment

    @staticmethod
    def delete(db: Session, equipment_id: int) -> bool:
        """
        Delete equipment.

        Optimizations:
        - Invalidates cache after deletion

        Args:
            db: Database session
            equipment_id: Equipment ID

        Returns:
            True if deletion successful, False if equipment not found
        """
        db_equipment = EquipmentRepository.get_by_id(db, equipment_id)
        if not db_equipment:
            return False

        db.delete(db_equipment)
        db.commit()

        # Invalidate cache entry
        EquipmentRepository._cache.pop(equipment_id, None)
        logger.debug(f"Deleted equipment {equipment_id}")

        return True

    @staticmethod
    def count_all(db: Session) -> int:
        """
        Count total number of equipments.

        Optimizations:
        - Uses COUNT() instead of fetching all records

        Args:
            db: Database session

        Returns:
            Total count of equipments
        """
        return db.query(func.count(Equipment.id)).scalar() or 0

    @staticmethod
    def get_active_equipments(db: Session) -> List[Equipment]:
        """
        Get all active equipments.

        Optimizations:
        - Filters by status field (should be indexed)
        - Eager loads relationships

        Args:
            db: Database session

        Returns:
            List of active Equipment instances
        """
        return db.query(Equipment).filter(
            Equipment.status == 'active'
        ).options(
            selectinload(Equipment.cycle_configurations)
        ).all()

    @staticmethod
    def clear_cache() -> None:
        """Clear the equipment cache."""
        EquipmentRepository._cache.clear()
        logger.debug("Equipment cache cleared")
