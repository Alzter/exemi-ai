import {Routes, Route} from "react-router-dom";
import Slides from "./slides";

export default function Onboarding({setSession} : any) {
  return (
    <div>
      <Routes>
        <Route path="/" element={<Slides setSession={setSession}/>}/>
      </Routes>
      </div>
  )
}