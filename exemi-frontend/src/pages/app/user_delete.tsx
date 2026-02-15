import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
import UserSelector from "../../components/admin/user_selector";

export default function UserDelete({session} : any){

    type UserSelected = {user : string};
    const [form, setForm] = useState<UserSelected>({user:""});

    // If user is not an admin, exit page
    let navigate = useNavigate();
    useEffect(() => {
        if (!session.user.admin){
            navigate("/");
        }
    }, [])

    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(false);

    function handleChange(event : React.ChangeEvent<HTMLInputElement>){
        const {name, value} = event.target;
        setForm(prev => ({...prev,[name]:value}));
    }

    async function handleSubmit(event : React.SubmitEvent<HTMLFormElement>){
        event.preventDefault();
        setLoading(true);
        console.log(form.user);
        setLoading(false);
    };

    return (
        <div className="form">
            <form className="login" onSubmit={handleSubmit}>
                <UserSelector session={session}/>
                <button type="submit" disabled={loading}>Delete User</button>
                {error ? (<div className='error'><p>{error}</p></div>) : null}
            </form>
        </div>
    )
}