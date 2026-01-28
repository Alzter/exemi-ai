import {Routes, Route} from "react-router-dom";
import MagicForm from "./form";

export default function Onboarding({session, setSession} : any) {
  return (
    <div>
      <Routes>
        <Route path="/" element={<MagicForm session={session} setSession={setSession}/>}/>
      </Routes>
      </div>
  )
}