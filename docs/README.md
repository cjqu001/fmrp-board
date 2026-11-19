# FMRP Highest / Lowest (static board)

Plain HTML. GitHub Pages serves it; no server or NAS needed.

- `index.html`, `board.js`, `style.css`: the page
- `board.csv`: all records, in board order (`lab, direction, value, residents, note, updated`)
- `photo-log/`: whiteboard photos. Kept only on your computer (git ignores it), never published.

## Edit (only on your computer, Chrome or Edge)

1. Open `index.html` from this folder (double-click it), or run
   `.venv\Scripts\python -m http.server 8096 --bind 127.0.0.1 --directory docs` and go to http://localhost:8096.
2. Click **Open board folder** and choose this `docs` folder, then allow editing.
3. Use **+ Add record** or **Edit** on any row. Every change saves straight to `board.csv`.
4. Commit and push `board.csv`. The public page updates a minute or two later.

Git history is the change log: `git log -p docs/board.csv` shows every change.

Visitors to the public page only see the board and the CSV / JPG / PDF export buttons.

## Exports and import

- **CSV**: downloads the board as a CSV file.
- **JPG**: a picture of the board (loads html2canvas, MIT license, from cdnjs).
- **PDF**: opens the print dialog; choose **Save as PDF**.
- **Import CSV** (editing only): replaces the board with a CSV that has the same columns.

No patient identifiers. Do not enter patient names, MRNs, DOBs, rooms or dates of service.
