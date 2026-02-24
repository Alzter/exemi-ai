import {Routes, Route} from "react-router-dom";
import Dashboard from "./dashboard";
import ChatUI from "./chat";
import UserCreate from "./user_create";
import UserDelete from "./user_delete";
import { useEffect, useState } from "react";
import Loading from "../loading";
import Onboarding from '../../pages/onboarding';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function LoggedInFlow({session, setSession, setError, logOut} : any) {
    const [isMagicValid, setMagicValid] = useState<boolean | null>(null);
    const isLoading = (isMagicValid == null);

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
        setSession(
            (prev : any) => ({...prev, last_sync_date : new Date()})
        );

        const response = await fetch(backendURL + "/canvas/all", {
            headers: {"Authorization" : "Bearer " + session.token},
            method: "POST",
        });

        if (!response.ok){
            let message = "System error obtaining information from Canvas! Contact Alexander Small.";
            try{
                let data = await response.json();
                if (typeof data.detail === "string"){
                    message = data.detail;
                }
            } finally {
                setError(message);
                logOut();
            };
        };
    };

    useEffect(() => {
        if (isMagicValid == null){
            checkIfUserMagicValid();
        }
    });

    useEffect(() => {
        console.log(session.last_sync_date);
        if (session.last_sync_date == null){
            fetchUserUnits();
        };
    }, []);

    if (isLoading){
        return (<Loading/>);
    };

    function ChatUIOrOnboarding() {
        if (isMagicValid){
            return (<ChatUI session={session} isViewing={false} logOut={logOut}/>);
        } else {
            return (<Onboarding session={session} setSession={setSession} setMagicValid={setMagicValid} logOut={logOut}/>);
        };
    };

    if (session.user.admin) {
        return (
            <div>
                <Routes>
                  <Route path="/" element={<Dashboard session={session} setSession={setSession} logOut={logOut}/>}/>
                  <Route path="chat/" element={<ChatUIOrOnboarding/>}/>
                  <Route path="chat_viewer/" element={<ChatUI session={session} isViewing={true} logOut={logOut}/>}/>
                  <Route path="user_create/" element={<UserCreate session={session}/>}/>
                  <Route path="user_delete/" element={<UserDelete session={session}/>}/>
                </Routes>
              </div>
        );
    } else {
        return (
            <div>
                <Routes>
                    <Route path="/" element={<ChatUIOrOnboarding/>}/>
                </Routes>
            </div>
        );
    };
};