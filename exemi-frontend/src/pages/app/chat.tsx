import {useState, useEffect} from 'react'
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import MessageBox from '../../components/chat/message_box';
import ChatMessagesUI from './chat_messages';

type Conversation = {
    created_at : Date
    id : number
}

export default function ChatUI({session} : any){
    
    function ConversationBox({conversation} : any){
        let ID = conversation ? conversation.id : null
        let title = conversation ? conversation.created_at.toLocaleString() : "New chat";
        function assignConversation(){
            setConversationID(ID);
        }
        let className = conversationID==ID ? "conversation-selected" : "conversation"
        
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

    const conversationBoxes = [<ConversationBox conversation={null}/>, ...conversations.map(
        conversation => <ConversationBox conversation={conversation}/>
    )]

    async function parseConversations(data : Array<any>){
        const conversations: Conversation[] = data.map(item => ({
            id: item.id,
            created_at: new Date(item.created_at),
        }));

        setConversations(conversations);
    }

    async function loadConversations(){
        let URL = backendURL + "/conversations/" + session.user_id
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
    }, [conversationID])

    return(
        <div className="chat">
            <div className="chat-sidebar">
                <p>Your chats:</p>
                <div className="conversation-container">
                    {conversationBoxes}
                </div>
            </div>
            <ChatMessagesUI
                session={session}
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