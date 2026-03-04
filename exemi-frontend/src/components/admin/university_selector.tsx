import { useEffect, useState } from "react"
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import {type Session} from '../../models';

export type UniversitySelectorParams = {
  session : Session,
  setError : any,
  universityName : string,
  setUniversityName : any,
  refreshTrigger : any
}

export default function UniversitySelector({
    session,
    setError,
    universityName,
    setUniversityName,
    refreshTrigger
} : UniversitySelectorParams){

    const [universityNames, setUniversityNames] = useState<string[]>([]);

    async function getUniversities() {
        const response = await fetch(backendURL + "/university", {
            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method:"GET"
        });

        if (response.ok){
            let data = await response.json();
            // console.log(data);
            let universities = data.map(d => d.name);
            // let userObjects = data as User[];
            setUniversityNames(universities);
            return;
        } else {
            let message = "System error!";
            try{
                let data = await response.json();
                if (typeof data.detail === "string"){
                    message = data.detail;
                }
                setError(message);
                return;
            } catch {
                setError(message);
            }
        }
    }

    useEffect(() => {
        getUniversities();
    }, [refreshTrigger]);

    useEffect(() => {
        setUniversityName(universityNames[0]);
    }, [universityNames]);

    return (
        <select
            name="university_name"
            value={universityName ?? ""}
            onChange={(event) => setUniversityName(event.target.value)}
        >
            {universityNames.map(university => (
                <option key={university} value={university}>
                    {university}
                </option>
            ))}
        </select>
    )
}
