import fs from 'node:fs';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {pipeline,env} from '@huggingface/transformers';
env.cacheDir='/tmp/lesstube-model-cache';
const index=JSON.parse(fs.readFileSync('data/index.json','utf8'));
const extract=await pipeline('feature-extraction','Xenova/bge-small-en-v1.5',{dtype:'q8'});
const cacheDir='data/embedding-cache';fs.mkdirSync(cacheDir,{recursive:true});
const vectors={};const pending=[];
for(const d of index.videos){
 const text=[d.title,d.channel,d.tags.join(', '),d.summary,d.search_text.slice(0,800)].join('\n');
 const digest=createHash('sha256').update(text).digest('hex');const filename=`${cacheDir}/${d.vid}-${digest}.json`;
 if(fs.existsSync(filename))vectors[d.vid]=JSON.parse(fs.readFileSync(filename,'utf8'));
 else pending.push({d,text,filename});
}
console.log('Embedding',pending.length,'new/changed videos;',Object.keys(vectors).length,'cached');
for(let i=0;i<pending.length;i+=16){
 const batch=pending.slice(i,i+16);const out=await extract(batch.map(x=>x.text),{pooling:'cls',normalize:true});
 for(let j=0;j<batch.length;j++){
  const vector=Array.from(out.data.slice(j*384,(j+1)*384),x=>Number(x.toFixed(6)));
  vectors[batch[j].d.vid]=vector;fs.writeFileSync(batch[j].filename,JSON.stringify(vector));
 }
 if(i%256===0)console.log(i,'/',pending.length);
}
const encoded=JSON.stringify(vectors);fs.writeFileSync('data/embeddings.json',encoded);fs.writeFileSync('data/embeddings.json.gz',gzipSync(encoded));
console.log('Embedded',Object.keys(vectors).length,'videos');
const {execFileSync}=await import('node:child_process');
execFileSync('python3',['-c',`
import pathlib,json,zipfile
root=pathlib.Path('.');dest=root/'public'/'download';e=json.loads((root/'data'/'export.json').read_text())
(dest/'embeddings.json.gz').write_bytes((root/'data'/'embeddings.json.gz').read_bytes())
e['files']=[f for f in e['files'] if not f['name'].startswith('embeddings.')]
e['files'].append({'name':'embeddings.json.gz','description':'Gzipped 384-dimensional BGE-small vectors keyed by video ID.','bytes':(dest/'embeddings.json.gz').stat().st_size,'rows':len(json.loads((root/'data'/'embeddings.json').read_text()))})
with zipfile.ZipFile(dest/'lesstube-data.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in e['files']:z.write(dest/f['name'],f['name'])
e['zip']['bytes']=(dest/'lesstube-data.zip').stat().st_size
(root/'data'/'export.json').write_text(json.dumps(e))
`],{stdio:'inherit'});
