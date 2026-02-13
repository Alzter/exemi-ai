import { useState, useEffect } from 'react';
import Loading from './pages/loading';
import Login from './pages/auth';
import LoggedInFlow from './pages/app';
import Onboarding from './pages/onboarding';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

type User = {

}

type Session = {
    token : string | null;
    user_id : number | null;
    user : User | null;
}

export default function AppRouter() {

    const [session, setSession] = useState<Session>({
        token : localStorage.getItem("token"),
        user_id : Number(localStorage.getItem("user_id")),
        user : localStorage.getItem("user")
    });

    const [error, setError] = useState<string | null>(null);
    const [isMagicValid, setMagicValid] = useState<boolean | null>(null);
    const [doUserUnitsExist, setUserUnitsExist] = useState<boolean | null>(null);

    const isLoggedIn = session.token !== null;
    const isLoading = (isLoggedIn && isMagicValid == null) || (isMagicValid && doUserUnitsExist == null);

    async function logOut() {
        setSession({
            token:null,
            user_id:null,
            user:null
        })
    };

    // If the backend API route /users/self does not return 200,
    // log the user out immediately!
    async function logOutIfJWTExpires() {
        const response = await fetch(backendURL + "/users/self", {
            headers: { "Authorization" : "Bearer " + session.token},
            method: "GET",
        });
        if (!response.ok){
            logOut();
            setError("Your session has expired. Please log in again.");
        };
    };
    
    // Call the backend API to determine if the user's current magic is valid.
    async function checkIfUserMagicValid() {
        try{
            const response = await fetch(backendURL + "/magic_valid", {
                headers: {"Authorization" : "Bearer " + session.token},
                method: "GET",
            });
            setMagicValid(response.ok);

        } catch {
            logOut();
            setError("System error verifying Canvas token! Please contact Alexander Small.");
        }
    };

    // Call the backend API to retrieve the user's units.
    async function fetchUserUnits() {
        setUserUnitsExist(true);
        // try{
        //     const response = await fetch(backendURL + "/canvas/units", {
        //         headers: {"Authorization" : "Bearer " + session.token},
        //         method: "POST",
        //     });
        //     if (!response.ok){
        //         logOut();
        //         setError("System error fetching units! Please contact Alexander Small.");
        //     } else{
        //         setUserUnitsExist(true);
        //     }
        // } catch {
        //     logOut();
        //     setError("System error fetching units! Please contact Alexander Small.");
        // }
    }

    // Synchronise user session (token) with local storage
    useEffect(() => {
        if (session.token){ localStorage.setItem("token", session.token); }
        else {localStorage.removeItem("token")}
        if (session.user_id){ localStorage.setItem("user_id", String(session.user_id)); }
        else {localStorage.removeItem("user_id")}
        
        if (isLoggedIn){
            setError(null);
            logOutIfJWTExpires();
        } else {
            setMagicValid(null);
        };
        if (isLoggedIn && isMagicValid == null){
            checkIfUserMagicValid();
        };
        if (isMagicValid && doUserUnitsExist == null){
            fetchUserUnits();
        }
    });

    if (isLoading) {return <Loading/>}

    if (isLoggedIn) {
        // TODO: Check if the user has a magic. If not, send them to onboarding to generate one.
        if (isMagicValid){
            return <LoggedInFlow session={session} setSession={setSession} logOut={logOut}/>
        } else {
            return <Onboarding session={session} setSession={setSession} setMagicValid={setMagicValid} logOut={logOut}/>
        }
    } else {
        return <Login error={error} setError={setError} setSession={setSession}/>
    }
}