export type UserUnit = {
    readable_name : string,
    nickname : string | null,
    colour : string | null,
    unit_id : number,
    user_id : number
}

export type User = {
    username : string,
    university_name : string,
    active_university_name : string | null,
    id : number,
    admin : boolean,
    disabled : boolean,
    password_hash : string,
    magic_hash : string,
    units : UserUnit[]
}

export type Session = {
    token : string | null;
    user_id : number | null;
    user : User | null;
    last_user_sync_date : Date | null;
    last_canvas_sync_date : Date | null;
}