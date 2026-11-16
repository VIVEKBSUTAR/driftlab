import type { RunRecord, RunDetail } from '../types/api';
const API_BASE = import.meta.env.VITE_API_URL || '/api';
export class ApiError extends Error {
  constructor(message:string, public status:number, public requestId?:string) { super(message); }
}
export async function request<T>(path:string, options:RequestInit={}):Promise<T> {
  let response:Response;
  try {
    response=await fetch(`${API_BASE}${path}`,{...options,credentials:'same-origin',headers:{'Content-Type':'application/json',...options.headers},signal:options.signal||AbortSignal.timeout(180000)});
  } catch(error) {
    if(error instanceof DOMException && (error.name==='TimeoutError'||error.name==='AbortError')) throw new ApiError('The request timed out. Check the run status before submitting again.',0);
    throw new ApiError('Cannot reach DriftLab. Check that the service is running and your connection is available.',0);
  }
  if(!response.ok){
    let message=`Request failed (${response.status})`;
    try{const body=await response.json();message=typeof body.detail==='string'?body.detail:JSON.stringify(body.detail||body);}catch{/* Preserve HTTP status for non-JSON failures. */}
    if(response.status===401)window.dispatchEvent(new Event('driftlab-auth-required'));
    throw new ApiError(message,response.status,response.headers.get('x-request-id')||undefined);
  }
  return response.json();
}
export const fetchRuns=()=>request<RunRecord[]>('/runs');
export const fetchRunDetail=(id:string)=>request<RunDetail>(`/runs/${encodeURIComponent(id)}?limit=1000`);
export const reportUrl=(id:string)=>`${API_BASE}/comparisons/${encodeURIComponent(id)}/report`;
export async function waitForRun(id:string, signal?:AbortSignal):Promise<RunRecord> {
  while(!signal?.aborted){
    const run=await request<RunRecord>(`/runs/${encodeURIComponent(id)}`,{signal});
    if(run.status==='completed')return run;
    if(['failed','cancelled'].includes(run.status))throw new Error(run.error||`Run ${run.status}`);
    await new Promise<void>((resolve,reject)=>{const cancel=()=>{clearTimeout(timer);reject(new DOMException('Cancelled','AbortError'));};const timer=setTimeout(()=>{signal?.removeEventListener('abort',cancel);resolve();},1000);signal?.addEventListener('abort',cancel,{once:true});});
  }
  throw new DOMException('Cancelled','AbortError');
}
