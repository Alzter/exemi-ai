import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
import {type User} from '../../models';
import UniversitySelector from "../../components/admin/university_selector";
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function EditUniAliases({session} : any){
    
    const [universityName, setUniversityName] = useState<string>("");
    const [error, setError] = useState<string | null>(null);
    let navigate = useNavigate();

    return (
        <div className="form wide">
            <h1>Manage University Aliases</h1>
            <p>
                Each university name references a Canvas provider URL.
                However, you may want to add additional providers
                (aliases) in case the original one fails.
            </p>
            <div className="input-row">
                <label>
                    University:
                </label>
                <UniversitySelector
                    universityName={universityName}
                    setUniversityName={setUniversityName}
                    session={session} setError={setError}
                    refreshTrigger={null}
                />
            </div>
            <button className="back" onClick={() => navigate("/")}>{"<"} Back</button>
            {error ? (<div className='error'><p>{error}</p></div>) : null}
        </div>
    )
}