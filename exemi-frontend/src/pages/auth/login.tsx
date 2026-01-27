import { useState } from 'react';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

type LoginForm = {
    username : string;
    password : string;
};
export default function Login(){
  
    const [error, setError] = useState<string | null>(null);
    const [form, setForm] = useState<LoginForm>({
        username:"",
        password:"",
    });
    
    function LoginError(){
      if (error){
        return (
          <div className='error'>
            <p>{error}</p>
          </div>
        )
      } else { return null }
    }

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
        // console.log(form);
        // console.log(backendURL);

        const body = new URLSearchParams();
        body.append("username", form.username);
        body.append("password", form.password);

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
              message = data.detail;
            } catch {
              // message += "Error message: " + await response.text();
            }
            
            setError(message);
            return;
        }

        const data = await response.json();
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', data.user);
        window.location.reload();

    }

    return (
        <div>
            <form onSubmit={handleSubmit}>
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
                <button type="submit">Log In</button>
                <LoginError/>
                {/* <input type="submit" value="Go"/> */}
            </form>
        </div>
    )
}
