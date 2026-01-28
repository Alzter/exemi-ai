import {Routes, Route} from "react-router-dom";
import Dashboard from "./dashboard";
import ChatUI from "./chat";

export default function LoggedInFlow({session, setSession} : any) {
  return (
    <div>
      <Routes>
        <Route path="/" element={<Dashboard session={session} setSession={setSession}/>}/>
        <Route path="chat/" element={<ChatUI/>}/>
      </Routes>
      </div>
  )
}