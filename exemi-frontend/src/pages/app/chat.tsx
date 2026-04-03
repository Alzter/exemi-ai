import {useState, useEffect} from 'react'
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import { useNavigate } from 'react-router-dom';
import {type User, type Session} from '../../models';
import ChatSidebar from '../../components/chat/Sidebar';
import ChatMessages from '../../components/chat/Messages';

type ChatUIParams = {
  session : Session,
  isViewing : boolean,
  logOut : any,
}

export default function ChatUI({session, isViewing, logOut} : ChatUIParams){

    let navigate = useNavigate();

    const [sidebarEnabled, setSidebarEnabled] = useState<boolean>(isViewing);
    const [conversationID, setConversationID] = useState<number|null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string|null>(null);

    return(
        <div className="chat">
            <ChatSidebar
                session={session}
                enabled={sidebarEnabled}
                setEnabled={setSidebarEnabled}
                isViewing={isViewing}
                loading={loading}
                conversationID={conversationID}
                setConversationID={setConversationID}
                setError={setError}
                logOut={logOut}
            />
            <ChatMessages
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
