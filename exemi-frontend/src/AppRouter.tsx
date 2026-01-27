import { useState, useEffect } from 'react';
import Auth from './pages/auth';
import LoggedInFlow from './pages/app';

type Session = {
    token : string | null,
    user_id : string | null
}

export default function AppRouter() {

    const [session, setSession] = useState<Session>({
        token : localStorage.getItem("token"),
        user_id : localStorage.getItem("user_id"),
    });
    
    // Synchronise user session (token) with local storage
    useEffect(() => {
        if (session.token){ localStorage.setItem("token", session.token); }
        else {localStorage.removeItem("token")}
        if (session.user_id){ localStorage.setItem("user_id", session.user_id); }
        else {localStorage.removeItem("user_id")}
    })

    const isLoggedIn = session.token !== null;

    if (isLoggedIn) { return <LoggedInFlow/> }
    else { return <Auth setSession={setSession}/> }
}