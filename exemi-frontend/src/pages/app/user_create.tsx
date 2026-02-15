import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
import {type User} from '../../models';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function UserCreate({session} : any){

    type UserCreateForm = {
        user_id : number;
        password : string;
    };
    
    // If user is not an admin, exit page
    let navigate = useNavigate();
    useEffect(() => {
        if (!session.user.admin){
            navigate("/");
        }
    }, []);

    useEffect(() => {
        autoIncrementUserID();
    }, []);

    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [form, setForm] = useState<UserCreateForm>({
        user_id:1,
        password:"",
    });
    const [highestLegalUserID, setHighestLegalUserID] = useState<number>(0);

    // Automatically increment the user ID value
    // to be an integer higher than the greatest
    // user ID, which is actually a username
    // cast to an integer since we don't use
    // real user IDs (PK) to identify users
    async function autoIncrementUserID() {
        const response = await fetch(backendURL + "/users", {
            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method:"GET"
        });

        if (response.ok){
            let data = await response.json();
            let userObjects = data as User[];

            // Get usernames that are valid integers
            const numericUsernames = userObjects
                .map(u => Number(u.username))
                .filter(n => Number.isInteger(n)
            );

            // Obtain the highest user ID number currently taken
            let lastUserID = 0;
            if (numericUsernames.length > 0){
                lastUserID = Math.max(...numericUsernames);
            }

            setHighestLegalUserID(lastUserID + 1);

            // Set the current user ID to the highest value + 1
            setForm(prev => ({...prev, user_id : lastUserID + 1}));
        };
    };

    function handleChange(event : React.ChangeEvent<HTMLInputElement>){
        const {name, value} = event.target;

        if (name === "user_id") {
            const num = Math.max(Number(value), highestLegalUserID);
            setForm(prev => ({ ...prev, user_id: num }));
            return;
        }

        setForm(prev => ({...prev,[name]:value}));
    }

    async function handleSubmit(event : React.SubmitEvent<HTMLFormElement>){
        event.preventDefault();
        setLoading(true);

        let body = {
            "username" : String(form.user_id),
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
            autoIncrementUserID();
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
                        name="user_id"
                        type="number"
                        value={form.user_id}
                        min={highestLegalUserID}
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
                <button type="button" onClick={() => navigate("/")}>Back</button>
                {error ? (<div className='error'><p>{error}</p></div>) : null}
            </form>
        </div>
    )
}