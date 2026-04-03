
import { MdErrorOutline } from "react-icons/md";

export default function BigError(){
    return(
        <div className="form">
            
            <p className="logo">exemi</p>
            <div className="error">
                <h1>
                <MdErrorOutline/>
                <br/>
                System Error</h1>
                <br/>
                <p>The Exemi backend is offline.
                    If you're reading this, something has gone wrong.
                    Please contact Alexander Small.</p>
            </div>
        </div>
    )
}