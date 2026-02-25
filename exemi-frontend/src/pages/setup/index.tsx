import { use, useState } from 'react';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;


export default function CreateAdminAccount({error, setError, setSession} : any){
    type UserCreateForm = {
        username : string;
        password : string;
        confirmPassword : string;
    };

    const [loading, setLoading] = useState<boolean>(false);
    const [form, setForm] = useState<UserCreateForm>({
        username:"",
        password:"",
        confirmPassword:"",
    });

    function handleChange(event : React.ChangeEvent<HTMLInputElement>){
        const {name, value} = event.target;
        setForm(prev => ({...prev,[name]:value}));
    }

    async function handleSubmit(event : React.SubmitEvent<HTMLFormElement>) {
        event.preventDefault();

        if (form.username == "" || form.password == ""){
            setError("Username or Password is empty!");
            return;
        }
        if (form.password != form.confirmPassword){
            setError("Passwords do not match!");
            return;
        }

        setLoading(true);

        let body = {"username":form.username, "password":form.password};

        const response = await fetch(backendURL + "/users/admin", {
            headers:{
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method:"POST",
            body: JSON.stringify(body),
        });

        if (!response.ok){
            let message = "Error creating administrator account.";
            try{
                let data = await response.json();
                if (typeof data.detail === "string"){
                    message = data.detail;
                }
            } finally {
                setError(message);
            };
            return;
        };

        // If the response was successful,
        // assume the admin account was created
        // and reload the page.
        window.location.reload();
    }

    return (
        <div className='form' style={{gap:0, paddingBottom:0}}>
            <div className="error" style={{padding:"1em"}}>
                <p>
                    <strong>No administrator
                    accounts currently exist</strong> in the database!
                    Please create one now.
                    If you are a participant
                    and are seeing this message,
                    something has gone terribly wrong.
                    Please email Alexander Small!
                </p>
            </div>
            <h1>Create Administrator Account</h1>

            <form className='login' onSubmit={handleSubmit}>
                <label>Username:
                    <input
                        name="username"
                        type="text"
                        value={form.username}
                        onChange={handleChange}
                    />
                </label>
                <label>Password:
                    <input
                        name="password"
                        type="password"
                        value={form.password}
                        onChange={handleChange}
                    />
                </label>
                <label>Confirm Password:
                    <input
                        name="confirmPassword"
                        type="password"
                        placeholder=""
                        value={form.confirmPassword}
                        onChange={handleChange}
                    />
                </label>
                <button type="submit" disabled={loading}>Log In</button>
                {error ? (<div className='error'><p>{error}</p></div>) : null}
            </form>
        </div>
    )
}