import {Routes, Route} from "react-router-dom";
import Dashboard from "./dashboard";

export default function LoggedInFlow({session, setSession} : any) {
  return (
    <div>
      <Routes>
        <Route path="/" element={<Dashboard session={session} setSession={setSession}/>}/>
      </Routes>
      </div>
  )
}