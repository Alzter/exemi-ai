import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function Dashboard({session, setSession, logOut} : any) {

  let navigate = useNavigate();

  async function chat(){
    navigate("/chat");
  }

  return (
    <div className='form'>
      <h1>Dashboard</h1>
      <button onClick={chat}>Start new Chat</button>
      <br/>
      <button>Create User Account</button>
      <button>Delete User Account</button>
      <button>View User Chats</button>
      <br/>
      <button onClick={logOut}>Log Out</button>
    </div>
  )
}
