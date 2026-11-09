# LessTube

Star if you like it! <3

HackerTube adapted to YouTube links in public LessWrong posts and comments. Includes the original-style responsive interface, privacy-enhanced player, semantic search, topic browsing, filters, playlists, personalized discovery, likes, watch later, history, keyboard navigation, and downloadable attributed data.

## Run

```sh
npm install
npm run dev
```

Open http://127.0.0.1:4317. Production has no runtime dependencies; the Node API reads the committed index.

## Rebuild the collection

```sh
python3 scripts/ingest.py
python3 scripts/build_index.py
node scripts/embed.mjs
npm test
```

See DATA.md for inclusion, ranking, attribution and limitations. The current index is a snapshot; refresh it manually with the importer. Browser state is local to each device.

## Deploy

Deploy this directory to Vercel with framework preset Other. public/ contains static assets; api/index.js handles data APIs. vercel.json maps application routes to the SPA and includes endpoint names in API rewrites. Only the compressed runtime index and embeddings are deployed to the API; raw crawl and embedding caches are ignored. Do not upload data/crawl, data/archive-v2, data/metadata, raw mention files, or node_modules. All discovered video IDs are included. Repeat links boost ranking; they are not an inclusion threshold. Post-body and comment sources are shown separately. Metadata failures retain fallback entries.

Semantic model dependencies are dev-only and do not run in the serverless function.

## Attribution

Source repository: https://github.com/eula01/lesstube.

Original idea: Andrej Karpathy. Original concept and interface: https://hackertube.org/about, created by @karpathy with Claude. Adapted with Codex for LessWrong. Source posts and comments belong to their respective authors and retain their original terms. LessTube is unaffiliated with LessWrong, YouTube, or HackerTube.
