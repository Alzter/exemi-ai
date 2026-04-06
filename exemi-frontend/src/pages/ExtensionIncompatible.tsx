import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { MdErrorOutline } from 'react-icons/md'
import {
  EXEMI_CANVAS_TOKEN_FAILURE_STICKY_KEY,
  type ExemiTokenFailureCode,
} from '../extensionAutomationMessages'

function failureMessageForCode(code: ExemiTokenFailureCode | string | undefined): string {
  switch (code) {
    case 'NO_NEW_TOKEN_BUTTON':
      return 'We could not find the “New access token” action on this page. Your institution may restrict token creation.'
    case 'SCRAPER_TIMEOUT':
    case 'FORM_TIMEOUT':
      return 'Canvas took too long to respond while Exemi was setting up. You can try again from onboarding.'
    case 'TOKEN_NOT_FOUND':
      return 'A token was generated but Exemi could not read it from the page. Try again or create a token manually.'
    case 'CLOSE_MODAL_FAILED':
      return 'The access token dialog could not be closed automatically. Your Canvas session may still be fine—try continuing manually.'
    case 'IFRAME_HANDSHAKE_TIMEOUT':
      return 'The extension sidebar did not respond in time. Reload the page and try again.'
    case 'UNKNOWN':
    default:
      return 'Exemi could not finish automatic token setup on this page.'
  }
}

export default function ExtensionIncompatible() {
  const navigate = useNavigate()

  const { code, detail } = useMemo(() => {
    try {
      const raw = sessionStorage.getItem(EXEMI_CANVAS_TOKEN_FAILURE_STICKY_KEY)
      if (!raw) return { code: undefined as string | undefined, detail: null as string | null }
      const o = JSON.parse(raw) as { code?: string }
      const c = typeof o.code === 'string' ? o.code : undefined
      return { code: c, detail: failureMessageForCode(c) }
    } catch {
      return { code: undefined, detail: null }
    }
  }, [])

  function dismiss() {
    try {
      sessionStorage.removeItem(EXEMI_CANVAS_TOKEN_FAILURE_STICKY_KEY)
    } catch {
      // ignore
    }
    navigate('/', { replace: true })
  }

  return (
    <div className="form">
      <p className="logo">exemi</p>
      <div className="error">
        <h1>
          <MdErrorOutline />
          <br />
          Extension setup issue
        </h1>
        <br />
        <p>
          {detail ??
            'Your university may not allow manual Canvas API access tokens, or Exemi could not complete automatic setup.'}
        </p>
        {code ? (
          <p className="meta" style={{ marginTop: '1rem', fontSize: '0.85em', color: '#555' }}>
            Reference: {code}
          </p>
        ) : null}
        <p style={{ marginTop: '1.5rem' }}>
          <button type="button" className="primary send" onClick={dismiss}>
            Back to sign-in
          </button>
        </p>
      </div>
    </div>
  )
}
