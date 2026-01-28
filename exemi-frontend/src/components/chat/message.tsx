type MessageProps = {
    content : string
    role : string
}

export default function Message({content} : MessageProps){
    return(
        <div className="message">
            <p>
                {content}
            </p>
        </div>
    )
}