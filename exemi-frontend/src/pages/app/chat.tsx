import {useState, useEffect} from 'react'
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import Message from '../../components/chat/message';

export default function ChatUI(){

    const [userMessage, setUserMessage] = useState<string>("");

    function updateMessage(event : React.ChangeEvent<HTMLInputElement>){
        setUserMessage(event.target.value);
    }

    async function sendMessage(event : React.FormEvent<HTMLFormElement>){
        event.preventDefault();

        console.log(userMessage);

        // TODO: call the backend API with the message.
    }

    return(
        <div className="chat">
            <div className="message-container">
                <Message role='user' content='Hello? How do I eat porridge?'/>
                <Message role='assistant' content='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus nec metus id est consequat mollis. Donec dapibus elit dolor, sed venenatis turpis fringilla vel. Nam id lectus vitae purus euismod pulvinar ut eu est. Fusce faucibus, ex eget pretium elementum, odio neque gravida elit, vitae maximus elit ipsum vel turpis.'/>
                <Message role='user' content='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus nec metus id est consequat mollis. Donec dapibus elit dolor, sed venenatis turpis fringilla vel. Nam id lectus vitae purus euismod pulvinar ut eu est. Fusce faucibus, ex eget pretium elementum, odio neque gravida elit, vitae maximus elit ipsum vel turpis.'/>
                <Message role='assistant' content='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus nec metus id est consequat mollis. Donec dapibus elit dolor, sed venenatis turpis fringilla vel. Nam id lectus vitae purus euismod pulvinar ut eu est. Fusce faucibus, ex eget pretium elementum, odio neque gravida elit, vitae maximus elit ipsum vel turpis.'/>
                <Message role='user' content='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus nec metus id est consequat mollis. Donec dapibus elit dolor, sed venenatis turpis fringilla vel. Nam id lectus vitae purus euismod pulvinar ut eu est. Fusce faucibus, ex eget pretium elementum, odio neque gravida elit, vitae maximus elit ipsum vel turpis.'/>
                <Message role='assistant' content='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus nec metus id est consequat mollis. Donec dapibus elit dolor, sed venenatis turpis fringilla vel. Nam id lectus vitae purus euismod pulvinar ut eu est. Fusce faucibus, ex eget pretium elementum, odio neque gravida elit, vitae maximus elit ipsum vel turpis.'/>
                <Message role='user' content='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus nec metus id est consequat mollis. Donec dapibus elit dolor, sed venenatis turpis fringilla vel. Nam id lectus vitae purus euismod pulvinar ut eu est. Fusce faucibus, ex eget pretium elementum, odio neque gravida elit, vitae maximus elit ipsum vel turpis.'/>
                <Message role='assistant' content='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus nec metus id est consequat mollis. Donec dapibus elit dolor, sed venenatis turpis fringilla vel. Nam id lectus vitae purus euismod pulvinar ut eu est. Fusce faucibus, ex eget pretium elementum, odio neque gravida elit, vitae maximus elit ipsum vel turpis.'/>
                <Message role='user' content='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus nec metus id est consequat mollis. Donec dapibus elit dolor, sed venenatis turpis fringilla vel. Nam id lectus vitae purus euismod pulvinar ut eu est. Fusce faucibus, ex eget pretium elementum, odio neque gravida elit, vitae maximus elit ipsum vel turpis.'/>
                <Message role='assistant' content='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus nec metus id est consequat mollis. Donec dapibus elit dolor, sed venenatis turpis fringilla vel. Nam id lectus vitae purus euismod pulvinar ut eu est. Fusce faucibus, ex eget pretium elementum, odio neque gravida elit, vitae maximus elit ipsum vel turpis.'/>
                <Message role='user' content='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus nec metus id est consequat mollis. Donec dapibus elit dolor, sed venenatis turpis fringilla vel. Nam id lectus vitae purus euismod pulvinar ut eu est. Fusce faucibus, ex eget pretium elementum, odio neque gravida elit, vitae maximus elit ipsum vel turpis.'/>

            </div>
            <form className="chatbox" onClick={sendMessage}>
                <input type="text" name="message" onChange={updateMessage} value={userMessage}/>
                <button type="submit">Send</button>
            </form>
        </div>
    )
}