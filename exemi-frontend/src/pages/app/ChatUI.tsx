import {useState, useRef} from 'react'
import {type Session} from '../../models';
import ChatSidebar from '../../components/chat/Sidebar';
import ChatMessages from '../../components/chat/Messages';
import TasksWindow from '../../components/tasks/TasksWindow';

type ChatUIParams = {
  session : Session,
  isViewing : boolean,
  logOut : any,
  /** When false, Tasks panel waits for a successful `/canvas/all` sync before calling `/tasks_generate/self`. */
  canvasSyncReady : boolean,
}

export default function ChatUI({session, isViewing, logOut, canvasSyncReady} : ChatUIParams){

    const chatMainRef = useRef<HTMLDivElement>(null);

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
            <div className="chat-main-area" ref={chatMainRef}>
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
                <TasksWindow session={session} layoutContainerRef={chatMainRef} canvasSyncReady={canvasSyncReady}/>
            </div>
        </div>
    )
}
