import { useEffect, useState } from "react"
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import {type User} from '../../models';

export default function UserSelector({session, setError, setUser} : any){

    const [users, setUsers] = useState<User[]>([]);
    const nonAdminUsers = users.filter(user => !user.admin);

    async function getUsers() {
        const response = await fetch(backendURL + "/users", {
            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method:"GET"
        });

        if (response.ok){
            let data = await response.json();
            let userObjects = data as User[];
            setUsers(userObjects);
            setUser(userObjects[0].username);
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
        getUsers();
    }, []);

    return (
        <select name="user" id="user">
            {nonAdminUsers.map(user => (
                <option value={user.username}>
                    {user.username}
                </option>
            ))}
        </select>
    )
}