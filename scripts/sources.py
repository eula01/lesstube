"""Extract direct YouTube links and their local context from public HTML."""
import html,re,urllib.parse
from html.parser import HTMLParser
PAT=re.compile(r'(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:[^\s<>"\']*?&(?:amp;)?)?v=|embed/|shorts/|live/|v/|watch/)|youtu\.be/)([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])',re.I)
class Text(HTMLParser):
 def __init__(self):super().__init__();self.out=[]
 def handle_data(self,s):self.out.append(s)
def plain(raw):
 p=Text();p.feed(raw);return re.sub(r'\s+',' ',' '.join(p.out)).strip()
def decode(raw):
 for _ in range(2):raw=html.unescape(urllib.parse.unquote(raw))
 return raw
def extract(raw):
 raw=decode(raw);ids=set(PAT.findall(raw));out={}
 if not ids:return out
 blocks=re.findall(r'<(p|li|blockquote|figcaption)\b[^>]*>([\s\S]*?)</\1>',raw)
 labels={}
 for anchor in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',raw,re.I):
  label=plain(anchor.group(2))
  if label and not re.match(r'https?://',label):
   for vid in PAT.findall(anchor.group(1)):labels.setdefault(vid,label[:200])
 for vid in ids:
  snippets=list(dict.fromkeys(plain(block) for _,block in blocks if vid in block))
  context=' '.join(s for s in snippets if s).strip()
  if not context:
   pos=raw.find(vid);context=plain(raw[max(0,pos-250):pos+700])
  out[vid]={'context':context[:3000], 'link_title':labels.get(vid,'')}
 return out

def mentions(record,source_type):
 raw=(record.get('contents') or {}).get('html') or '';links=extract(raw)
 if not links:return []
 post=record if source_type=='post' else record.get('post') or {}
 date=record['postedAt'];user=record.get('user') or {};base='https://www.lesswrong.com'
 url=f"{base}/posts/{post['_id']}/{post.get('slug','')}" if post.get('_id') else f"{base}/comments/{record['_id']}"
 if source_type=='comment' and post:url+=f"?commentId={record['_id']}"
 text=plain(raw)
 return [{'vid':vid,'id':record['_id'],'source_type':source_type,'author':user.get('displayName') or 'Deleted user','author_id':record.get('userId') or user.get('_id'),'ym':date[:7],'date':date,'story':post.get('title') or 'LessWrong discussion','post_id':post.get('_id'),'url':url,'text':(text if source_type=='comment' else context['context'])[:5000],'excerpt':len(text)>5000 or source_type=='post','karma':record.get('baseScore') or 0,**context} for vid,context in links.items()]
