import AppRouter from './AppRouter'
import './App.css';

import { BrowserRouter, HashRouter } from 'react-router';

function isExtensionOrigin(): boolean {
  if (typeof window === 'undefined') return false;
  const p = window.location.protocol;
  return (
    p === 'chrome-extension:' ||
    p === 'moz-extension:' ||
    p === 'safari-web-extension:'
  );
}

function App() {
  const Router = isExtensionOrigin() ? HashRouter : BrowserRouter;
  return (
    <Router>
      <AppRouter />
    </Router>
  );
}

export default App
