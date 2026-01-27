import { useState, useEffect } from 'react';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function Dashboard() {

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.reload();
  }

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
      <h1>Dashboard</h1>
      <button onClick={fetchUser}>fetch user info</button>
      <button onClick={logout}>Logout</button>
    </div>
  )
}
