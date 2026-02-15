import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
import UserSelector from "../../components/admin/user_selector";

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

    // function handleChange(event : React.ChangeEvent<HTMLInputElement>){
    //     setUser(event.target.value);
    //     console.log(event.target.value);
    // }

    async function handleSubmit(event : React.SubmitEvent<HTMLFormElement>){
        event.preventDefault();
        setLoading(true);
        console.log(user);
        setLoading(false);
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