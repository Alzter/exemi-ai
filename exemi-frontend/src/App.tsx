import { useState, useEffect } from 'react';
import './App.css';

import Auth from './pages/auth';
import LoggedInFlow from './pages/app';
import { BrowserRouter } from 'react-router';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  
  useEffect( () => {
    const token = localStorage.getItem("token");
    const user = localStorage.getItem("user");
    if (token) { setIsLoggedIn(true); }
  }, []);

  return (
    <BrowserRouter>
      {isLoggedIn ? <LoggedInFlow /> : <Auth />}
    </BrowserRouter>
  )
}

export default App
