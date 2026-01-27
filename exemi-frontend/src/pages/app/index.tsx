import {Routes, Route} from "react-router-dom";
import Dashboard from "./dashboard";
import { useState, useEffect } from 'react';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function LoggedInFlow() {
  const [loading, isLoading] = useState(true);
  const [error, setError] = useState(null);
  const [user, setUser] = useState(null);
  
  useEffect( () => {
    fetchUser;
  })

  const fetchUser = async () => {
    const response = await fetch(backendURL + "/users/self", {
      headers: {
        "Authorization" : "Bearer " + localStorage.getItem("token")
      },
      method: "POST",
    })
    
    if (!response.ok){
      throw new Error("User not found");
    }
    const data = await response.json();
    console.log(data);
  }

  return (
    <div>
      <Routes>
        <Route path="/" element={<Dashboard/>}/>
      </Routes>
      </div>
  )
}
