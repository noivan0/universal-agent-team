import React, { useMemo } from 'react'

interface CycleProgressBarProps {
  currentTime: number          // Current elapsed time in seconds
  targetTime: number           // Target cycle time in seconds
  minTime: number              // Minimum acceptable time
  maxTime: number              // Maximum acceptable time
  showLabel?: boolean          // Show percentage label
}

/**
 * CycleProgressBar Component
 * Optimizations:
 * - React.memo to prevent re-renders on identical props
 * - useMemo for expensive calculations
 * - Smooth transitions with CSS
 */
const CycleProgressBar = React.memo(function CycleProgressBar({
  currentTime,
  targetTime,
  minTime,
  maxTime,
  showLabel = true
}: CycleProgressBarProps) {
  // Memoize calculations to prevent recalculation on every render
  const { progressPercent, minPercent, maxPercent, barColor, statusText } = useMemo(() => {
    // Calculate percentages
    const progress = Math.min((currentTime / targetTime) * 100, 100)
    const min = (minTime / targetTime) * 100
    const max = (maxTime / targetTime) * 100

    // Determine color based on status
    let color: string
    if (currentTime < minTime) {
      color = 'bg-blue-500'  // Too fast (not reached minimum)
    } else if (currentTime <= targetTime) {
      color = 'bg-green-500' // On track (at or below target)
    } else if (currentTime <= maxTime) {
      color = 'bg-yellow-500' // Over target but within max
    } else {
      color = 'bg-red-500'    // Exceeding maximum
    }

    // Determine status text
    let status: string
    if (currentTime < minTime) {
      status = `${currentTime.toFixed(1)}s (Too Fast)`
    } else if (currentTime <= targetTime) {
      status = `${currentTime.toFixed(1)}s (On Track)`
    } else if (currentTime <= maxTime) {
      status = `${currentTime.toFixed(1)}s (Over Target)`
    } else {
      status = `${currentTime.toFixed(1)}s (Exceeded)`
    }

    return {
      progressPercent: progress,
      minPercent: min,
      maxPercent: max,
      barColor: color,
      statusText: status
    }
  }, [currentTime, targetTime, minTime, maxTime])

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium text-gray-700">Cycle Progress</span>
        {showLabel && (
          <span className="text-sm font-semibold text-gray-900">
            {statusText}
          </span>
        )}
      </div>

      {/* Main progress bar with threshold markers */}
      <div className="relative h-6 bg-gray-200 rounded-full overflow-hidden">
        {/* Min threshold marker */}
        <div
          className="absolute h-full w-0.5 bg-blue-300"
          style={{ left: `${minPercent}%` }}
          title={`Min: ${minTime.toFixed(1)}s`}
        />

        {/* Target marker */}
        <div
          className="absolute h-full w-0.5 bg-green-400"
          style={{ left: '100%' }}
          title={`Target: ${targetTime.toFixed(1)}s`}
        />

        {/* Max threshold marker */}
        <div
          className="absolute h-full w-0.5 bg-red-400"
          style={{ left: `${maxPercent}%` }}
          title={`Max: ${maxTime.toFixed(1)}s`}
        />

        {/* Progress fill with smooth animation */}
        <div
          className={`h-full ${barColor} transition-all duration-300 ease-out`}
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Labels */}
      <div className="flex justify-between text-xs text-gray-500">
        <span>{minTime.toFixed(1)}s</span>
        <span>{targetTime.toFixed(1)}s</span>
        <span>{maxTime.toFixed(1)}s</span>
      </div>
    </div>
  )
})
