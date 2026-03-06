"""Pytest configuration and fixtures for all tests."""

import os
from datetime import datetime, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.core.database import Base
from backend.models import Equipment, ProductType, CycleConfiguration, TimeseriesData
from backend.core.config import settings


# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Session:
    """Create a new database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_equipment(db_session: Session) -> Equipment:
    """Create a sample equipment for testing."""
    equipment = Equipment(
        name="Assembly Line 1",
        description="Main assembly line",
        status="active",
        location="Building A",
        model="AL-2000"
    )
    db_session.add(equipment)
    db_session.commit()
    db_session.refresh(equipment)
    return equipment


@pytest.fixture
def sample_product_type(db_session: Session) -> ProductType:
    """Create a sample product type for testing."""
    product = ProductType(
        code="MODEL_A",
        name="Standard Widget",
        description="Standard product model"
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def sample_cycle_config(
    db_session: Session,
    sample_equipment: Equipment,
    sample_product_type: ProductType
) -> CycleConfiguration:
    """Create a sample cycle configuration for testing."""
    config = CycleConfiguration(
        equipment_id=sample_equipment.id,
        product_type_id=sample_product_type.id,
        target_cycle_time=60.0,
        min_cycle_time=55.0,
        max_cycle_time=65.0,
        cycle_start_signal="CYCLE_START",
        cycle_end_signal="CYCLE_END",
        pattern_detection_enabled=True,
        pattern_threshold=0.8,
        status="active"
    )
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    return config


@pytest.fixture
def sample_timeseries_data(
    db_session: Session,
    sample_equipment: Equipment
) -> list[TimeseriesData]:
    """Create sample time series data for testing."""
    base_time = datetime.now()
    data_points = []

    # Create 100 data points with a 60-second cycle pattern
    for i in range(100):
        timestamp = base_time + timedelta(seconds=i)

        # Create a simple sine wave pattern to represent cycles
        # Cycle: 0-60s = rising, 60-120s = falling
        phase = (i % 120) / 120 * 2 * 3.14159
        value = 50 + 10 * __import__('math').sin(phase)

        # Add signal markers at cycle boundaries
        signal_name = None
        if i % 60 == 0:
            signal_name = "CYCLE_START"
        elif i % 60 == 59:
            signal_name = "CYCLE_END"

        data = TimeseriesData(
            equipment_id=sample_equipment.id,
            timestamp=timestamp,
            data_point=value,
            signal_name=signal_name,
            signal_value=float(signal_name is not None)
        )
        data_points.append(data)

    db_session.add_all(data_points)
    db_session.commit()

    return data_points


@pytest.fixture
def sample_sine_wave_data(
    db_session: Session,
    sample_equipment: Equipment
) -> list[TimeseriesData]:
    """Create pure sine wave data for pattern detection testing."""
    import math

    base_time = datetime.now()
    data_points = []
    frequency = 0.1  # Complete cycle every ~63 seconds

    for i in range(300):  # 5 minutes of data
        timestamp = base_time + timedelta(seconds=i)
        # Generate sine wave with period ~63 seconds
        value = 50 + 15 * math.sin(2 * math.pi * frequency * i / 60)

        data = TimeseriesData(
            equipment_id=sample_equipment.id,
            timestamp=timestamp,
            data_point=value
        )
        data_points.append(data)

    db_session.add_all(data_points)
    db_session.commit()

    return data_points
