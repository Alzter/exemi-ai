import { useState, useEffect } from 'react';
import Loading from './pages/loading';
import Login from './pages/auth';
import LoggedInFlow from './pages/app';
import InitialSetup from './pages/setup';
import {type User, type Session} from './models';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function AppRouter() {

    const [session, setSession] = useState<Session>({
        token : localStorage.getItem("token"),
        user_id : Number(localStorage.getItem("user_id")),
        user : localStorage.getItem("user") != null ? JSON.parse(String(localStorage.getItem("user"))) as User : null
    });

    const [error, setError] = useState<string | null>(null);
    const [isInitialSetupRequired, setInitialSetupRequired] = useState<boolean|null>(null);

    const isLoggedIn = session.token !== null;
    const isLoading = (isInitialSetupRequired == null);

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
    
    async function checkIfInitialSetupRequired() {
        const response = await fetch(backendURL + "/admins", {
            headers: {"Authorization" : "Bearer " + session.token,
                accept: "application/json"
            },
            method: "GET",
        });

        if (!response.ok){
            setError("System error fetching administrator accounts!");
            return;
        }

        let doAdminAccountsExist : boolean = await response.json() as boolean;

        setInitialSetupRequired(!doAdminAccountsExist);
    };

    // Set session.user to the current User object.
    async function fetchUser() {
        try{
            const response = await fetch(backendURL + "/users/self", {
                headers: {"Authorization" : "Bearer " + session.token},
                method: "GET"
            });

            if (!response.ok){
                logOut();
                setError("System error obtaining user account! Contact Alexander Small.");
                return;
            }

            let data = await response.json();
            let userObject = data as User;

            setSession({
                ...session,
                user : userObject
            });

        } catch {
            // Mega oops if this happens.
            logOut();
            setError("System error obtaining user account! Contact Alexander Small.");
        };
    };

    useEffect(() => {
        if (isInitialSetupRequired == null){
            checkIfInitialSetupRequired();
        }
    }, []);

    // Synchronise user session (token) with local storage
    useEffect(() => {
        if (session.token){
            localStorage.setItem("token", session.token);
        } else {
            localStorage.removeItem("token");
        };

        if (session.user_id){
            localStorage.setItem("user_id", String(session.user_id));
        } else {
            localStorage.removeItem("user_id");
        };

        if (session.user_id && !session.user){
            fetchUser();
        };

        if (session.user){
            localStorage.setItem("user", JSON.stringify(session.user));
        } else{
            localStorage.removeItem("user");
        };
        
        if (isLoggedIn){
            setError(null);
            logOutIfJWTExpires();
        };
    });

    if (isLoading) {return <Loading/>}

    if (isInitialSetupRequired){
        return <InitialSetup error={error} setError={setError} setSession={setSession}/>
    };

    if (isLoggedIn) {
        return <LoggedInFlow session={session} setSession={setSession} setError={setError} logOut={logOut}/>
    } else {
        return <Login error={error} setError={setError} setSession={setSession}/>
    };
};