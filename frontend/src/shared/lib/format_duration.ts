/**
 * Format elapsed milliseconds into a human-readable duration string.
 *
 * Examples:
 *   formatDuration(39000)     → "39s"
 *   formatDuration(125000)    → "2m 5s"
 *   formatDuration(3661000)   → "1h 1m 1s"
 *   formatDuration(43560000)  → "12h 6m 0s"
 */
export function formatDuration(diffMs: number): string {
  const totalSec = Math.floor(diffMs / 1000)
  const hrs = Math.floor(totalSec / 3600)
  const mins = Math.floor((totalSec % 3600) / 60)
  const secs = totalSec % 60

  if (hrs > 0) {
    return `${hrs}h ${mins}m ${secs}s`
  }
  return `${mins}m ${secs}s`
}
