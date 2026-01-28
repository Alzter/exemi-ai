import {Routes, Route} from "react-router-dom";
import MagicForm from "./form";

export default function Onboarding({session, setSession, setMagicValid} : any) {
  return (
    <div>
      <Routes>
        <Route path="/" element={<MagicForm session={session} setSession={setSession} setMagicValid={setMagicValid}/>}/>
      </Routes>
      </div>
  )
}