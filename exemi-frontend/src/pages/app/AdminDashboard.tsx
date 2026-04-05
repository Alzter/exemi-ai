import { useNavigate } from 'react-router-dom';
import { MdAdd, MdSearch, MdDelete, MdEdit } from "react-icons/md";

export default function AdminDashboard({logOut} : any) {

  let navigate = useNavigate();

  return (
    <div className='form'>
      <h1>Admin Dashboard</h1>
      <button onClick={() => navigate("/chat")}>
        Start New Chat
      </button>

      <div style={{display:"flex", flexDirection:"column", width:"100%", gap:"1em", margin:"1em 0em"}}>
        <div className="double-column-buttons">
        <button onClick={() => navigate("/user_create")}>
          <MdAdd/>
          Add User
        </button>
        <button onClick={() => navigate("/user_delete")}>
          <MdDelete/>
          Delete User
        </button>
        {/* <button disabled>
          <MdSettings/>
          Edit User
        </button> */}
        </div>
        <button onClick={() => navigate("/chat_viewer")}>
          <MdSearch/>
          Read User Chats
        </button>
        <button onClick={() => navigate("/uni_aliases")}>
          <MdEdit/>
          Configure University Aliases
        </button>
      </div>

      {/* <br/> */}
      <button onClick={logOut}>Log Out</button>
    </div>
  )
}
