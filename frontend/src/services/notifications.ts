"""Browser push notifications service."""

export class NotificationService {
  private static instance: NotificationService
  private isSupported: boolean = false
  private isPermissionGranted: boolean = false

  private constructor() {
    // Check if Notification API is supported
    this.isSupported = 'Notification' in window

    if (this.isSupported) {
      // Check if permission already granted
      this.isPermissionGranted = Notification.permission === 'granted'

      // Register service worker
      this.registerServiceWorker()
    }
  }

  static getInstance(): NotificationService {
    if (!NotificationService.instance) {
      NotificationService.instance = new NotificationService()
    }
    return NotificationService.instance
  }

  private registerServiceWorker(): void {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/service-worker.js')
        .then(registration => {
          console.log('Service Worker registered for notifications')
        })
        .catch(error => {
          console.warn('Service Worker registration failed:', error)
        })
    }
  }

  /**
   * Request notification permission from user
   */
  async requestPermission(): Promise<boolean> {
    if (!this.isSupported) {
      console.warn('Notifications not supported in this browser')
      return false
    }

    if (this.isPermissionGranted) {
      return true
    }

    try {
      const permission = await Notification.requestPermission()
      this.isPermissionGranted = permission === 'granted'
      return this.isPermissionGranted
    } catch (error) {
      console.error('Failed to request notification permission:', error)
      return false
    }
  }

  /**
   * Show a notification
   */
  notify(title: string, options?: NotificationOptions): Notification | null {
    if (!this.isSupported || !this.isPermissionGranted) {
      console.warn('Cannot show notification: not supported or permission denied')
      return null
    }

    const defaultOptions: NotificationOptions = {
      icon: '/icon-192x192.png',
      badge: '/badge-72x72.png',
      ...options
    }

    try {
      const notification = new Notification(title, defaultOptions)
      return notification
    } catch (error) {
      console.error('Failed to show notification:', error)
      return null
    }
  }

  /**
   * Show alert notification
   */
  notifyAlert(equipmentName: string, alertType: string, severity: string, message: string): void {
    const title = `⚠️ ${equipmentName} - Alert`

    const body = message.length > 100
      ? message.substring(0, 97) + '...'
      : message

    const options: NotificationOptions = {
      body,
      tag: `alert-${severity}`, // Replaces previous notifications with same tag
      requireInteraction: severity === 'critical' // Critical alerts require user interaction
    }

    // Add icon based on severity
    if (severity === 'critical') {
      options.badge = '/icon-alert-critical.png'
    } else if (severity === 'warning') {
      options.badge = '/icon-alert-warning.png'
    }

    const notification = this.notify(title, options)

    if (notification) {
      notification.onclick = () => {
        window.focus()
        notification.close()
      }
    }
  }

  /**
   * Show cycle completed notification
   */
  notifyCycleCompleted(equipmentName: string, cycleTime: number, status: string): void {
    const statusEmoji = status === 'normal' ? '✅' :
                       status === 'too_long' ? '⏱️' :
                       '⚡'

    const title = `${statusEmoji} Cycle Completed - ${equipmentName}`
    const body = `Cycle time: ${cycleTime.toFixed(1)}s (${status})`

    this.notify(title, {
      body,
      tag: 'cycle-completed'
    })
  }

  /**
   * Show in-app toast notification (if needed)
   */
  showToast(message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info'): void {
    // This could be enhanced with a toast library like react-hot-toast or sonner
    console.log(`[${type.toUpperCase()}] ${message}`)
  }

  isGranted(): boolean {
    return this.isPermissionGranted
  }

  isAvailable(): boolean {
    return this.isSupported
  }
}

// Export singleton
export const notificationService = NotificationService.getInstance()

// Convenience function for checking and requesting permissions
export async function initializeNotifications(): Promise<boolean> {
  const service = NotificationService.getInstance()

  if (!service.isAvailable()) {
    console.warn('Notifications not available in this browser')
    return false
  }

  if (service.isGranted()) {
    return true
  }

  // Request permission
  const granted = await service.requestPermission()

  if (granted) {
    console.log('Notification permission granted')
  } else {
    console.log('Notification permission denied')
  }

  return granted
}
