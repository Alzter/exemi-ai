import {Routes, Route} from "react-router"
import Login from "./login"

export default function Auth() {
    return (
    <Routes>
        <Route path="/" element={<Login/>}/>
    </Routes>
    )
}