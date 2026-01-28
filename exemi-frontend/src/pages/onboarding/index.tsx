import {useState, useEffect} from 'react';
import MagicForm from "./form";

interface Slide {
  photoURL : string,
  text : string
}

const slides : Slide[] = [
  {
    photoURL: "/assets/onboarding_slides/test.png",
    text:"TEST",
  },
  {
    photoURL: "/assets/onboarding_slides/test.png",
    text:"TEST2",
  },
  {
    photoURL: "",
    text: "TEST3"
  }
]

export default function Onboarding({session, setSession, setMagicValid} : any) {



  const [progress, setProgress] = useState<number>(0);

  async function logOut(){
    setSession({
        token:null,
        user_id:null
    });
  }

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
    <div>
      <div className="slide_progress">
        <div className='slide_progress_fill' style={{ width: progress_bar_width }}/>
      </div>

      <div className="slideshow">
        <p>{text}</p>
        {progress < slides.length - 1 ? (
            <img src={photoURL}/>
        ) : null}
      </div>


      
      {progress == slides.length - 1 ? (
        <MagicForm  session={session} setSession={setSession} setMagicValid={setMagicValid}/>
      ) : null}

      <button className="back" onClick={back}>{"<"} Back</button>
      {progress < slides.length - 1 ? (
        <button className="next" onClick={next}>Next {">"}</button>
      ) : null}

      {/* <Routes>
        <Route path="/" element={<MagicForm session={session} setSession={setSession} setMagicValid={setMagicValid}/>}/>
      </Routes> */}
    </div>
  )
}