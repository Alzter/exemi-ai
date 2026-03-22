import { Fragment } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ExemiCanvasContextProvider } from './canvasExtensionContext'

createRoot(document.getElementById('root')!).render(
  <Fragment>
    <ExemiCanvasContextProvider>
      <App />
    </ExemiCanvasContextProvider>
  </Fragment>,
)
