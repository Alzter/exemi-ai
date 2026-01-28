import {Routes, Route} from "react-router-dom";
import Slides from "./slides";

export default function Onboarding() {
  return (
    <div>
      <Routes>
        <Route path="/" element={<Slides/>}/>
      </Routes>
      </div>
  )
}