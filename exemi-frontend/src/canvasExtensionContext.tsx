import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'

export type ExemiCanvasPageContext = {
  href: string
  path: string
  query: string
}

export const EXEMI_CANVAS_CONTEXT_MESSAGE = 'EXEMI_CANVAS_CONTEXT'

const defaultCtx: ExemiCanvasPageContext = { href: '', path: '', query: '' }

const ExemiCanvasContext = createContext<ExemiCanvasPageContext>(defaultCtx)

function isAllowedSenderOrigin(origin: string): boolean {
  try {
    const u = new URL(origin)
    if (u.protocol === 'https:' && u.hostname.endsWith('.instructure.com')) {
      return true
    }
    if (u.protocol === 'moz-extension:' || u.protocol === 'chrome-extension:') {
      return true
    }
  } catch {
    return false
  }
  return false
}

export function ExemiCanvasContextProvider({ children }: { children: ReactNode }) {
  const [ctx, setCtx] = useState<ExemiCanvasPageContext>(defaultCtx)

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (!isAllowedSenderOrigin(event.origin)) return
      const data = event.data
      if (!data || typeof data !== 'object') return
      if ((data as { type?: string }).type !== EXEMI_CANVAS_CONTEXT_MESSAGE) return
      const payload = (data as { payload?: ExemiCanvasPageContext }).payload
      if (!payload || typeof payload.href !== 'string') return
      setCtx({
        href: payload.href,
        path: typeof payload.path === 'string' ? payload.path : '',
        query: typeof payload.query === 'string' ? payload.query : '',
      })
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [])

  return (
    <ExemiCanvasContext.Provider value={ctx}>{children}</ExemiCanvasContext.Provider>
  )
}

export function useExemiCanvasPageContext(): ExemiCanvasPageContext {
  return useContext(ExemiCanvasContext)
}
