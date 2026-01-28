import {useState, useEffect} from 'react';
const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export default function MagicForm({session, setSession, setMagicValid} : any){
    type MagicForm = {
        university_name : string;
        magic : string;
    }

    const [isSubmitting, setSubmitting] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const [form, setForm] = useState<MagicForm>({
        university_name:"swinburne",
        magic:"",
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

    function handleChange(event : React.ChangeEvent<HTMLInputElement>){
        const {name, value} = event.target;
        setForm(prev => ({
            ...prev,
            [name]:value,
        }));
    }

    async function updateUserMagic(event : React.FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setSubmitting(true);

        console.log(form);
        console.log(backendURL);

        try{
            const response = await fetch(backendURL + "/users/self", {
                headers:{
                    "Authorization" : "Bearer " + session.token,
                    "Content-Type":"application/json",
                    accept:"application/json"
                },
                method:"PATCH",
                body: JSON.stringify(form),
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
                setSubmitting(false);
                return;
            }
            
            if (response.ok) {
                setSubmitting(false);
                // Triggers a recheck of the user's magic
                // which if successful will send them to
                // the dashboard page.
                setMagicValid(null);
            }

        } catch{
            setError("System error! Please contact Alexander Small.");
            setSubmitting(false);
        }

    }

    return (
        <form className='magic' onSubmit={updateUserMagic}>
            {/* NOTE: The university_name text entry form is INVISIBLE for now. */}
            <label style={{display:"none"}}>Enter your University name:
                <input
                    name="university_name"
                    type="text"
                    value={form.university_name}
                    onChange={handleChange}
                />
            </label>
            <label>
                <input
                    name="magic"
                    type="password"
                    value={form.magic}
                    onChange={handleChange}
                />
            </label>
            <button type="submit" disabled={isSubmitting || form.magic == ""}>Sign In</button>
            <LoginError/>
        </form>
    );
}