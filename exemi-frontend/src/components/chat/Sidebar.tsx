import {useState, useEffect, type CSSProperties} from 'react'
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import { useNavigate } from 'react-router-dom';
import {type Session} from '../../models';
import { parseColourRawToOklch } from '../../utils/taskBoardUtils';
import { MdCheck, MdEdit } from 'react-icons/md';
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
    id : number
    name : string | null
    created_at : Date
    colour_raw : string | null
}

export default function ChatSidebar({session, enabled, setEnabled, isViewing, loading, conversationID, setConversationID, setError, logOut} : ChatSidebarParams) {

    let navigate = useNavigate();

    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [username, setUsername] = useState<string>(
        isViewing ? "1" : (session.user?.username ?? "")
    );
    const [hoveredConversationID, setHoveredConversationID] = useState<number | null>(null);
    const [editingConversationID, setEditingConversationID] = useState<number | null>(null);
    const [draftConversationName, setDraftConversationName] = useState<string>("");

    function toggleChatSidebar(){
        if (enabled){ setEnabled(false); } else { setEnabled(true); }
        // setEnabled(prev => !prev);
    };

    async function parseConversations(data : Array<any>, auto_select_first_conversation : boolean){
        const conversations: Conversation[] = data.map(item => ({
            id: item.id,
            name: item.name,
            created_at: new Date(item.created_at),
            colour_raw: item.colour_raw,
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
        const hasConversationID = typeof ID === "number";
        const isConversation = !!conversation && hasConversationID;
        const isSelected = conversationID == ID;
        const isHovered = hoveredConversationID == ID;
        const isEditing = isConversation && editingConversationID == ID;
        
        let title = "";
        if (conversation){
            if (conversation.name){
                title = conversation.name;
            } else {
                let conversationDateString = conversation.created_at.toLocaleString(
                    "en-AU", {timeZone: "Australia/Sydney"}
                )
                title = conversationDateString;
            }
        } else {
            title = "+ Create New Chat";
        };

        function assignConversation(){
            if (isEditing){
                return;
            }
            setConversationID(ID);
        };

        async function confirmRename(event : any){
            event.preventDefault();
            event.stopPropagation();

            if (!conversation || !hasConversationID){
                return;
            }

            const nextName = draftConversationName.trim();
            setConversations(prev => prev.map(c => c.id === conversation.id ? {...c, name: nextName || null} : c));
            setEditingConversationID(null);
            setDraftConversationName("");

            const URL = backendURL + "/conversation/" + ID;
            const response = await fetch(URL, {
                headers: {
                    "Authorization": "Bearer " + session.token,
                    "Content-Type": "application/json",
                    accept: "application/json"
                },
                method: "PATCH",
                body: JSON.stringify({name: nextName})
            });

            if (!response.ok){
                setError("Error updating conversation name!");
            }
        }

        function startRename(event : any){
            event.preventDefault();
            event.stopPropagation();
            if (!conversation || !hasConversationID){
                return;
            }
            setEditingConversationID(ID);
            setDraftConversationName(conversation.name ?? "");
        }

        function cancelRename(event : any){
            event.preventDefault();
            event.stopPropagation();
            setEditingConversationID(null);
            setDraftConversationName("");
        }

        let className = isSelected ? "primary conversation-selected" : "primary conversation";
        if (!conversation) {className = "primary";}
        

        let backgroundColor : string = "";
        let hoverColor : string = "";
        let activeColor : string = "";
        
        if (conversation?.colour_raw){
            backgroundColor = parseColourRawToOklch(conversation.colour_raw, 0.92, 0.036);
            hoverColor = parseColourRawToOklch(conversation.colour_raw, 0.85, 0.06);
            activeColor = parseColourRawToOklch(conversation.colour_raw, 0.8, 0.1);
            // console.log("colour_raw: " + conversation.colour_raw);
        };

        const buttonStyle: CSSProperties & Record<string, string> = {};
        if (backgroundColor) { buttonStyle["--conversation-bg"] = backgroundColor; }
        if (hoverColor) { buttonStyle["--conversation-hover-bg"] = hoverColor; }
        if (activeColor) { buttonStyle["--conversation-active-bg"] = activeColor; }

        const showRenameButton = isConversation && (isSelected || isHovered) && !isEditing;
        const showConfirmButton = isEditing && isConversation;

        const actionSlotMirrorPadding = "calc(32px + 0.3em)";
        const titleParagraphStyle: CSSProperties = {
            flexGrow: 1,
            minWidth: 0,
            margin: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            ...(showRenameButton
                ? {paddingLeft: actionSlotMirrorPadding, textAlign: "center"}
                : {}),
        };

        return (
            <button
                onClick = {assignConversation}
                className={className}
                style={buttonStyle}
                onMouseEnter={() => { if (isConversation) { setHoveredConversationID(ID); } }}
                onMouseLeave={() => { if (isConversation) { setHoveredConversationID(null); } }}
                disabled={loading}>
                    {isEditing ? (
                        <>
                            <input
                                value={draftConversationName}
                                onChange={(event) => { setDraftConversationName(event.target.value); }}
                                onClick={(event) => { event.stopPropagation(); }}
                                onBlur={cancelRename}
                                onKeyDown={(event) => {
                                    if (event.key === "Enter"){
                                        void confirmRename(event);
                                    } else if (event.key === "Escape"){
                                        cancelRename(event);
                                    }
                                }}
                                type="text"
                                placeholder="Enter chat name..."
                                autoFocus
                                style={{flexGrow: 1, minWidth: 0, margin:0, height:"80%"}}
                            />
                            <button
                                className="primary"
                                onMouseDown={(event) => { event.preventDefault(); }}
                                onClick={confirmRename}
                                type="button"
                                style={{width: "32px", height: "32px", minWidth: "32px", padding: 0}}>
                                {showConfirmButton ? <MdCheck style={{margin:0}} aria-hidden /> : null}
                            </button>
                        </>
                    ) : (
                        <>
                            <p style={titleParagraphStyle}>
                                {title}
                            </p>
                            {showRenameButton ? (
                                <button
                                    className="floating"
                                    onClick={startRename}
                                    type="button"
                                    style={{width: "32px", height: "32px", minWidth: "32px", borderRadius: "8px"}}>
                                    <MdEdit aria-hidden />
                                </button>
                            ) : null}
                        </>
                    )}
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