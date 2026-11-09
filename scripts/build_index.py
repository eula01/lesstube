"""Build the reproducible LessTube index. Run after ingest.py; caches YouTube metadata."""
import gzip,collections,concurrent.futures as cf,datetime as dt,html,json,math,pathlib,re,time,urllib.request,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; META=DATA/'metadata'; META.mkdir(exist_ok=True)
EXCLUDED=json.loads((ROOT/'excluded-videos.json').read_text()) if (ROOT/'excluded-videos.json').exists() else {}
TAX=[
 ('ai','AI & Machine Learning',[
 ('alignment','AI Alignment','alignment|superintelligence|existential risk|ai safety|yudkowsky|bostrom|mesa.optimizer|corrigibility|instrumental convergence|miri|robert miles'),
 ('ml','Machine Learning','machine learning|neural network|deep learning|backpropagation|gradient descent|transformer|llm|language model|karpathy|gpt|chatgpt'),
 ('agents','Agents & Decision Theory','decision theory|newcomb|prisoner|agent foundations|functional decision|timeless decision|causal decision|logical induction|game theory')]),
 ('rationality','Rationality & Thinking',[
 ('bias','Cognitive Biases','cognitive bias|kahneman|tversky|confirmation bias|thinking fast|heuristics|motivated reasoning|overconfidence|alief'),
 ('bayes','Bayesian Reasoning','bayes|probability|statistics|statistical|forecast|prediction|calibration|base rate|updating|uncertainty'),
 ('epistemology','Epistemology','epistemology|rationality|rationalist|truth|belief|evidence|epistemic|critical thinking|scout mindset|lesswrong'),
 ('practice','Applied Rationality','cfar|applied rationality|double crux|goal factoring|internal double crux|noticing|focusing|gtd')]),
 ('mind','Mind & Human Behavior',[
 ('psychology','Psychology','psychology|psychological|cognition|behavioral|behavioural|mental model|perception|attention'),
 ('neuro','Neuroscience','neuroscience|neuron|brain|dopamine|cortex|sapolsky|neurobiology|neural circuit'),
 ('consciousness','Consciousness','consciousness|qualia|sentience|sentient|chalmers|hard problem|integrated information'),
 ('meditation','Meditation & Wellbeing','meditation|mindfulness|jhana|buddhis|mental health|depression|therapy|therapeutic|trauma|wellbeing')]),
 ('science','Science & Mathematics',[
 ('physics','Physics','physics|quantum|feynman|relativity|thermodynamics|entropy|spacetime|particle|cosmology'),
 ('math','Mathematics','mathematics|mathematical|3blue1brown|linear algebra|calculus|geometry|infinity|godel|gödel|proof|number theory'),
 ('biology','Biology & Evolution','biology|evolution|darwin|genetic|dna|natural selection|evolutionary|molecular'),
 ('methods','Scientific Method','scientific method|replication|causal inference|experiment|science|research methods')]),
 ('philosophy','Philosophy & Ethics',[
 ('ethics','Ethics','ethics|ethical|morality|moral|utilitarian|consequentialis|effective altruism|peter singer|animal welfare'),
 ('philosophy','Philosophy','philosophy|philosophical|free will|determinism|existentialis|nietzsche|dennett|identity|meaning of life'),
 ('future','Long-term Futures','future|futurism|longterm|singularity|transhuman|cryonics|longevity|life extension|civilization|civilisation')]),
 ('society','Society & Coordination',[
 ('economics','Economics','economics|economic|market|incentive|capitalism|financial|finance|growth|trade'),
 ('coordination','Coordination & Institutions','coordination|institution|governance|cooperation|cooperate|public goods|social dilemma|mechanism design'),
 ('history','History & Culture','history|historical|culture|civilization|religion|anthropology|politics|political')]),
 ('computing','Computing & Technology',[
 ('cs','Computer Science','computer science|algorithm|computation|turing|complexity|computerphile|programming|software|coding'),
 ('technology','Technology & Engineering','engineering|technology|robot|space|energy|nuclear|rocket|fusion|hardware')]),
 ('life','Life, Learning & Creativity',[
 ('learning','Learning & Education','learning|education|teaching|teach|lecture|explaining|explanation|understanding|school|university'),
 ('productivity','Productivity & Agency','productivity|procrastination|habit|motivation|agency|akrasia|self.improvement|career|work'),
 ('art','Art, Music & Humor','music|song|comedy|humor|humour|funny|art|creativ|film|animation|storytelling')])]

def load_mentions():
 if (DATA/'mentions-v2.json').exists(): return json.loads((DATA/'mentions-v2.json').read_text())
 records={}
 for p in (DATA/'archive-v2').glob('*.json'):
  for m in json.loads(p.read_text()).get('mentions',[]): records[m['source_type']+':'+m['id']+':'+m['vid']]=m
 return list(records.values())

def candidates(ms):
 groups=collections.defaultdict(list)
 for m in ms:
  if m['vid'] not in EXCLUDED: groups[m['vid']].append(m)
 return dict(groups)

def metadata(vid):
 p=META/f'{vid}.json'
 if p.exists():
  try:return json.loads(p.read_text())
  except (OSError,ValueError):pass
 try:
  url='https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v='+vid+'&format=json'
  request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
  o=json.load(urllib.request.urlopen(request,timeout=15))
  result={'title':o['title'],'channel':o.get('author_name',''),'duration_s':None,'views':None,'published':None,'description':'','metadata_status':'available','available':True}
 except Exception as e:
  result={'available':False,'metadata_status':'lookup_failed','error':str(e)[:120]}
 p.write_text(json.dumps(result,ensure_ascii=False));return result

def stance(text):
 t=text.lower()
 if re.search(r'\b(misleading|debunk|nonsense|wrong|disagree|terrible|inaccurate)\b',t): return 'critical'
 if re.search(r'\b(hilarious|funny|parody|joke|rickroll)\b',t): return 'joke'
 if re.search(r'\b(highly recommend|must.watch|strongly recommend|one of the best|excellent talk)\b',t): return 'strong_rec'
 if re.search(r'\b(recommend|worth watching|great (talk|video|lecture)|good (talk|video|lecture))\b',t): return 'rec'
 return 'reference'
def main():
 ms=load_mentions(); groups=candidates(ms); print('All discovered videos',len(groups),flush=True)
 with cf.ThreadPoolExecutor(max_workers=10) as pool: metas=dict(zip(groups,pool.map(metadata,groups)))
 videos=[]; included=[]
 for vid,mm in groups.items():
  meta=metas[vid]
  if not meta.get('available'):
   label=next((m.get('link_title') for m in mm if len(m.get('link_title',''))>3),'')
   meta={'title':('Linked as: '+label) if label else 'YouTube video '+vid,'channel':'YouTube metadata unavailable','duration_s':None,'views':None,'published':None,'description':'','available':False,'metadata_status':'lookup_failed'}
  mm=sorted(mm,key=lambda m:(m['author']=='Deleted user',-m.get('karma',0),m['date']))
  for m in mm: m['stance']=stance(m.get('context',m['text']))
  context=' '.join(m['story']+' '+m.get('context',m['text'])[:1500] for m in mm)
  text=(meta['title']+' '+meta['description'][:1000]+' '+context).lower()
  cats=[]
  for aid,area,topics in TAX:
   for cid,name,terms in topics:
    terms=terms.split('|'); score=sum(len(re.findall(r'(?<!\w)'+t+r'(?!\w)',text)) for t in terms)
    # Weight actual metadata above discussion context.
    score+=sum(5*len(re.findall(r'(?<!\w)'+t+r'(?!\w)',(meta['title']+' '+meta['description'][:500]).lower())) for t in terms)
    if score: cats.append({'id':cid,'name':name,'area':aid,'score':score})
  cats=sorted(cats,key=lambda c:-c['score'])[:3] or [{'id':'learning','name':'Learning & Education','area':'life','score':0}]
  title=meta['title'].lower(); typ=next((t for t,p in [('interview',r'interview|podcast|conversation|lex fridman'),('lecture',r'lecture|course|class|lesson|university|stanford|mit '),('tutorial',r'tutorial|how to|walkthrough'),('documentary',r'documentary'),('comedy',r'comedy|parody'),('music',r'official music|music video'),('explainer',r'explain|3blue1brown|veritasium|computerphile'),('talk',r'talk|ted|conference|keynote')] if re.search(p,title)),'commentary')
  years=sorted({m['ym'][:4] for m in mm}); months={m['ym'] for m in mm}; authors={m.get('author_id') or m['author'] for m in mm if m.get('author_id') or m['author']!='Deleted user'}
  # Extractive summary with visible attribution; never fabricate a review.
  lead=re.sub(r'https?://\S+','[link]',mm[0].get('context',mm[0]['text'])); summary=lead[:350]+('…' if len(lead)>350 else '')
  summary=f"From {mm[0]['author']} in “{mm[0]['story']}”: {summary}"
  hn={'mentions':len(mm),'recommenders':len(authors),'rec_months':len(months),'first':years[0],'last':years[-1]}
  source_counts={'posts':sum(m['source_type']=='post' for m in mm),'comments':sum(m['source_type']=='comment' for m in mm)}
  video={'vid':vid,'metadata_status':meta.get('metadata_status','available' if meta.get('available') else 'lookup_failed'),'source_counts':source_counts,**{k:meta[k] for k in ['title','channel','duration_s','views','published']},'summary':summary,'why_hn':f"Linked by {len(authors)} distinct LessWrong author{'s' if len(authors)!=1 else ''} in {source_counts['posts']} posts and {source_counts['comments']} comments across {len(months)} months ({years[0]}–{years[-1]}). See the source references below; a link does not necessarily mean endorsement.",'content_type':typ,'level':'general','shelf_life':'evergreen' if max(years)!=min(years) else 'unclassified','categories':[{k:c[k] for k in ['id','name','area']} for c in cats],'tags':[c['name'] for c in cats],'hn':hn,'score':round(len(months)*3+len(authors)*2+math.log1p(len(mm)),3),'last_mentioned':max(m['date'] for m in mm),'authors':sorted(authors),'search_text':(meta['description'][:1000]+' '+context)[:6000]}
  videos.append(video); included.extend(mm)
 videos.sort(key=lambda d:-d['score'])
 taxonomy=[]
 for aid,name,topics in TAX:
  cats=[{'id':cid,'name':n,'description':terms.replace('|',', '),'count':sum(any(c['id']==cid for c in d['categories']) for d in videos)} for cid,n,terms in topics]
  taxonomy.append({'id':aid,'name':name,'count':sum(any(c['area']==aid for c in d['categories']) for d in videos),'categories':[c for c in cats if c['count']]})
 scan=json.loads((DATA/'scan-v2.json').read_text()) if (DATA/'scan-v2.json').exists() else {'scanned':sum(json.loads(p.read_text()).get('scanned',0) for p in (DATA/'archive-v2').glob('*.json')),'completed':dt.datetime.now(dt.timezone.utc).isoformat()}
 stats={'videos':len(videos),'comments':sum(m['source_type']=='comment' for m in included),'post_mentions':sum(m['source_type']=='post' for m in included),'mentions':len(included),'scanned_comments':scan.get('scanned_comments',0),'scanned_posts':scan.get('scanned_posts',0),'scanned':scan['scanned'],'categories':sum(len(a['categories']) for a in taxonomy),'areas':len(taxonomy),'first_year':min(m['ym'][:4] for m in included),'last_year':max(m['ym'][:4] for m in included),'generated':scan['completed'][:10],'metadata_available':sum(v['metadata_status']=='available' for v in videos),'metadata_failed':sum(v['metadata_status']!='available' for v in videos),'inclusion':'All distinct linked video IDs except explicit owner exclusions; no author, month, text-length, or metadata-success threshold.'}
 index={'videos':videos,'comments':included,'taxonomy':taxonomy,'stats':stats}
 (DATA/'index.json').write_text(json.dumps(index,ensure_ascii=False,separators=(',',':')))
 (DATA/'index.json.gz').write_bytes(gzip.compress((DATA/'index.json').read_bytes(),mtime=0))
 download=ROOT/'public'/'download';download.mkdir(exist_ok=True)
 exports=[('videos.jsonl','Video IDs, source summaries, categories, and community counts.',[{k:v for k,v in d.items() if k not in ['title','channel','duration_s','views','published','search_text','authors']} for d in videos]),('mentions.jsonl','Post and comment source excerpts with author attribution, dates, types, and original URLs.',included),('taxonomy.json','Topic areas, categories, synonyms, and counts.',taxonomy)]
 manifest=[]
 for name,description,rows in exports:
  p=download/name;p.write_text(('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n') if name.endswith('jsonl') else json.dumps(rows,ensure_ascii=False,indent=2))
  manifest.append({'name':name,'bytes':p.stat().st_size,'rows':len(rows),'description':description})
 doc=ROOT/'DATA.md';(download/'DATA.md').write_text(doc.read_text());manifest.append({'name':'DATA.md','bytes':doc.stat().st_size,'description':'Methodology, schemas, attribution, and reproducibility.'})
 with zipfile.ZipFile(download/'lesstube-data.zip','w',zipfile.ZIP_DEFLATED) as z:
  for f in manifest:z.write(download/f['name'],f['name'])
 (DATA/'export.json').write_text(json.dumps({'videos':len(videos),'mentions':len(included),'generated':stats['generated'],'files':manifest,'zip':{'name':'lesstube-data.zip','bytes':(download/'lesstube-data.zip').stat().st_size}}))
 print(json.dumps(stats,indent=2),flush=True)
if __name__=='__main__':main()
