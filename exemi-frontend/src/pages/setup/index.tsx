import { useState } from 'react';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;


export default function CreateAdminAccount({error, setError} : any){
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

        try{
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
                let data = await response.json();
                if (typeof data.detail === "string"){
                    message = data.detail;
                }
                setLoading(false);
                setError(message);
                return;
            };

        } catch {
            setLoading(false);
            setError("Error creating administrator account.");
            return;
        }

        // If the response was successful,
        // assume the admin account was created
        // and reload the page.
        window.location.reload();
    }

    return (
        <div className='form wide' style={{gap:0, paddingBottom:0}}>
            <h1>Create Administrator Account</h1>

            <div className="error">
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

            <form className='login' style={{marginTop:"2em"}} onSubmit={handleSubmit}>
                <div className="input-row">
                    <label htmlFor='username'>
                        Username:
                    </label>
                    <input
                        name="username"
                        id="username"
                        type="text"
                        value={form.username}
                        onChange={handleChange}
                    />
                </div>
                <div className="input-row">
                    <label htmlFor='password'>
                        Password:
                    </label>
                    <input
                        name="password"
                        id="password"
                        type="password"
                        value={form.password}
                        onChange={handleChange}
                    />
                </div>
                <div className="input-row">
                    <label htmlFor='confirmPassword'>
                        Confirm Pass:
                    </label>
                    <input
                        name="confirmPassword"
                        id="confirmPassword"
                        type="password"
                        value={form.confirmPassword}
                        onChange={handleChange}
                    />
                </div>
                <button className="primary" type="submit" disabled={loading}>Create Account</button>
                {error ? (<div className='error'><p>{error}</p></div>) : null}
            </form>
        </div>
    )
}