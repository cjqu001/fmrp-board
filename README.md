# FMRP Highest / Lowest Record Board

The FMRP whiteboard of highest and lowest lab values, as a public web page:
**https://cjqu001.github.io/fmrp-board/**

- Anyone with the link can view it and export it as CSV, JPG or PDF.
- Only Quinones edits it, on their own computer, then pushes to GitHub.
- No patient identifiers, ever.

## Files

- `docs/index.html`, `docs/board.js`, `docs/style.css`: the page (GitHub Pages serves `docs/` from `main`)
- `docs/board.csv`: all records, in board order
- `docs/photo-log/`: whiteboard photos, kept only on this computer (git ignores it)
- `scripts/db_to_csv.py`: copies records from the old Flask database into `docs/board.csv`

How to edit: see [docs/README.md](docs/README.md).

## Change log

Git history of the board file is the change log:

```sh
git log -p docs/board.csv
```

To undo a change, restore an older `board.csv` (for example `git checkout <commit> -- docs/board.csv`),
then commit and push.

## History

Until 2026-11-19 the board was a Flask + SQLite app in Docker on the home NAS, with logins and an
append-only audit log. It was replaced by this static page to free the NAS. The old code is in git
history (commit `6c2c9f5` and earlier); see `project_log.md` for the decisions.
