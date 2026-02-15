import { useEffect } from "react"
import { useNavigate } from "react-router"

export default function UserCreate({session} : any){

    // If user is not an admin, exit page
    let navigate = useNavigate();
    useEffect(() => {
        if (!session.user.admin){
            navigate("/");
        }
    }, [])

    return (
        <div>
            <p>Not implemented</p>
        </div>
    )
}