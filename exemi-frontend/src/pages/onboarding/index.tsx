import {useState, useEffect, type ReactNode} from 'react';
import MagicForm from "./form";

interface Slide {
  photoURL : string,
  text : ReactNode
}

// Hard-coded garbage
const UNIVERSITY = "swinburne";

const CANVAS_SETTINGS_LINK = "https://" + UNIVERSITY + ".instructure.com/profile/settings"

const slides : Slide[] = [
  {
    photoURL: "",
    text:(<p style={{fontSize:"1.5em"}}>
      To sign in with Canvas, we will need you to create an <strong>access token</strong> for your Canvas account.
      </p>),
  },
  {
    photoURL: "/assets/onboarding_slides/1.png",
    text:(<p>
      Click <a href={CANVAS_SETTINGS_LINK} target="_blank" rel="noopener noreferrer">here</a> to open your Canvas account settings page.
    </p>),
  },
  {
    photoURL: "/assets/onboarding_slides/2.png",
    text:(
      <p>Scroll down to “Approved integrations” and click “New access token”.</p>
    )
  },
  {
    photoURL: "/assets/onboarding_slides/3.png",
    text:(
      <p>Input these values into the fields, then click "Generate token".</p>
    )
  },
  {
    photoURL: "/assets/onboarding_slides/4.png",
    text:(
      <p>Copy the token text on the page.</p>
    )
  },
  {
    photoURL: "",
    text:(
      <p style={{fontSize:"1.5em"}}>Enter the copied text here:</p>
    )
  }
]

export default function Onboarding({session, setSession, setMagicValid, logOut} : any) {

  const [progress, setProgress] = useState<number>(0);

  async function back(){
    if (progress == 0){ logOut(); return; }
    setProgress((prev) => prev - 1);
  }

  async function next(){
    if (progress == slides.length) { return; }
    setProgress((prev) => prev + 1);
  }
  
  const {photoURL, text} = slides[progress];

  const progress_bar_width : string = ((progress / (slides.length - 1)) * 100).toString() + "%";

  useEffect(() => {console.log(progress_bar_width)});

  return (
    <div className="slideshow">
      <div className="slideshow-header">
        <h1>Sign in with Canvas</h1>
        <div className="slide-progress">
          <div className='slide-progress-fill' style={{ width: progress_bar_width }}/>
        </div>
      </div>

      <div className="slideshow-content">

        {text}
        {photoURL != "" ? (
            <img src={photoURL}/>
        ) : null}


        
        {progress == slides.length - 1 ? (
          <MagicForm  session={session} setSession={setSession} setMagicValid={setMagicValid}/>
        ) : null}

        <button className="back" onClick={back}>{"<"} Back</button>
        {progress < slides.length - 1 ? (
          <button className="next" onClick={next}>Next {">"}</button>
        ) : null}
      </div>
      <div style={{minHeight:100}}></div>
    </div>
  )
}