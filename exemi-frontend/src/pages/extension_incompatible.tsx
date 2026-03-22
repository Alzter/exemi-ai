import { MdErrorOutline } from 'react-icons/md'

export default function ExtensionIncompatible() {
  return (
    <div className="form">
      <p className="logo">exemi</p>
      <div className="error">
        <h1>
          <MdErrorOutline />
          <br />
          Extension not compatible
        </h1>
        <br />
        <p>
          Your university is not yet compatible with the Exemi browser extension. Your
          institution has disabled the manual creation of Canvas API access tokens, or
          Exemi could not complete token setup on this page.
        </p>
      </div>
    </div>
  )
}
