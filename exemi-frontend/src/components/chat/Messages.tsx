import React, {useState, useEffect, useRef, type ChangeEvent} from 'react';
import {type UserUnit} from '../../models';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import MessageBox from './MessageBox';
import { parseColourRawToOklch } from '../../utils/taskBoardUtils';

type ChatUIProps = {
    session : any,
    isViewing : boolean,
    conversationID : number | null,
    setConversationID : any,
    loading : boolean,
    setLoading : any,
    error : string | null,
    setError : any,
    taskDeconstructionRequest?: {
        requestId: number;
        text: string;
        unitId: number | null;
    } | null;
}

type Message = {
    role : string,
    content : string,
    id : number
}

function dispatchTasksRefreshRequested() {
    if (typeof window === 'undefined') return;
    window.dispatchEvent(new CustomEvent('tasks-refresh-requested'));
}

export default function ChatMessagesUI({
    session,
    isViewing,
    conversationID,
    setConversationID,
    loading,
    setLoading,
    error,
    setError,
    taskDeconstructionRequest,
} : ChatUIProps){

    const [units, setUnits] = useState<UserUnit[]>([]);
    // const units : UserUnit[] = session.user.units;

    const [awaitingLLMResponse, setAwaitingLLMResponse] = useState<boolean>(false);

    const [messages, setMessages] = useState<Message[]>([]);

    const [unitSelected, setUnitSelected] = useState<UserUnit|null>(null);
    const [conversationUnitID, setConversationUnitID] = useState<number | null>(null);
    const [conversationColourRaw, setConversationColourRaw] = useState<string | null>(null);
    const [isTextareaFocused, setIsTextareaFocused] = useState<boolean>(false);

    const unitID : number | null = (unitSelected && !conversationID) ? unitSelected.unit_id : null;
    const unitThemeColourRaw = conversationID ? conversationColourRaw : (unitSelected?.colour ?? null);
    const UnitThemeColour = unitThemeColourRaw
        ? parseColourRawToOklch(unitThemeColourRaw, 0.6, 0.2)
        : undefined;
    const userMessageBackgroundColour = conversationColourRaw
        ? parseColourRawToOklch(conversationColourRaw, 0.92, 0.036)
        : undefined;
    const unitSelectWidth = unitSelected
        ? `${Math.min(Math.max(unitSelected.readable_name.length + 2, 8), 30)}ch`
        : "8em";
    const unitSelectStyle = unitSelected?.colour
        ? {
            backgroundColor: parseColourRawToOklch(unitSelected.colour, 0.92, 0.036),
            borderColor: UnitThemeColour,
            fontWeight: "600"
        }
        : undefined;
    const unitSelectWrapperStyle = {width: conversationID ? "0" : unitSelectWidth};
    const sizedUnitSelectStyle = {
        ...unitSelectStyle,
        minWidth: unitSelectWidth,
        maxWidth: unitSelectWidth
    };
    const textareaStyle = UnitThemeColour && isTextareaFocused ? {borderColor: UnitThemeColour} : undefined;
    const sendButtonStyle = UnitThemeColour ? {backgroundColor: UnitThemeColour} : undefined;

    // The user's current message text.
    const [userText, setUserText] = useState<string>("");

    // Obtain the list of the user's units when first loading
    useEffect(() => {
        getUserUnits();
    }, []);

    // Keep unit selector in sync with the currently selected conversation.
    useEffect(() => {
        if (!conversationID){
            setConversationUnitID(null);
            return;
        }

        if (conversationUnitID === null){
            setUnitSelected(null);
            return;
        }

        const matchingUnit = units.find((unit) => unit.unit_id === conversationUnitID) ?? null;
        setUnitSelected(matchingUnit);
    }, [conversationID, conversationUnitID, units]);

    // Auto-update the height of the chat box
    // when the user message text changes
    // OR the size of the textarea changes.
    useEffect(() => {
        const chatbox = chatboxTextRef.current;
        if (!chatbox) return;

        const updateHeight = () => {
            // console.log("Size updated");
            chatbox.style.height = "auto";
            chatbox.style.height = `${chatbox.scrollHeight + 4}px`;
        };

        // Observe width changes
        const resizeObserver = new ResizeObserver(() => {
            updateHeight();
        });

        resizeObserver.observe(chatbox);

        return () => resizeObserver.disconnect();
        
    }, [userText]);

    // The HTML element for the chat text box.
    const chatboxRef = useRef<HTMLFormElement>(null);
    const chatboxTextRef = useRef<HTMLTextAreaElement>(null);
    const lastHandledTaskDeconstructionIdRef = useRef<number>(0);

    function ErrorDisplay() {
        if (!error) return (null)
        return(
            <div className='error'>
                <p>{error}</p>
            </div>
        )
    }

    async function getUserUnits(){
        const URL = backendURL + "/user_units"

        const response = await fetch(URL, {
            headers:{
                "Authorization" : "Bearer " + session.token,
                accept:"application/json"
            },
            method:"GET"
        });
        
        if (!response.ok) {
            setError("Error obtaining user units!");
            return;
        };

        const data = await response.json();
        const units : UserUnit[] = data as UserUnit[];

        // Sort units alphabetically
        units.sort((a, b) => a.readable_name.localeCompare(b.readable_name));

        setUnits(units);
    };

    async function handleUnitSelected(event : ChangeEvent<HTMLSelectElement>){
        const unit : UserUnit | undefined = units.find(unit => unit.readable_name === event.target.value);

        if (unit){
            setUnitSelected(unit);
        } else {
            setUnitSelected(null);
        };
    };

    // useEffect(() => {
    //     if (unitID){
    //         console.log(unitID);
    //     } else {
    //         console.log("No unit");
    //     }
    // }, [unitID]);

    // If we're waiting for the LLM to respond, add a message with the text "Thinking..." to the end of the list
    const messageBoxes = [...messages.map(
        message => (
            <MessageBox
                role={message.role}
                content={message.content}
                key={message.id}
                userBackgroundColour={userMessageBackgroundColour}
            />
        )
    ), ...(
        awaitingLLMResponse ? [<MessageBox role="assistant" content="Thinking..." key={-2}/>] : []
    )]

    function handleTextUpdate(event : React.ChangeEvent<HTMLTextAreaElement>){
        setUserText(event.target.value);
    };

    function handleTextKeyDown(event : React.KeyboardEvent<HTMLTextAreaElement>){
        // Manually intercept the HTML text area
        // "key down" event to submit the user's
        // message if the Enter key is pressed
        // without the Shift key.

        // By default, HTML text areas do not
        // call a form submit when Enter is pressed.
        if (event.key === "Enter" && !event.shiftKey){
            event.preventDefault();

            let chatbox = chatboxRef.current;
            if (chatbox){
                chatbox.requestSubmit();
            };
        };
    };
    
    async function getInitialMessage() {
        // Obtain the LLM's conversation starter
        // message before the conversation is
        // formally created.
        
        const URL = backendURL + "/conversation_greeting"
        
        const response = await fetch(URL, {
            headers:{
                "Authorization" : "Bearer " + session.token,
                accept:"application/json"
            },
            method:"GET"
        });
        
        if (!response.ok) {
            setError("Error obtaining LLM initial message.");
            return;
        };

        let initial_message = await response.json();
        setMessages(prev => [
            ...prev,
            {"role":"assistant","content":initial_message,"id":0}
        ]);
    };

    async function handleLLMResponse(conversationID : number) {
        // Stream the LLM's response from the server.
        // Credit to Irtiza Hafiz for the code: https://youtu.be/i7GlWbAFDtY

        let URL = backendURL + "/conversation_stream_reply/" + conversationID

        try{
            const llm_response = await fetch(URL, {
                headers:{
                    "Authorization" : "Bearer " + session.token,
                    accept:"application/json"
                },
                method:"GET"
            });

            if (!llm_response.ok || !llm_response.body) {
                setError("Error retrieving LLM response.");
                setAwaitingLLMResponse(false);
                setLoading(false);
                return;
            }

            // Add an empty message before the LLM responds
            setMessages(prev => [
                ...prev,
                {"role":"assistant","content":"",id:-3}
            ]);

            const reader = llm_response.body.getReader();
            const decoder = new TextDecoder("utf-8");

            let done = false;
            let responseText = ""

            while (!done){
                const {value, done: readerDone} = await reader.read();
                done = readerDone;
                
                const chunkValue : string = decoder.decode(value, {stream:true});
                
                if (!chunkValue) { continue };

                setAwaitingLLMResponse(false);

                responseText += chunkValue;

                // Overwrite the placeholder LLM message with the
                // current streamed content.
                setMessages(prev => [
                    ...prev.slice(0, -1), // Drop the previous LLM message
                    {"role":"assistant","content":responseText,id:-3}
                ]);
                
            };
            dispatchTasksRefreshRequested();
        } catch {
            setError("Error retrieving LLM response.");
            setAwaitingLLMResponse(false);
            setLoading(false);
        };
    };

    async function sendTextMessage(
        text: string,
        options?: {forceNewConversation?: boolean; newConversationUnitId?: number | null},
    ) {
        const cleanText = text.trim();
        if (!cleanText || loading){
            return;
        };
        const forceNewConversation = Boolean(options?.forceNewConversation);
        const newConversationUnitId = options?.newConversationUnitId;

        setLoading(true);
        setUserText("");
        
        // Step 1: Send the user's message to the server
        // and receive a Conversation object with the
        // new list of messages and Conversation ID

        // Send the user's message on the client side
        // by updating the local list of messages
        // to contain the new message.
        setMessages(prev => [
            ...prev,
            {"role":"user","content":cleanText,"id":1}
        ]);

        // Show a placeholder "Thinking..." message before the LLM responds properly
        setAwaitingLLMResponse(true);
        
        let body = {
            "message_text" : cleanText,
            "unit_id" : forceNewConversation
                ? (newConversationUnitId ?? null)
                : unitID,
        };

        const useExistingConversation = !forceNewConversation && Boolean(conversationID);
        let URL =
            backendURL + "/conversation" + (useExistingConversation ? "/" + conversationID : "")
        // console.log(body);
        // console.log(URL);
        
        const response = await fetch(URL, {
            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method:"POST",
            body: JSON.stringify(body)
        });

        if (!response.ok){
            let message = "System error! Please contact Alexander Small.";
            try{
                if (response.status == 504){
                    message = "Error! The Exemi chatbot took too long to respond! Please try again later."
                } else {
                    let data = await response.json();
                    if (typeof data.detail === "string"){
                        message = data.detail;
                    }
                }
                setError(message);
            } catch {
                setError(message);
            }
            setAwaitingLLMResponse(false);
            setLoading(false);
            return;
        };

        const conversation = await response.json();
        setConversationID(conversation.id);
        setConversationColourRaw(conversation.colour_raw ?? null);

        const messages : Message[] = conversation.messages as Message[];

        setMessages(messages);
        
        // Step 2: If the Conversation returned successfully,
        // call the LLM to respond to the user's message.
        
        await handleLLMResponse(conversation.id);

        setLoading(false);
    }

    async function sendMessage(event : React.SubmitEvent<HTMLFormElement>){
        event.preventDefault();
        await sendTextMessage(userText);
    }

    async function parseMessages(data : Array<any>){
        const messages : Message[] = data.map(item => ({
            role : item.role,
            content : item.content,
            id : item.id
        }));

        setMessages(messages);
    }

    async function loadMessages(conversationID : number | null){
        if (!conversationID) {
            setMessages([]);
            setConversationUnitID(null);
            setConversationColourRaw(null);

            if (!isViewing){
                await getInitialMessage();
            }
            
            return;
        }

        let URL = backendURL + "/conversation/" + conversationID
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
        setConversationUnitID(data.unit_id ?? null);
        setConversationColourRaw(data.colour_raw ?? null);
        parseMessages(data.messages);
    }
  
    async function deleteConversation() {
        setLoading(true);

        let URL = backendURL + "/conversation/" + conversationID
        const response = await fetch(URL, {
            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method:"DELETE"
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

        setLoading(false);
        setConversationID(null);
    }

    useEffect(() => {
        loadMessages(conversationID);
    }, [conversationID])

    useEffect(() => {
        if (isViewing || loading) return;
        if (!taskDeconstructionRequest) return;
        if (taskDeconstructionRequest.requestId <= lastHandledTaskDeconstructionIdRef.current) return;
        lastHandledTaskDeconstructionIdRef.current = taskDeconstructionRequest.requestId;
        void sendTextMessage(taskDeconstructionRequest.text, {
            forceNewConversation: true,
            newConversationUnitId: taskDeconstructionRequest.unitId,
        });
    }, [isViewing, loading, taskDeconstructionRequest]);
    // When loading the conversation,
    // retrieve any existing messages if there are any.
    // useEffect(() => {
    //     if (initialConversationID && !conversationID){
    //         setConversationID(initialConversationID);
    //         fetchMessages();
    //     }
    // })

    return(
        <div className="chat-messages">
            <div className="message-container">
                {messageBoxes}
            </div>
            <ErrorDisplay/>
            { isViewing ? (
              <div className="chatbox">
                <button className="primary" disabled={loading || !conversationID} onClick={deleteConversation}>Delete Chat</button>
              </div>
            ) : (
                <form className="chatbox" ref={chatboxRef} onSubmit={sendMessage}>
                    <div
                        className={
                            "chatbox-unit-select-wrap" +
                            (conversationID ? "" : " chatbox-unit-select-wrap--open")
                        }
                        style={unitSelectWrapperStyle}
                        aria-hidden={Boolean(conversationID)}>
                        <select
                            className="unit-select"
                            name="unit"
                            id="unit"
                            value={unitSelected?.readable_name ?? "all"}
                            onChange={handleUnitSelected}
                            disabled={Boolean(conversationID)}
                            style={sizedUnitSelectStyle}>
                            <option value="all">All Units</option>
                            {units.map((unit) => <option
                                value={unit.readable_name}
                                key={unit.unit_id}
                            >
                                {unit.readable_name}
                            </option>)}
                        </select>
                    </div>
                    <textarea
                        autoFocus
                        placeholder="Ask anything"
                        ref={chatboxTextRef}
                        rows={1}
                        onChange={handleTextUpdate}
                        onKeyDown={handleTextKeyDown}
                        onFocus={() => { setIsTextareaFocused(true); }}
                        onBlur={() => { setIsTextareaFocused(false); }}
                        value={userText}
                        style={textareaStyle}
                    />
                    <button className="primary" type="submit" disabled={loading} style={sendButtonStyle}>Send</button>
                </form>
            )}
        </div>
    )
}
