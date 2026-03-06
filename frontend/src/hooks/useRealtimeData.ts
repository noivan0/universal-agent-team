import { useEffect, useState, useCallback } from 'react'
import { wsClient, WebSocketMessage } from '../services/websocket'

interface Cycle {
  start_time: string
  end_time: string
  cycle_duration: number
  status: 'normal' | 'too_long' | 'too_short'
  detection_method: string
  confidence: number
}

interface EquipmentStatus {
  id: number
  name: string
  status: string
  location?: string
  model?: string
}

interface Alert {
  id: number
  alert_type: string
  severity: string
  message: string
  cycle_time: number
  threshold_min: number
  threshold_max: number
  created_at: string
}

export function useRealtimeData(equipmentId?: number) {
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected')
  const [lastCycle, setLastCycle] = useState<Cycle | null>(null)
  const [activeCycle, setActiveCycle] = useState<any | null>(null)
  const [equipmentStatus, setEquipmentStatus] = useState<EquipmentStatus | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [recentEvents, setRecentEvents] = useState<WebSocketMessage[]>([])

  // Connect to WebSocket on mount
  useEffect(() => {
    const connectWebSocket = async () => {
      try {
        setConnectionStatus('connecting')
        const endpoint = equipmentId ? `/ws/equipment/${equipmentId}` : '/ws/realtime'
        await wsClient.connect(endpoint)
        setConnectionStatus('connected')
      } catch (error) {
        console.error('Failed to connect WebSocket:', error)
        setConnectionStatus('disconnected')
      }
    }

    connectWebSocket()

    return () => {
      // Don't disconnect on unmount to keep connection alive
      // wsClient.disconnect()
    }
  }, [equipmentId])

  // Listen to cycle completed events
  useEffect(() => {
    const unsubscribe = wsClient.on('cycle_completed', (message) => {
      if (!equipmentId || message.equipment_id === equipmentId) {
        setLastCycle(message.data)
        setRecentEvents(prev => [message, ...prev.slice(0, 9)])
      }
    })

    return unsubscribe
  }, [equipmentId])

  // Listen to active cycle updates
  useEffect(() => {
    const unsubscribe = wsClient.on('active_cycle', (message) => {
      if (!equipmentId || message.equipment_id === equipmentId) {
        setActiveCycle(message.data)
      }
    })

    return unsubscribe
  }, [equipmentId])

  // Listen to equipment status changes
  useEffect(() => {
    const unsubscribe = wsClient.on('equipment_status_changed', (message) => {
      if (!equipmentId || message.equipment_id === equipmentId) {
        if (equipmentStatus) {
          setEquipmentStatus({ ...equipmentStatus, status: message.status })
        }
        setRecentEvents(prev => [message, ...prev.slice(0, 9)])
      }
    })

    return unsubscribe
  }, [equipmentId, equipmentStatus])

  // Listen to alerts
  useEffect(() => {
    const unsubscribe = wsClient.on('alert_created', (message) => {
      if (!equipmentId || message.equipment_id === equipmentId) {
        setAlerts(prev => [message.data, ...prev])
        setRecentEvents(prev => [message, ...prev.slice(0, 9)])
      }
    })

    return unsubscribe
  }, [equipmentId])

  // Listen to equipment alerts list
  useEffect(() => {
    const unsubscribe = wsClient.on('equipment_alerts', (message) => {
      if (!equipmentId || message.equipment_id === equipmentId) {
        setAlerts(message.alerts || [])
      }
    })

    return unsubscribe
  }, [equipmentId])

  // Callback to request equipment status
  const requestStatus = useCallback(() => {
    if (equipmentId) {
      wsClient.requestEquipmentStatus(equipmentId)
    }
  }, [equipmentId])

  // Callback to request active cycle
  const requestActiveCycle = useCallback(() => {
    if (equipmentId) {
      wsClient.requestActiveCycle(equipmentId)
    }
  }, [equipmentId])

  // Callback to request alerts
  const requestAlerts = useCallback(() => {
    if (equipmentId) {
      wsClient.requestAlerts(equipmentId)
    }
  }, [equipmentId])

  return {
    connectionStatus,
    lastCycle,
    activeCycle,
    equipmentStatus,
    alerts,
    recentEvents,
    requestStatus,
    requestActiveCycle,
    requestAlerts,
    isConnected: connectionStatus === 'connected'
  }
}

// Hook for monitoring global real-time events
export function useGlobalRealtime() {
  const [events, setEvents] = useState<WebSocketMessage[]>([])
  const [lastAlert, setLastAlert] = useState<Alert | null>(null)
  const [lastCycle, setLastCycle] = useState<Cycle | null>(null)

  useEffect(() => {
    // Subscribe to all events
    const unsubscribe = wsClient.onAny((message) => {
      setEvents(prev => [message, ...prev.slice(0, 49)])

      // Extract specific types for easy access
      if (message.type === 'alert_created') {
        setLastAlert(message.data)
      } else if (message.type === 'cycle_completed') {
        setLastCycle(message.data)
      }
    })

    return unsubscribe
  }, [])

  return {
    events,
    lastAlert,
    lastCycle
  }
}
