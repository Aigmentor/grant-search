import React from 'react'
export default function Login() : React.ReactElement {

    const state=`rio_state_${window.crypto.randomUUID()}`
    return <button className="bg-gray-800 hover:bg-grey-500 text-white font-bold py-2 px-4 rounded"> 
        <a style={{textDecoration: "none"}} href={`/app/login/${state}`}>
        <img 
            alt="Google Logo"
            src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Google_%22G%22_logo.svg/24px-Google_%22G%22_logo.svg.png" width={24} height={24}/>Click Here to Login</a> 
           </button>
}