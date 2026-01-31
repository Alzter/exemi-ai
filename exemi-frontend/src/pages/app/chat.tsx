import {useState, useEffect} from 'react'
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import MessageBox from '../../components/chat/message_box';

type ChatUIProps = {
    session : any,
    initialConversationID : number | null
}

type Message = {
    role : string,
    content : string
}

export default function ChatUI({session, initialConversationID} : ChatUIProps){

    const [conversationID, setConversationID] = useState<number|null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string|null>(null);

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

    async function sendMessage(event : React.FormEvent<HTMLFormElement>){
        event.preventDefault();
        setLoading(true);
        
        // Send the user's message on the client side
        // by updating the local list of messages
        // to contain the new message.
        setMessages(prev => [
            ...prev,
            {"role":"user","content":userText}
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
            setError("System error! Please contact Alexander Small.");
            return;
        }

        const data = await response.json();
        setConversationID(data.id);

        const messages : Message[] = data.messages as Message[];

        setMessages(messages);

        // TODO: call the backend API with the message.
        setLoading(false);
    }
    async function fetchMessages(){
        // TODO: PLACEHOLDER STUB
        setMessages([
            {"role":"user","content":"Hello! How do I eat porridge?"},
            {"role":"assistant","content":"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus nec metus id est consequat mollis. Donec dapibus elit dolor, sed venenatis turpis fringilla vel. Nam id lectus vitae purus euismod pulvinar ut eu est. Fusce faucibus, ex eget pretium elementum, odio neque gravida elit, vitae maximus elit ipsum vel turpis."},
            {"role":"user","content":"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus nec metus id est consequat mollis. Donec dapibus elit dolor, sed venenatis turpis fringilla vel. Nam id lectus vitae purus euismod pulvinar ut eu est. Fusce faucibus, ex eget pretium elementum, odio neque gravida elit, vitae maximus elit ipsum vel turpis."},
            {"role":"user","content":"HELLO 1"}
        ])
    }

    // When loading the conversation,
    // retrieve any existing messages if there are any.
    useEffect(() => {
        if (initialConversationID && !conversationID){
            setConversationID(initialConversationID);
            fetchMessages();
        }
    })

    return(
        <div className="chat">
            <div className="message-container">
                {messageBoxes}
            </div>
            <ErrorDisplay/>
            <form className="chatbox" onSubmit={sendMessage}>
                {/* TODO: User message box should wrap text and expand vertically */}
                <input type="text" onChange={handleTextUpdate} value={userText}/>
                <button type="submit" disabled={loading}>Send</button>
            </form>
        </div>
    )
}