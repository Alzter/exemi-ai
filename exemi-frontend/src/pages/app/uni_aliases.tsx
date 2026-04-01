import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
import UniversitySelector from "../../components/admin/university_selector";
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import { MdAdd, MdDelete, MdSave } from "react-icons/md";

export default function ConfigureUniversities({session} : any){

    type UniversityAlias = {
        id : number,
        name : string,
        universityName : string,
        canvasUrl : string
    };

    function AliasBox({alias} : {alias : UniversityAlias}){
        const [aliasName, setAliasName] = useState<string>(alias.name);
        const [aliasCanvasUrl, setAliasCanvasUrl] = useState<string>(alias.canvasUrl);

        async function saveAlias() {
            setLoading(true);
            setError(null);

            const response = await fetch(backendURL + "/university_alias/" + alias.id, {
                headers:{
                    "Authorization" : "Bearer " + session.token,
                    "Content-Type":"application/json",
                    accept:"application/json"
                },
                method: "PATCH",
                body: JSON.stringify({
                    name: aliasName.trim(),
                    canvas_url: aliasCanvasUrl.trim().length > 0 ? aliasCanvasUrl.trim() : null
                })
            });

            if (!response.ok){
                let message = "Error updating university alias!";
                try{
                    let data = await response.json();
                    if (typeof data.detail === "string"){
                        message = data.detail;
                    }
                } finally {
                    setError(message);
                    setLoading(false);
                    return;
                };
            };

            await getAliases(universityName);
            setLoading(false);
        }

        return(
            <div className="input-row" style={{height:"3em"}}>
                <input
                    value={aliasName}
                    onChange={(event) => setAliasName(event.target.value)}
                    disabled={loading}
                    placeholder="Alias name"
                />
                <input
                    type="url"
                    placeholder="Alias URL (optional)"
                    value={aliasCanvasUrl}
                    onChange={(event) => setAliasCanvasUrl(event.target.value)}
                    disabled={loading}
                />
                <button
                    onClick={() => {saveAlias()}}
                    disabled={loading || (aliasName.trim() === alias.name && aliasCanvasUrl.trim() === alias.canvasUrl)}
                    title="Save alias changes"
                ><MdSave/></button>
                <button
                    onClick={() => {deleteAlias(alias)}}
                    disabled={loading}
                    title="Delete alias"
                ><MdDelete/></button>
            </div>
        );
    };

    type AliasForm = {
        alias_name : string,
        alias_canvas_url : string
    };

    type UniversityForm = {
        university_name : string,
        university_canvas_url : string
    }

    const [universityName, setUniversityName] = useState<string>("");
    const [universityCanvasUrl, setUniversityCanvasUrl] = useState<string>("");
    const [savedUniversityCanvasUrl, setSavedUniversityCanvasUrl] = useState<string>("");
    const [universityAliases, setUniversityAliases] = useState<UniversityAlias[]>([]);
    const [universitiesRefreshTrigger, setUniversitiesRefreshTrigger] = useState<number>(0);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [universityForm, setUniversityForm] = useState<UniversityForm>({
        university_name: "",
        university_canvas_url: ""
    });
    const [form, setForm] = useState<AliasForm>({
        alias_name : "",
        alias_canvas_url : ""
    });

    function handleChange(event : React.ChangeEvent<HTMLInputElement>){
        const {name, value} = event.target;
        setForm(prev => ({...prev,[name]:value}));
    };

    function handleUniversityFormChange(event : React.ChangeEvent<HTMLInputElement>){
        const {name, value} = event.target;
        setUniversityForm(prev => ({...prev,[name]:value}));
    };

    useEffect(() => {
        if (universityName){
            getAliases(universityName);
        };
    }, [universityName]);

    let navigate = useNavigate();

    function parseAliases(data : Array<any>){
        const aliases : UniversityAlias[] = data.map(a => ({
            id : a.id,
            name : a.name,
            universityName : a.university_name,
            canvasUrl : a.canvas_url ?? ""
        }));
        setUniversityAliases(aliases);
    };

    async function getAliases(university_name : string){
        const response = await fetch(backendURL + "/university/" + university_name, {
            headers: {"Authorization" : "Bearer " + session.token},
            method: "GET"
        });

        if (!response.ok){
            let message = "Error obtaining aliases for university: " + university_name + "!";
            try{
                let data = await response.json();
                if (typeof data.detail === "string"){
                    message = data.detail;
                }
            } finally {
                setError(message);
                setLoading(false);
                return;
            };
        };

        let data = await response.json();
        setUniversityCanvasUrl(data.canvas_url ?? "");
        setSavedUniversityCanvasUrl(data.canvas_url ?? "");
        parseAliases(data.aliases);
    };

    async function saveUniversityUrl(event : React.FormEvent<HTMLFormElement>){
        event.preventDefault();
        if (!universityName) return;

        setLoading(true);
        setError(null);

        const trimmedCanvasUrl = universityCanvasUrl.trim();
        const response = await fetch(backendURL + "/university/" + encodeURIComponent(universityName), {
            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method: "PATCH",
            body: JSON.stringify({
                canvas_url: trimmedCanvasUrl.length > 0 ? trimmedCanvasUrl : null
            })
        });

        if (!response.ok){
            let message = "Error updating university URL!";
            try{
                let data = await response.json();
                if (typeof data.detail === "string"){
                    message = data.detail;
                }
            } finally {
                setError(message);
                setLoading(false);
                return;
            };
        };

        const data = await response.json();
        const updatedCanvasUrl = data.canvas_url ?? "";
        setUniversityCanvasUrl(updatedCanvasUrl);
        setSavedUniversityCanvasUrl(updatedCanvasUrl);
        await getAliases(universityName);
        setLoading(false);
    };

    async function addAlias(event : React.SubmitEvent<HTMLFormElement>){
        event.preventDefault();

        setLoading(true);

        let body = {
            "university_name" : universityName,
            "name" : form.alias_name,
            "canvas_url" : form.alias_canvas_url.trim().length > 0 ? form.alias_canvas_url.trim() : null
        }

        const response = await fetch(backendURL + "/university_alias", {
            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method: "POST",
            body: JSON.stringify(body)
        });

        if (!response.ok){
            let message = "Error creating University alias!";
            try{
                let data = await response.json();
                if (typeof data.detail === "string"){
                    message = data.detail;
                }
            } finally {
                setError(message);
                setLoading(false);
                return;
            };
        };

        let data = await response.json();
        parseAliases(data.aliases);
        
        // Clear the alias name text field
        setForm(prev => ({...prev, alias_name:"", alias_canvas_url:""}));

        setLoading(false);
    };

    async function addUniversity(event : React.SubmitEvent<HTMLFormElement>){
        event.preventDefault();
        setLoading(true);
        setError(null);

        const name = universityForm.university_name.trim().toLowerCase();
        const canvasUrl = universityForm.university_canvas_url.trim();
        const body = {
            name,
            canvas_url: canvasUrl.length > 0 ? canvasUrl : null
        };

        const response = await fetch(backendURL + "/university", {
            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method: "POST",
            body: JSON.stringify(body)
        });

        if (!response.ok){
            let message = "Error creating university!";
            try{
                let data = await response.json();
                if (typeof data.detail === "string"){
                    message = data.detail;
                }
            } finally {
                setError(message);
                setLoading(false);
                return;
            };
        };

        setUniversityForm({university_name:"", university_canvas_url:""});
        setUniversitiesRefreshTrigger(prev => prev + 1);
        setUniversityName(name);
        await getAliases(name);
        setLoading(false);
    };

    async function deleteUniversity(){
        if (!universityName) return;
        setLoading(true);
        setError(null);

        if (!window.confirm("Are you sure you want to delete this university? This is IRREVERSIBLE!")){
            setLoading(false);
            return;
        };

        const response = await fetch(backendURL + "/university/" + encodeURIComponent(universityName), {
            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method: "DELETE"
        });

        if (!response.ok){
            let message = "Error deleting university!";
            try{
                let data = await response.json();
                if (typeof data.detail === "string"){
                    message = data.detail;
                }
            } finally {
                setError(message);
                setLoading(false);
                return;
            };
        };

        setUniversityAliases([]);
        setUniversityCanvasUrl("");
        setSavedUniversityCanvasUrl("");
        setUniversityName("");
        setUniversitiesRefreshTrigger(prev => prev + 1);
        setLoading(false);
    };

    async function deleteAlias(alias : UniversityAlias){
        setLoading(true);
        const response = await fetch(backendURL + "/university_alias/" + alias.id, {
            headers:{
                "Authorization" : "Bearer " + session.token,
                "Content-Type":"application/json",
                accept:"application/json"
            },
            method: "DELETE"
        });

        if (!response.ok){
            setLoading(false);
            setError("Error deleting university alias!")
            return;
        };
        
        getAliases(universityName);
        setLoading(false);
    };

    return (
        <div className="form wide">
            <h1>Configure Universities</h1>
            <div className="conditional" style={{marginBottom:"0", height:"auto", overflow:"visible"}}>
            <h2 style={{marginBottom:"0.4em"}}>New University</h2>
            <form onSubmit={addUniversity} style={{width:"100%"}}>
                <div className="input-row" style={{height:"3em"}}>
                    <label htmlFor="university_name_create">New:</label>
                    <input
                        id="university_name_create"
                        name="university_name"
                        placeholder="University name"
                        value={universityForm.university_name}
                        onChange={handleUniversityFormChange}
                        disabled={loading}
                    />
                    <input
                        id="university_canvas_url_create"
                        name="university_canvas_url"
                        type="url"
                        placeholder="Canvas URL (optional)"
                        value={universityForm.university_canvas_url}
                        onChange={handleUniversityFormChange}
                        disabled={loading}
                    />
                    <button disabled={loading || universityForm.university_name.trim().length === 0}>
                        <MdAdd/>
                        Create
                    </button>
                </div>
            </form>
            </div>
            <div className="conditional" style={{marginBottom:"0", height:"auto", overflow:"visible"}}>
            <h2 style={{marginBottom:"0.4em"}}>Manage University</h2>
            <div className="input-row" style={{height:"3em"}}>
                <label
                htmlFor="university_name">
                    University:
                </label>
                <UniversitySelector
                    universityName={universityName}
                    setUniversityName={setUniversityName}
                    session={session} setError={setError}
                    refreshTrigger={universitiesRefreshTrigger}
                    disabled={loading}
                />
            </div>
            <form onSubmit={saveUniversityUrl} className="input-row" style={{height:"3em"}}>
                    <label
                        htmlFor="canvas_url"
                    >Canvas URL:</label>
                    <input
                        id="canvas_url"
                        name="canvas_url"
                        type="url"
                        placeholder="https://example.instructure.com"
                        value={universityCanvasUrl}
                        onChange={(event) => setUniversityCanvasUrl(event.target.value)}
                        disabled={loading || !universityName}
                    />
                    <button
                        type="submit"
                        disabled={loading || !universityName || universityCanvasUrl.trim() === savedUniversityCanvasUrl.trim()}
                    >
                        <MdSave/>
                        Save URL
                    </button>
            </form>
            <div className="input-row" style={{height:"3em"}}>
                <label>Delete:</label>
                <button
                    onClick={deleteUniversity}
                    disabled={loading || !universityName}
                    style={{maxWidth:"14em"}}
                >
                    <MdDelete/>
                    Delete Selected
                </button>
            </div>
            </div>
            <div className="conditional" style={{marginBottom:"0", height:"auto", overflow:"visible"}}>
            <h2 style={{marginBottom:"0.4em"}}>Manage Aliases</h2>
            <p>
                Each university name references a Canvas provider URL.
                However, you may want to add additional providers
                (aliases) in case the original one fails.
            </p>
            <div className="conditional">
                <form onSubmit={addAlias} style={{width:"100%"}}>
                    <div className="input-row" style={{height:"3em"}}>
                        <label
                            htmlFor="alias_name"
                        >Alias:</label>
                        <input
                            id="alias_name"
                            name="alias_name"
                            onChange={handleChange}
                            value={form.alias_name}
                            // disabled={loading}
                        />
                        <input
                            id="alias_canvas_url"
                            name="alias_canvas_url"
                            type="url"
                            placeholder="Alias URL (optional)"
                            onChange={handleChange}
                            value={form.alias_canvas_url}
                        />
                        <button disabled={loading || form.alias_name.trim().length === 0}>
                            <MdAdd/>
                            Add
                        </button>
                    </div>
                </form>
                {universityAliases.map(
                    alias => <AliasBox alias={alias} key={alias.id}/>
                )}
            </div>
            </div>
            <button className="back" onClick={() => navigate("/")}>{"<"} Back</button>
            {error ? (<div className='error'><p>{error}</p></div>) : null}
        </div>
    );
};