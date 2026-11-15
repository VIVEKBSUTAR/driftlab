import type { RunRecord, RunDetail, CompareRequest, CompareResponse, TriggerRunRequest } from '../types/api';
const API_BASE = import.meta.env.VITE_API_URL || '/api';
export async function request<T>(path:string, options:RequestInit={}):Promise<T> {
 const res=await fetch(`${API_BASE}${path}`,{...options,headers:{'Content-Type':'application/json',...options.headers},signal:options.signal||AbortSignal.timeout(180000)});
 if(!res.ok){let message=`Request failed (${res.status})`;try{const body=await res.json();message=typeof body.detail==='string'?body.detail:JSON.stringify(body.detail||body);}catch{}throw Error(message);}return res.json();
}
export async function checkApiHealth(){try{return (await request<{status:string}>('/',{signal:AbortSignal.timeout(3000)})).status==='healthy';}catch{return false;}}
export const fetchRuns=()=>request<RunRecord[]>('/runs');
export const fetchRunDetail=(id:string)=>request<RunDetail>(`/runs/${encodeURIComponent(id)}`);
export const compareRuns=(payload:CompareRequest)=>request<CompareResponse>('/compare',{method:'POST',body:JSON.stringify(payload)});
export const triggerRun=(payload:TriggerRunRequest)=>request<{status:string;run_id:string}>('/runs',{method:'POST',body:JSON.stringify(payload)});
export const reportUrl=(id:string)=>`${API_BASE}/comparisons/${encodeURIComponent(id)}/report`;
export const fetchComparisons=()=>request<CompareResponse[]>('/comparisons');
