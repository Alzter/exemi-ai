import { useState, useEffect } from 'react';
import Loading from './pages/loading';
import BigError from './pages/error';
import Login from './pages/auth';
import LoggedInFlow from './pages/app';
import InitialSetup from './pages/setup';
import {type User, type Session} from './models';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
const userSyncIntervalHours = import.meta.env.VITE_USER_SYNC_INTERVAL_HOURS;

export default function AppRouter() {

    const [session, setSession] = useState<Session>({
        token : localStorage.getItem("token"),
        user_id : Number(localStorage.getItem("user_id")),
        user : localStorage.getItem("user") != null ? JSON.parse(String(localStorage.getItem("user"))) as User : null,
        last_user_sync_date : localStorage.getItem("last_user_sync_date") != null ? new Date(String(localStorage.getItem("last_user_sync_date"))) : null,
        last_canvas_sync_date : localStorage.getItem("last_canvas_sync_date") != null ? new Date(String(localStorage.getItem("last_canvas_sync_date"))) : null
    });

    const [error, setError] = useState<string | null>(null);
    const [isBackendOnline, setBackendOnline] = useState<boolean|null>(null);
    const [isInitialSetupRequired, setInitialSetupRequired] = useState<boolean|null>(null);

    const isLoggedIn = session.token !== null;
    const isLoading = (isInitialSetupRequired == null || isBackendOnline == null);

    async function logOut() {
        setSession({
            token:null,
            user_id:null,
            user:null,
            last_user_sync_date:null,
            last_canvas_sync_date:null
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
    
    async function checkIfBackendOnline() {
        // console.log("Querying backend");
        try{
            const response = await fetch(backendURL, {
            headers: {"Authorization" : "Bearer " + session.token,
                accept: "application/json"
            },
            method: "GET",
            });
            setBackendOnline(response.ok);
        } catch {
            setBackendOnline(false);
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

    // Set session.user to the current User object
    async function fetchUser() {
        setSession(
            (prev : any) => ({...prev, last_user_sync_date : new Date()})
        );

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
            logOut();
            setError("System error obtaining user account! Contact Alexander Small.");
        };
    };

    const last_user_sync_date = session.last_user_sync_date ? session.last_user_sync_date as Date : new Date();
    const now = new Date();
    const sync_hours_ago : number = Math.abs(now.getTime() - last_user_sync_date.getTime()) / (60*60*1000);
    const syncRequired : boolean = (session.last_user_sync_date == null || sync_hours_ago >= userSyncIntervalHours)

    useEffect(() => {
        console.log(sync_hours_ago);
        if (session.user_id && syncRequired){
            console.log("fetch")
            fetchUser();
        }
    }, [syncRequired]);

    useEffect(() => {
        if (isBackendOnline == null){
            checkIfBackendOnline();
        };
    }, []);

    useEffect(() => {
        if (isBackendOnline == true && isInitialSetupRequired == null){
            checkIfInitialSetupRequired();
        };
    }, [isBackendOnline]);

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

        if (session.last_user_sync_date){
            localStorage.setItem("last_user_sync_date", session.last_user_sync_date.toISOString());
        } else {
            localStorage.removeItem("last_user_sync_date");
        };

        if (session.last_canvas_sync_date){
            localStorage.setItem("last_canvas_sync_date", session.last_canvas_sync_date.toISOString());
        } else {
            localStorage.removeItem("last_canvas_sync_date");
        };
        
        if (isLoggedIn){
            setError(null);
            logOutIfJWTExpires();
        };
    });
    
    if (isBackendOnline == false) {return <BigError/>}
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