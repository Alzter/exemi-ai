import { useState, useEffect } from 'react';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function Dashboard({session, setSession} : any) {

  async function logOut(){
    setSession({
      token:null,
      user_id:null
    });
  };

  return (
    <div>
      <h1>Dashboard</h1>
      <button onClick={logOut}>Logout</button>
    </div>
  )
}
