import { useEffect, useRef, useState } from 'react'
import { useTenant } from '@/shared/hooks/useTenant'

export interface ReadyItem {
  id: number
  correlation_id: number
  name_cpy: string
  station_type_cpy: string
  state: string
}

const playNotificationSound = () => {
  try {
    const AudioContextClass =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    if (!AudioContextClass) return

    const audioCtx = new AudioContextClass()
    const oscillator = audioCtx.createOscillator()
    const gainNode = audioCtx.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(audioCtx.destination)

    oscillator.type = 'sine'
    // Warm, high-low notification tone (Chime)
    oscillator.frequency.setValueAtTime(587.33, audioCtx.currentTime) // D5
    oscillator.frequency.setValueAtTime(880, audioCtx.currentTime + 0.15) // A5

    gainNode.gain.setValueAtTime(0.05, audioCtx.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.4)

    oscillator.start(audioCtx.currentTime)
    oscillator.stop(audioCtx.currentTime + 0.4)
  } catch (_error) {}
}

const triggerVibration = () => {
  if ('vibrate' in navigator) {
    // Vibrate pattern: vibrate 150ms, pause 100ms, vibrate 150ms
    navigator.vibrate([150, 100, 150])
  }
}

const requestNotificationPermission = () => {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission()
  }
}

const showSystemNotification = (title: string, body: string) => {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, {
      body,
      icon: '/pwa-192x192.png',
    })
  }
}

export function useKitchenAlerts() {
  const { tenantId } = useTenant()
  const [readyItems, setReadyItems] = useState<ReadyItem[]>([])
  const websockets = useRef<WebSocket[]>([])

  useEffect(() => {
    requestNotificationPermission()

    if (!tenantId) return

    const stations = ['GRILL', 'BEVERAGE']
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host

    const activeSockets: WebSocket[] = []

    for (const station of stations) {
      const wsUrl = `${protocol}//${host}/api/v1/kitchen/ws?tenant_id=${tenantId}&station_type=${station}`
      const ws = new WebSocket(wsUrl)

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.event === 'ITEM_READY') {
            const item: ReadyItem = data.item
            setReadyItems((prev) => {
              // Avoid duplicates
              if (prev.some((p) => p.id === item.id)) return prev
              return [...prev, item]
            })

            // Audio-Visual feedback
            playNotificationSound()
            triggerVibration()
            showSystemNotification(`Item Pronto!`, `Mesa / Pedido pronto: ${item.name_cpy}`)
          }
        } catch (_err) {}
      }

      ws.onerror = (_err) => {}

      ws.onclose = () => {
        // Reconnection logic
      }

      activeSockets.push(ws)
    }

    websockets.current = activeSockets

    return () => {
      for (const ws of activeSockets) {
        ws.close()
      }
    }
  }, [tenantId])

  const dismissReadyItem = (itemId: number) => {
    setReadyItems((prev) => prev.filter((item) => item.id !== itemId))
  }

  return {
    readyItems,
    dismissReadyItem,
  }
}
