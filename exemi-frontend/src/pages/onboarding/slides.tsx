import {useState, useEffect} from 'react';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function Slides({setSession} : any){

    type MagicForm = {
        university : string;
        magic : string;
    }
    const [error, setError] = useState<string | null>(null);

    const [form, setForm] = useState<MagicForm>({
        university:"swinburne",
        magic:"",
    });

    function handleChange(event : React.ChangeEvent<HTMLInputElement>){
        const {name, value} = event.target;
        setForm(prev => ({
            ...prev,
            [name]:value,
        }));
    }

    async function updateUserMagic(event : React.FormEvent<HTMLFormElement>) {
        event.preventDefault();

        console.log(form);
        console.log(backendURL);

        const body = new URLSearchParams();
        body.append("magic", form.magic);
        body.append("university", form.university);

        const response = await fetch(backendURL + "/users/self", {
            headers:{
                "Content-Type":"application/x-www-form-urlencoded",
                accept:"application/json"
            },
            method:"PATCH",
            body: body.toString(),
        });
    }

    async function back(){
        setSession({
            token:null,
            user_id:null
        });
    }

    return (
        <div>
            <form onSubmit={updateUserMagic}>
                {/* NOTE: The university text entry form is INVISIBLE for now. */}
                <label style={{display:"none"}}>Enter your University name:
                    <input
                        name="university"
                        type="text"
                        value={form.university}
                        onChange={handleChange}
                    />
                </label>
                <label>Enter the text here:
                    <input
                        name="magic"
                        type="password"
                        value={form.magic}
                        onChange={handleChange}
                    />
                </label>
                <button type="submit">Go</button>
            </form>
            <button onClick={back}>BACK</button>
        </div>
    );
}