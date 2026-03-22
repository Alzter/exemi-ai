import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useExemiCanvasPageContext } from './canvasExtensionContext'
import {
  EXEMI_AUTOMATION_READY,
  EXEMI_AUTOMATION_REDIRECTING,
  EXEMI_CANVAS_TOKEN_RESULT,
  EXEMI_IFRAME_AUTOMATION_RESUME_KEY,
  isExemiCanvasEmbedderOrigin,
  isExemiExtensionIframe,
  type ExemiCanvasTokenResultPayload,
} from './extensionAutomationMessages'

type Options = {
  onTokenResult: (payload: ExemiCanvasTokenResultPayload) => void
}

function parentOriginFromHref(href: string): string | null {
  try {
    return new URL(href).origin
  } catch {
    return null
  }
}

/**
 * Handshake with the extension content script for automated Canvas token creation.
 * Only active when the app runs inside the extension iframe on Canvas.
 */
export function useExtensionCanvasTokenAutomation({ onTokenResult }: Options): void {
  const location = useLocation()
  const ctx = useExemiCanvasPageContext()
  const onTokenResultRef = useRef(onTokenResult)
  onTokenResultRef.current = onTokenResult

  useEffect(() => {
    if (!isExemiExtensionIframe()) return

    const parentOrigin = parentOriginFromHref(ctx.href)
    const postTarget = parentOrigin ?? '*'

    const sendReady = () => {
      window.parent.postMessage(
        {
          type: EXEMI_AUTOMATION_READY,
          payload: { hashRoute: location.pathname, isOnboarding: true },
        },
        postTarget,
      )
    }

    sendReady()

    const onMessage = (event: MessageEvent) => {
      if (event.source !== window.parent) return
      if (!isExemiCanvasEmbedderOrigin(event.origin)) return
      const data = event.data
      if (!data || typeof data !== 'object') return
      const t = (data as { type?: string }).type
      if (t === EXEMI_AUTOMATION_REDIRECTING) {
        try {
          sessionStorage.setItem(EXEMI_IFRAME_AUTOMATION_RESUME_KEY, '1')
        } catch {
          // ignore
        }
        return
      }
      if (t === EXEMI_CANVAS_TOKEN_RESULT) {
        try {
          sessionStorage.removeItem(EXEMI_IFRAME_AUTOMATION_RESUME_KEY)
        } catch {
          // ignore
        }
        const payload = (data as { payload?: ExemiCanvasTokenResultPayload }).payload
        if (!payload || typeof payload !== 'object' || !('ok' in payload)) return
        onTokenResultRef.current(payload as ExemiCanvasTokenResultPayload)
      }
    }

    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [ctx.href, location.pathname])
}
