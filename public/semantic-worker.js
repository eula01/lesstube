// Searches run locally. Only the resulting numeric vector is sent to LessTube.
import {pipeline,env} from 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1/dist/transformers.min.js';
env.allowLocalModels=false;
env.backends.onnx.wasm.numThreads=1;
let model;
self.onmessage=async({data:{id,q}})=>{
 try{
  model??=pipeline('feature-extraction','Xenova/bge-small-en-v1.5',{dtype:'q8',device:'wasm'});
  const extract=await model;
  const out=await extract('Represent this sentence for searching relevant passages: '+q,{pooling:'cls',normalize:true});
  self.postMessage({id,vector:Array.from(out.data,x=>Number(x.toFixed(6)))});
 }catch(e){self.postMessage({id,error:String(e.message||e)});}
};
