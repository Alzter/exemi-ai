import { useEffect, useState } from "react"
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import {type User, type Session} from '../../models';

export type UserSelectorParams = {
  session : Session,
  setError : any,
  username : string,
  setUsername : any,
  refreshTrigger : any
}

export default function UserSelector({session, setError, username, setUsername, refreshTrigger} : UserSelectorParams){

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
    }, [refreshTrigger]);

    useEffect(() => {
        if (
            nonAdminUsers.length > 0 &&
            !nonAdminUsers.some(u => u.username === username)
        ) {
            setUsername(nonAdminUsers[0].username);
        }
    }, [users]);

    return (
        <select
            name="user"
            value={username ?? ""}
            onChange={(event) => setUsername(event.target.value)}
        >
            {nonAdminUsers.map(user => (
                <option value={user.username}>
                    {user.username}
                </option>
            ))}
        </select>
    )
}
