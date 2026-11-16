import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, request, waitForRun } from './api';
const response=(body:unknown,status=200)=>({ok:status<400,status,headers:new Headers({'x-request-id':'request-123'}),json:async()=>body});
afterEach(()=>{vi.unstubAllGlobals();vi.useRealTimers();});
describe('real API transport',()=>{
 it('propagates backend failures and request IDs without invented success',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({detail:'Inference unavailable'},503)));await expect(request('/runs',{method:'POST',body:'{}'})).rejects.toMatchObject({status:503,message:'Inference unavailable',requestId:'request-123'});});
 it('surfaces a network outage',async()=>{vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));await expect(request('/runs')).rejects.toBeInstanceOf(ApiError);});
 it('requests reauthentication when the session expires',async()=>{const listener=vi.fn();window.addEventListener('driftlab-auth-required',listener);vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({detail:'Authentication required'},401)));await expect(request('/runs')).rejects.toMatchObject({status:401});expect(listener).toHaveBeenCalledOnce();window.removeEventListener('driftlab-auth-required',listener);});
 it('does not confuse timeout with a completed run',async()=>{vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new DOMException('timeout','TimeoutError')));await expect(request('/runs')).rejects.toMatchObject({status:0,message:expect.stringContaining('Check the run status')});});
 it('waits for persisted completion before proceeding to analysis',async()=>{vi.useFakeTimers();const fetch=vi.fn().mockResolvedValueOnce(response({status:'pending'})).mockResolvedValueOnce(response({status:'running'})).mockResolvedValueOnce(response({status:'completed',id:'r1'}));vi.stubGlobal('fetch',fetch);const result=waitForRun('r1');await vi.advanceTimersByTimeAsync(2000);await expect(result).resolves.toMatchObject({id:'r1',status:'completed'});expect(fetch).toHaveBeenCalledTimes(3);});
 it('shows recorded job failures',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({status:'failed',error:'Backend stopped'})));await expect(waitForRun('r1')).rejects.toThrow('Backend stopped');});
});
