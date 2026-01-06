import { useState } from 'react'
import './App.css'

import Auth from './pages/auth'
import { BrowserRouter } from 'react-router'

function App() {
  return (
    <BrowserRouter>
      <Auth/>
    </BrowserRouter>
  )
}

export default App
