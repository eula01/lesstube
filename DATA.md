# LessTube data

LessTube adapts Andrej Karpathy's HackerTube idea (https://hackertube.org/about) to public LessWrong posts and comments. Source: https://github.com/eula01/lesstube.

## Reproduce

Requires Python 3.10+ and Node.js 22+. Importing needs no API key. Semantic indexing uses the dev dependency @huggingface/transformers.

Run `python3 scripts/ingest.py`, `python3 scripts/build_index.py`, `npm install`, then `node scripts/embed.mjs`.

The importer queries LessWrong's public GraphQL API in annual windows from 2005 to the current year. Comments are read oldest-first and posts newest-first. It checkpoints each page and continues until an empty page: a short page is NOT assumed to be the last page. Import caches live in data/archive-v2. Remove the current year's post/comment files to refresh those windows. Private, deleted and otherwise inaccessible records are outside the index. It is a dated snapshot, not a live subscription or a guaranteed complete historical archive. Timestamp-only cursors may miss records sharing an exact page-boundary timestamp.

## Inclusion

Every discovered 11-character YouTube video ID is included unless listed in excluded-videos.json by the site owner, even when linked once, in a bare-link comment, or only in a post body. There is no minimum author, month, or text-length requirement. Duplicate links within one post or comment count once. The same video appearing in both a post and a comment has two source references. Standard watch, embed, shorts, live, and youtu.be URLs are recognized, including HTML-escaped and percent-encoded variants. Redirect-only URLs without a YouTube ID and deleted/inaccessible content cannot be recovered.

A failed YouTube metadata lookup never excludes a video. Such records use their link label (explicitly marked "Linked as") or video ID as a fallback title. A 403/404 is recorded as a lookup failure, not a definitive claim that a video is deleted. Titles and channels use lightweight YouTube oEmbed lookups. Duration, view counts and upload dates are optional; unknown values are excluded only by filters that require them.

## Files

- videos.jsonl: one video per line. `vid` is its YouTube ID. `summary` is an attributed source extract. `source_counts.posts` and `.comments` count the two reference types. `hn` is a retained compatibility field containing total mentions, distinct authors (`recommenders`), distinct months (`rec_months`), and first/last years. These counts mean links, not endorsements.
- mentions.jsonl: one source/video association per line. `source_type` is `post` or `comment`; `id` identifies that source. `author_id` is used for independent-author counts when available, with display names only as a fallback. `url` is the original LessWrong URL. `context` is the local paragraph around the video link; `text` is a bounded source excerpt, not necessarily the full post or comment. `link_title` is the original anchor label. A source that mentions multiple videos appears once per video.
- taxonomy.json: areas/categories, related search vocabulary, and counts.
- embeddings.json.gz: gzipped JSON with one normalized, 384-dimensional BGE-small embedding per video ID.

Video titles, channels, descriptions, view counts, durations, and upload dates are fetched separately and omitted from the reusable data export. The runtime index includes optional metadata for the app.

## Ranking and labels

Rank = 3 × distinct calendar months + 2 × distinct authors + log(1 + source mentions), combining post and comment links. Repeated linking increases rank; it never determines eligibility. Home sorts by this score, with a small personalization bonus capped at 0.25 and a tiny seeded tie-break. Likes, dislikes, history and saved videos are device-local. Browse all includes every indexed ID, including watched videos.

Stance labels are keyword estimates: `strong_rec`, `rec`, `reference`, `joke`, `critical`. They are not human or model judgments and can be wrong. Topics and content types are also keyword estimates. A link can be a recommendation, criticism, joke, or incidental citation. Source excerpts can concern the broader discussion.

Search combines vocabulary-expanded text matching with BGE-small-en-v1.5 embeddings. The quantized open model runs in a browser Web Worker, downloading from Hugging Face through Transformers.js from jsDelivr. If loading fails, text/topic search remains available. Queries use BGE's retrieval prefix, CLS pooling and L2 normalization; document vectors use the same model/pooling and are built from titles, channels, categories and source context. No external paid AI service is called.

## Attribution and rights

Source text remains the work of its original authors and retains its original terms. Preserve the author and LessWrong source URL. This project does not grant additional rights to third-party text, videos or metadata. Credit LessWrong and its authors, and Andrej Karpathy/HackerTube for the original idea and interface. LessTube is independent of LessWrong, HackerTube, and YouTube.
