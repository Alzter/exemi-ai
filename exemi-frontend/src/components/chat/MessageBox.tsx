import Markdown from 'react-markdown';

type MessageProps = {
    content : string
    role : string
    userBackgroundColour? : string
}

export default function MessageBox({content, role, userBackgroundColour} : MessageProps){
    // Don't render system or tool messages
    if (role != "user" && role != "assistant") return null

    let stylingClass = role == "user" ? "user-message" : "message"
    const style = role === "user" && userBackgroundColour ? {backgroundColor: userBackgroundColour} : undefined;

    return(
        <div className={stylingClass} style={style}>
            <Markdown>
                {content}
            </Markdown>
        </div>
    )
}