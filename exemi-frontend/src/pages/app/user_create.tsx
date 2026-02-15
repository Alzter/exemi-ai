import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function UserCreate({session} : any){

    type LoginForm = {
        username : number;
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
        username:1,
        password:"",
    });

    function handleChange(event : React.ChangeEvent<HTMLInputElement>){
        const {name, value} = event.target;
        setForm(prev => ({...prev,[name]:value}));
    }

    async function handleSubmit(event : React.SubmitEvent<HTMLFormElement>){
        event.preventDefault();
        setLoading(true);

        let body = {
            "username" : String(form.username),
            "password" : form.password
        }

        const response = await fetch(backendURL + "/users", {

            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method:"POST",
            body: JSON.stringify(body)
        });

        if (response.ok){
            setError("User successfully created!");
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
    }

    return (
        <div className="form">
            <h1>Create User Account</h1>
            <form className="login" onSubmit={handleSubmit}>
                <label>Enter participant ID:
                    <input
                        name="username"
                        type="number"
                        value={form.username}
                        onChange={handleChange}
                    />
                </label>
                <label>Enter password:
                    <input
                        name="password"
                        type="password"
                        value={form.password}
                        onChange={handleChange}
                    />
                </label>
                <button type="submit" disabled={loading}>Create Account</button>
                <button onClick={() => navigate("/")}>Back</button>
                {error ? (<div className='error'><p>{error}</p></div>) : null}
            </form>
        </div>
    )
}