import {Routes, Route} from "react-router-dom";
import Slides from "./slides";

export default function Onboarding({session, setSession} : any) {
  return (
    <div>
      <Routes>
        <Route path="/" element={<Slides session={session} setSession={setSession}/>}/>
      </Routes>
      </div>
  )
}