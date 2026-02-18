import {Routes, Route} from "react-router-dom";
import Dashboard from "./dashboard";
import ChatUI from "./chat";
import UserCreate from "./user_create";
import UserDelete from "./user_delete";

export default function LoggedInFlow({session, setSession, logOut} : any) {
  return (
    <div>
      <Routes>
        <Route path="/" element={<Dashboard session={session} setSession={setSession} logOut={logOut}/>}/>
        <Route path="chat/" element={<ChatUI session={session}/>}/>
        <Route path="user_create/" element={<UserCreate session={session}/>}/>
        <Route path="user_delete/" element={<UserDelete session={session}/>}/>
      </Routes>
      </div>
  )
}