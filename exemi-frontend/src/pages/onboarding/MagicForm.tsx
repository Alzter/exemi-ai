import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
const backendURL = import.meta.env.VITE_BACKEND_API_URL
import { type Session } from '../../models'
import { isExemiExtensionIframe } from '../../extensionAutomationMessages'

type AutomationPrefill = {
  token: string
  universitySubdomain?: string
}

type MagicFormParams = {
  session: Session
  setSession: any
  /** From session when set; when null, university field is shown. */
  universityName: string | null
  /** e.g. swinburne from *.instructure.com when extension has Canvas context */
  canvasSubdomainHint?: string | null
  setMagicValid: any
  automationPrefill?: AutomationPrefill | null
  autoSubmitFromAutomation?: boolean
}

export default function MagicForm({
  session,
  setSession: _setSession,
  universityName,
  canvasSubdomainHint,
  setMagicValid,
  automationPrefill,
  autoSubmitFromAutomation,
}: MagicFormParams) {
    type MagicForm = {
        university_name : string;
        magic : string;
    }

  const navigate = useNavigate()
  const formElRef = useRef<HTMLFormElement>(null)
  const didAutoSubmit = useRef(false)

  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const [form, setForm] = useState<MagicForm>({
    university_name:
      (universityName && universityName.trim()) ||
      (canvasSubdomainHint && canvasSubdomainHint.trim()) ||
      '',
    magic: '',
  })

  useEffect(() => {
    const fromSession = universityName?.trim() || ''
    const fromCanvas = canvasSubdomainHint?.trim() || ''
    if (fromSession || fromCanvas) {
      setForm((prev) => ({
        ...prev,
        university_name: fromSession || fromCanvas || prev.university_name,
      }))
    }
  }, [universityName, canvasSubdomainHint])

  useEffect(() => {
    if (!automationPrefill) return
    setForm((prev) => ({
      ...prev,
      magic: automationPrefill.token,
      university_name:
        universityName?.trim() ||
        automationPrefill.universitySubdomain ||
        canvasSubdomainHint?.trim() ||
        prev.university_name,
    }))
  }, [automationPrefill, universityName, canvasSubdomainHint])

  useEffect(() => {
    if (!autoSubmitFromAutomation || didAutoSubmit.current) return
    if (!automationPrefill) return
    if (!form.magic.trim()) return
    if (!universityName?.trim() && !form.university_name.trim()) return
    didAutoSubmit.current = true
    queueMicrotask(() => formElRef.current?.requestSubmit())
  }, [
    autoSubmitFromAutomation,
    automationPrefill,
    form.magic,
    form.university_name,
    universityName,
  ])

    function handleChange(event : React.ChangeEvent<HTMLInputElement>){
        const {name, value} = event.target;
        setForm(prev => ({...prev,[name]:value}));
    }

    async function updateUserMagic(event : React.FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setLoading(true);

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
                    if (typeof data.detail === "string"){
                        message = data.detail;
                    }
                } catch {
                // message += "Error message: " + await response.text();
                }
                setLoading(false);
                if (isExemiExtensionIframe()) {
                    navigate('/extension_incompatible')
                    return
                }
                setError(message);
                return;
            }
            
            if (response.ok) {
                setLoading(false);
                // Triggers a recheck of the user's magic
                // which if successful will send them to
                // the dashboard page.
                setMagicValid(null);
            }

        } catch{
            setLoading(false);
            if (isExemiExtensionIframe()) {
                navigate('/extension_incompatible')
                return
            }
            setError("System error! Please contact Alexander Small.");
        }

    }

    return (
        <form ref={formElRef} className='magic' onSubmit={updateUserMagic}>
            {/* NOTE: The university_name text entry form is INVISIBLE for now. */}
            <label style={universityName ? {display:"none"} : {}}>
                Enter your University name:
                <input
                    placeholder="swinburne"
                    name="university_name"
                    type="text"
                    value={form.university_name}
                    onChange={handleChange}
                />
            </label>
            <label>
                {universityName ? null : "Enter your token here:"}
                <input
                    name="magic"
                    type="password"
                    value={form.magic}
                    onChange={handleChange}
                />
            </label>
            <button type="submit" disabled={loading || form.magic == ""}>Sign In</button>
            {error ? (<div className='error'><p>{error}</p></div>) : null}
        </form>
    );
}