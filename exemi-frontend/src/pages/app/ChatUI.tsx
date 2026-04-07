import {useEffect, useRef, useState} from 'react'
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
    const [taskDeconstructionRequest, setTaskDeconstructionRequest] = useState<{
        requestId: number;
        text: string;
        unitId: number | null;
    } | null>(null);

    useEffect(() => {
        if (typeof window === 'undefined') return;
        let requestIdCounter = 0;
        const onTaskDeconstructionRequest = (event: Event) => {
            const custom = event as CustomEvent<{
                taskId?: number;
                taskName?: string;
                unitId?: number | null;
            }>;
            const taskName = custom.detail?.taskName?.trim() || 'this task';
            const unitId =
                typeof custom.detail?.unitId === 'number' && Number.isFinite(custom.detail.unitId)
                    ? custom.detail.unitId
                    : null;
            requestIdCounter += 1;
            setTaskDeconstructionRequest({
                requestId: requestIdCounter,
                text: `Can you help me break down the task: **${taskName}** into smaller steps? Please create new tasks for each step. Have the due date of each task be the same as the original task and have each task be no longer than 10 minutes in length.`,
                unitId,
            });
        };
        window.addEventListener('task-deconstruction-request', onTaskDeconstructionRequest);
        return () =>
            window.removeEventListener('task-deconstruction-request', onTaskDeconstructionRequest);
    }, []);

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
                    taskDeconstructionRequest={taskDeconstructionRequest}
                />
                <TasksWindow session={session} layoutContainerRef={chatMainRef} canvasSyncReady={canvasSyncReady}/>
            </div>
        </div>
    )
}
