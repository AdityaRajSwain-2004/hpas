import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "../types";
import { USE_MOCK_DATA } from "../config";
interface AuthStore { user:User|null; isAuthenticated:boolean; isLoading:boolean; error:string|null; login:(e:string,p:string)=>Promise<void>; logout:()=>void; clearError:()=>void; }
export const useAuthStore = create<AuthStore>()(persist((set)=>({
  user:null, isAuthenticated:false, isLoading:false, error:null,
  login:async(email,password)=>{
    set({isLoading:true,error:null});
    await new Promise(r=>setTimeout(r,600));
    if(USE_MOCK_DATA){
      if(email==="demo@treeni.com"&&password==="demo123"){
        set({user:{id:"u1",name:"Arjun Mehta",email,role:"admin",avatar:"AM"},isAuthenticated:true,isLoading:false});
        localStorage.setItem("treeni_token","mock-token");
      } else { set({error:"Use demo@treeni.com / demo123",isLoading:false}); }
      return;
    }
    try {
      const resp=await fetch("/api/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,password})});
      if(!resp.ok) throw new Error("Invalid credentials");
      const data=await resp.json();
      localStorage.setItem("treeni_token",data.token||email);
      set({user:data.user,isAuthenticated:true,isLoading:false});
    } catch(e:any){ set({error:e.message,isLoading:false}); }
  },
  logout:()=>{ localStorage.removeItem("treeni_token"); set({user:null,isAuthenticated:false}); },
  clearError:()=>set({error:null}),
}),{name:"treeni-auth",partialize:(s)=>({user:s.user,isAuthenticated:s.isAuthenticated})}));
