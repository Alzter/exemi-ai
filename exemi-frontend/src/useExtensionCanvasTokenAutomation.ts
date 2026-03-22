import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useExemiCanvasPageContext } from './canvasExtensionContext'
import {
  EXEMI_AUTOMATION_READY,
  EXEMI_AUTOMATION_REDIRECTING,
  EXEMI_CANVAS_TOKEN_RESULT,
  EXEMI_CANVAS_TOKEN_FAILURE_STICKY_KEY,
  EXEMI_IFRAME_AUTOMATION_RESUME_KEY,
  EXEMI_IFRAME_AUTOMATION_SESSION_PENDING_KEY,
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

    const referrerCanvasOrigin = (): string | null => {
      if (!document.referrer) return null
      try {
        const o = new URL(document.referrer).origin
        return isExemiCanvasEmbedderOrigin(o) ? o : null
      } catch {
        return null
      }
    }

    const parentOrigin =
      parentOriginFromHref(ctx.href) ?? referrerCanvasOrigin()
    const postTarget = parentOrigin ?? '*'

    const sendReady = () => {
      let redirectResume = false
      let sessionPending = false
      try {
        redirectResume = sessionStorage.getItem(EXEMI_IFRAME_AUTOMATION_RESUME_KEY) === '1'
        sessionPending =
          sessionStorage.getItem(EXEMI_IFRAME_AUTOMATION_SESSION_PENDING_KEY) === '1'
      } catch {
        // ignore
      }
      const automationResume = redirectResume || sessionPending
      window.parent.postMessage(
        {
          type: EXEMI_AUTOMATION_READY,
          payload: {
            hashRoute: location.pathname,
            isOnboarding: true,
            automationResume,
          },
        },
        postTarget,
      )
    }

    sendReady()
    const retryIds = [400, 1200, 2500].map((ms) =>
      window.setTimeout(sendReady, ms),
    )

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
          sessionStorage.removeItem(EXEMI_IFRAME_AUTOMATION_SESSION_PENDING_KEY)
        } catch {
          // ignore
        }
        const payload = (data as { payload?: ExemiCanvasTokenResultPayload }).payload
        if (!payload || typeof payload !== 'object' || !('ok' in payload)) return
        const p = payload as ExemiCanvasTokenResultPayload
        try {
          if (p.ok) {
            sessionStorage.removeItem(EXEMI_CANVAS_TOKEN_FAILURE_STICKY_KEY)
          } else {
            sessionStorage.setItem(
              EXEMI_CANVAS_TOKEN_FAILURE_STICKY_KEY,
              JSON.stringify({ code: p.code }),
            )
          }
        } catch {
          // ignore
        }
        onTokenResultRef.current(p)
      }
    }

    window.addEventListener('message', onMessage)
    return () => {
      for (const id of retryIds) window.clearTimeout(id)
      window.removeEventListener('message', onMessage)
    }
  }, [ctx.href, location.pathname])
}
