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

    async function sendMessage(event : React.SubmitEvent<HTMLFormElement>){
        event.preventDefault();
        setLoading(true);
        
        // Send the user's message on the client side
        // by updating the local list of messages
        // to contain the new message.
        setMessages(prev => [
            ...prev,
            {"role":"user","content":userText}
        ]);

        // Placeholder message while LLM responds
        setMessages(prev => [
            ...prev,
            {"role":"assistant","content":"Thinking..."}
        ]);
        
        let body = {"message_text" : userText};

        let URL = backendURL + "/conversation"
        if (conversationID) {URL += "/" + conversationID}
        console.log(body);
        console.log(URL);

        setUserText("");

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
            const data = await response.json();
            if (typeof data.detail === "string"){
                message = data.detail;
            }
            setError(message);
            return;
        }

        const data = await response.json();
        setConversationID(data.id);

        const messages : Message[] = data.messages as Message[];

        setMessages(messages);

        // TODO: call the backend API with the message.
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
