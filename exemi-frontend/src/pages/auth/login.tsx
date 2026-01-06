import { useState } from 'react';
const baseURL = import.meta.env.VITE_BACKEND_API_URL;

type LoginForm = {
    token : string;
    // username : string;
};

export default function Login(){

    const [form, setForm] = useState<LoginForm>({
        token:""
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
            method:"POST",
            body:JSON.stringify(form)
        });

        if (!response.ok){
            // TODO: Replace with an Error state, find
            // a way to pass this up to the UI
            throw new Error("Login request failed");
        }

        const data = await response.json();
        console.log("Responee:", data);
    }

    return (
        <form onSubmit={handleSubmit}>
            <label>TOKEN:
                <input
                    name="token"
                    type="password"
                    value={form.token}
                    onChange={handleChange}
                />
            </label>
            <button type="submit">Go</button>
            {/* <input type="submit" value="Go"/> */}
        </form>
    )
}