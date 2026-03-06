"""Hybrid Cycle Detection Engine (Signal-based + Pattern-based).

This module implements cycle detection using a hybrid approach combining:

1. **Signal-Based Detection**:
   - Looks for explicit cycle_start_signal and cycle_end_signal markers in data
   - Simple, fast, and accurate when signals are available
   - Assumes PLC or sensor provides clear cycle markers

2. **Pattern-Based Detection** (FFT + Autocorrelation + Anomaly Detection):
   - **Fast Fourier Transform (FFT)**: Detects periodicity by finding dominant frequencies
   - **Autocorrelation**: Identifies repeating patterns by measuring self-similarity
   - **Statistical Anomaly Detection**: Uses Z-score to find cycle boundaries
   - Useful when explicit signals are unavailable

3. **Hybrid Mode** (Combined):
   - Uses signal-based when signals available (higher confidence: 1.0)
   - Falls back to pattern-based when signals missing (confidence: 0.7-0.75)
   - Provides maximum flexibility and robustness
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session

from backend.models import TimeseriesData, CycleLabel, CycleConfiguration
from config.constants import (
    PATTERN_MIN_DATA_POINTS,
    PATTERN_MIN_PERIOD,
    ANOMALY_ZSCORE_THRESHOLD,
    AUTOCORRELATION_THRESHOLD,
    CONFIDENCE_SIGNAL_BASED,
    CONFIDENCE_ANOMALY_BASED,
    CONFIDENCE_PATTERN_BASED,
    ROLLING_WINDOW_BASE_DIVISOR,
    ROLLING_WINDOW_MIN_SIZE,
    MIN_CYCLE_DURATION_SECONDS,
)

logger = logging.getLogger(__name__)


class CycleDetector:
    """
    Hybrid Cycle Detection Engine for time series data.

    This class implements cycle detection using a hybrid approach combining:

    1. **Signal-Based Detection**:
       - Looks for explicit cycle_start_signal and cycle_end_signal markers in data
       - Simple, fast, and accurate when signals are available
       - Assumes PLC or sensor provides clear cycle markers

    2. **Pattern-Based Detection** (FFT + Autocorrelation + Anomaly Detection):
       - **Fast Fourier Transform (FFT)**: Detects periodicity by finding dominant frequencies
       - **Autocorrelation**: Identifies repeating patterns by measuring self-similarity
       - **Statistical Anomaly Detection**: Uses Z-score to find cycle boundaries
       - Useful when explicit signals are unavailable

    3. **Hybrid Mode** (Combined):
       - Uses signal-based when signals available (higher confidence: 1.0)
       - Falls back to pattern-based when signals missing (confidence: 0.7-0.75)
       - Provides maximum flexibility and robustness

    Example:
        >>> detector = CycleDetector()
        >>> cycles = detector.detect_cycles(
        ...     timeseries_data=data_points,
        ...     config=cycle_config,
        ...     db=session
        ... )
        >>> print(f"Detected {len(cycles)} cycles")
    """

    @staticmethod
    def detect_cycles(
        timeseries_data: List[TimeseriesData],
        config: CycleConfiguration,
        db: Session
    ) -> List[CycleLabel]:
        """
        Main detection method that combines signal and pattern-based approaches.

        Args:
            timeseries_data: List of time series data points
            config: Cycle configuration with thresholds and signal names
            db: Database session

        Returns:
            List of detected CycleLabel objects
        """
        if not timeseries_data:
            logger.warning(f"No timeseries data provided for equipment {config.equipment_id}")
            return []

        logger.info(
            f"Starting cycle detection for equipment {config.equipment_id}, "
            f"{len(timeseries_data)} data points"
        )

        cycles = []

        # Try signal-based detection first
        if config.cycle_start_signal and config.cycle_end_signal:
            logger.debug(f"Attempting signal-based detection with signals: "
                        f"{config.cycle_start_signal}, {config.cycle_end_signal}")
            signal_cycles = CycleDetector._detect_by_signal(
                timeseries_data,
                config
            )
            logger.info(f"Signal-based detection found {len(signal_cycles)} cycles")
            cycles.extend(signal_cycles)

        # Try pattern-based detection if enabled
        if config.pattern_detection_enabled and not cycles:
            logger.debug("Attempting pattern-based detection")
            pattern_cycles = CycleDetector._detect_by_pattern(
                timeseries_data,
                config
            )
            logger.info(f"Pattern-based detection found {len(pattern_cycles)} cycles")
            cycles.extend(pattern_cycles)

        # Persist cycles to database
        if cycles:
            for cycle in cycles:
                db.add(cycle)
            db.commit()
            logger.info(f"Persisted {len(cycles)} cycles to database")

        return cycles

    @staticmethod
    def _detect_by_signal(
        timeseries_data: List[TimeseriesData],
        config: CycleConfiguration
    ) -> List[CycleLabel]:
        """
        Signal-based cycle detection using explicit start/end markers.

        Strategy:
        1. Find all occurrences of cycle_start_signal
        2. For each start, find the next cycle_end_signal
        3. Create CycleLabel for the period between start and end

        Args:
            timeseries_data: Time series data points
            config: Configuration with signal names

        Returns:
            List of detected cycles
        """
        cycles = []

        if not config.cycle_start_signal or not config.cycle_end_signal:
            return cycles

        # Find signal occurrences
        start_indices = []
        end_indices = []

        for idx, point in enumerate(timeseries_data):
            if point.signal_name == config.cycle_start_signal:
                start_indices.append(idx)
            elif point.signal_name == config.cycle_end_signal:
                end_indices.append(idx)

        if not start_indices or not end_indices:
            logger.warning(
                f"No signal markers found. "
                f"Start signals: {len(start_indices)}, End signals: {len(end_indices)}"
            )
            return cycles

        # Match starts with ends
        for start_idx in start_indices:
            # Find next end signal after this start
            matching_ends = [idx for idx in end_indices if idx > start_idx]
            if not matching_ends:
                continue

            end_idx = matching_ends[0]
            start_time = timeseries_data[start_idx].timestamp
            end_time = timeseries_data[end_idx].timestamp

            # Calculate cycle duration in seconds
            cycle_duration = (end_time - start_time).total_seconds()

            # Determine status based on thresholds
            status = CycleDetector._determine_status(cycle_duration, config)

            cycle = CycleLabel(
                equipment_id=config.equipment_id,
                product_type_id=config.product_type_id,
                start_time=start_time,
                end_time=end_time,
                cycle_duration=cycle_duration,
                detection_method="signal",
                confidence=CONFIDENCE_SIGNAL_BASED,
                status=status
            )
            cycles.append(cycle)

            logger.debug(
                f"Signal-based cycle detected: {start_time} to {end_time}, "
                f"duration {cycle_duration}s, status {status}"
            )

        return cycles

    @staticmethod
    def _detect_by_pattern(
        timeseries_data: List[TimeseriesData],
        config: CycleConfiguration
    ) -> List[CycleLabel]:
        """
        Pattern-based cycle detection using statistical methods.

        Combines three methods:
        1. FFT (Fast Fourier Transform): Detect periodicity
        2. Autocorrelation: Find repeating patterns
        3. Statistical Anomaly: Identify cycle boundaries

        Args:
            timeseries_data: Time series data points
            config: Configuration with thresholds

        Returns:
            List of detected cycles
        """
        cycles = []

        # Extract data points and timestamps
        values = np.array([point.data_point for point in timeseries_data])
        timestamps = [point.timestamp for point in timeseries_data]

        if len(values) < PATTERN_MIN_DATA_POINTS:
            logger.warning(
                f"Insufficient data for pattern detection: {len(values)} points "
                f"(minimum: {PATTERN_MIN_DATA_POINTS})"
            )
            return cycles

        # Method 1: Estimate period using FFT
        try:
            fft_period = CycleDetector._estimate_period_by_fft(values)
            logger.debug(f"FFT estimated period: {fft_period} samples")
        except Exception as e:
            logger.warning(f"FFT period estimation failed: {e}")
            fft_period = None

        # Method 2: Estimate period using autocorrelation
        try:
            acf_period = CycleDetector._estimate_period_by_autocorrelation(values)
            logger.debug(f"Autocorrelation estimated period: {acf_period} samples")
        except Exception as e:
            logger.warning(f"Autocorrelation period estimation failed: {e}")
            acf_period = None

        # Method 3: Detect anomaly boundaries
        try:
            anomaly_indices = CycleDetector._detect_anomaly_boundaries(values)
            logger.debug(f"Found {len(anomaly_indices)} anomaly boundary points")
        except Exception as e:
            logger.warning(f"Anomaly detection failed: {e}")
            anomaly_indices = []

        # Ensemble voting for period estimation
        estimated_period = CycleDetector._ensemble_period_estimation(
            fft_period,
            acf_period,
            len(anomaly_indices)
        )

        if not estimated_period or estimated_period < PATTERN_MIN_PERIOD:
            logger.warning(
                f"Invalid estimated period: {estimated_period}, "
                f"minimum required: {PATTERN_MIN_PERIOD}, skipping cycle generation"
            )
            return cycles

        logger.debug(f"Ensemble estimated period: {estimated_period} samples")

        # Generate cycles using anomaly boundaries and period
        cycles = CycleDetector._generate_cycles_from_boundaries(
            timestamps,
            values,
            anomaly_indices,
            estimated_period,
            config
        )

        return cycles

    @staticmethod
    def _estimate_period_by_fft(data: np.ndarray) -> Optional[int]:
        """
        Estimate cycle period using Fast Fourier Transform.

        FFT analyzes the frequency spectrum of the time series to identify the
        dominant frequency component, which corresponds to the cycle period.

        Algorithm:
        1. Apply FFT to the data (after mean normalization)
        2. Calculate magnitude spectrum
        3. Find the peak in positive frequencies (excluding DC component)
        4. Convert frequency to period using: period = 1 / frequency

        Advantages:
        - Fast O(n log n) computation
        - Effective for periodic signals
        - Robust to noise for clear patterns

        Limitations:
        - Requires at least one complete cycle in data
        - Sensitive to non-periodic components
        - May miss secondary periodicities

        Args:
            data: Input time series as numpy array

        Returns:
            Estimated period in samples, or None if unable to estimate

        Raises:
            Silently catches exceptions and returns None to allow fallback
        """
        try:
            from scipy.fft import fft, fftfreq

            # Apply FFT
            n = len(data)
            fft_values = np.abs(fft(data - np.mean(data)))
            frequencies = fftfreq(n)

            # Find peak in positive frequencies (skip DC component)
            positive_freqs = frequencies[:n // 2]
            positive_fft = fft_values[:n // 2]

            if len(positive_fft) < 2:
                return None

            # Find the frequency with maximum power (excluding DC)
            peak_idx = np.argmax(positive_fft[1:]) + 1

            if positive_freqs[peak_idx] > 0:
                period = int(1 / positive_freqs[peak_idx])
                return period if period > 0 else None
            return None
        except Exception as e:
            logger.warning(f"FFT estimation error: {e}")
            return None

    @staticmethod
    def _estimate_period_by_autocorrelation(data: np.ndarray) -> Optional[int]:
        """
        Estimate cycle period using autocorrelation analysis.

        Autocorrelation measures how much a signal resembles itself at different lags.
        For periodic signals, peaks occur at multiples of the period.

        Algorithm:
        1. Normalize the data (zero mean, unit variance)
        2. Compute autocorrelation using scipy.signal.correlate
        3. Find the first significant peak (correlation > 0.5) after lag 1
        4. The lag of this peak is the estimated period

        Mathematical Basis:
        - ACF(k) = sum((x[i] - mean) * (x[i+k] - mean)) / variance
        - For periodic data with period P, ACF(P) ≈ ACF(0)

        Advantages:
        - Robust to amplitude variations
        - Works well with noisy periodic signals
        - Identifies fundamental period reliably

        Limitations:
        - Computationally more expensive than FFT
        - May fail with very short data sequences
        - Sensitive to trend in non-stationary signals

        Args:
            data: Input time series as normalized numpy array

        Returns:
            Estimated period in samples (lag), or None if unable to estimate

        Raises:
            Silently catches exceptions and returns None to allow fallback
        """
        try:
            from scipy import signal

            # Normalize data
            data_norm = (data - np.mean(data)) / np.std(data)

            # Calculate autocorrelation
            autocorr = signal.correlate(data_norm, data_norm, mode='full')
            autocorr = autocorr / np.max(autocorr)

            # Get only the second half (positive lags)
            mid = len(autocorr) // 2
            autocorr = autocorr[mid:]

            # Find first significant peak (> threshold) after lag 1
            peaks = np.where(autocorr[1:] > AUTOCORRELATION_THRESHOLD)[0] + 1

            if len(peaks) > 0:
                return int(peaks[0])
            return None
        except Exception as e:
            logger.warning(f"Autocorrelation estimation error: {e}")
            return None

    @staticmethod
    def _detect_anomaly_boundaries(data: np.ndarray) -> List[int]:
        """
        Detect cycle boundaries using statistical anomaly detection.

        Cycle transitions typically exhibit statistical anomalies as the
        equipment changes from one operational state to another.

        Algorithm:
        1. Compute rolling mean with window size = max(5, len(data) / 20)
        2. Compute rolling standard deviation
        3. Calculate Z-scores: z = |value - rolling_mean| / rolling_std
        4. Flag points where |z| > 2.5 as anomalies
        5. Return sorted indices of anomalous points

        Why Z-score > 2.5?
        - Standard normal: 99.4% of values have |z| < 3
        - Z > 2.5 represents ~1.2% tail probability
        - Balances sensitivity and false positive rate
        - Tuned for cycle transition detection

        Rolling Window Rationale:
        - window = len(data) / 20: Adaptive to data length
        - Captures local deviations without being distracted by long-term trends
        - Minimum of 5 samples: Ensures statistical stability

        Use Cases:
        - Detecting abrupt changes in machine behavior
        - Identifying when equipment switches modes
        - Finding cycle start/end points without explicit signals

        Limitations:
        - Assumes relatively stationary data between transitions
        - May miss gradual drift-type anomalies
        - Sensitive to outliers that aren't cycle boundaries

        Args:
            data: Input time series as numpy array

        Returns:
            List of indices where anomalies (likely cycle boundaries) occur
            Empty list if unable to detect anomalies
        """
        try:
            window = max(ROLLING_WINDOW_MIN_SIZE, len(data) // ROLLING_WINDOW_BASE_DIVISOR)
            rolling_mean = np.convolve(data, np.ones(window) / window, mode='same')
            rolling_std = np.array([
                np.std(data[max(0, i - window):i + window])
                for i in range(len(data))
            ])

            # Avoid division by zero
            rolling_std = np.where(rolling_std == 0, 1e-6, rolling_std)

            # Calculate Z-scores
            z_scores = np.abs((data - rolling_mean) / rolling_std)

            # Anomalies are points with Z-score > threshold
            anomalies = np.where(z_scores > ANOMALY_ZSCORE_THRESHOLD)[0]

            return list(anomalies)
        except Exception as e:
            logger.warning(f"Anomaly detection error: {e}")
            return []

    @staticmethod
    def _ensemble_period_estimation(
        fft_period: Optional[int],
        acf_period: Optional[int],
        anomaly_count: int
    ) -> Optional[int]:
        """
        Combine multiple period estimation methods using ensemble voting.

        Strategy:
        - If both FFT and ACF agree (within 20%), use average
        - If only one is available, use it
        - Use anomaly_count as fallback
        """
        valid_periods = []

        if fft_period and fft_period > 0:
            valid_periods.append(fft_period)
        if acf_period and acf_period > 0:
            valid_periods.append(acf_period)

        if not valid_periods:
            # Fallback: use anomaly count to estimate period
            if anomaly_count >= 2:
                return max(5, anomaly_count)
            return None

        # Average the valid periods
        avg_period = int(np.mean(valid_periods))

        # Sanity check: period should be reasonable (>= 5 samples)
        return avg_period if avg_period >= 5 else None

    @staticmethod
    def _generate_cycles_from_boundaries(
        timestamps: List[datetime],
        values: np.ndarray,
        anomaly_indices: List[int],
        period: int,
        config: CycleConfiguration
    ) -> List[CycleLabel]:
        """
        Generate cycles from detected anomaly boundaries and estimated period.

        Combines anomaly points and periodic sampling to create complete cycles.
        """
        cycles = []

        if len(anomaly_indices) < 2:
            # Fallback: create cycles using periodic sampling
            logger.debug(f"Using periodic sampling with period {period}")
            for start_idx in range(0, len(timestamps) - period, period):
                end_idx = min(start_idx + period, len(timestamps) - 1)

                if start_idx == end_idx:
                    continue

                start_time = timestamps[start_idx]
                end_time = timestamps[end_idx]
                cycle_duration = (end_time - start_time).total_seconds()

                status = CycleDetector._determine_status(cycle_duration, config)

                cycle = CycleLabel(
                    equipment_id=config.equipment_id,
                    product_type_id=config.product_type_id,
                    start_time=start_time,
                    end_time=end_time,
                    cycle_duration=cycle_duration,
                    detection_method="pattern",
                    confidence=CONFIDENCE_PATTERN_BASED,
                    status=status
                )
                cycles.append(cycle)

        else:
            # Use anomaly indices as cycle boundaries
            logger.debug(f"Using anomaly boundaries to create cycles")
            for i in range(len(anomaly_indices) - 1):
                start_idx = anomaly_indices[i]
                end_idx = anomaly_indices[i + 1]

                if start_idx >= end_idx or start_idx >= len(timestamps):
                    continue

                start_time = timestamps[start_idx]
                end_time = timestamps[min(end_idx, len(timestamps) - 1)]
                cycle_duration = (end_time - start_time).total_seconds()

                # Skip cycles shorter than minimum threshold
                if cycle_duration < MIN_CYCLE_DURATION_SECONDS:
                    continue

                status = CycleDetector._determine_status(cycle_duration, config)

                cycle = CycleLabel(
                    equipment_id=config.equipment_id,
                    product_type_id=config.product_type_id,
                    start_time=start_time,
                    end_time=end_time,
                    cycle_duration=cycle_duration,
                    detection_method="pattern",
                    confidence=CONFIDENCE_ANOMALY_BASED,
                    status=status
                )
                cycles.append(cycle)

        return cycles

    @staticmethod
    def _determine_status(cycle_duration: float, config: CycleConfiguration) -> str:
        """
        Determine cycle status based on duration and configuration thresholds.

        Returns:
            'normal' if within thresholds, 'too_long' if exceeds max, 'too_short' if below min
        """
        if cycle_duration < config.min_cycle_time:
            return "too_short"
        elif cycle_duration > config.max_cycle_time:
            return "too_long"
        else:
            return "normal"
