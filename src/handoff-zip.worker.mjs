import {zipSync} from 'fflate';

self.onmessage=({data})=>{
  try{
    const bytes=zipSync(data);
    self.postMessage({bytes},[bytes.buffer]);
  }catch(error){self.postMessage({error:error.message});}
};
