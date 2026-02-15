import { useState } from 'react';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;


export default function Login({error, setError, setSession} : any){
        
    type LoginForm = {
        username : string;
        password : string;
    };

    const [loading, setLoading] = useState<boolean>(false);
    const [form, setForm] = useState<LoginForm>({
        username:"",
        password:"",
    });

    function handleChange(event : React.ChangeEvent<HTMLInputElement>){
        const {name, value} = event.target;
        setForm(prev => ({...prev,[name]:value}));
    }

    async function handleSubmit(event : React.SubmitEvent<HTMLFormElement>) {
        event.preventDefault();
        setLoading(true);
        // console.log(form);
        // console.log(backendURL);

        const body = new URLSearchParams();
        body.append("username", form.username);
        body.append("password", form.password);

        try{
            const response = await fetch(backendURL + "/login", {
                headers:{
                    "Content-Type":"application/x-www-form-urlencoded",
                    accept:"application/json"
                },
                method:"POST",
                body: body.toString(),
            });

            if (!response.ok){
                let message = "System error! Please contact Alexander Small."
                try {
                    const data = await response.json();
                    if (typeof data.detail === "string"){
                        message = data.detail;
                    }
                } catch {
                // message += "Error message: " + await response.text();
                }
                
                setError(message);
                setLoading(false);
                return;
            }

            if (response.ok){
                const data = await response.json();
                setSession({
                    token : data.access_token,
                    user_id : Number(data.user_id),
                    user : data.user
                });
                setLoading(false);
            }
        } catch (error) {
            // Doomsday scenario
            setError("System error! Exemi server is not running! Please contact Alexander Small.");
            console.log(error);
            setLoading(false);
        }
    }

    return (
        <div className='form'>
            <h1>Exemi</h1>
            <form className='login' onSubmit={handleSubmit}>
                <label>Enter your participant ID:
                    <input
                        name="username"
                        type="text"
                        value={form.username}
                        onChange={handleChange}
                    />
                </label>
                <label>Enter your password:
                    <input
                        name="password"
                        type="password"
                        value={form.password}
                        onChange={handleChange}
                    />
                </label>
                <button type="submit" disabled={loading}>Log In</button>
                {error ? (<div className='error'><p>{error}</p></div>) : null}
                {/* <LoginError/> */}
                {/* <input type="submit" value="Go"/> */}
            </form>
        </div>
    )
}
