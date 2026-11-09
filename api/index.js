import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
const root = process.cwd();
const readData=name=>{const compressed=path.join(root,'data',name+'.gz');return JSON.parse(fs.existsSync(compressed)?gunzipSync(fs.readFileSync(compressed)).toString('utf8'):fs.readFileSync(path.join(root,'data',name),'utf8'));};
const index=readData('index.json');
const exportsInfo = JSON.parse(fs.readFileSync(path.join(root,'data/export.json'),'utf8'));
const {videos,taxonomy,stats,comments}=index;
const vectors=(fs.existsSync(path.join(root,'data/embeddings.json.gz'))||fs.existsSync(path.join(root,'data/embeddings.json')))?readData('embeddings.json'):{};
const byId=new Map(videos.map(d=>[d.vid,d]));
const commentsById=new Map();
for(const m of comments){ if(!commentsById.has(m.vid))commentsById.set(m.vid,[]);commentsById.get(m.vid).push(m); }
const slim=d=>{ const {search_text,authors,...rest}=d; return rest; };
const words=s=>String(s).toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,'').match(/[a-z0-9]+/g)||[];
const stop=new Set('a an the and or of to in on for with is are how what why it that this from video videos talk talks'.split(' '));
const wordSet=s=>new Set(words(s).filter(w=>!stop.has(w)));
const searchable=new Map(videos.map(d=>[d.vid,{title:wordSet(d.title),channel:wordSet(d.channel),body:wordSet(d.summary+' '+d.search_text+' '+d.tags.join(' '))}]));
const finite=(v,fallback)=>Number.isFinite(Number(v))?Number(v):fallback;
const count=p=>Math.min(100,Math.max(0,Math.floor(finite(p.get('n')??36,36))));
const offset=p=>Math.min(videos.length,Math.max(0,Math.floor(finite(p.get('offset')??0,0))));
const ids=(p,k)=>new Set((p.get(k)||'').split(',').slice(0,500).filter(v=>/^[\w-]{11}$/.test(v)));
function hash(s){let h=2166136261;for(const c of s){h^=c.charCodeAt(0);h=Math.imul(h,16777619);}return (h>>>0)/4294967296;}
export function filter(items,p){
 return items.filter(d=>{
  if(p.get('source')==='post'&&!(d.source_counts?.posts>0))return false;
  if(p.get('source')==='comment'&&!(d.source_counts?.comments>0))return false;
  if(p.get('cat')&&!d.categories.some(c=>c.id===p.get('cat')))return false;
  if(p.get('area')&&!d.categories.some(c=>c.area===p.get('area')))return false;
  const dur=p.get('dur'),s=d.duration_s;
  if(dur&&(!s||({short:s>=240,medium:s<240||s>=1200,long:s<1200||s>3600,xlong:s<=3600}[dur]??false)))return false;
  if(p.get('type')&&d.content_type!==p.get('type'))return false;
  if(p.get('evergreen')==='1'&&d.shelf_life!=='evergreen')return false;
  if(p.get('gems')==='1'&&!(d.views!=null&&d.views<100000))return false;
  const date=p.get('date'),year=d.published?new Date(d.published).getFullYear():null;
  if(date==='year'&&(!d.published||Date.now()-Date.parse(d.published)>365.25*86400000))return false;
  if(date&&/^\d{4}s$/.test(date)&&(!year||year<Number(date.slice(0,4))||year>=Number(date.slice(0,4))+10))return false;
  return true;
 });
}
function sorted(items,p){
 const sort=p.get('sort');
 return [...items].sort((a,b)=>sort==='recent'?b.last_mentioned.localeCompare(a.last_mentioned):sort==='date'?String(b.published||'').localeCompare(String(a.published||'')):sort==='old'?String(a.published||'9999').localeCompare(String(b.published||'9999')):sort==='views'?(b.views??-1)-(a.views??-1):b.score-a.score);
}
function topicSimilarity(a,b){const bs=new Set(b.categories.map(c=>c.id));return a.categories.reduce((n,c)=>n+Number(bs.has(c.id)),0);}
function sharedAuthors(a,b){const bs=new Set(b.authors);return a.authors.reduce((n,c)=>n+Number(bs.has(c)),0);}
export function search(p){
 const q=(p.get('q')||'').slice(0,300);const tokens=[...wordSet(q)];
 if(!tokens.length)return {results:[],weak:true};
 const topicMatches=taxonomy.flatMap(a=>a.categories).filter(c=>{
  const terms=wordSet(c.name+' '+c.description);return tokens.some(t=>terms.has(t));
 });
 let queryVector;
 try { const v=JSON.parse(p.get('vector')||'null'); if(Array.isArray(v)&&v.length===384&&v.every(n=>typeof n==='number'&&Number.isFinite(n))){const norm=Math.hypot(...v);if(norm>0)queryVector=v.map(n=>n/norm);} }catch{}
 const candidates=filter(videos,p).map(d=>{
  const s=searchable.get(d.vid);
  let score=tokens.reduce((n,t)=>n+(s.title.has(t)?12:0)+(s.channel.has(t)?6:0)+(s.body.has(t)?2:0),0);
  const topic=topicMatches.find(c=>d.categories.some(x=>x.id===c.id));
  if(topic) score+=3;
  if(d.title.toLowerCase().includes(q.toLowerCase()))score+=20;
  let cosine=null;
  if(queryVector&&vectors[d.vid]){cosine=queryVector.reduce((n,x,i)=>n+x*vectors[d.vid][i],0);score=cosine>.40?cosine*100+Math.min(score,40)*.8:score;}
  return {d,score,topic,cosine};
 }).filter(x=>x.score>0).sort((a,b)=>b.score-a.score||b.d.score-a.d.score);
 const matches=candidates.slice(0,100).map(x=>({...slim(x.d),...(x.topic?{via:x.topic.name}:{})}));
 if(p.get('sort')) return {results:sorted(matches,p),weak:!candidates.length};
 return {results:matches,weak:!candidates.length,semantic:Boolean(queryVector)};
}
const playlists=taxonomy.filter(a=>a.count>=3).map((a,i)=>{
 const items=videos.filter(d=>d.categories.some(c=>c.area===a.id)).slice(0,12);
 const minutes=Math.round(items.reduce((n,d)=>n+(d.duration_s||0),0)/60);
 return {slug:a.id,title:a.name,tier:i<2?'start':'deep',pitch:'Videos from LessWrong posts and comments, with repeated links ranked first.',intro:'Explore '+a.name.toLowerCase()+' through videos linked in LessWrong posts and comments. Ordered by distinct months and authors linking each video, rather than YouTube popularity. Open a video to read the original context.',cover:items.slice(0,4).map(d=>d.vid),count:items.length,minutes,videos:items.map(d=>({...slim(d),note:d.why_hn}))};
});
export function respond(url){
 const p=url.searchParams;const endpoint=p.get('endpoint')||url.pathname.replace(/^\/api\//,'');
 switch(endpoint){
  case 'config':return {frames_source:'youtube'};
  case 'stats':return stats;
  case 'export':return exportsInfo;
  case 'browse':return taxonomy;
  case 'docs':return [...ids(p,'vids')].map(id=>byId.get(id)).filter(Boolean).map(slim);
  case 'list':return sorted(filter(videos,p),p).slice(offset(p),offset(p)+count(p)).map(slim);
  case 'search':return search(p);
  case 'feed':{
   const likes=[...ids(p,'like')].map(id=>byId.get(id)).filter(Boolean),dislikes=ids(p,'dislike'),seen=ids(p,'seen'),seed=(p.get('seed')||'0').slice(0,40);
   const pool=videos.filter(d=>!dislikes.has(d.vid)&&!seen.has(d.vid));
   const ranked=pool.map(d=>{
    const personal=Math.min(.25,likes.reduce((n,liked)=>n+topicSimilarity(d,liked)*.015+Math.min(sharedAuthors(d,liked),5)*.005,0));
    return {d,weight:d.score+personal+hash(seed+d.vid)*.0001};
   }).sort((a,b)=>b.weight-a.weight);
   return ranked.slice(offset(p),offset(p)+count(p)).map(({d})=>({...slim(d),reason:`Linked ${d.hn.mentions} times by ${d.hn.recommenders} authors across ${d.hn.rec_months} months. Repeated linking increases rank.`}));
  }
  case 'video':{const d=byId.get(p.get('vid'));if(!d)return null;return {video:slim(d),comments:commentsById.get(d.vid)||[]};}
  case 'related':{const d=byId.get(p.get('vid'));if(!d)return [];return videos.filter(x=>x.vid!==d.vid).map(x=>({d:x,s:topicSimilarity(d,x)*3+sharedAuthors(d,x)})).sort((a,b)=>b.s-a.s||b.d.score-a.d.score).slice(0,count(p)).map(x=>slim(x.d));}
  case 'playlists':return playlists.map(({videos,...p})=>p);
  case 'playlist':return playlists.find(d=>d.slug===p.get('slug'))||null;
  default:return null;
 }
}
export default async function handler(req,res){
 if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405,{'Allow':'GET, HEAD'});return res.end();}
 try{
 const url=new URL(req.url,'https://lesstube.vercel.app');
 // A routing rewrite may expose its destination as /api/index while retaining the original path header.
 const data=respond(url);
 if(data===null){res.writeHead(404,{'Content-Type':'application/json'});return res.end(JSON.stringify({error:'Not found'}));}
 res.writeHead(200,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'public, max-age=60, s-maxage=3600','X-Content-Type-Options':'nosniff'});
 res.end(req.method==='HEAD'?'':JSON.stringify(data));
 }catch(e){console.error(e);res.writeHead(500,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'Unable to load the collection'}));}
}
