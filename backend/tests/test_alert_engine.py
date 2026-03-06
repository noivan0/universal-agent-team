"""Unit tests for Alert Engine."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.services.alert_engine import AlertEngine
from backend.models import Alert, CycleLabel, CycleConfiguration, Equipment, ProductType, AlertNotification


class TestAlertCreation:
    """Test alert creation logic."""

    def test_create_alert_for_cycle_too_short(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test alert creation for cycle that is too short."""
        # Create a cycle that is too short
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=45),
            cycle_duration=45.0,
            detection_method="signal",
            confidence=1.0,
            status="too_short"
        )
        db_session.add(cycle)
        db_session.commit()

        # Create alert
        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        # Assert
        assert alert is not None
        assert alert.alert_type == "cycle_too_short"
        assert alert.severity == "warning"  # 45 is not < 55*0.8 = 44
        assert alert.cycle_time == 45.0
        assert alert.threshold_min == 55.0
        assert alert.threshold_max == 65.0
        assert alert.is_acknowledged == False
        assert "too short" in alert.message.lower()

    def test_create_alert_for_cycle_too_long(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test alert creation for cycle that is too long."""
        # Create a cycle that is too long
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=75),
            cycle_duration=75.0,
            detection_method="signal",
            confidence=1.0,
            status="too_long"
        )
        db_session.add(cycle)
        db_session.commit()

        # Create alert
        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        # Assert
        assert alert is not None
        assert alert.alert_type == "cycle_too_long"
        assert alert.severity == "warning"  # 75 is not > 65*1.2 = 78
        assert alert.cycle_time == 75.0
        assert "too long" in alert.message.lower()

    def test_no_alert_for_normal_cycle(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test that no alert is created for normal cycle."""
        # Create a normal cycle
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=60),
            cycle_duration=60.0,
            detection_method="signal",
            confidence=1.0,
            status="normal"
        )
        db_session.add(cycle)
        db_session.commit()

        # Create alert
        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        # Assert
        assert alert is None


class TestSeverityDetermination:
    """Test alert severity calculation."""

    def test_severity_critical_for_very_short_cycle(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test that very short cycles get critical severity."""
        # Create a cycle that is less than 80% of minimum (55 * 0.8 = 44)
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=40),
            cycle_duration=40.0,
            detection_method="signal",
            confidence=1.0,
            status="too_short"
        )
        db_session.add(cycle)
        db_session.commit()

        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        assert alert is not None
        assert alert.severity == "critical"

    def test_severity_warning_for_slightly_short_cycle(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test that slightly short cycles get warning severity."""
        # Create a cycle that is between 80% of minimum and minimum (44 < x < 55)
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=50),
            cycle_duration=50.0,
            detection_method="signal",
            confidence=1.0,
            status="too_short"
        )
        db_session.add(cycle)
        db_session.commit()

        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        assert alert is not None
        assert alert.severity == "warning"

    def test_severity_critical_for_very_long_cycle(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test that very long cycles get critical severity."""
        # Create a cycle that exceeds 120% of maximum (65 * 1.2 = 78)
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=85),
            cycle_duration=85.0,
            detection_method="signal",
            confidence=1.0,
            status="too_long"
        )
        db_session.add(cycle)
        db_session.commit()

        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        assert alert is not None
        assert alert.severity == "critical"

    def test_severity_warning_for_slightly_long_cycle(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test that slightly long cycles get warning severity."""
        # Create a cycle that is between maximum and 120% of maximum (65 < x < 78)
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=70),
            cycle_duration=70.0,
            detection_method="signal",
            confidence=1.0,
            status="too_long"
        )
        db_session.add(cycle)
        db_session.commit()

        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        assert alert is not None
        assert alert.severity == "warning"


class TestBatchProcessing:
    """Test batch cycle checking."""

    def test_check_batch_cycles_mixed(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test batch processing with mix of normal and anomalous cycles."""
        cycles = []

        # Create 3 normal cycles
        for i in range(3):
            cycle = CycleLabel(
                equipment_id=sample_equipment.id,
                product_type_id=sample_product_type.id,
                start_time=datetime.now() + timedelta(seconds=i*100),
                end_time=datetime.now() + timedelta(seconds=i*100+60),
                cycle_duration=60.0,
                detection_method="signal",
                confidence=1.0,
                status="normal"
            )
            cycles.append(cycle)

        # Create 2 anomalous cycles
        for i in range(2):
            cycle = CycleLabel(
                equipment_id=sample_equipment.id,
                product_type_id=sample_product_type.id,
                start_time=datetime.now() + timedelta(seconds=(3+i)*100),
                end_time=datetime.now() + timedelta(seconds=(3+i)*100+70),
                cycle_duration=70.0,
                detection_method="signal",
                confidence=1.0,
                status="too_long"
            )
            cycles.append(cycle)

        db_session.add_all(cycles)
        db_session.commit()

        # Process batch
        alerts = AlertEngine.check_batch_cycles(cycles, sample_cycle_config, db_session)

        # Assert
        assert len(alerts) == 2  # Only anomalous cycles create alerts
        assert all(a.alert_type == "cycle_too_long" for a in alerts)

    def test_check_batch_empty(
        self,
        db_session: Session,
        sample_cycle_config: CycleConfiguration
    ):
        """Test batch processing with empty list."""
        alerts = AlertEngine.check_batch_cycles([], sample_cycle_config, db_session)
        assert alerts == []


class TestAlertAcknowledgment:
    """Test alert acknowledgment functionality."""

    def test_acknowledge_alert(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test acknowledging an alert."""
        # Create a cycle and alert
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=75),
            cycle_duration=75.0,
            detection_method="signal",
            confidence=1.0,
            status="too_long"
        )
        db_session.add(cycle)
        db_session.commit()

        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)
        assert alert.is_acknowledged == False

        # Acknowledge the alert
        acknowledged_alert = AlertEngine.acknowledge_alert(alert.id, "john_doe", db_session)

        # Assert
        assert acknowledged_alert is not None
        assert acknowledged_alert.is_acknowledged == True
        assert acknowledged_alert.acknowledged_by == "john_doe"
        assert acknowledged_alert.acknowledged_at is not None

    def test_acknowledge_nonexistent_alert(
        self,
        db_session: Session
    ):
        """Test acknowledging a non-existent alert."""
        result = AlertEngine.acknowledge_alert(99999, "john_doe", db_session)
        assert result is None

    def test_acknowledge_alert_idempotent(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test that acknowledging an already acknowledged alert works."""
        # Create and acknowledge an alert
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=75),
            cycle_duration=75.0,
            detection_method="signal",
            confidence=1.0,
            status="too_long"
        )
        db_session.add(cycle)
        db_session.commit()

        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)
        AlertEngine.acknowledge_alert(alert.id, "john_doe", db_session)

        # Acknowledge again
        reack = AlertEngine.acknowledge_alert(alert.id, "jane_doe", db_session)

        # Should work without error
        assert reack is not None
        assert reack.is_acknowledged == True
        # Last person to acknowledge should be recorded
        assert reack.acknowledged_by == "jane_doe"


class TestAlertRetrieval:
    """Test alert retrieval functionality."""

    def test_get_unacknowledged_alerts_for_equipment(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test retrieving unacknowledged alerts for an equipment."""
        # Create multiple alerts
        cycles = []
        for i in range(3):
            cycle = CycleLabel(
                equipment_id=sample_equipment.id,
                product_type_id=sample_product_type.id,
                start_time=datetime.now() + timedelta(seconds=i*100),
                end_time=datetime.now() + timedelta(seconds=i*100+75),
                cycle_duration=75.0,
                detection_method="signal",
                confidence=1.0,
                status="too_long"
            )
            cycles.append(cycle)
        db_session.add_all(cycles)
        db_session.commit()

        # Create alerts
        for cycle in cycles:
            AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        # Acknowledge one alert
        alerts = db_session.query(Alert).all()
        AlertEngine.acknowledge_alert(alerts[0].id, "john_doe", db_session)

        # Retrieve unacknowledged alerts
        unack_alerts = AlertEngine.get_unacknowledged_alerts_for_equipment(
            sample_equipment.id,
            db_session
        )

        # Assert
        assert len(unack_alerts) == 2
        assert all(not a.is_acknowledged for a in unack_alerts)

    def test_get_unacknowledged_alerts_empty(
        self,
        db_session: Session,
        sample_equipment: Equipment
    ):
        """Test retrieving unacknowledged alerts when none exist."""
        alerts = AlertEngine.get_unacknowledged_alerts_for_equipment(
            sample_equipment.id,
            db_session
        )
        assert alerts == []

    def test_get_critical_alerts(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test retrieving critical alerts."""
        # Create critical and non-critical alerts
        # Critical: cycle 40s (< 44)
        critical_cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=40),
            cycle_duration=40.0,
            detection_method="signal",
            confidence=1.0,
            status="too_short"
        )
        db_session.add(critical_cycle)
        db_session.commit()
        AlertEngine.check_cycle_and_create_alert(critical_cycle, sample_cycle_config, db_session)

        # Non-critical: cycle 50s (44 < 50 < 55)
        warning_cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now() + timedelta(seconds=100),
            end_time=datetime.now() + timedelta(seconds=150),
            cycle_duration=50.0,
            detection_method="signal",
            confidence=1.0,
            status="too_short"
        )
        db_session.add(warning_cycle)
        db_session.commit()
        AlertEngine.check_cycle_and_create_alert(warning_cycle, sample_cycle_config, db_session)

        # Retrieve critical alerts
        critical_alerts = AlertEngine.get_critical_alerts(db_session)

        # Assert
        assert len(critical_alerts) == 1
        assert critical_alerts[0].severity == "critical"
        assert critical_alerts[0].cycle_time == 40.0

    def test_get_critical_alerts_excludes_acknowledged(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test that acknowledged critical alerts are excluded."""
        # Create critical alert
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=40),
            cycle_duration=40.0,
            detection_method="signal",
            confidence=1.0,
            status="too_short"
        )
        db_session.add(cycle)
        db_session.commit()

        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        # Acknowledge it
        AlertEngine.acknowledge_alert(alert.id, "john_doe", db_session)

        # Retrieve critical alerts
        critical_alerts = AlertEngine.get_critical_alerts(db_session)

        # Assert
        assert len(critical_alerts) == 0


class TestAlertMessageFormatting:
    """Test alert message formatting."""

    def test_alert_message_includes_thresholds(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test that alert messages include threshold values."""
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=45),
            cycle_duration=45.0,
            detection_method="signal",
            confidence=1.0,
            status="too_short"
        )
        db_session.add(cycle)
        db_session.commit()

        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        # Assert
        assert "45.0" in alert.message  # Cycle time
        assert "55.0" in alert.message  # Minimum threshold
        assert "minimum" in alert.message.lower()

    def test_alert_message_for_too_long(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test alert message for too-long cycle includes maximum threshold."""
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=75),
            cycle_duration=75.0,
            detection_method="signal",
            confidence=1.0,
            status="too_long"
        )
        db_session.add(cycle)
        db_session.commit()

        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        # Assert
        assert "75.0" in alert.message  # Cycle time
        assert "65.0" in alert.message  # Maximum threshold
        assert "maximum" in alert.message.lower()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_duration_cycle(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test alert creation for zero-duration cycle."""
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now(),  # Same timestamp
            cycle_duration=0.0,
            detection_method="signal",
            confidence=1.0,
            status="too_short"
        )
        db_session.add(cycle)
        db_session.commit()

        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        # Should create alert for zero duration (< min)
        assert alert is not None
        assert alert.cycle_time == 0.0

    def test_extremely_short_cycle(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test alert creation for extremely short cycle."""
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=1),
            cycle_duration=1.0,
            detection_method="signal",
            confidence=1.0,
            status="too_short"
        )
        db_session.add(cycle)
        db_session.commit()

        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        # Should create critical alert
        assert alert is not None
        assert alert.severity == "critical"

    def test_boundary_cycle_at_min(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test cycle exactly at minimum threshold."""
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=55),
            cycle_duration=55.0,
            detection_method="signal",
            confidence=1.0,
            status="normal"
        )
        db_session.add(cycle)
        db_session.commit()

        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        # Should not create alert (at boundary is normal)
        assert alert is None

    def test_boundary_cycle_at_max(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test cycle exactly at maximum threshold."""
        cycle = CycleLabel(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=65),
            cycle_duration=65.0,
            detection_method="signal",
            confidence=1.0,
            status="normal"
        )
        db_session.add(cycle)
        db_session.commit()

        alert = AlertEngine.check_cycle_and_create_alert(cycle, sample_cycle_config, db_session)

        # Should not create alert (at boundary is normal)
        assert alert is None
