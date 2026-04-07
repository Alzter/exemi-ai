import { useState, useCallback, useEffect, type ReactNode } from 'react'
import MagicForm from './MagicForm'
import { useNavigate } from 'react-router-dom'
import { useExemiCanvasPageContext } from '../../canvasExtensionContext'
import {
  EXEMI_IFRAME_AUTOMATION_SESSION_PENDING_KEY,
  instructureSubdomainFromCanvasHref,
  isExemiExtensionIframe,
} from '../../extensionAutomationMessages'
import { useExtensionCanvasTokenAutomation } from '../../useExtensionCanvasTokenAutomation'

interface Slide {
  photoURL : string,
  text : ReactNode
}

export default function Onboarding({session, setSession, setMagicValid, logOut} : any) {

  const [isSwinburneOnlineStudent, setIsSwinburneOnlineStudent] = useState<boolean|null>(null);

  const UNIVERSITY = session.user.university_name
  const ctx = useExemiCanvasPageContext()
  const canvasSubdomain = instructureSubdomainFromCanvasHref(ctx.href)
  const institutionForLinks =
    isSwinburneOnlineStudent ? "swinburneonline" : (typeof UNIVERSITY === 'string' && UNIVERSITY.trim()) || canvasSubdomain || '';
  const CANVAS_SETTINGS_LINK = institutionForLinks
    ? `https://${institutionForLinks}.instructure.com/profile/settings`
    : '';
  
  const isSwinburneStudent = UNIVERSITY.trim() == "swinburne" || canvasSubdomain == "swinburne";

  useEffect(() => {
    if (!isExemiExtensionIframe()) return
    try {
      sessionStorage.setItem(EXEMI_IFRAME_AUTOMATION_SESSION_PENDING_KEY, '1')
    } catch {
      // ignore
    }
    return () => {
      try {
        sessionStorage.removeItem(EXEMI_IFRAME_AUTOMATION_SESSION_PENDING_KEY)
      } catch {
        // ignore
      }
    }
  }, [])

  let slides : Slide[] = [
    {
      photoURL: "",
      text:(<p style={{fontSize:"1.5em"}}>
        To sign in with Canvas, we will need you to create an <strong>access token</strong> for your Canvas account.
        </p>),
    },
    {
      photoURL: "/assets/onboarding_slides/1.png",
      text: institutionForLinks ? (
        <p>
          Click{' '}
          <a href={CANVAS_SETTINGS_LINK} target="_blank" rel="noopener noreferrer">
            here
          </a>{' '}
          to open your Canvas account settings page.
        </p>
      ) : (
        <p>First, open your Canvas account settings page.</p>
      ),
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
      text: (
        <p style={{ fontSize: '1.5em' }}>Enter the copied text here:</p>
      ),
    }
  ]

  // IF the student is from Swinburne, ask them FIRST
  // if they are a Swinburne Online student BEFORE
  // proceeding.
  if (isSwinburneStudent && !isExemiExtensionIframe()){
    slides = [
    {
      photoURL: "",
      text:(
        <div>
          <p style={{fontSize:"1.5em"}}>
          Are you a Swinburne Online student?
          </p>
          <div className="input-row" style={{minHeight:"4em"}}>
            <button className="primary" onClick={() => {
              setIsSwinburneOnlineStudent(false);
              next();
            }}>No</button>
            <button className="primary" onClick={() => {
              setIsSwinburneOnlineStudent(true);
              next();
            }}>Yes</button>
          </div>
        </div>)
    }, ...slides];
  };

  const [progress, setProgress] = useState<number>(0)
  const [automationPrefill, setAutomationPrefill] = useState<{
    token: string
    universitySubdomain?: string
  } | null>(null)

  const navigate = useNavigate()
  const lastSlideIndex = slides.length - 1

  useExtensionCanvasTokenAutomation({
    onTokenResult: useCallback(
      (p) => {
        if (!p.ok) {
          navigate('/extension_incompatible')
          return
        }
        setProgress(lastSlideIndex)
        setAutomationPrefill({
          token: p.token,
          universitySubdomain: p.universitySubdomain,
        })
      },
      [navigate, lastSlideIndex],
    ),
  })

  async function back(){
    if (progress == 0){

      if (session.user.admin){
        navigate("/");
      } else {
        logOut();
        return;
      }
    }
    setProgress((prev) => prev - 1);
  }

  async function next(){
    if (progress == slides.length) { return; }
    setProgress((prev) => prev + 1);
  }
  
  const awaitingUserConfirmDialog : boolean = (isSwinburneStudent && !isExemiExtensionIframe() && isSwinburneOnlineStudent == null);
  const disableNextButton : boolean = (progress >= slides.length - 1) || awaitingUserConfirmDialog;

  useEffect(() => {console.log("Awaiting confirm dialog: " + awaitingUserConfirmDialog);});
  useEffect(() => {console.log("Disable Next Button: " + disableNextButton);});
  useEffect(() => {console.log("Is Online Student: " + isSwinburneOnlineStudent);});
  useEffect(() => {console.log(isSwinburneOnlineStudent == null);});

  const {photoURL, text} = slides[progress];

  const progress_bar_width : string = ((progress / (slides.length - 1)) * 100).toString() + "%";

  // useEffect(() => {console.log(progress_bar_width)});

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
          <MagicForm
            session={session}
            setSession={setSession}
            universityName={
              typeof UNIVERSITY === 'string' && UNIVERSITY.trim() ? UNIVERSITY : null
            }
            canvasSubdomainHint={canvasSubdomain}
            setMagicValid={setMagicValid}
            automationPrefill={automationPrefill}
            autoSubmitFromAutomation={automationPrefill != null}
          />
        ) : null}

        <button className="primary back" onClick={back}>{"<"} Back</button>
        {!disableNextButton ? (
          <button className="primary next" onClick={next}>Next {">"}</button>
        ) : null}
      </div>
      <div style={{minHeight:100}}></div>
    </div>
  )
}