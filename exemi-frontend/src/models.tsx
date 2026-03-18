export type User = {
    username : string,
    university_name : string,
    active_university_name : string | null,
    id : number,
    admin : boolean,
    disabled : boolean,
    password_hash : string,
    magic_hash : string
}

export type Session = {
    token : string | null;
    user_id : number | null;
    user : User | null;
    last_sync_date : Date | null;
}