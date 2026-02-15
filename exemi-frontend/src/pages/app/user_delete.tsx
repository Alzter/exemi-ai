import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
import UserSelector from "../../components/admin/user_selector";
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function UserDelete({session} : any){

    const [user, setUser] = useState<string>();

    // If user is not an admin, exit page
    let navigate = useNavigate();
    useEffect(() => {
        if (!session.user.admin){
            navigate("/");
        }
    }, [])

    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(false);

    async function handleSubmit(event : React.SubmitEvent<HTMLFormElement>){
        event.preventDefault();
        setLoading(true);
        
        const response = await fetch(backendURL + "/users/" + user, {
            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method:"DELETE"
        });

        if (response.ok){
            setError("User successfully deleted!");
            setLoading(false);
            return;
        } else {
            let message = "System error!";
            try{
                let data = await response.json();
                if (typeof data.detail === "string"){
                    message = data.detail;
                }
                setError(message);
                setLoading(false);
                return;
            } catch {
                setError(message);
                setLoading(false);
            }
        }
    };

    return (
        <div className="form">
            <form className="login" onSubmit={handleSubmit}>
                <UserSelector session={session} setError={setError} setUser={setUser}/>
                <button type="submit" disabled={loading}>Delete User</button>
                <button onClick={() => navigate("/")}>Back</button>
                {error ? (<div className='error'><p>{error}</p></div>) : null}
            </form>
        </div>
    )
}