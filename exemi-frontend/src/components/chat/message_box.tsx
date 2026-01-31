type MessageProps = {
    content : string
    role : string
}

export default function MessageBox({content, role} : MessageProps){
    let stylingClass = role == "user" ? "user-message" : "message"
    
    return(
        <div className={stylingClass}>
            <p>
                {content}
            </p>
        </div>
    )
}