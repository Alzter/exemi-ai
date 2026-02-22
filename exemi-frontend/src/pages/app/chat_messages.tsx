import {useState, useEffect} from 'react'
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import MessageBox from '../../components/chat/message_box';

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
    content : string
}

type Conversation = {
    created_at : Date
    id : number
}

export default function ChatMessagesUI({session, isViewing, conversationID, setConversationID, loading, setLoading, error, setError} : ChatUIProps){

    const [messages, setMessages] = useState<Message[]>([]);

    // The user's current message text.
    const [userText, setUserText] = useState<string>("");

    function ErrorDisplay() {
        if (!error) return (null)
        return(
            <div className='error'>
                <p>{error}</p>
            </div>
        )
    }

    const messageBoxes = messages.map(
        message => <MessageBox role={message.role} content={message.content}/>
    )

    function handleTextUpdate(event : React.ChangeEvent<HTMLInputElement>){
        setUserText(event.target.value);
    }

    //
    async function handleLLMResponse(conversationID : number) {
        // Stream the LLM's response from the server.
        // Credit to Irtiza Hafiz for the code: https://youtu.be/i7GlWbAFDtY
        let responseText = ""

        let URL = backendURL + "/conversation_stream_reply/" + conversationID

        const llm_response = await fetch(URL, {
            headers:{
                "Authorization" : "Bearer " + session.token,
                accept:"application/json"
            },
            method:"GET"
        });

        const reader = llm_response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let done = false;

        // Create an empty LLM message
        setMessages(prev => [
            ...prev,
            {"role":"assistant","content":""}
        ]);

        while (!done){
            const {value, done: readerDone} = await reader.read();
            done = readerDone;
            
            const chunkValue = decoder.decode(value, {stream:true});

            console.log(chunkValue);
            responseText += chunkValue;
        };

        // if (!llm_response.ok){
        //     let message = "System error! Please contact Alexander Small.";
        //     try{
        //         if (llm_response.status == 504){
        //             message = "Error! The Exemi chatbot took too long to respond! Please try again later."
        //         } else {
        //              let data = await llm_response.json();
        //              if (typeof data.detail === "string"){
        //                  message = data.detail;
        //              }
        //         }
        //         setError(message);
        //     } catch {
        //         setError(message);
        //     }
        //     return;
        // }

        // // Add the LLM's response on the client-side.
        // // The server will add it to the database
        // // asynchronously.
        // const reply = await llm_response.json();

        // setMessages(prev => [
        //     ...prev,
        //     {"role":"assistant","content":reply}
        // ]);
    }

    async function sendMessage(event : React.SubmitEvent<HTMLFormElement>){
        event.preventDefault();
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
            {"role":"user","content":userText}
        ]);

        // Placeholder message while LLM responds
        // setMessages(prev => [
        //     ...prev,
        //     {"role":"assistant","content":"Thinking..."}
        // ]);
        
        let body = {"message_text" : userText};

        let URL = backendURL + "/conversation" + (conversationID ? "/" + conversationID : "")
        console.log(body);
        console.log(URL);
        
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
                let data = await response.json();
                if (typeof data.detail === "string"){
                    message = data.detail;
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
            content : item.content
        }));

        setMessages(messages);
    }

    async function loadMessages(conversationID : number | null){
        if (!conversationID) {
            setMessages([]);
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
              <form className="chatbox" onSubmit={sendMessage}>
                  {/* TODO: User message box should wrap text and expand vertically */}
                  <input type="text" onChange={handleTextUpdate} value={userText}/>
                  <button type="submit" disabled={loading}>Send</button>
              </form>
            )}
        </div>
    )
}
