"""Fetch lightweight YouTube titles/channels as the archive scan runs."""
import concurrent.futures as cf,json,pathlib,time
from build_index import metadata,META,DATA
while True:
 ids=set()
 for p in (DATA/'archive-v2').glob('*.json'):
  try:ids.update(m['vid'] for m in json.loads(p.read_text()).get('mentions',[]))
  except (OSError,ValueError):pass
 pending=sorted(v for v in ids if not (META/f'{v}.json').exists())
 print(f'Metadata: {len(ids)-len(pending):,}/{len(ids):,} cached; {len(pending):,} pending',flush=True)
 with cf.ThreadPoolExecutor(max_workers=10) as pool:
  for i,_ in enumerate(pool.map(metadata,pending)):
   if i and i%250==0:print(f'Fetched {i:,}/{len(pending):,}',flush=True)
 if (DATA/'scan-v2.json').exists():
  final=set(m['vid'] for m in json.loads((DATA/'mentions-v2.json').read_text()))
  if all((META/f'{v}.json').exists() for v in final):break
 time.sleep(5)
print('METADATA COMPLETE',flush=True)
