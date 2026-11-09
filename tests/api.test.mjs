import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {respond} from '../api/index.js';
const get=(s)=>respond(new URL('https://test.local/api/'+s));
const read=name=>JSON.parse(fs.existsSync(new URL('../data/'+name+'.gz',import.meta.url))?gunzipSync(fs.readFileSync(new URL('../data/'+name+'.gz',import.meta.url))).toString():fs.readFileSync(new URL('../data/'+name,import.meta.url),'utf8'));
const index=read('index.json');
test('every source-linked video is included, including singleton, post-only and metadata-failed videos',()=>{
 const allIds=new Set(index.comments.map(m=>m.vid));
 assert.equal(index.videos.length,allIds.size);
 assert.ok(index.videos.some(v=>v.hn.mentions===1));
 assert.ok(index.videos.some(v=>v.source_counts.posts>0&&v.source_counts.comments===0));
 assert.ok(index.videos.some(v=>v.metadata_status==='lookup_failed'));
 for(const d of index.videos)assert.ok(allIds.has(d.vid));
 assert.ok(index.comments.every(m=>new URL(m.url).hostname==='www.lesswrong.com'));
});
test('default feed ranks repeated linking higher without excluding singletons',()=>{
 const page=get('feed?n=100');assert.ok(page.every((d,i)=>!i||page[i-1].score>=d.score));
 const singleton=index.videos.find(d=>d.hn.mentions===1);assert.equal(get('video?vid='+singleton.vid).video.vid,singleton.vid);
});
test('post-only videos have correctly attributed sources and can be filtered',()=>{
 const d=index.videos.find(v=>v.source_counts.posts>0&&v.source_counts.comments===0);
 const detail=get('video?vid='+d.vid);assert.ok(detail.comments.length>0);assert.ok(detail.comments.every(m=>m.source_type==='post'&&!m.url.includes('commentId=')));
 assert.ok(get('list?source=post&n=100').every(v=>v.source_counts.posts>0));
 assert.ok(get('list?source=comment&n=100').every(v=>v.source_counts.comments>0));
});
test('seeded pagination is stable, unique and respects exclusions',()=>{
 const all=get('feed?seed=test&n=100');const first=get('feed?seed=test&n=3'),second=get('feed?seed=test&n=3&offset=3');
 assert.deepEqual([...first,...second].map(d=>d.vid),all.slice(0,6).map(d=>d.vid));assert.equal(new Set(all.map(d=>d.vid)).size,all.length);
 const filtered=get(`feed?seed=test&n=100&seen=${all[0].vid}&dislike=${all[1].vid}`);assert.ok(!filtered.some(d=>[all[0].vid,all[1].vid].includes(d.vid)));
});
test('duration, topic and views filters match real metadata',()=>{
 assert.ok(get('list?dur=xlong&n=100').every(d=>d.duration_s>3600));
 assert.ok(get('list?gems=1&n=100').every(d=>d.views>0&&d.views<100000));
 const cat=index.videos[0].categories[0].id;assert.ok(get(`list?cat=${cat}&n=100`).every(d=>d.categories.some(c=>c.id===cat)));
});
test('search finds an exact known title and returns an empty result for nonsense',()=>{
 const d=index.videos[0];assert.equal(get('search?q='+encodeURIComponent(d.title)).results[0].vid,d.vid);
 assert.equal(get('search?q=qzxvzzq987234xxx').results.length,0);
});
test('video page contains source comments and related videos exclude itself',()=>{
 const d=index.videos[0];assert.equal(get('video?vid='+d.vid).video.vid,d.vid);assert.ok(get('video?vid='+d.vid).comments.length>=3);
 assert.ok(get('related?vid='+d.vid).every(v=>v.vid!==d.vid));assert.equal(get('video?vid=invalid'),null);
});
test('personal library preserves requested order and ignores malformed ids',()=>{
 const a=index.videos.slice(0,3).map(d=>d.vid).reverse();assert.deepEqual(get('docs?vids='+a.join(',')+',invalid').map(d=>d.vid),a);
});
test('playlists have real playable videos and accurate duration totals',()=>{
 for(const p of get('playlists')){const full=get('playlist?slug='+p.slug);assert.equal(full.videos.length,p.count);assert.equal(full.minutes,Math.round(full.videos.reduce((n,d)=>n+(d.duration_s||0),0)/60));}
});
test('semantic vectors cover every video and retrieve the same video by meaning',()=>{
 const vectors=read('embeddings.json');
 for(const d of index.videos){assert.equal(vectors[d.vid].length,384);assert.ok(Math.abs(Math.hypot(...vectors[d.vid])-1)<.001);}
 const d=index.videos[0];const result=get('search?q=semanticquery&vector='+encodeURIComponent(JSON.stringify(vectors[d.vid])));assert.equal(result.results[0].vid,d.vid);assert.equal(result.semantic,true);
 assert.doesNotThrow(()=>get('search?q=bayes&vector=%5Bnull%5D'));
});

test('excluded video is absent from direct lookup, libraries and search',()=>{
 assert.equal(get('video?vid=dQw4w9WgXcQ'),null);
 assert.deepEqual(get('docs?vids=dQw4w9WgXcQ'),[]);
 assert.ok(!get('search?q=Rick%20Astley').results.some(d=>d.vid==='dQw4w9WgXcQ'));
});
