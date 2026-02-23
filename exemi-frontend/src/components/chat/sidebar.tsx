import {useState, useEffect, useRef} from 'react'
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import { useNavigate } from 'react-router-dom';
import {type Session} from '../../models';
import UserSelector from '../admin/user_selector';

type ChatSidebarParams = {
    session : Session,
    enabled : boolean,
    setEnabled : any,
    isViewing : boolean,
    loading : boolean,
    conversationID : number | null,
    setConversationID : any,
    setError : any,
    logOut : any
}

type Conversation = {
    created_at : Date
    id : number
}

export default function ChatSidebar({session, enabled, setEnabled, isViewing, loading, conversationID, setConversationID, setError, logOut} : ChatSidebarParams) {

    let navigate = useNavigate();

    const sidebarRef = useRef<HTMLDivElement>(null);
    const sidebarButtonRef = useRef<HTMLButtonElement>(null);
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [username, setUsername] = useState<string>(session.user.username);

    function toggleChatSidebar(){
        if (enabled){ setEnabled(false); } else { setEnabled(true); }
        // setEnabled(prev => !prev);
    };

    // Handle changing the sidebar's CSS class
    // to hide it if it is disabled
    useEffect(() => {
        const sidebar = sidebarRef.current;
        const sidebarButton = sidebarButtonRef.current;
        if (!sidebar || !sidebarButton) return;
        sidebar.classList.toggle("hidden", !enabled);
        sidebarButton.classList.toggle("hidden", !enabled);

    }, [enabled]);

    useEffect(() => {
        setConversationID(null)
    }, [username]);

    async function parseConversations(data : Array<any>){
        const conversations: Conversation[] = data.map(item => ({
            id: item.id,
            created_at: new Date(item.created_at),
        }));

        setConversations(conversations);
    }

    async function loadConversations(){
        let URL = backendURL + "/conversations/" + username 
        const response = await fetch(URL, {
            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method:"GET"
        })

        if (!response.ok){
            let message = "System error! Please contact Alexander Small.";
            const data = await response.json();
            if (typeof data.detail === "string"){
                message = data.detail;
            }
            setError(message);
            return;
        }

        const data = await response.json();
        parseConversations(data);
    }

    // When component loads, fetch conversations.
    useEffect(() => {
        loadConversations();
    }, [conversationID, username]);

    function ConversationSelector({conversation} : any){
        let ID = conversation ? conversation.id : null;
        
        let title = "";
        if (conversation){
            let conversationDateString = conversation.created_at.toLocaleString(
                "en-AU", {timeZone: "Australia/Sydney"}
            )
            title = conversationDateString;
        } else {
            title = "+ Create New Chat";
        };

        function assignConversation(){
            setConversationID(ID);
        };

        let className = conversationID==ID ? "conversation-selected" : "conversation";
        if (!conversation) {className = "";}

        return (
            <button
                onClick = {assignConversation}
                className={className}
                disabled={conversationID==ID || loading}>
                    {title}
            </button>
        );
    };

    const conversationSelectors = conversations.map(
        conversation => <ConversationSelector conversation={conversation}/>
    );

    return (
        <div>
            <button onClick={toggleChatSidebar} className="sidebar-button" ref={sidebarButtonRef}>☰</button>
            <div className="chat-sidebar" ref={sidebarRef}>
                <div className="chat-sidebar-header">
                <p className="logo">exemi</p>
                </div>

                {isViewing ? (
                    <UserSelector session={session} setError={setError} username={username} setUsername={setUsername} refreshTrigger={null}/>
                ) : (
                    <ConversationSelector conversation={null}/>
                )}

                <p>Your chats:</p>
                <div className="conversation-container">
                    {conversationSelectors}
                </div>
                
                <div className="chat-sidebar-footer">
                {session.user.admin ? (
                    <button onClick={() => {navigate("/");}}>Back to Dashboard</button>
                ) : (
                    <button onClick={logOut}>Log Out</button>
                )}
                </div>
            </div>
        </div>
    );
};