import {useState, useEffect} from 'react'
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import ChatMessagesUI from './chat_messages';
import { useNavigate } from 'react-router-dom';
import {type User, type Session} from '../../models';
import UserSelector from '../../components/admin/user_selector';

type ChatUIParams = {
  session : Session,
  isViewing : boolean
}

type Conversation = {
    created_at : Date
    id : number
}

export default function ChatUI({session, isViewing} : ChatUIParams){

    const [username, setUsername] = useState<string>(session.user.username);

    let navigate = useNavigate();
    // Only let the user view other user's
    // conversations (chat logs) if the
    // user is an administrator
    useEffect(() => {
        setConversationID(null);
        if (username != session.user.username && !session.user.admin){
            navigate("/");
        }
    }, [username]);

    useEffect(() => {
      console.log(username);
    }, [username]);

    function ConversationSelector({conversation} : any){
        let ID = conversation ? conversation.id : null
        let title = conversation ? conversation.created_at.toLocaleString() : "+ Create New Chat";
        function assignConversation(){
            setConversationID(ID);
        }
        let className = conversationID==ID ? "conversation-selected" : "conversation"
        if (!conversation) {className = "";}
        
        return (
            <button
                onClick = {assignConversation}
                className={className}
                disabled={conversationID==ID || loading}>
                    {title}
            </button>
        )
    }

    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [conversationID, setConversationID] = useState<number|null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string|null>(null);

    // const conversationSelectors = [<ConversationSelector conversation={null}/>, ...conversations.map(
    //     conversation => <ConversationSelector conversation={conversation}/>
    // )];
    const conversationSelectors = conversations.map(
        conversation => <ConversationSelector conversation={conversation}/>
    );

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
    }, [conversationID, username])

    return(
        <div className="chat">
            <div className="chat-sidebar">
                <div className="chat-sidebar-header">
                  <p>exemi</p>
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
                  <button onClick={() => {navigate("/");}}>Back to Dashboard</button>
                </div>
            </div>
            <ChatMessagesUI
                session={session}
                isViewing={isViewing}
                conversationID={conversationID}
                setConversationID={setConversationID}
                loading={loading}
                setLoading={setLoading}
                error={error}
                setError={setError}
            />
        </div>
    )
}
