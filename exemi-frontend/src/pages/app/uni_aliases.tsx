import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
import UniversitySelector from "../../components/admin/university_selector";
const backendURL = import.meta.env.VITE_BACKEND_API_URL;
import { MdAdd, MdDelete, MdSave } from "react-icons/md";

export default function ConfigureUniversities({session} : any){

    type UniversityAlias = {
        id : number,
        name : string,
        universityName : string
    };

    function AliasBox({alias} : {alias : UniversityAlias}){
        return(
            <div className="input-row">
                <p>{alias.name}</p>
                <button
                    onClick={() => {deleteAlias(alias)}}
                    disabled={loading}
                ><MdDelete/></button>
            </div>
        );
    };

    type AliasForm = {
        alias_name : string
    };

    const [universityName, setUniversityName] = useState<string>("");
    const [universityCanvasUrl, setUniversityCanvasUrl] = useState<string>("");
    const [savedUniversityCanvasUrl, setSavedUniversityCanvasUrl] = useState<string>("");
    const [universityAliases, setUniversityAliases] = useState<UniversityAlias[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [form, setForm] = useState<AliasForm>({
        alias_name : ""
    });

    function handleChange(event : React.ChangeEvent<HTMLInputElement>){
        const {name, value} = event.target;
        console.log(event.target.value);
        setForm(prev => ({...prev,[name]:value}));
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
            universityName : a.university_name
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
            "name" : form.alias_name
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
        setForm(prev => ({...prev, alias_name:""}));

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
            <div className="input-row">
                <label
                htmlFor="university_name">
                    University:
                </label>
                <UniversitySelector
                    universityName={universityName}
                    setUniversityName={setUniversityName}
                    session={session} setError={setError}
                    refreshTrigger={null}
                    disabled={loading}
                />
            </div>
            <form onSubmit={saveUniversityUrl} className="input-row">
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
            <h2>Manage Aliases</h2>
            <p>
                Each university name references a Canvas provider URL.
                However, you may want to add additional providers
                (aliases) in case the original one fails.
            </p>
            <div className="conditional">
                <form onSubmit={addAlias}>
                    <div className="input-row">
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
                        <button disabled={loading}><MdAdd/></button>
                    </div>
                </form>
                {universityAliases.map(
                    alias => <AliasBox alias={alias} key={alias.id}/>
                )}
            </div>
            <button className="back" onClick={() => navigate("/")}>{"<"} Back</button>
            {error ? (<div className='error'><p>{error}</p></div>) : null}
        </div>
    );
};