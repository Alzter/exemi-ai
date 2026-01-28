import { useState, useEffect } from 'react';
import Loading from './pages/loading';
import Auth from './pages/auth';
import LoggedInFlow from './pages/app';
import Onboarding from './pages/onboarding';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

type Session = {
    token : string | null;
    user_id : string | null;
}

export default function AppRouter() {

    const [session, setSession] = useState<Session>({
        token : localStorage.getItem("token"),
        user_id : localStorage.getItem("user_id"),
    });

    const [isMagicValid, setMagicValid] = useState<boolean | null>(null);

    const isLoggedIn = session.token !== null;
    const isLoading = isLoggedIn && isMagicValid == null;

    // Call the backend API to determine if the user's current magic is valid.
    async function checkIfUserMagicValid() {
        const response = await fetch(backendURL + "/magic_valid", {
            headers: {
                "Authorization" : "Bearer " + session.token
            },
            method: "GET",
            }
        );

        setMagicValid(response.ok);
    };

    // Synchronise user session (token) with local storage
    useEffect(() => {
        if (session.token){ localStorage.setItem("token", session.token); }
        else {localStorage.removeItem("token")}
        if (session.user_id){ localStorage.setItem("user_id", session.user_id); }
        else {localStorage.removeItem("user_id")}
        
        if (isLoggedIn && isMagicValid == null){
            checkIfUserMagicValid();
        }
        if (!isLoggedIn){
            setMagicValid(null);
        }
    });

    if (isLoading) {return <Loading/>}

    if (isLoggedIn) {
        // TODO: Check if the user has a magic. If not, send them to onboarding to generate one.
        if (isMagicValid){
            return <LoggedInFlow/>
        } else {
            return <Onboarding/>
        }
    } else {
        return <Auth setSession={setSession}/>
    }
}