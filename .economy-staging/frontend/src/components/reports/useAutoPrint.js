import { useEffect } from 'react'

export function useAutoPrint(enabled, ready) {
  useEffect(() => {
    if (!enabled || !ready) return undefined

    let cancelled = false

    const run = async () => {
      try {
        if (document.fonts?.ready) {
          await document.fonts.ready
        }
      } catch {
        // Ignore and continue.
      }

      await new Promise((resolve) => window.requestAnimationFrame(() => resolve()))
      await new Promise((resolve) => window.requestAnimationFrame(() => resolve()))
      await new Promise((resolve) => window.setTimeout(resolve, 300))

      if (!cancelled) {
        window.print()
      }
    }

    run()

    return () => {
      cancelled = true
    }
  }, [enabled, ready])
}
