"""Unit tests for Cycle Detection Engine (CycleDetector)."""

import pytest
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.services.cycle_detector import CycleDetector
from backend.models import TimeseriesData, CycleLabel, CycleConfiguration, Equipment, ProductType


class TestSignalBasedDetection:
    """Test signal-based cycle detection method."""

    def test_signal_based_detection_simple_cycle(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test signal-based detection with clear start/end signals."""
        # Create time series with explicit cycle start/end markers
        base_time = datetime.now()
        data_points = []

        # Cycle 1: 0-60 seconds
        for i in range(61):
            signal_name = "CYCLE_START" if i == 0 else ("CYCLE_END" if i == 60 else None)
            data = TimeseriesData(
                equipment_id=sample_equipment.id,
                timestamp=base_time + timedelta(seconds=i),
                data_point=50.0 + float(i % 20),
                signal_name=signal_name
            )
            data_points.append(data)

        # Cycle 2: 61-125 seconds
        for i in range(61, 126):
            signal_name = "CYCLE_START" if i == 61 else ("CYCLE_END" if i == 125 else None)
            data = TimeseriesData(
                equipment_id=sample_equipment.id,
                timestamp=base_time + timedelta(seconds=i),
                data_point=50.0 + float((i - 61) % 20),
                signal_name=signal_name
            )
            data_points.append(data)

        db_session.add_all(data_points)
        db_session.commit()

        # Detect cycles
        cycles = CycleDetector.detect_cycles(data_points, sample_cycle_config, db_session)

        # Assert
        assert len(cycles) == 2
        assert cycles[0].detection_method == "signal"
        assert cycles[0].cycle_duration == 60.0
        assert cycles[0].status == "normal"
        assert cycles[0].confidence == 1.0
        assert cycles[1].cycle_duration == 64.0  # 61-125 is 64 seconds

    def test_signal_based_detection_no_signals(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType
    ):
        """Test signal-based detection with no signal markers."""
        # Create config without signal names
        config = CycleConfiguration(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            target_cycle_time=60.0,
            min_cycle_time=55.0,
            max_cycle_time=65.0,
            cycle_start_signal=None,
            cycle_end_signal=None,
            pattern_detection_enabled=False
        )
        db_session.add(config)
        db_session.commit()

        # Create data without signals
        base_time = datetime.now()
        data_points = [
            TimeseriesData(
                equipment_id=sample_equipment.id,
                timestamp=base_time + timedelta(seconds=i),
                data_point=50.0
            )
            for i in range(100)
        ]
        db_session.add_all(data_points)
        db_session.commit()

        # Detect cycles
        cycles = CycleDetector.detect_cycles(data_points, config, db_session)

        # Should return empty list since no signals and pattern detection disabled
        assert len(cycles) == 0

    def test_signal_based_detection_mismatched_signals(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test signal-based detection with only start signals (no matching ends)."""
        base_time = datetime.now()
        data_points = []

        # Add only CYCLE_START signals, no CYCLE_END
        for i in range(100):
            signal_name = "CYCLE_START" if i % 30 == 0 else None
            data = TimeseriesData(
                equipment_id=sample_equipment.id,
                timestamp=base_time + timedelta(seconds=i),
                data_point=50.0,
                signal_name=signal_name
            )
            data_points.append(data)

        db_session.add_all(data_points)
        db_session.commit()

        # Detect cycles
        cycles = CycleDetector.detect_cycles(data_points, sample_cycle_config, db_session)

        # Should return empty list since no complete start-end pairs
        assert len(cycles) == 0

    def test_signal_based_detection_too_long_cycle(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test cycle status determination for cycle exceeding max threshold."""
        base_time = datetime.now()
        data_points = []

        # Create cycle that lasts 75 seconds (exceeds max of 65s)
        for i in range(76):
            signal_name = "CYCLE_START" if i == 0 else ("CYCLE_END" if i == 75 else None)
            data = TimeseriesData(
                equipment_id=sample_equipment.id,
                timestamp=base_time + timedelta(seconds=i),
                data_point=50.0,
                signal_name=signal_name
            )
            data_points.append(data)

        db_session.add_all(data_points)
        db_session.commit()

        # Detect cycles
        cycles = CycleDetector.detect_cycles(data_points, sample_cycle_config, db_session)

        # Assert status is "too_long"
        assert len(cycles) == 1
        assert cycles[0].cycle_duration == 75.0
        assert cycles[0].status == "too_long"

    def test_signal_based_detection_too_short_cycle(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test cycle status determination for cycle below min threshold."""
        base_time = datetime.now()
        data_points = []

        # Create cycle that lasts 45 seconds (below min of 55s)
        for i in range(46):
            signal_name = "CYCLE_START" if i == 0 else ("CYCLE_END" if i == 45 else None)
            data = TimeseriesData(
                equipment_id=sample_equipment.id,
                timestamp=base_time + timedelta(seconds=i),
                data_point=50.0,
                signal_name=signal_name
            )
            data_points.append(data)

        db_session.add_all(data_points)
        db_session.commit()

        # Detect cycles
        cycles = CycleDetector.detect_cycles(data_points, sample_cycle_config, db_session)

        # Assert status is "too_short"
        assert len(cycles) == 1
        assert cycles[0].cycle_duration == 45.0
        assert cycles[0].status == "too_short"


class TestPatternBasedDetection:
    """Test pattern-based cycle detection method."""

    def test_pattern_based_detection_sine_wave(
        self,
        db_session: Session,
        sample_sine_wave_data: list[TimeseriesData],
        sample_equipment: Equipment,
        sample_product_type: ProductType
    ):
        """Test pattern-based detection on periodic sine wave data."""
        config = CycleConfiguration(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            target_cycle_time=60.0,
            min_cycle_time=55.0,
            max_cycle_time=65.0,
            cycle_start_signal=None,
            cycle_end_signal=None,
            pattern_detection_enabled=True,
            pattern_threshold=0.8
        )
        db_session.add(config)
        db_session.commit()

        # Detect cycles
        cycles = CycleDetector.detect_cycles(sample_sine_wave_data, config, db_session)

        # Should detect multiple cycles (sine wave with ~63s period)
        assert len(cycles) >= 2
        for cycle in cycles:
            assert cycle.detection_method == "pattern"
            assert 0 < cycle.confidence <= 1.0
            # Most cycles should be normal since they follow the pattern
            assert cycle.status in ["normal", "too_long", "too_short"]

    def test_pattern_based_detection_insufficient_data(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType
    ):
        """Test pattern-based detection with insufficient data points."""
        config = CycleConfiguration(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            target_cycle_time=60.0,
            min_cycle_time=55.0,
            max_cycle_time=65.0,
            cycle_start_signal=None,
            cycle_end_signal=None,
            pattern_detection_enabled=True
        )
        db_session.add(config)
        db_session.commit()

        # Create only 5 data points (less than minimum of 10)
        base_time = datetime.now()
        data_points = [
            TimeseriesData(
                equipment_id=sample_equipment.id,
                timestamp=base_time + timedelta(seconds=i),
                data_point=50.0
            )
            for i in range(5)
        ]
        db_session.add_all(data_points)
        db_session.commit()

        # Detect cycles
        cycles = CycleDetector.detect_cycles(data_points, config, db_session)

        # Should return empty list due to insufficient data
        assert len(cycles) == 0

    def test_pattern_based_detection_disabled(
        self,
        db_session: Session,
        sample_sine_wave_data: list[TimeseriesData],
        sample_equipment: Equipment,
        sample_product_type: ProductType
    ):
        """Test that pattern detection is skipped when disabled."""
        config = CycleConfiguration(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            target_cycle_time=60.0,
            min_cycle_time=55.0,
            max_cycle_time=65.0,
            cycle_start_signal=None,
            cycle_end_signal=None,
            pattern_detection_enabled=False
        )
        db_session.add(config)
        db_session.commit()

        # Detect cycles
        cycles = CycleDetector.detect_cycles(sample_sine_wave_data, config, db_session)

        # Should return empty list since pattern detection is disabled
        assert len(cycles) == 0


class TestHybridDetection:
    """Test hybrid cycle detection (signal + pattern combined)."""

    def test_hybrid_signal_prioritized_over_pattern(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType
    ):
        """Test that signal-based detection takes priority when signals are available."""
        config = CycleConfiguration(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            target_cycle_time=60.0,
            min_cycle_time=55.0,
            max_cycle_time=65.0,
            cycle_start_signal="CYCLE_START",
            cycle_end_signal="CYCLE_END",
            pattern_detection_enabled=True  # Even though enabled, signal should take priority
        )
        db_session.add(config)
        db_session.commit()

        # Create data with clear signals
        base_time = datetime.now()
        data_points = []

        for i in range(100):
            signal_name = None
            if i % 60 == 0:
                signal_name = "CYCLE_START"
            elif i % 60 == 59:
                signal_name = "CYCLE_END"

            data = TimeseriesData(
                equipment_id=sample_equipment.id,
                timestamp=base_time + timedelta(seconds=i),
                data_point=50.0,
                signal_name=signal_name
            )
            data_points.append(data)

        db_session.add_all(data_points)
        db_session.commit()

        # Detect cycles
        cycles = CycleDetector.detect_cycles(data_points, config, db_session)

        # All cycles should be detected via signal-based method
        assert len(cycles) > 0
        for cycle in cycles:
            assert cycle.detection_method == "signal"


class TestPeriodEstimation:
    """Test period estimation methods (FFT and autocorrelation)."""

    def test_fft_period_estimation_simple_sine(self):
        """Test FFT-based period estimation on simple sine wave."""
        # Create sine wave with 30-sample period
        period = 30
        data = np.array([
            np.sin(2 * np.pi * i / period) for i in range(300)
        ])

        estimated_period = CycleDetector._estimate_period_by_fft(data)

        # FFT should estimate period close to 30
        assert estimated_period is not None
        # Allow 20% tolerance
        assert 24 <= estimated_period <= 36

    def test_fft_period_estimation_insufficient_data(self):
        """Test FFT-based period estimation with very short data."""
        data = np.array([1.0, 2.0])

        estimated_period = CycleDetector._estimate_period_by_fft(data)

        # Should handle gracefully
        assert estimated_period is None or estimated_period > 0

    def test_autocorrelation_period_estimation(self):
        """Test autocorrelation-based period estimation."""
        # Create repeating pattern with 40-sample period
        period = 40
        pattern = np.array([i % 20 for i in range(period)])
        data = np.tile(pattern, 5)  # Repeat 5 times

        estimated_period = CycleDetector._estimate_period_by_autocorrelation(data)

        # Autocorrelation should estimate period close to 40
        assert estimated_period is not None
        assert estimated_period > 10  # Should detect periodicity


class TestAnomalyDetection:
    """Test anomaly boundary detection for cycle boundaries."""

    def test_anomaly_detection_step_changes(self):
        """Test anomaly detection with clear step changes."""
        # Create data with step changes
        data = np.concatenate([
            np.ones(30) * 50.0,      # Steady at 50
            np.ones(30) * 100.0,     # Jump to 100
            np.ones(30) * 50.0,      # Jump back to 50
            np.ones(30) * 100.0      # Jump to 100
        ])

        anomalies = CycleDetector._detect_anomaly_boundaries(data)

        # Should detect anomalies around the step change points
        assert len(anomalies) > 0
        # Anomalies should include areas around indices 30 and 60
        anomaly_ranges = [a for a in anomalies if 20 < a < 40] + [a for a in anomalies if 50 < a < 70]
        assert len(anomaly_ranges) > 0

    def test_anomaly_detection_noisy_data(self):
        """Test anomaly detection on noisy data."""
        np.random.seed(42)
        # Create steady data with noise
        data = np.random.normal(50.0, 2.0, 100)

        anomalies = CycleDetector._detect_anomaly_boundaries(data)

        # Should detect few anomalies in random noise
        assert len(anomalies) < 20  # Fewer than 20% of data


class TestEnsembleEstimation:
    """Test ensemble voting for period estimation."""

    def test_ensemble_both_methods_agree(self):
        """Test ensemble voting when both FFT and ACF methods agree."""
        fft_period = 60
        acf_period = 62
        anomaly_count = 5

        estimated = CycleDetector._ensemble_period_estimation(fft_period, acf_period, anomaly_count)

        # Should return average of the two
        assert estimated is not None
        assert 60 <= estimated <= 62

    def test_ensemble_only_fft_available(self):
        """Test ensemble voting with only FFT available."""
        fft_period = 60
        acf_period = None
        anomaly_count = 3

        estimated = CycleDetector._ensemble_period_estimation(fft_period, acf_period, anomaly_count)

        # Should return FFT period
        assert estimated == 60

    def test_ensemble_fallback_to_anomaly_count(self):
        """Test ensemble voting fallback to anomaly count."""
        fft_period = None
        acf_period = None
        anomaly_count = 10

        estimated = CycleDetector._ensemble_period_estimation(fft_period, acf_period, anomaly_count)

        # Should return anomaly count as estimate
        assert estimated == 10

    def test_ensemble_all_methods_fail(self):
        """Test ensemble voting when all methods fail."""
        fft_period = None
        acf_period = None
        anomaly_count = 0

        estimated = CycleDetector._ensemble_period_estimation(fft_period, acf_period, anomaly_count)

        # Should return None when no valid period found
        assert estimated is None


class TestStatusDetermination:
    """Test cycle status determination logic."""

    def test_status_normal(self, sample_cycle_config: CycleConfiguration):
        """Test that normal cycle gets 'normal' status."""
        status = CycleDetector._determine_status(60.0, sample_cycle_config)
        assert status == "normal"

    def test_status_too_long(self, sample_cycle_config: CycleConfiguration):
        """Test that long cycle gets 'too_long' status."""
        status = CycleDetector._determine_status(70.0, sample_cycle_config)
        assert status == "too_long"

    def test_status_too_short(self, sample_cycle_config: CycleConfiguration):
        """Test that short cycle gets 'too_short' status."""
        status = CycleDetector._determine_status(45.0, sample_cycle_config)
        assert status == "too_short"

    def test_status_boundary_min(self, sample_cycle_config: CycleConfiguration):
        """Test status at minimum boundary (inclusive)."""
        status = CycleDetector._determine_status(55.0, sample_cycle_config)
        assert status == "normal"

    def test_status_boundary_max(self, sample_cycle_config: CycleConfiguration):
        """Test status at maximum boundary (inclusive)."""
        status = CycleDetector._determine_status(65.0, sample_cycle_config)
        assert status == "normal"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_timeseries_data(
        self,
        db_session: Session,
        sample_cycle_config: CycleConfiguration
    ):
        """Test detection with empty time series data."""
        cycles = CycleDetector.detect_cycles([], sample_cycle_config, db_session)
        assert cycles == []

    def test_single_data_point(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType
    ):
        """Test detection with single data point."""
        config = CycleConfiguration(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            target_cycle_time=60.0,
            min_cycle_time=55.0,
            max_cycle_time=65.0,
            pattern_detection_enabled=False
        )
        db_session.add(config)
        db_session.commit()

        data = [TimeseriesData(
            equipment_id=sample_equipment.id,
            timestamp=datetime.now(),
            data_point=50.0
        )]

        cycles = CycleDetector.detect_cycles(data, config, db_session)
        assert cycles == []

    def test_zero_duration_cycle(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType,
        sample_cycle_config: CycleConfiguration
    ):
        """Test handling of zero-duration cycles."""
        base_time = datetime.now()
        data_points = []

        # Create start and end signals at same timestamp
        data_points.append(TimeseriesData(
            equipment_id=sample_equipment.id,
            timestamp=base_time,
            data_point=50.0,
            signal_name="CYCLE_START"
        ))
        data_points.append(TimeseriesData(
            equipment_id=sample_equipment.id,
            timestamp=base_time,  # Same timestamp!
            data_point=50.0,
            signal_name="CYCLE_END"
        ))

        db_session.add_all(data_points)
        db_session.commit()

        cycles = CycleDetector.detect_cycles(data_points, sample_cycle_config, db_session)

        # Should handle zero duration gracefully
        assert all(c.cycle_duration == 0.0 for c in cycles)

    def test_nan_values_in_data(
        self,
        db_session: Session,
        sample_equipment: Equipment,
        sample_product_type: ProductType
    ):
        """Test handling of NaN values in time series data."""
        config = CycleConfiguration(
            equipment_id=sample_equipment.id,
            product_type_id=sample_product_type.id,
            target_cycle_time=60.0,
            min_cycle_time=55.0,
            max_cycle_time=65.0,
            pattern_detection_enabled=True
        )
        db_session.add(config)
        db_session.commit()

        base_time = datetime.now()
        data_points = [
            TimeseriesData(
                equipment_id=sample_equipment.id,
                timestamp=base_time + timedelta(seconds=i),
                data_point=float('nan') if i % 10 == 0 else 50.0
            )
            for i in range(50)
        ]
        db_session.add_all(data_points)
        db_session.commit()

        # Should not crash on NaN values
        cycles = CycleDetector.detect_cycles(data_points, config, db_session)
        # Results may vary, but should not raise exception
        assert isinstance(cycles, list)
