import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function Dashboard({session, setSession, logOut} : any) {

  let navigate = useNavigate();

  return (
    <div className='form'>
      <h1>{session.user.admin ? "Admin Dashboard" : "Dashboard"}</h1>
      <button onClick={() => navigate("/chat")}>Start new Chat</button>

      {/* Admin-mode buttons */}
      {session.user.admin ? (<>
        <br/>
        <button onClick={() => navigate("/user_create")}>Create User Account</button>
        <button onClick={() => navigate("/user_delete")}>Delete User Account</button>
        <button onClick={() => navigate("/chat_viewer")}>View User Chats</button>
        <br/>
      </>) : null}

      <button onClick={logOut}>Log Out</button>
    </div>
  )
}
