import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
import UserSelector from "../../components/admin/user_selector";
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function UserDelete({session} : any){

    const [user, setUser] = useState<string>();
    const [refreshUsers, setRefreshUsers] = useState(0);

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
        
        if (user === session.user.username){
            setError("You cannot delete your own account!");
            setLoading(false);
            return;
        }
        
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
            // Reload the user selector to remove
            // the user account option that was just deleted
            setRefreshUsers(prev => prev + 1);
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
            <h1>Delete User Account</h1>
            <form className="login" onSubmit={handleSubmit}>
                <UserSelector session={session} setError={setError} user={user} setUser={setUser} refreshTrigger={refreshUsers}/>
                <button type="submit" disabled={loading}>Delete Account</button>
                <button type="button" onClick={() => navigate("/")}>Back</button>
                {error ? (<div className='error'><p>{error}</p></div>) : null}
            </form>
        </div>
    )
}