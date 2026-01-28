import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function Dashboard({session, setSession} : any) {

  let navigate = useNavigate();

  async function chat(){
    navigate("/chat");
  }

  async function logOut(){
    setSession({
      token:null,
      user_id:null
    });
  };

  return (
    <div className='form'>
      <h1>Dashboard</h1>
      <button onClick={chat}>Chat</button>
      <button onClick={logOut}>Logout</button>
    </div>
  )
}
