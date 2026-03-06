# Algorithm Documentation

This document provides detailed explanations of complex algorithms used in the Cycle Time Monitoring System.

## Table of Contents

1. [Cycle Detection Algorithms](#cycle-detection-algorithms)
2. [Alert Generation Algorithms](#alert-generation-algorithms)
3. [Anomaly Detection](#anomaly-detection)
4. [Pattern Recognition](#pattern-recognition)

---

## Cycle Detection Algorithms

### Overview

The system uses a hybrid approach combining three cycle detection methods:

1. **Signal-Based Detection** - Uses explicit start/end markers
2. **Pattern-Based Detection** - Uses FFT and autocorrelation
3. **Anomaly Detection** - Uses statistical Z-score analysis

### Signal-Based Detection

**Purpose**: Detect cycles when explicit signal markers are available

**Algorithm**:

```
Input: timeseries_data, cycle_start_signal, cycle_end_signal
Output: List of CycleLabel objects

1. Find all indices where signal_name == cycle_start_signal
   start_indices = [i for i, point in enumerate(data)
                    if point.signal_name == cycle_start_signal]

2. Find all indices where signal_name == cycle_end_signal
   end_indices = [i for i, point in enumerate(data)
                  if point.signal_name == cycle_end_signal]

3. For each start_idx in start_indices:
     a. Find the first end_idx where end_idx > start_idx
     b. If no matching end found, skip
     c. Calculate cycle_duration = (end_time - start_time).total_seconds()
     d. Determine status (normal, too_long, too_short)
     e. Create CycleLabel with confidence=1.0 (high confidence)

4. Return all created cycles
```

**Confidence Score**: `1.0` (100%)

**Rationale**: Signal-based detection is the most accurate when signals are explicitly provided by the PLC or sensor system.

**Advantages**:
- High accuracy (explicit markers)
- Fast O(n) computation
- No false positives if signals are reliable

**Disadvantages**:
- Requires signals to be configured
- Doesn't work if signals are missing or malformed

---

### Fast Fourier Transform (FFT) Period Detection

**Purpose**: Detect periodicity in data by analyzing frequency spectrum

**Algorithm**:

```
Input: data (numpy array of values)
Output: estimated_period (int) or None

1. Apply FFT to mean-normalized data:
   fft_values = abs(fft(data - mean(data)))

2. Calculate frequency array:
   frequencies = fftfreq(len(data))

3. Extract positive frequencies (skip DC component):
   positive_freqs = frequencies[:n//2]
   positive_fft = fft_values[:n//2]

4. Find peak frequency:
   peak_idx = argmax(positive_fft[1:]) + 1

5. Convert frequency to period:
   period = int(1 / positive_freqs[peak_idx])
   return period if period > 0 else None
```

**Mathematical Basis**:

- FFT transforms time-domain signal to frequency domain
- Peak in frequency spectrum indicates dominant periodicity
- Period = 1 / frequency

**Complexity**: O(n log n) where n = number of data points

**Example**:

```
Signal with 20-sample period:
- FFT peak occurs at frequency = 0.05 Hz
- Period = 1 / 0.05 = 20 samples ✓
```

**Advantages**:
- Fast computation
- Effective for clear periodic patterns
- Robust to noise for strong signals

**Disadvantages**:
- Requires at least one complete cycle
- Sensitive to non-periodic components
- May miss secondary periodicities

---

### Autocorrelation-Based Period Detection

**Purpose**: Identify repeating patterns by measuring signal self-similarity

**Algorithm**:

```
Input: data (numpy array of values)
Output: estimated_period (int) or None

1. Normalize data:
   data_norm = (data - mean) / std_dev

2. Compute autocorrelation:
   acf = correlate(data_norm, data_norm, mode='full')
   acf = acf / max(acf)  # Normalize to 0-1

3. Extract positive lags (second half of correlation):
   mid = len(acf) // 2
   acf = acf[mid:]

4. Find first significant peak (correlation > THRESHOLD):
   threshold = 0.5  # AUTOCORRELATION_THRESHOLD
   peaks = where(acf[1:] > threshold)[0] + 1

5. Return the first peak index as period:
   return peaks[0] if len(peaks) > 0 else None
```

**Mathematical Basis**:

```
ACF(k) = Σ((x[i] - μ) * (x[i+k] - μ)) / σ²

For periodic signal with period P:
- ACF(P) ≈ ACF(0) (very similar to itself at P lag)
- ACF(2P) ≈ ACF(0) (repeats at multiples)
```

**Threshold Justification**:

- **Threshold = 0.5**: Indicates 50% correlation strength
- Higher threshold → fewer, stronger patterns
- Lower threshold → more patterns, but more false positives
- 0.5 is a good balance for typical manufacturing data

**Complexity**: O(n²) with naive implementation, O(n log n) with FFT acceleration

**Example**:

```
Data: [1, 2, 3, 1, 2, 3, 1, 2, 3, ...]  (period = 3)

ACF values at different lags:
- lag=0: 1.0 (perfect self-match)
- lag=1: 0.2 (low correlation)
- lag=2: 0.1 (low correlation)
- lag=3: 0.95 ← Peak! (almost perfect repeat)
- lag=4: 0.2 (low correlation)
- lag=6: 0.95 ← Another peak (at 2×period)

First peak at lag=3 → period = 3 ✓
```

**Advantages**:
- Robust to amplitude variations
- Works well with noisy signals
- Identifies fundamental period reliably

**Disadvantages**:
- Computationally expensive
- Fails with very short sequences
- Sensitive to data trends

---

### Ensemble Period Estimation

**Purpose**: Combine multiple period estimates for robustness

**Algorithm**:

```
Input: fft_period, acf_period, anomaly_count
Output: final_estimated_period (int) or None

1. Collect valid periods:
   valid_periods = []
   if fft_period > 0: valid_periods.append(fft_period)
   if acf_period > 0: valid_periods.append(acf_period)

2. If no valid periods from FFT/ACF:
     a. Fallback to anomaly-based estimate:
        if anomaly_count >= 2:
          return max(5, anomaly_count)  # PATTERN_MIN_PERIOD=5
        else:
          return None

3. If periods available:
     a. Average them: avg_period = int(mean(valid_periods))
     b. Sanity check: return avg_period if avg_period >= 5 else None

4. Return final estimate
```

**Voting Logic**:

| FFT | ACF | Anomaly Count | Decision |
|-----|-----|---------------|----------|
| 20  | 20  | 5             | Use 20 (strong consensus) |
| 20  | 22  | 5             | Use 21 (average, within tolerance) |
| 20  | None| 5             | Use 20 (FFT available) |
| None| 20  | 5             | Use 20 (ACF available) |
| None| None| 5             | Use 5 (anomaly count) |
| None| None| 0             | Return None (cannot estimate) |

**Advantages**:
- Increases confidence through consensus
- Graceful degradation if one method fails
- Fallback mechanism prevents complete failure

---

### Statistical Anomaly Detection (Z-Score)

**Purpose**: Identify cycle boundaries where machine behavior changes abruptly

**Algorithm**:

```
Input: data (numpy array)
Output: List of indices where anomalies occur

1. Calculate adaptive rolling window size:
   window = max(ROLLING_WINDOW_MIN_SIZE=5, len(data) // ROLLING_WINDOW_BASE_DIVISOR=20)

   Rationale: Smaller window = 5 samples for stability
              Larger window = len(data)/20 for adaptive scaling

2. Compute rolling statistics:
   rolling_mean = convolve(data, ones(window)/window)
   rolling_std = array of std_dev in window around each point

3. Normalize standard deviation:
   rolling_std = where(rolling_std == 0, 1e-6, rolling_std)
   (Prevent division by zero)

4. Calculate Z-scores:
   z_scores = abs((data - rolling_mean) / rolling_std)

   Z-score formula: z = (value - mean) / std_dev

5. Detect anomalies:
   anomalies = where(z_scores > ANOMALY_ZSCORE_THRESHOLD=2.5)[0]

6. Return indices of anomalous points
```

**Z-Score Threshold Justification**:

| Z-Score | Probability | Interpretation |
|---------|------------|-----------------|
| 1.0     | 68%        | Within 1 std dev (normal) |
| 2.0     | 95%        | Within 2 std devs (mostly normal) |
| 2.5     | 98.8%      | Within 2.5 std devs (rare) |
| 3.0     | 99.7%      | Beyond 3 std devs (very rare) |

**Selected Threshold = 2.5**:
- Represents ~1.2% tail probability
- Balances sensitivity (catch real transitions) and false positives (avoid noise)
- Tuned empirically for manufacturing equipment

**Rolling Window Rationale**:

```
Why adaptive window?

Data length: 1000 points
- Fixed window=20: May miss slow transitions
- Adaptive window = 1000/20 = 50: Captures broader trends

Why minimum of 5?
- Prevents window from becoming too small
- Ensures statistical stability (need at least 5 samples)
- Minimum confidence in rolling std calculation
```

**Example**:

```
Equipment starts cycle:
- Before: steady state, low variance
- At transition: rapid change in sensor value
- Z-score > 2.5 for several samples
- These flagged as anomaly boundaries

After cycle detection:
- Anomaly indices = [100, 200, 300]
- Cycles: 100→200, 200→300, etc.
```

**Advantages**:
- No need for pre-configured signals
- Detects abrupt changes automatically
- Robust to varying signal magnitudes

**Disadvantages**:
- Misses gradual drift-type anomalies
- Sensitive to outliers
- Requires sufficient data (min 10 points)

---

## Alert Generation Algorithms

### Cycle Anomaly Detection

**Purpose**: Determine if a cycle is anomalous and generate alerts

**Algorithm**:

```
Input: cycle (CycleLabel), config (CycleConfiguration)
Output: Alert object or None

1. Compare cycle duration to thresholds:

   if cycle.duration < config.min_cycle_time:
       alert_type = "cycle_too_short"

       # Determine severity
       critical_threshold = config.min_cycle_time * (1.0 / ALERT_SEVERITY_CRITICAL_FACTOR=1.2)

       if cycle.duration < critical_threshold:
           severity = "critical"
       else:
           severity = "warning"

   elif cycle.duration > config.max_cycle_time:
       alert_type = "cycle_too_long"

       # Determine severity
       critical_threshold = config.max_cycle_time * ALERT_SEVERITY_CRITICAL_FACTOR=1.2

       if cycle.duration > critical_threshold:
           severity = "critical"
       else:
           severity = "warning"

   else:
       # Within normal range
       return None

2. Create Alert record:
   alert = Alert(
       equipment_id=cycle.equipment_id,
       cycle_label_id=cycle.id,
       alert_type=alert_type,
       severity=severity,
       message=...,
       cycle_time=cycle.cycle_duration,
       threshold_min=config.min_cycle_time,
       threshold_max=config.max_cycle_time,
       is_acknowledged=False
   )

3. Persist to database and return
```

### Severity Calculation Example

**Scenario**: Cycle Too Long Alert

```
config.max_cycle_time = 300 seconds
ALERT_SEVERITY_CRITICAL_FACTOR = 1.2
critical_threshold = 300 × 1.2 = 360 seconds

Case 1: cycle.duration = 310 seconds
  310 < 360 → severity = "warning"
  Message: "Cycle slightly over limit, monitor closely"

Case 2: cycle.duration = 370 seconds
  370 > 360 → severity = "critical"
  Message: "Cycle significantly over limit, requires immediate attention"
```

---

## Anomaly Detection

### Confidence Scoring

The system assigns confidence scores based on detection method:

| Method | Confidence | Rationale |
|--------|-----------|-----------|
| Signal-Based | 1.0 (100%) | Explicit markers from PLC |
| Anomaly-Based | 0.75 (75%) | Statistical detection, slight uncertainty |
| Pattern-Based | 0.7 (70%) | Statistical estimation, more uncertainty |

**Usage**: Higher confidence cycles weighted more heavily in analytics

---

## Pattern Recognition

### Cycle Pattern Matching

**Purpose**: Identify similar cycles and detect deviations

**Algorithm**:

```
Input: current_cycle, historical_cycles
Output: similarity_score (0.0-1.0)

1. Extract features from current cycle:
   features = [duration, variance, shape]

2. Compare to historical patterns:
   for historical in historical_cycles:
       similarity = calculate_similarity(current, historical)
       if similarity > THRESHOLD:
           mark_as_pattern_match()

3. Return match results and confidence
```

---

## Performance Considerations

### Computational Complexity

| Algorithm | Complexity | Time (1000 points) |
|-----------|-----------|-------------------|
| FFT Period | O(n log n) | ~10 ms |
| Autocorrelation | O(n²) | ~100 ms |
| Anomaly Detection | O(n) | ~5 ms |
| Ensemble Voting | O(1) | <1 ms |

### Memory Usage

- FFT: O(n) - stores FFT array
- Autocorrelation: O(n) - stores correlation array
- Z-score: O(n) - stores rolling statistics

### Optimization Strategies

1. **Batch Processing**: Process multiple equipment in parallel
2. **Caching**: Store period estimates, reuse for similar data
3. **Sampling**: For very large datasets, use sampling
4. **Early Exit**: Stop processing if clear pattern found

---

## Configuration and Tuning

### Key Parameters

```python
# In config/constants.py
ANOMALY_ZSCORE_THRESHOLD = 2.5        # Z-score for anomaly detection
AUTOCORRELATION_THRESHOLD = 0.5       # Correlation threshold for ACF
PATTERN_MIN_DATA_POINTS = 10          # Minimum data for pattern detection
PATTERN_MIN_PERIOD = 5                # Minimum acceptable period
ROLLING_WINDOW_BASE_DIVISOR = 20      # Window size = data_length / 20
ROLLING_WINDOW_MIN_SIZE = 5           # Minimum window size
ALERT_SEVERITY_CRITICAL_FACTOR = 1.2  # Multiplier for critical severity
CONFIDENCE_SIGNAL_BASED = 1.0         # Signal detection confidence
CONFIDENCE_ANOMALY_BASED = 0.75       # Anomaly detection confidence
CONFIDENCE_PATTERN_BASED = 0.7        # Pattern detection confidence
MIN_CYCLE_DURATION_SECONDS = 1.0      # Skip cycles < 1 second
```

### Tuning Guide

**If Too Many False Alerts**:
- Increase `ANOMALY_ZSCORE_THRESHOLD` (e.g., 2.5 → 3.0)
- Increase `AUTOCORRELATION_THRESHOLD` (e.g., 0.5 → 0.6)
- Increase alert severity threshold

**If Missing Real Issues**:
- Decrease `ANOMALY_ZSCORE_THRESHOLD` (e.g., 2.5 → 2.0)
- Decrease `AUTOCORRELATION_THRESHOLD` (e.g., 0.5 → 0.4)
- Decrease alert severity threshold

**For More Stable Estimates**:
- Increase `ROLLING_WINDOW_MIN_SIZE` (e.g., 5 → 10)
- Increase `PATTERN_MIN_DATA_POINTS` (e.g., 10 → 20)

---

## References

- **FFT**: Cooley-Tukey Algorithm (O(n log n) Fast Fourier Transform)
- **Autocorrelation**: Wiener-Khinchin Theorem
- **Z-Score**: Standard Score in Normal Distribution
- **Ensemble Methods**: Bootstrap Aggregating (Bagging)

