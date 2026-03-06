"""WebSocket client service for real-time updates."""

export type WebSocketMessageType =
  | 'cycle_completed'
  | 'alert_created'
  | 'equipment_status_changed'
  | 'active_cycle'
  | 'equipment_status'
  | 'equipment_alerts'
  | 'ping'
  | 'pong'
  | 'error'

export interface WebSocketMessage {
  type: WebSocketMessageType
  equipment_id?: number
  data?: any
  message?: string
  timestamp?: string
  [key: string]: any
}

interface WebSocketListener {
  (message: WebSocketMessage): void
}

class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 3000
  private heartbeatInterval: NodeJS.Timeout | null = null
  private messageListeners: Map<WebSocketMessageType, Set<WebSocketListener>> = new Map()
  private globalListeners: Set<WebSocketListener> = new Set()
  private isConnecting = false
  private isIntentionallyClosed = false

  constructor(baseUrl: string = '') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    this.url = baseUrl || `${protocol}//${window.location.host}`
  }

  /**
   * Connect to WebSocket endpoint
   * @param endpoint - WebSocket endpoint path (e.g., '/ws/realtime' or '/ws/equipment/1')
   */
  connect(endpoint: string = '/ws/realtime'): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        console.log('WebSocket already connected')
        resolve()
        return
      }

      if (this.isConnecting) {
        console.log('WebSocket connection already in progress')
        return
      }

      this.isConnecting = true
      this.isIntentionallyClosed = false
      const wsUrl = `${this.url}${endpoint}`

      console.log(`Connecting to WebSocket: ${wsUrl}`)

      try {
        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          console.log('WebSocket connected')
          this.isConnecting = false
          this.reconnectAttempts = 0
          this.startHeartbeat()
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data) as WebSocketMessage
            this.handleMessage(message)
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e)
          }
        }

        this.ws.onerror = (event) => {
          console.error('WebSocket error:', event)
          this.isConnecting = false
          reject(new Error('WebSocket connection failed'))
        }

        this.ws.onclose = () => {
          console.log('WebSocket disconnected')
          this.isConnecting = false
          this.stopHeartbeat()

          if (!this.isIntentionallyClosed) {
            this.attemptReconnect(endpoint)
          }
        }
      } catch (e) {
        this.isConnecting = false
        reject(e)
      }
    })
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    console.log('Disconnecting from WebSocket')
    this.isIntentionallyClosed = true
    this.stopHeartbeat()

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * Send message to WebSocket server
   */
  send(message: WebSocketMessage): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected')
      return
    }

    try {
      this.ws.send(JSON.stringify(message))
    } catch (e) {
      console.error('Failed to send WebSocket message:', e)
    }
  }

  /**
   * Send ping for heartbeat
   */
  private sendPing(): void {
    this.send({
      type: 'ping',
      timestamp: new Date().toISOString()
    })
  }

  /**
   * Handle incoming WebSocket message
   */
  private handleMessage(message: WebSocketMessage): void {
    // Notify global listeners
    this.globalListeners.forEach(listener => {
      try {
        listener(message)
      } catch (e) {
        console.error('Error in global WebSocket listener:', e)
      }
    })

    // Notify type-specific listeners
    const typeListeners = this.messageListeners.get(message.type)
    if (typeListeners) {
      typeListeners.forEach(listener => {
        try {
          listener(message)
        } catch (e) {
          console.error(`Error in WebSocket listener for ${message.type}:`, e)
        }
      })
    }
  }

  /**
   * Subscribe to specific message type
   */
  on(messageType: WebSocketMessageType, listener: WebSocketListener): () => void {
    if (!this.messageListeners.has(messageType)) {
      this.messageListeners.set(messageType, new Set())
    }

    const listeners = this.messageListeners.get(messageType)!
    listeners.add(listener)

    // Return unsubscribe function
    return () => {
      listeners.delete(listener)
    }
  }

  /**
   * Subscribe to all messages
   */
  onAny(listener: WebSocketListener): () => void {
    this.globalListeners.add(listener)

    // Return unsubscribe function
    return () => {
      this.globalListeners.delete(listener)
    }
  }

  /**
   * Request equipment status
   */
  requestEquipmentStatus(equipmentId: number): void {
    this.send({
      type: 'ping' as any, // Using ping as request type
      equipment_id: equipmentId,
      timestamp: new Date().toISOString()
    })
  }

  /**
   * Request active cycle data
   */
  requestActiveCycle(equipmentId: number): void {
    this.send({
      type: 'ping' as any,
      equipment_id: equipmentId,
      timestamp: new Date().toISOString()
    })
  }

  /**
   * Request alerts for equipment
   */
  requestAlerts(equipmentId: number): void {
    this.send({
      type: 'ping' as any,
      equipment_id: equipmentId,
      timestamp: new Date().toISOString()
    })
  }

  /**
   * Get connection status
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  /**
   * Attempt to reconnect
   */
  private attemptReconnect(endpoint: string): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`)

    setTimeout(() => {
      this.connect(endpoint).catch(e => {
        console.error('Reconnection failed:', e)
      })
    }, delay)
  }

  /**
   * Start heartbeat ping
   */
  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected()) {
        this.sendPing()
      }
    }, 30000) // Ping every 30 seconds
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }
}

// Export singleton instance
export const wsClient = new WebSocketClient()

// Export class for testing
export { WebSocketClient }
