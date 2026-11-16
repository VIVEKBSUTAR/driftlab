import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { FlaskConical, LoaderCircle, LockKeyhole } from 'lucide-react';
import { request } from './services/api';
const AccessContext=createContext({required:false,logout:async()=>{}});
export const useWorkspaceAccess=()=>useContext(AccessContext);
export function AccessGate({children}:{children:ReactNode}){
  const [session,setSession]=useState<{authenticated:boolean;required:boolean}|null>(null);
  const [key,setKey]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const check=useCallback(async()=>{try{setSession(await request('/auth/session'));setError('');}catch(e){setError(e instanceof Error?e.message:String(e));}},[]);
  useEffect(()=>{void check();const expired=()=>setSession({authenticated:false,required:true});window.addEventListener('driftlab-auth-required',expired);return()=>window.removeEventListener('driftlab-auth-required',expired);},[check]);
  async function login(e:FormEvent){e.preventDefault();setBusy(true);setError('');try{await request('/auth/login',{method:'POST',body:JSON.stringify({token:key})});setKey('');await check();}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}}
  const logout=async()=>{await request('/auth/logout',{method:'POST',body:'{}'});setSession({authenticated:false,required:true});};
  if(session?.authenticated)return <AccessContext.Provider value={{required:session.required,logout}}>{children}</AccessContext.Provider>;
  return <main className="access-gate"><section className="panel form-panel"><FlaskConical size={32}/><div className="eyebrow">DRIFTLAB WORKSPACE</div><h1>{session?'Workspace access':'Connecting to DriftLab'}</h1><p className="muted">{session?'Enter the workspace access key supplied by your administrator.':'The application must connect to its API before loading evaluation data.'}</p>{error&&<p className="error-text" role="alert">{error}</p>}{session?<form onSubmit={login}><div className="field"><label htmlFor="access-key">Workspace access key</label><input id="access-key" type="password" autoComplete="current-password" value={key} onChange={e=>setKey(e.target.value)} required maxLength={256}/></div><button className="btn primary wide" disabled={busy}>{busy?<LoaderCircle className="spin" size={16}/>:<LockKeyhole size={16}/>}Connect securely</button></form>:<button className="btn secondary" onClick={()=>void check()}>Retry connection</button>}<small className="muted">Access keys are sent to this workspace over your connection and are not stored in browser storage. Server sessions use an HttpOnly cookie.</small></section></main>;
}
