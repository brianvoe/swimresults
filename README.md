# swimresults

Searchable swim meet results from NASH D1 / Championship Meet Maestro PDFs — with a Vue app for season and swimmer dashboards.

## Web app

```bash
npm install
npm run dev
```

Runs on http://localhost:3333. The port is pinned in `vite.config.ts` with `strictPort`, so a conflict fails loudly instead of silently moving the site elsewhere.

| Route | Page |
|-------|------|
| `/` | Season home: championship podium, season points, meet timeline, leaders, fastest swims |
| `/swimmers` | Every swimmer, sortable and filterable |
| `/swimmer/:slug` | One swimmer: per-event bests, race-by-race grid, progression charts, relays |
| `/meet/:id` | One meet, event by event, with a link to the source PDF |
| `/team/:slug` | One team: roster and meet-by-meet points |
| `/leaderboards` | Fastest time per event, filterable by gender and age group |

Every page has a shareable URL. Search (swimmers, teams, meets) is in the header and bound to `/` or `⌘K`.

JSON is served from `public/data` and PDFs from `public/pdfs` (both symlinks to the repo root). `public/_redirects` provides the SPA fallback for static hosting, and `npm run build` copies `index.html` to `404.html` for hosts that use that convention instead.

## Data

Parsed JSON lives in `data/`:

| File | Description |
|------|-------------|
| `data/meets.json` | Meet index, including precomputed per-meet team scores |
| `data/meets/*.json` | Full results per meet (events, places, times, relays) |
| `data/athletes.json` | Athlete search index with dual rankings + season summary |

The home page reads only the index and the athlete file; individual meet files load on demand.

PDFs are in `pdfs/`:

| File | Meet |
|------|------|
| `meet1-d1-cottonwood.pdf` | Meet 1 · D1 |
| `meet1-d2-jcc.pdf` | Meet 1 · D2 |
| `meet2-d1-7hills.pdf` | Meet 2 · D1 |
| `meet2-d2-westhaven.pdf` | Meet 2 · D2 |
| `meet3-d1-richland.pdf` | Meet 3 · D1 |
| `meet3-d2-bstc.pdf` | Meet 3 · D2 |
| `championship-williamson.pdf` | Championship (both divisions) |

## Regenerate JSON from PDFs

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/parse_meets.py
```

Each individual result includes:

- Official age-group place / field
- Computed overall place / field (`All Men`, `All Women`, or `Overall` for open events)
- `rank_display` like `1st/11 (40-49)` + `1st/40 (All Men)`

The parser also merges duplicate athlete spellings across meets and flags implausible
times with `suspect_time`, using two rules:

- an absolute floor per event, for times no human has swum
- a per-swimmer check that flags a swim far faster than that swimmer's best other
  swim in the same event, which catches a clock that stopped on the split

Flagged swims keep their official placing and points, and the site marks them, but
they are excluded from records, leaderboards, personal bests, and improvement stats.
The script prints everything it flagged at the end of a run.
