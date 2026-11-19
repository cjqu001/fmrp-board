# Tech stack (all free and open source)

| Part | Choice | License |
|---|---|---|
| Page | Plain HTML, CSS and vanilla JS in `docs/` | — |
| Data | `docs/board.csv` | — |
| Hosting | GitHub Pages (public repo, `main` / `docs`) | free |
| JPG export | html2canvas 1.4.1, loaded from cdnjs only when used | MIT |
| PDF export | Browser print dialog (Save as PDF) | — |
| Editing | File System Access API (Chrome / Edge) on your own computer | — |
| Change log | Git history of `docs/board.csv` | GPL-2.0 (git) |

The older Flask + SQLite + Docker version (retired 2026-11-19) is in git history: check out commit `6c2c9f5` to see it.
