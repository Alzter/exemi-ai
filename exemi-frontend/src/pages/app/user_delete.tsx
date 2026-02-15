import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
import UserSelector from "../../components/admin/user_selector";

export default function UserDelete({session} : any){

    // If user is not an admin, exit page
    let navigate = useNavigate();
    useEffect(() => {
        if (!session.user.admin){
            navigate("/");
        }
    }, [])

    const [error, setError] = useState<string | null>(null);

    return (
        <div className="form">
            <UserSelector session={session}/>
            {error ? (<div className='error'><p>{error}</p></div>) : null}
        </div>
    )
}