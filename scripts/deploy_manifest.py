"""List only the reviewed deployable files; never include local caches or credentials."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
paths=['package.json','package-lock.json','vercel.json','api/index.js','public/index.html','public/semantic-worker.js','data/index.json.gz','data/export.json','data/embeddings.json.gz']
manifest=json.loads((ROOT/'data/export.json').read_text())
paths += ['public/download/'+f['name'] for f in manifest['files']]+['public/download/'+manifest['zip']['name']]
print(json.dumps([{'file':p,'size':(ROOT/p).stat().st_size,'sha':hashlib.sha1((ROOT/p).read_bytes()).hexdigest()} for p in paths]))
