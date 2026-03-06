import React, { useState } from 'react'
import { AlertCircle, CheckCircle, Trash2, AlertTriangle } from 'lucide-react'

interface Alert {
  id: number
  equipment_id: number
  alert_type: string
  severity: string
  message: string
  cycle_time: number
  threshold_min: number
  threshold_max: number
  created_at: string
  is_acknowledged?: boolean
}

interface AlertPanelProps {
  alerts: Alert[]
  equipmentName?: string
  onAcknowledge?: (alertId: number) => void
  onDismiss?: (alertId: number) => void
  isLoading?: boolean
}

export default function AlertPanel({
  alerts,
  equipmentName,
  onAcknowledge,
  onDismiss,
  isLoading = false
}: AlertPanelProps) {
  const [selectedAlertId, setSelectedAlertId] = useState<number | null>(null)

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'warning':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'info':
        return 'text-blue-600 bg-blue-50 border-blue-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertCircle className="w-5 h-5 text-red-600" />
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-600" />
      default:
        return <AlertCircle className="w-5 h-5 text-gray-600" />
    }
  }

  const getAlertTypeLabel = (type: string) => {
    switch (type) {
      case 'cycle_too_long':
        return '⏱️ Cycle Too Long'
      case 'cycle_too_short':
        return '⚡ Cycle Too Short'
      default:
        return type
    }
  }

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        <h3 className="font-semibold text-gray-900">Alerts</h3>
        <div className="flex items-center justify-center h-20">
          <p className="text-gray-500">Loading alerts...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center">
        <h3 className="font-semibold text-gray-900">
          Alerts
          {alerts.length > 0 && (
            <span className="ml-2 text-sm font-normal text-gray-600">
              ({alerts.length})
            </span>
          )}
        </h3>
        {equipmentName && (
          <span className="text-xs text-gray-500">{equipmentName}</span>
        )}
      </div>

      {alerts.length === 0 ? (
        <div className="text-center py-6 bg-gray-50 rounded-lg">
          <p className="text-gray-500">No active alerts</p>
          <p className="text-xs text-gray-400 mt-1">All systems operating normally</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`border rounded-lg p-3 cursor-pointer transition ${
                selectedAlertId === alert.id
                  ? `${getSeverityColor(alert.severity)} border-current`
                  : getSeverityColor(alert.severity)
              }`}
              onClick={() => setSelectedAlertId(selectedAlertId === alert.id ? null : alert.id)}
            >
              {/* Alert Header */}
              <div className="flex items-start gap-2">
                <div className="flex-shrink-0 mt-0.5">
                  {getSeverityIcon(alert.severity)}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold text-sm">
                      {getAlertTypeLabel(alert.alert_type)}
                    </h4>
                    <span className="text-xs opacity-75">
                      {formatTime(alert.created_at)}
                    </span>
                  </div>

                  <p className="text-sm mt-0.5">{alert.message}</p>

                  {/* Details (shown when selected) */}
                  {selectedAlertId === alert.id && (
                    <div className="mt-2 pt-2 border-t opacity-80 space-y-1">
                      <div className="text-xs">
                        <span className="font-semibold">Cycle Time:</span> {alert.cycle_time.toFixed(1)}s
                      </div>
                      <div className="text-xs">
                        <span className="font-semibold">Range:</span> {alert.threshold_min.toFixed(1)}s - {alert.threshold_max.toFixed(1)}s
                      </div>
                      <div className="text-xs">
                        <span className="font-semibold">Deviation:</span>
                        {alert.alert_type === 'cycle_too_long' ? (
                          ` +${(alert.cycle_time - alert.threshold_max).toFixed(1)}s over max`
                        ) : (
                          ` -${(alert.threshold_min - alert.cycle_time).toFixed(1)}s below min`
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex-shrink-0 flex gap-1">
                  {!alert.is_acknowledged && onAcknowledge && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onAcknowledge(alert.id)
                      }}
                      className="p-1 hover:opacity-80 transition"
                      title="Acknowledge"
                    >
                      <CheckCircle className="w-4 h-4" />
                    </button>
                  )}

                  {onDismiss && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onDismiss(alert.id)
                      }}
                      className="p-1 hover:opacity-80 transition"
                      title="Dismiss"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
