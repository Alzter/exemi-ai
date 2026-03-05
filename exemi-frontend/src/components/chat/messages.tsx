import React, {useState, useEffect, useRef} from 'react'
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import MessageBox from './message_box';

type ChatUIProps = {
    session : any,
    isViewing : boolean,
    conversationID : number | null,
    setConversationID : any,
    loading : boolean,
    setLoading : any,
    error : string | null,
    setError : any
}

type Message = {
    role : string,
    content : string,
    id : number
}

type Conversation = {
    created_at : Date
    id : number
}

export default function ChatMessagesUI({session, isViewing, conversationID, setConversationID, loading, setLoading, error, setError} : ChatUIProps){

    const [awaitingLLMResponse, setAwaitingLLMResponse] = useState<boolean>(false);

    const [messages, setMessages] = useState<Message[]>([]);

    // The user's current message text.
    const [userText, setUserText] = useState<string>("");

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

    function ErrorDisplay() {
        if (!error) return (null)
        return(
            <div className='error'>
                <p>{error}</p>
            </div>
        )
    }

    // If we're waiting for the LLM to respond, add a message with the text "Thinking..." to the end of the list
    const messageBoxes = [...messages.map(
        message => <MessageBox role={message.role} content={message.content} key={message.id}/>
    ), ...(
        awaitingLLMResponse ? [<MessageBox role="assistant" content="Thinking..." key={-2}/>] : []
    )]

    function handleTextUpdate(event : React.ChangeEvent<HTMLTextAreaElement>){
        setUserText(event.target.value);
    }

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
        }
    }
    
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
        }

        let initial_message = await response.json();
        setMessages(prev => [
            ...prev,
            {"role":"assistant","content":initial_message,"id":0}
        ]);
    }

    async function handleLLMResponse(conversationID : number) {
        // Stream the LLM's response from the server.
        // Credit to Irtiza Hafiz for the code: https://youtu.be/i7GlWbAFDtY

        let URL = backendURL + "/conversation_stream_reply/" + conversationID

        const llm_response = await fetch(URL, {
            headers:{
                "Authorization" : "Bearer " + session.token,
                accept:"application/json"
            },
            method:"GET"
        });

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
    }

    async function sendMessage(event : React.SubmitEvent<HTMLFormElement>){
        event.preventDefault();

        // Prevent the user sending an empty message
        if (!userText.trim() || loading){
            return;
        }

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
            {"role":"user","content":userText,"id":1}
        ]);

        // Show a placeholder "Thinking..." message before the LLM responds properly
        setAwaitingLLMResponse(true);
        
        let body = {"message_text" : userText};

        let URL = backendURL + "/conversation" + (conversationID ? "/" + conversationID : "")
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
            return;
        }

        const conversation = await response.json();
        setConversationID(conversation.id);

        const messages : Message[] = conversation.messages as Message[];

        setMessages(messages);
        
        // Step 2: If the Conversation returned successfully,
        // call the LLM to respond to the user's message.
        
        await handleLLMResponse(conversation.id);

        setLoading(false);
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
                <button disabled={loading || !conversationID} onClick={deleteConversation}>Delete Chat</button>
              </div>
            ) : (
              <form className="chatbox" ref={chatboxRef} onSubmit={sendMessage}>
                  <textarea
                    autoFocus
                    placeholder="Ask anything"
                    ref={chatboxTextRef}
                    rows={1}
                    onChange={handleTextUpdate}
                    onKeyDown={handleTextKeyDown}
                    value={userText}
                />
                  <button type="submit" disabled={loading}>Send</button>
              </form>
            )}
        </div>
    )
}
