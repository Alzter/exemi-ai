import {Routes, Route} from "react-router"
import Login from "./login"

export default function Auth({setSession} : any) {
    return (
    <Routes>
        <Route path="/" element={<Login setSession={setSession}/>}/>
    </Routes>
    )
}