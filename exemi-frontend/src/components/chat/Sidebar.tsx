import {useState, useEffect} from 'react'
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import { useNavigate } from 'react-router-dom';
import {type Session} from '../../models';
// import UserSelector from '../admin/UserSelector';

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

    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [username, setUsername] = useState<string>(
        isViewing ? "1" : (session.user?.username ?? "")
    );

    function toggleChatSidebar(){
        if (enabled){ setEnabled(false); } else { setEnabled(true); }
        // setEnabled(prev => !prev);
    };

    async function parseConversations(data : Array<any>, auto_select_first_conversation : boolean){
        const conversations: Conversation[] = data.map(item => ({
            id: item.id,
            created_at: new Date(item.created_at),
        }));

        setConversations(conversations);

        if (auto_select_first_conversation) {
            if (conversations.length > 0){
                setConversationID(conversations[0].id);
            } else {
                setConversationID(null);
            };
        };
    };

    async function loadConversations(auto_select_first_conversation : boolean){
        let URL = backendURL + "/conversations/" + username 
        const response = await fetch(URL, {
            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method:"GET"
        });

        if (!response.ok){
            let message = "System error! Please contact Alexander Small.";
            const data = await response.json();
            if (typeof data.detail === "string"){
                message = data.detail;
            }
            setError(message);
            return;
        };

        const data = await response.json();
        parseConversations(data, auto_select_first_conversation);
    }

    // When component loads, fetch conversations.
    useEffect(() => {
        loadConversations(false);
    }, [conversationID]);

    // When username changes (viewing conversations)
    // fetch new conversations and select the latest
    // conversation if it exists
    useEffect(() => {
        loadConversations(isViewing);
    }, [username]);

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

        let className = conversationID==ID ? "primary conversation-selected" : "primary conversation";
        if (!conversation) {className = "primary";}

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
        conversation => <ConversationSelector conversation={conversation} key={conversation ? conversation.id : -1}/>
    );

    return (
        <div>
            <button onClick={toggleChatSidebar} className={"sidebar-button" + (enabled ? "" : " hidden")}>☰</button>
            <div className={"chat-sidebar" + (enabled ? "" : " hidden")}>
                <div className="chat-sidebar-header">
                <p className="logo">exemi</p>
                </div>

                {isViewing ? (
                    <input
                        autoFocus
                        name="username"
                        value={username}
                        onChange={(event)=>{setUsername(event.target.value)}}
                        type="number"
                        autoComplete='off'
                    />
                    // <UserSelector session={session} setError={setError} username={username} setUsername={setUsername} refreshTrigger={null}/>
                ) : (
                    <ConversationSelector conversation={null}/>
                )}

                <p>Your chats:</p>
                <div className="conversation-container">
                    {conversationSelectors}
                </div>
                
                <div className="chat-sidebar-footer">
                {session.user?.admin ? (
                    <button className="primary" onClick={() => {navigate("/");}}>Back to Dashboard</button>
                ) : (
                    <button className="primary" onClick={logOut}>Log Out</button>
                )}
                </div>
            </div>
        </div>
    );
};