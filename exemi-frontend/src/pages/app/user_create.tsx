import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function UserCreate({session} : any){

    type LoginForm = {
        username : string;
        password : string;
    };
    
    // If user is not an admin, exit page
    let navigate = useNavigate();
    useEffect(() => {
        if (!session.user.admin){
            navigate("/");
        }
    }, []);

    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [form, setForm] = useState<LoginForm>({
        username:"",
        password:"",
    });

    function handleChange(event : React.ChangeEvent<HTMLInputElement>){
        const {name, value} = event.target;
        setForm(prev => ({...prev,[name]:value}));
    }

    async function handleSubmit(event : React.SubmitEvent<HTMLFormElement>){
        event.preventDefault();
        setLoading(true);

        const response = await fetch(backendURL + "/")
    }

    return (
        <div className="form">
            <h1>Create new User</h1>
            <form className="create-user" onSubmit={handleSubmit}>
                <label>Enter participant ID:
                    <input
                        name="username"
                        type="text"
                        value={form.username}
                        onChange={handleChange}
                    />
                </label>
            </form>
        </div>
    )
}