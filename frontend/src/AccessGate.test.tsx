import '@testing-library/jest-dom/vitest';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AccessGate } from './AccessGate';
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('keeps protected content hidden until the server confirms a session',async()=>{
 let signedIn=false;
 const fetch=vi.fn(async(path:string,options?:RequestInit)=>{
  if(path.endsWith('/auth/login')){expect(JSON.parse(options?.body as string)).toEqual({token:'workspace-secret'});signedIn=true;return {ok:true,status:200,json:async()=>({authenticated:true})};}
  return {ok:true,status:200,json:async()=>({authenticated:signedIn,required:true})};
 });
 vi.stubGlobal('fetch',fetch);
 render(<AccessGate><div>Protected workspace</div></AccessGate>);
 const input=await screen.findByLabelText('Workspace access key');
 expect(screen.queryByText('Protected workspace')).not.toBeInTheDocument();
 await userEvent.type(input,'workspace-secret');
 await userEvent.click(screen.getByRole('button',{name:'Connect securely'}));
 await waitFor(()=>expect(screen.getByText('Protected workspace')).toBeInTheDocument());
 expect(localStorage.length).toBe(0);expect(sessionStorage.length).toBe(0);
});
it('shows an offline state instead of simulated results',async()=>{vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new TypeError('offline')));render(<AccessGate><div>Protected workspace</div></AccessGate>);expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach DriftLab');expect(screen.queryByText('Protected workspace')).not.toBeInTheDocument();});
