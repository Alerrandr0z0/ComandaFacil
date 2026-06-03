/// <reference lib="webworker" />

import { BackgroundSyncPlugin } from 'workbox-background-sync'
import { ExpirationPlugin } from 'workbox-expiration'
import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching'
import { registerRoute } from 'workbox-routing'
import { CacheFirst, NetworkFirst, StaleWhileRevalidate } from 'workbox-strategies'

declare const self: ServiceWorkerGlobalScope

// Auto-clean up outdated caches from previous versions of the app
cleanupOutdatedCaches()

// Precache and route static assets generated in the build
precacheAndRoute(self.__WB_MANIFEST)

// 1. Menu Cache: StaleWhileRevalidate (Serve instantly from cache, refetch in background)
registerRoute(
  ({ url }) => url.pathname.includes('/api/v1/menu'),
  new StaleWhileRevalidate({
    cacheName: 'menu-cache',
    plugins: [
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 12 * 60 * 60, // 12 hours
      }),
    ],
  }),
)

// 2. Table Status and Orders Cache: NetworkFirst (Attempt network, fallback to cache)
registerRoute(
  ({ url }) => url.pathname.includes('/api/v1/order') && !url.pathname.includes('/items'),
  new NetworkFirst({
    cacheName: 'orders-status-cache',
    networkTimeoutSeconds: 3, // Fast timeout to switch to offline view quickly
    plugins: [
      new ExpirationPlugin({
        maxEntries: 200,
        maxAgeSeconds: 30, // 30 seconds TTL
      }),
    ],
  }),
)

// 3. Static assets/images (from UI or external sources)
registerRoute(
  ({ request }) => request.destination === 'image' || request.destination === 'font',
  new CacheFirst({
    cacheName: 'static-assets',
    plugins: [
      new ExpirationPlugin({
        maxEntries: 50,
        maxAgeSeconds: 30 * 24 * 60 * 60, // 30 Days
      }),
    ],
  }),
)

// 4. Background Sync: Enqueue offline writes (creating orders, adding items, request payments)
const bgSyncPlugin = new BackgroundSyncPlugin('offline-writes-queue', {
  maxRetentionTime: 24 * 60, // Retry for up to 24 hours
})

// Register the route for POST, PUT, PATCH, DELETE operations on orders or payments
registerRoute(
  ({ url }) => url.pathname.includes('/api/v1/order') || url.pathname.includes('/api/v1/payments'),
  new NetworkFirst({
    plugins: [bgSyncPlugin],
  }),
  'POST',
)

registerRoute(
  ({ url }) => url.pathname.includes('/api/v1/order') || url.pathname.includes('/api/v1/payments'),
  new NetworkFirst({
    plugins: [bgSyncPlugin],
  }),
  'PUT',
)

registerRoute(
  ({ url }) => url.pathname.includes('/api/v1/order') || url.pathname.includes('/api/v1/payments'),
  new NetworkFirst({
    plugins: [bgSyncPlugin],
  }),
  'PATCH',
)

// Self install immediately when a new SW is detected
self.addEventListener('install', () => {
  self.skipWaiting()
})

// Claim all active client tabs immediately
self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})
