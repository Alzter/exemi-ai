import {Routes, Route} from "react-router-dom";
import Dashboard from "./dashboard";

export default function LoggedInFlow({setSession} : any) {
  return (
    <div>
      <Routes>
        <Route path="/" element={<Dashboard setSession={setSession}/>}/>
      </Routes>
      </div>
  )
}