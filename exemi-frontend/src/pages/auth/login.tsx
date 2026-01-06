import { useState } from 'react';
const baseURL = import.meta.env.VITE_BACKEND_API_URL;

type LoginForm = {
    provider : string;
    token : string;
};

export default function Login(){

    const [form, setForm] = useState<LoginForm>({
        provider:"swinburne",
        token:"",
    });

    // const [token, setToken] = useState("");

    function handleChange(event : React.ChangeEvent<HTMLInputElement>){
        
        // Determine the name and value of the changed form fields
        const {name, value} = event.target;

        // Functional State Setter
        // Update the form state to a copy of the existing state
        // with the changed property overwritten.
        setForm(prev => ({
            ...prev,
            [name]:value,
        }));
    }

    async function handleSubmit(event : React.FormEvent<HTMLFormElement>) {
        event.preventDefault();
        console.log(form);

        console.log(baseURL);

        const response = await fetch(baseURL + "/login", {
            headers:{
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method:"POST",
            body:JSON.stringify(form),
        });

        if (!response.ok){
            // TODO: Replace with an Error state, find
            // a way to pass this up to the UI
            throw new Error("Login request failed");
        }

        const data = await response.json();
        console.log("Response:", data);
    }

    return (
        <div>
            <form onSubmit={handleSubmit}>
                <label>Enter your University name:
                    <input
                        name="provider"
                        type="text"
                        value={form.provider}
                        onChange={handleChange}
                    />
                </label>
                <label>Enter your Canvas token:
                    <input
                        name="token"
                        type="password"
                        value={form.token}
                        onChange={handleChange}
                    />
                </label>
                <button type="submit">Log In</button>
                {/* <input type="submit" value="Go"/> */}
            </form>
        </div>
    )
}