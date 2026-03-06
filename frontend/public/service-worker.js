/**
 * Service Worker for handling push notifications
 */

const CACHE_NAME = 'cycle-monitor-v1'
const urlsToCache = [
  '/',
  '/index.html',
  '/manifest.json'
]

// Install event - cache resources
self.addEventListener('install', event => {
  console.log('[ServiceWorker] Installing...')

  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[ServiceWorker] Caching app shell')
        return cache.addAll(urlsToCache)
      })
  )

  // Immediately activate without waiting
  self.skipWaiting()
})

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[ServiceWorker] Activating...')

  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('[ServiceWorker] Deleting old cache:', cacheName)
            return caches.delete(cacheName)
          }
        })
      )
    })
  )

  self.clients.claim()
})

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return
  }

  // Skip API calls (let them go to network)
  if (event.request.url.includes('/api/') || event.request.url.includes('/ws')) {
    return
  }

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached response if available
        if (response) {
          return response
        }

        // Otherwise fetch from network
        return fetch(event.request)
          .then(response => {
            // Don't cache if not a successful response
            if (!response || response.status !== 200 || response.type === 'error') {
              return response
            }

            // Clone the response for caching
            const responseToCache = response.clone()

            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache)
              })

            return response
          })
      })
      .catch(error => {
        console.error('[ServiceWorker] Fetch error:', error)
        // Could return offline page here
      })
  )
})

// Handle push notifications
self.addEventListener('push', event => {
  console.log('[ServiceWorker] Received push notification:', event)

  let notificationData = {
    title: 'Cycle Monitor Alert',
    body: 'New alert received',
    icon: '/icon-192x192.png',
    badge: '/badge-72x72.png',
    tag: 'alert'
  }

  if (event.data) {
    try {
      const data = event.data.json()
      notificationData = {
        ...notificationData,
        ...data
      }
    } catch (error) {
      notificationData.body = event.data.text()
    }
  }

  event.waitUntil(
    self.registration.showNotification(notificationData.title, {
      body: notificationData.body,
      icon: notificationData.icon,
      badge: notificationData.badge,
      tag: notificationData.tag,
      requireInteraction: true,
      data: notificationData
    })
  )
})

// Handle notification clicks
self.addEventListener('notificationclick', event => {
  console.log('[ServiceWorker] Notification clicked:', event)

  event.notification.close()

  // Focus on open window or open new one
  event.waitUntil(
    clients.matchAll({ type: 'window' })
      .then(clientList => {
        for (const client of clientList) {
          if (client.url === '/' && 'focus' in client) {
            return client.focus()
          }
        }
        if (clients.openWindow) {
          return clients.openWindow('/')
        }
      })
  )
})

// Handle notification dismissal
self.addEventListener('notificationclose', event => {
  console.log('[ServiceWorker] Notification dismissed:', event)
})

// Handle background sync for offline support (future use)
self.addEventListener('sync', event => {
  console.log('[ServiceWorker] Background sync:', event.tag)

  if (event.tag === 'sync-alerts') {
    event.waitUntil(syncAlerts())
  }
})

async function syncAlerts() {
  try {
    // Sync any pending alert acknowledgments
    const pendingAlerts = await getFromIndexedDB('pendingAlerts')
    // TODO: Send to server
  } catch (error) {
    console.error('Failed to sync alerts:', error)
  }
}

// Simple IndexedDB helpers (future enhancement)
function getFromIndexedDB(storeName) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('CycleMonitorDB', 1)

    request.onerror = () => reject(request.error)
    request.onsuccess = () => {
      const db = request.result
      const transaction = db.transaction([storeName], 'readonly')
      const store = transaction.objectStore(storeName)
      const getAllRequest = store.getAll()

      getAllRequest.onerror = () => reject(getAllRequest.error)
      getAllRequest.onsuccess = () => resolve(getAllRequest.result)
    }
  })
}

console.log('[ServiceWorker] Loaded and ready to handle notifications')
