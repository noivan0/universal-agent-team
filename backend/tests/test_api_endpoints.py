"""Integration tests for API endpoints."""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.core.database import Base, get_db, engine
from backend.models import Equipment, ProductType, CycleConfiguration, TimeseriesData, CycleLabel, Alert


# Create test database
@pytest.fixture(scope="module")
def setup_test_db():
    """Set up test database for API tests."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session, setup_test_db):
    """Create test client with test database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


class TestEquipmentEndpoints:
    """Test equipment management endpoints."""

    def test_create_equipment(self, client: TestClient, db_session: Session):
        """Test POST /api/equipments to create new equipment."""
        response = client.post(
            "/api/equipments",
            json={
                "name": "Assembly Line 1",
                "description": "Main assembly line",
                "status": "active",
                "location": "Building A",
                "model": "AL-2000"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Assembly Line 1"
        assert data["status"] == "active"
        assert "id" in data

    def test_create_equipment_duplicate_name(self, client: TestClient, db_session: Session):
        """Test that duplicate equipment names are rejected."""
        # Create first equipment
        client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )

        # Try to create duplicate
        response = client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )

        # Should fail with 4xx error
        assert response.status_code >= 400

    def test_get_equipment_list(self, client: TestClient, db_session: Session):
        """Test GET /api/equipments to retrieve all equipment."""
        # Create test equipment
        for i in range(3):
            client.post(
                "/api/equipments",
                json={"name": f"Line {i}", "status": "active"}
            )

        response = client.get("/api/equipments")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

    def test_get_equipment_by_id(self, client: TestClient, db_session: Session):
        """Test GET /api/equipments/{id} to retrieve specific equipment."""
        # Create equipment
        create_response = client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )
        equipment_id = create_response.json()["id"]

        # Get equipment
        response = client.get(f"/api/equipments/{equipment_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == equipment_id
        assert data["name"] == "Assembly Line 1"

    def test_get_nonexistent_equipment(self, client: TestClient):
        """Test GET /api/equipments/{id} with invalid ID."""
        response = client.get("/api/equipments/99999")
        assert response.status_code == 404

    def test_update_equipment(self, client: TestClient, db_session: Session):
        """Test PUT /api/equipments/{id} to update equipment."""
        # Create equipment
        create_response = client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )
        equipment_id = create_response.json()["id"]

        # Update equipment
        response = client.put(
            f"/api/equipments/{equipment_id}",
            json={"name": "Assembly Line 1", "status": "maintenance"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "maintenance"

    def test_delete_equipment(self, client: TestClient, db_session: Session):
        """Test DELETE /api/equipments/{id} to delete equipment."""
        # Create equipment
        create_response = client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )
        equipment_id = create_response.json()["id"]

        # Delete equipment
        response = client.delete(f"/api/equipments/{equipment_id}")
        assert response.status_code == 200

        # Verify deleted
        get_response = client.get(f"/api/equipments/{equipment_id}")
        assert get_response.status_code == 404


class TestProductTypeEndpoints:
    """Test product type management endpoints."""

    def test_create_product_type(self, client: TestClient):
        """Test POST /api/product-types to create product type."""
        response = client.post(
            "/api/product-types",
            json={
                "code": "MODEL_A",
                "name": "Standard Widget",
                "description": "Standard product model"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "MODEL_A"
        assert data["name"] == "Standard Widget"

    def test_get_product_types(self, client: TestClient):
        """Test GET /api/product-types to retrieve all product types."""
        # Create product types
        for i in range(2):
            client.post(
                "/api/product-types",
                json={"code": f"MODEL_{i}", "name": f"Model {i}"}
            )

        response = client.get("/api/product-types")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2


class TestCycleConfigurationEndpoints:
    """Test cycle configuration endpoints."""

    def test_create_cycle_config(self, client: TestClient, db_session: Session):
        """Test POST /api/cycle-configs to create cycle configuration."""
        # Create dependencies first
        equip_response = client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )
        equipment_id = equip_response.json()["id"]

        product_response = client.post(
            "/api/product-types",
            json={"code": "MODEL_A", "name": "Standard Widget"}
        )
        product_id = product_response.json()["id"]

        # Create cycle config
        response = client.post(
            "/api/cycle-configs",
            json={
                "equipment_id": equipment_id,
                "product_type_id": product_id,
                "target_cycle_time": 60.0,
                "min_cycle_time": 55.0,
                "max_cycle_time": 65.0,
                "cycle_start_signal": "CYCLE_START",
                "cycle_end_signal": "CYCLE_END",
                "pattern_detection_enabled": True,
                "pattern_threshold": 0.8
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["target_cycle_time"] == 60.0
        assert data["min_cycle_time"] == 55.0
        assert data["max_cycle_time"] == 65.0

    def test_create_cycle_config_invalid_thresholds(self, client: TestClient, db_session: Session):
        """Test that invalid thresholds are rejected."""
        # Create dependencies
        equip_response = client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )
        equipment_id = equip_response.json()["id"]

        product_response = client.post(
            "/api/product-types",
            json={"code": "MODEL_A", "name": "Standard Widget"}
        )
        product_id = product_response.json()["id"]

        # Try to create with min > max
        response = client.post(
            "/api/cycle-configs",
            json={
                "equipment_id": equipment_id,
                "product_type_id": product_id,
                "target_cycle_time": 60.0,
                "min_cycle_time": 70.0,  # Greater than max!
                "max_cycle_time": 65.0,
                "cycle_start_signal": "CYCLE_START",
                "cycle_end_signal": "CYCLE_END"
            }
        )

        # Should fail validation
        assert response.status_code >= 400

    def test_get_cycle_configs_for_equipment(self, client: TestClient, db_session: Session):
        """Test GET /api/cycle-configs/{equipment_id}."""
        # Create dependencies
        equip_response = client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )
        equipment_id = equip_response.json()["id"]

        product_response = client.post(
            "/api/product-types",
            json={"code": "MODEL_A", "name": "Standard Widget"}
        )
        product_id = product_response.json()["id"]

        # Create config
        client.post(
            "/api/cycle-configs",
            json={
                "equipment_id": equipment_id,
                "product_type_id": product_id,
                "target_cycle_time": 60.0,
                "min_cycle_time": 55.0,
                "max_cycle_time": 65.0
            }
        )

        # Get configs
        response = client.get(f"/api/cycle-configs/{equipment_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestTimeseriesEndpoints:
    """Test time series data endpoints."""

    def test_submit_timeseries_data(self, client: TestClient, db_session: Session):
        """Test POST /api/timeseries to submit time series data."""
        # Create equipment
        equip_response = client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )
        equipment_id = equip_response.json()["id"]

        # Submit timeseries data
        response = client.post(
            "/api/timeseries",
            json={
                "equipment_id": equipment_id,
                "timestamp": datetime.now().isoformat(),
                "data_point": 50.0,
                "signal_name": "CYCLE_START"
            }
        )

        assert response.status_code == 200

    def test_submit_batch_timeseries_data(self, client: TestClient, db_session: Session):
        """Test batch submission of time series data."""
        # Create equipment
        equip_response = client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )
        equipment_id = equip_response.json()["id"]

        # Submit batch data
        base_time = datetime.now()
        data = [
            {
                "equipment_id": equipment_id,
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "data_point": 50.0 + float(i % 20)
            }
            for i in range(10)
        ]

        response = client.post(
            "/api/timeseries/batch",
            json={"data": data}
        )

        assert response.status_code == 200

    def test_get_timeseries_data(self, client: TestClient, db_session: Session):
        """Test GET /api/timeseries/{equipment_id} to retrieve time series data."""
        # Create equipment
        equip_response = client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )
        equipment_id = equip_response.json()["id"]

        # Submit data
        base_time = datetime.now()
        for i in range(5):
            client.post(
                "/api/timeseries",
                json={
                    "equipment_id": equipment_id,
                    "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                    "data_point": 50.0
                }
            )

        # Get data
        response = client.get(f"/api/timeseries/{equipment_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5


class TestCycleEndpoints:
    """Test cycle label endpoints."""

    def test_get_cycles_for_equipment(self, client: TestClient, db_session: Session):
        """Test GET /api/cycles/{equipment_id} to retrieve detected cycles."""
        # Create equipment and config
        equip_response = client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )
        equipment_id = equip_response.json()["id"]

        product_response = client.post(
            "/api/product-types",
            json={"code": "MODEL_A", "name": "Standard Widget"}
        )
        product_id = product_response.json()["id"]

        client.post(
            "/api/cycle-configs",
            json={
                "equipment_id": equipment_id,
                "product_type_id": product_id,
                "target_cycle_time": 60.0,
                "min_cycle_time": 55.0,
                "max_cycle_time": 65.0,
                "pattern_detection_enabled": False
            }
        )

        # Get cycles (even if empty initially)
        response = client.get(f"/api/cycles/{equipment_id}")

        assert response.status_code == 200
        data = response.json()
        # Should be list (may be empty)
        assert isinstance(data, list)

    def test_get_cycles_with_date_range(self, client: TestClient, db_session: Session):
        """Test GET /api/cycles/{equipment_id} with date range filter."""
        # Create equipment
        equip_response = client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )
        equipment_id = equip_response.json()["id"]

        # Get cycles with date range
        start_time = (datetime.now() - timedelta(hours=1)).isoformat()
        end_time = datetime.now().isoformat()

        response = client.get(
            f"/api/cycles/{equipment_id}",
            params={"start_time": start_time, "end_time": end_time}
        )

        assert response.status_code == 200


class TestAlertEndpoints:
    """Test alert management endpoints."""

    def test_get_alerts(self, client: TestClient, db_session: Session):
        """Test GET /api/alerts to retrieve all alerts."""
        response = client.get("/api/alerts")

        assert response.status_code == 200
        data = response.json()
        # Should be list (may be empty)
        assert isinstance(data, list)

    def test_get_alerts_for_equipment(self, client: TestClient, db_session: Session):
        """Test GET /api/alerts/{equipment_id}."""
        # Create equipment
        equip_response = client.post(
            "/api/equipments",
            json={"name": "Assembly Line 1", "status": "active"}
        )
        equipment_id = equip_response.json()["id"]

        response = client.get(f"/api/alerts/{equipment_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_acknowledge_alert(self, client: TestClient, db_session: Session):
        """Test PUT /api/alerts/{id}/acknowledge."""
        # Create alert in database
        equipment = Equipment(name="Assembly Line 1", status="active")
        db_session.add(equipment)
        db_session.commit()

        alert = Alert(
            equipment_id=equipment.id,
            alert_type="cycle_too_long",
            severity="warning",
            message="Cycle time too long",
            cycle_time=70.0,
            threshold_min=55.0,
            threshold_max=65.0,
            is_acknowledged=False
        )
        db_session.add(alert)
        db_session.commit()

        # Acknowledge alert
        response = client.put(
            f"/api/alerts/{alert.id}/acknowledge",
            json={"acknowledged_by": "test_user"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_acknowledged"] == True

    def test_acknowledge_nonexistent_alert(self, client: TestClient):
        """Test acknowledging non-existent alert."""
        response = client.put(
            "/api/alerts/99999/acknowledge",
            json={"acknowledged_by": "test_user"}
        )

        assert response.status_code == 404


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client: TestClient):
        """Test GET /health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_includes_version(self, client: TestClient):
        """Test that health check includes version info."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data or "status" in data


class TestErrorHandling:
    """Test error handling and validation."""

    def test_invalid_json(self, client: TestClient):
        """Test error handling for invalid JSON."""
        response = client.post(
            "/api/equipments",
            content="invalid json",
            headers={"content-type": "application/json"}
        )

        # Should return error
        assert response.status_code >= 400

    def test_missing_required_field(self, client: TestClient):
        """Test validation of required fields."""
        response = client.post(
            "/api/equipments",
            json={"status": "active"}  # Missing 'name' field
        )

        # Should fail validation
        assert response.status_code >= 400

    def test_invalid_enum_value(self, client: TestClient):
        """Test validation of enum fields."""
        response = client.post(
            "/api/equipments",
            json={
                "name": "Assembly Line 1",
                "status": "invalid_status"  # Invalid status
            }
        )

        # Should fail validation
        assert response.status_code >= 400

    def test_404_for_nonexistent_resource(self, client: TestClient):
        """Test 404 for non-existent resource."""
        response = client.get("/api/equipments/99999")
        assert response.status_code == 404


class TestPaginationAndFiltering:
    """Test pagination and filtering."""

    def test_get_alerts_with_limit(self, client: TestClient, db_session: Session):
        """Test GET /api/alerts with limit parameter."""
        # Create some alerts
        equipment = Equipment(name="Assembly Line 1", status="active")
        db_session.add(equipment)
        db_session.commit()

        for i in range(5):
            alert = Alert(
                equipment_id=equipment.id,
                alert_type="cycle_too_long",
                severity="warning",
                message=f"Alert {i}",
                cycle_time=70.0,
                threshold_min=55.0,
                threshold_max=65.0
            )
            db_session.add(alert)
        db_session.commit()

        # Get with limit
        response = client.get("/api/alerts?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

    def test_get_unacknowledged_alerts_only(self, client: TestClient, db_session: Session):
        """Test filtering for unacknowledged alerts."""
        equipment = Equipment(name="Assembly Line 1", status="active")
        db_session.add(equipment)
        db_session.commit()

        # Create mix of acknowledged and unacknowledged
        for i in range(3):
            alert = Alert(
                equipment_id=equipment.id,
                alert_type="cycle_too_long",
                severity="warning",
                message=f"Alert {i}",
                cycle_time=70.0,
                threshold_min=55.0,
                threshold_max=65.0,
                is_acknowledged=(i % 2 == 0)  # Alternate
            )
            db_session.add(alert)
        db_session.commit()

        # Get unacknowledged only
        response = client.get(f"/api/alerts/{equipment.id}?unacknowledged_only=true")

        assert response.status_code == 200
