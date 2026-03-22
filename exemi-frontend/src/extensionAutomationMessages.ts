/** postMessage types for Canvas token automation (iframe ↔ content script). Keep in sync with exemi-extension/src/extensionAutomationMessages.ts */

export const EXEMI_AUTOMATION_READY = 'EXEMI_AUTOMATION_READY'
export const EXEMI_AUTOMATION_REDIRECTING = 'EXEMI_AUTOMATION_REDIRECTING'
export const EXEMI_CANVAS_TOKEN_RESULT = 'EXEMI_CANVAS_TOKEN_RESULT'

export type ExemiAutomationReadyPayload = {
  hashRoute: string
  isOnboarding: boolean
}

export type ExemiTokenFailureCode =
  | 'NO_NEW_TOKEN_BUTTON'
  | 'SCRAPER_TIMEOUT'
  | 'TOKEN_NOT_FOUND'
  | 'CLOSE_MODAL_FAILED'
  | 'FORM_TIMEOUT'
  | 'IFRAME_HANDSHAKE_TIMEOUT'
  | 'UNKNOWN'

export type ExemiCanvasTokenResultPayload =
  | { ok: true; token: string; universitySubdomain?: string }
  | { ok: false; code: ExemiTokenFailureCode }

export const EXEMI_IFRAME_AUTOMATION_RESUME_KEY = 'exemi_iframe_token_automation_resume'

export function isExemiExtensionIframe(): boolean {
  if (typeof window === 'undefined') return false
  const p = window.location.protocol
  return (
    p === 'chrome-extension:' ||
    p === 'moz-extension:' ||
    p === 'safari-web-extension:'
  )
}

/** True if origin is a typical Canvas host (messages from the embedding tab). */
export function isExemiCanvasEmbedderOrigin(origin: string): boolean {
  try {
    const u = new URL(origin)
    return u.protocol === 'https:' && u.hostname.endsWith('.instructure.com')
  } catch {
    return false
  }
}
