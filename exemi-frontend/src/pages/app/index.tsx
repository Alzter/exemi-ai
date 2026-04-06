import { Routes, Route, useNavigate } from "react-router-dom";
import AdminDashboard from "./AdminDashboard";
import ChatUI from "./ChatUI";
import UserCreate from "./UserCreate";
import UserDelete from "./UserDelete";
import EditUniAliases from "./EditUniAliases";
import { useEffect, useState } from "react";
import Loading from "../Loading";
import Onboarding from '../../pages/onboarding';
import ExtensionIncompatible from '../ExtensionIncompatible';
import {
  EXEMI_CANVAS_TOKEN_FAILURE_STICKY_KEY,
  isExemiExtensionIframe,
} from "../../extensionAutomationMessages";
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
const canvasSyncIntervalHours = Number(import.meta.env.VITE_CANVAS_SYNC_INTERVAL_HOURS) || 6;

function computeCanvasSyncRequired(session: {last_canvas_sync_date: Date | null}): boolean {
    if (session.last_canvas_sync_date == null) return true;
    const last = session.last_canvas_sync_date as Date;
    const now = new Date();
    const sync_hours_ago = Math.abs(now.getTime() - last.getTime()) / (60 * 60 * 1000);
    return sync_hours_ago >= canvasSyncIntervalHours;
}

export default function LoggedInFlow({session, setSession, setError, logOut} : any) {
    const navigate = useNavigate();
    const [isMagicValid, setMagicValid] = useState<boolean | null>(null);
    const isLoading = (isMagicValid == null);

    useEffect(() => {
        if (isLoading) return;
        if (!isExemiExtensionIframe()) return;
        try {
            if (sessionStorage.getItem(EXEMI_CANVAS_TOKEN_FAILURE_STICKY_KEY)) {
                navigate("/extension_incompatible/", { replace: true });
            }
        } catch {
            // ignore
        }
    }, [navigate, isLoading]);

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
            return;
        }
        setSession(
            (prev : any) => ({...prev, last_canvas_sync_date : new Date()})
        );
    };

    useEffect(() => {
        if (isMagicValid == null){
            checkIfUserMagicValid();
        }
    }, [isMagicValid]);

    const syncRequired : boolean = computeCanvasSyncRequired(session);
    /** Derived: false until `last_canvas_sync_date` reflects a completed `/canvas/all` (sync no longer required). */
    const canvasSyncReady = !syncRequired;

    useEffect(() => {
        if (isMagicValid == true && syncRequired) {
            fetchUserUnits();
        }
    }, [isMagicValid, syncRequired]);

    if (isLoading){
        return (<Loading/>);
    };

    function ChatUIOrOnboarding() {
        if (isMagicValid){
            return (<ChatUI session={session} isViewing={false} logOut={logOut} canvasSyncReady={canvasSyncReady}/>);
        } else {
            return (<Onboarding session={session} setSession={setSession} setMagicValid={setMagicValid} logOut={logOut}/>);
        };
    };

    if (session.user.admin) {
        return (
            <div>
                <Routes>
                  <Route path="/" element={<AdminDashboard session={session} setSession={setSession} logOut={logOut}/>}/>
                  <Route path="chat/" element={<ChatUIOrOnboarding/>}/>
                  <Route path="chat_viewer/" element={<ChatUI session={session} isViewing={true} logOut={logOut} canvasSyncReady={canvasSyncReady}/>}/>
                  <Route path="user_create/" element={<UserCreate session={session}/>}/>
                  <Route path="user_delete/" element={<UserDelete session={session}/>}/>
                  <Route path="uni_aliases/" element={<EditUniAliases session={session}/>}/>
                  <Route path="extension_incompatible/" element={<ExtensionIncompatible/>}/>
                </Routes>
              </div>
        );
    } else {
        return (
            <div>
                <Routes>
                    <Route path="/" element={<ChatUIOrOnboarding/>}/>
                    <Route path="extension_incompatible/" element={<ExtensionIncompatible/>}/>
                </Routes>
            </div>
        );
    };
};