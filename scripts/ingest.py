"""Resumable public LessWrong post/comment scan; no eligibility or text-length filter."""
import concurrent.futures as cf,datetime as dt,json,pathlib,re,threading,time,urllib.request
from sources import PAT,plain,mentions
ROOT=pathlib.Path(__file__).resolve().parents[1];CACHE=ROOT/'data'/'archive-v2';CACHE.mkdir(parents=True,exist_ok=True)
lock=threading.Lock();PAGE=3000

def gql(query):
 for attempt in range(6):
  try:
   req=urllib.request.Request('https://www.lesswrong.com/graphql',data=json.dumps({'query':query}).encode(),headers={'Content-Type':'application/json','User-Agent':'LessTube/2.0 (public video discovery)'})
   r=json.load(urllib.request.urlopen(req,timeout=120))
   if r.get('errors'):raise RuntimeError(str(r['errors'])[:500])
   return r['data']
  except Exception:
   if attempt==5:raise
   time.sleep(2**attempt)

def scan(task):
 kind,year=task;path=CACHE/f'{kind}-{year}.json';checkpoint=CACHE/f'{kind}-{year}.checkpoint.json'
 if path.exists():
  saved=json.loads(path.read_text())
  if saved.get('exhausted'):return saved
 start=f'{year}-01-01T00:00:00.000Z';end=f'{year+1}-01-01T00:00:00.000Z'
 state=json.loads(checkpoint.read_text()) if checkpoint.exists() else saved if path.exists() else {'source_type':kind,'year':year,'cursor':start if kind=='comment' else end,'scanned':0,'mentions':[]}
 while True:
  if kind=='comment':
   sel={'after':state['cursor'],'before':end,'sortBy':'oldest'}
   body='comments(selector:{allRecentComments:SELECTOR},limit:3000){results{_id userId postedAt baseScore user{displayName} post{_id title slug} contents{html}}}'
  else:
   sel={'after':start,'before':state['cursor'],'hideCommunity':False}
   body='posts(selector:{new:SELECTOR},limit:3000){results{_id userId postedAt baseScore title slug user{displayName} contents{html}}}'
  selector=re.sub(r'"(\w+)":',r'\1:',json.dumps(sel))
  rows=gql('{'+body.replace('SELECTOR',selector)+'}')['comments' if kind=='comment' else 'posts']['results']
  dates=[r['postedAt'] for r in rows]
  if dates and dates!=sorted(dates,reverse=kind=='post'):raise RuntimeError('API returned an unexpected date order')
  previous=state['cursor'];boundary=set(state.get('boundary_ids',[]))
  fresh=[r for r in rows if not (state['scanned']>0 and r['postedAt']==previous and (not boundary or r['_id'] in boundary))]
  for row in fresh:state['mentions'].extend(mentions(row,kind))
  state['scanned']+=len(fresh)
  if rows:
   last=rows[-1]['postedAt']
   state['boundary_ids']=[r['_id'] for r in rows if r['postedAt']==last]
   if last==previous:
    # Some selectors use inclusive date bounds. Step beyond an exhausted boundary.
    moment=dt.datetime.fromisoformat(last.replace('Z','+00:00'))+dt.timedelta(milliseconds=1 if kind=='comment' else -1)
    state['cursor']=moment.isoformat(timespec='milliseconds').replace('+00:00','Z')
    state['boundary_ids']=[]
   else:state['cursor']=last
  temporary=checkpoint.with_suffix('.tmp');temporary.write_text(json.dumps(state,ensure_ascii=False));temporary.replace(checkpoint)
  with lock:print(f"{kind} {year}: {state['scanned']:,} scanned, {len(state['mentions']):,} mentions",flush=True)
  if not rows:
   state['exhausted']=True
   break
  time.sleep(.12)
 state['completed']=dt.datetime.now(dt.timezone.utc).isoformat();path.write_text(json.dumps(state,ensure_ascii=False));checkpoint.unlink(missing_ok=True);return state

def consolidate(results):
 unique={m['source_type']+':'+m['id']+':'+m['vid']:m for r in results for m in r['mentions']}
 (ROOT/'data'/'mentions-v2.json').write_text(json.dumps(list(unique.values()),ensure_ascii=False))
 stats={'scanned_comments':sum(r['scanned'] for r in results if r['source_type']=='comment'),'scanned_posts':sum(r['scanned'] for r in results if r['source_type']=='post'),'completed':dt.datetime.now(dt.timezone.utc).isoformat(),'mentions':len(unique),'unique_videos':len({m['vid'] for m in unique.values()}),'schema_version':2}
 stats['scanned']=stats['scanned_comments']+stats['scanned_posts'];(ROOT/'data'/'scan-v2.json').write_text(json.dumps(stats));print('COMPLETE',stats,flush=True)
if __name__=='__main__':
 now=dt.datetime.now(dt.timezone.utc);years=range(2005,now.year+1)
 tasks=[(kind,y) for kind in ['post','comment'] for y in years]
 with cf.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(scan,tasks))
 consolidate(results)
