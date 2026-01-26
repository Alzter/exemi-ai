import {Routes, Route} from "react-router-dom";
import Dashboard from "./dashboard";

export default function LoggedInFlow() {
  return (
    <div>
      <Routes>
        <Route path="/" element={<Dashboard/>}/>
      </Routes>
      </div>
  )
}
