import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import handler from './api/index.js';
const root=path.resolve('public');
http.createServer(async(req,res)=>{
 try {
 const u=new URL(req.url,'http://localhost');
 if(u.pathname.startsWith('/api/')) return await handler(req,res);
 const p=path.resolve(root,'.'+decodeURIComponent(u.pathname));
 if(!p.startsWith(root+path.sep)&&p!==root){res.writeHead(403);return res.end();}
 const file=fs.existsSync(p)&&fs.statSync(p).isFile()?p:path.join(root,'index.html');
 if(u.pathname.startsWith('/download/')&&file.endsWith('index.html')){res.writeHead(404);return res.end('Not found');}
 const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json','.jsonl':'application/x-ndjson','.zip':'application/zip','.md':'text/plain; charset=utf-8'};
 res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream'});fs.createReadStream(file).pipe(res);
 }catch(e){console.error(e);res.writeHead(500);res.end('Server error');}
}).listen(4317,'127.0.0.1',()=>console.log('LessTube: http://127.0.0.1:4317'));
