// FMRP Highest / Lowest: static board.
// Everyone sees the board read from board.csv. Editing, import and the photo log only
// appear when the page is opened from your own computer (file:// or localhost).
"use strict";

const COLS = ["lab", "direction", "value", "residents", "note", "updated"];
const EDIT_MODE = location.protocol === "file:" || ["localhost", "127.0.0.1"].includes(location.hostname);
const HTML2CANVAS = "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js";

let records = [];      // [{lab, direction, value, residents, note, updated}]
let folder = null;     // directory handle from "Open board folder"
let editing = -1;      // index being edited, or records.length for a new one

const $ = (id) => document.getElementById(id);
const today = () => new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD, local time

// ---------- CSV ----------

function parseCSV(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  text = text.replace(/^﻿/, "");
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); rows.push(row); row = []; field = "";
    } else field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  const header = (rows.shift() || []).map((h) => h.trim().toLowerCase());
  if (!["lab", "direction", "value"].every((c) => header.includes(c))) {
    throw new Error("The CSV needs at least lab, direction and value columns.");
  }
  return rows
    .filter((r) => r.some((v) => v.trim()))
    .map((r) => Object.fromEntries(COLS.map((c) => [c, (r[header.indexOf(c)] ?? "").trim()])));
}

function toCSV(list) {
  const esc = (v) => (/[",\r\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
  return [COLS.join(","), ...list.map((r) => COLS.map((c) => esc(r[c] || "")).join(","))].join("\n") + "\n"; // LF, like the rest of the repo
}

// ---------- board ----------

function render() {
  const tbody = $("rows");
  tbody.replaceChildren();
  if (!records.length) {
    tbody.innerHTML = '<tr><td colspan="5">No records yet.</td></tr>';
    return;
  }
  const dirs = {};
  records.forEach((r) => (dirs[r.lab] ??= new Set()).add(r.direction));
  records.forEach((r, i) => {
    const tr = document.createElement("tr");
    const lab = cell(tr, "lab", r.lab);
    if (dirs[r.lab].has("High") && dirs[r.lab].has("Low") && r.direction !== "Count") {
      lab.textContent += ` (${r.direction.toLowerCase()})`;
    }
    cell(tr, "value", r.value);
    const who = cell(tr, "", "");
    r.residents.split("/").map((n) => n.trim()).filter(Boolean).forEach((name, j) => {
      if (j) who.append(" / ");
      const s = document.createElement("span");
      s.textContent = name;
      if (name.includes("?")) { s.className = "unsure"; s.title = "Handwriting uncertain"; }
      who.append(s);
    });
    if (r.note) { const d = document.createElement("div"); d.className = "note"; d.textContent = r.note; who.append(d); }
    cell(tr, "updated", r.updated);
    if (EDIT_MODE) {
      const td = cell(tr, "edit-only no-print", "");
      const b = document.createElement("button");
      b.type = "button"; b.textContent = "Edit"; b.disabled = !folder;
      b.onclick = () => openEditor(i);
      td.append(b);
    }
    tbody.append(tr);
  });
  $("lab-names").replaceChildren(...[...new Set(records.map((r) => r.lab))].sort().map(option));
  const names = new Set(records.flatMap((r) => r.residents.split("/").map((n) => n.trim()).filter(Boolean)));
  $("resident-names").replaceChildren(...[...names].sort().map(option));
}

function cell(tr, cls, text) {
  const td = document.createElement("td");
  if (cls) td.className = cls;
  td.textContent = text;
  tr.append(td);
  return td;
}

function option(v) { const o = document.createElement("option"); o.value = v; return o; }

function status(msg, bad = false) { const s = $("status"); s.textContent = msg; s.classList.toggle("bad", bad); }

async function loadPublished() {
  try {
    const res = await fetch(`board.csv?v=${Date.now()}`);
    if (!res.ok) throw new Error(res.status);
    records = parseCSV(await res.text());
    render();
  } catch {
    $("rows").innerHTML = EDIT_MODE
      ? '<tr><td colspan="5">Click <b>Open board folder</b> and choose the <code>docs</code> folder.</td></tr>'
      : '<tr><td colspan="5">The board could not be loaded. Please try again later.</td></tr>';
  }
}

// ---------- editing (your computer only) ----------

async function openFolder() {
  if (!window.showDirectoryPicker) {
    status("Editing needs Chrome or Edge (this browser can't save to a folder).", true);
    return;
  }
  try {
    folder = await window.showDirectoryPicker({ id: "fmrp-board", mode: "readwrite" });
    const file = await (await folder.getFileHandle("board.csv")).getFile();
    records = parseCSV(await file.text());
  } catch (e) {
    folder = null;
    if (e.name !== "AbortError") status(`Couldn't open board.csv in that folder: ${e.message}`, true);
    return;
  }
  $("add-record").disabled = false;
  $("folder-hint").hidden = true;
  $("open-folder").textContent = `Folder: ${folder.name}`;
  status(`Opened ${folder.name}/board.csv. Changes save to it automatically.`);
  render();
  loadPhotos();
}

async function save(message) {
  render();
  if (!folder) { status("Not saved: open the board folder first, or use Export CSV.", true); return; }
  try {
    const w = await (await folder.getFileHandle("board.csv", { create: true })).createWritable();
    await w.write(toCSV(records));
    await w.close();
    status(`${message} Saved to board.csv. Commit and push to publish.`);
  } catch (e) {
    status(`Couldn't save board.csv: ${e.message}`, true);
  }
}

function openEditor(i) {
  editing = i;
  const r = records[i] || { lab: "", direction: "High", value: "", residents: "", note: "" };
  const f = $("edit-form");
  for (const c of ["lab", "direction", "value", "residents", "note"]) f.elements[c].value = r[c];
  $("edit-title").textContent = records[i] ? "Edit record" : "Add record";
  $("delete-record").hidden = !records[i];
  $("editor").returnValue = ""; // so Esc after an earlier save doesn't save again
  $("editor").showModal();
}

$("editor").addEventListener("close", () => {
  if ($("editor").returnValue !== "save") return;
  const f = $("edit-form");
  const clean = (v) => v.split(/\s+/).filter(Boolean).join(" ");
  const r = {
    lab: clean(f.elements.lab.value),
    direction: f.elements.direction.value,
    value: f.elements.value.value.trim(),
    residents: f.elements.residents.value.split("/").map(clean).filter(Boolean).join(" / "),
    note: f.elements.note.value.trim(),
    updated: today(),
  };
  if (editing < records.length) {
    records[editing] = r;
    save(`Updated ${r.lab}.`);
  } else {
    // New records go right after the last row with the same lab, otherwise at the end.
    let at = records.length;
    records.forEach((x, j) => { if (x.lab.toLowerCase() === r.lab.toLowerCase()) at = j + 1; });
    records.splice(at, 0, r);
    save(`Added ${r.lab}.`);
  }
});

$("delete-record").onclick = () => {
  const r = records[editing];
  if (!confirm(`Delete ${r.lab} (${r.direction}) ${r.value}? Git history keeps the old version.`)) return;
  records.splice(editing, 1);
  $("editor").close("deleted");
  save(`Deleted ${r.lab}.`);
};

$("import-csv").onchange = async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  try {
    const rows = parseCSV(await file.text());
    if (!confirm(`Replace the board (${records.length} records) with ${file.name} (${rows.length} records)?`)) return;
    records = rows;
    save(`Imported ${rows.length} records from ${file.name}.`);
  } catch (err) {
    status(`Import failed: ${err.message}`, true);
  }
};

// ---------- exports ----------

function download(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

$("export-csv").onclick = () => download(new Blob([toCSV(records)], { type: "text/csv" }), `fmrp-board-${today()}.csv`);

$("export-jpg").onclick = async () => {
  const btn = $("export-jpg");
  btn.disabled = true;
  try {
    if (!window.html2canvas) {
      await new Promise((ok, fail) => {
        const s = document.createElement("script");
        s.src = HTML2CANVAS; s.onload = ok; s.onerror = () => fail(new Error("couldn't load html2canvas (offline?)"));
        document.head.append(s);
      });
    }
    document.body.classList.add("capturing");
    const canvas = await html2canvas($("board-area"), { backgroundColor: "#fff", scale: 2 });
    canvas.toBlob((b) => download(b, `fmrp-board-${today()}.jpg`), "image/jpeg", 0.92);
  } catch (e) {
    alert(`JPG export failed: ${e.message}`);
  } finally {
    document.body.classList.remove("capturing");
    btn.disabled = false;
  }
};

$("export-pdf").onclick = () => window.print();

// ---------- whiteboard photo log (your computer only, in photo-log/) ----------

async function photoDir() {
  return folder.getDirectoryHandle("photo-log", { create: true });
}

async function loadPhotos() {
  const list = $("photo-list");
  if (!folder) { list.textContent = "Open the board folder on the Board tab first."; return; }
  const files = [];
  for await (const [name, h] of (await photoDir()).entries()) {
    if (h.kind === "file" && /\.(jpe?g|png|gif|webp|heic|pdf)$/i.test(name)) files.push(h);
  }
  files.sort((a, b) => b.name.localeCompare(a.name));
  list.replaceChildren();
  if (!files.length) { list.textContent = "No photos yet."; return; }
  for (const h of files) {
    const file = await h.getFile();
    const url = URL.createObjectURL(file);
    const fig = document.createElement("figure");
    const cap = document.createElement("figcaption");
    cap.textContent = h.name;
    if (/\.pdf$/i.test(h.name)) {
      const a = document.createElement("a");
      a.href = url; a.target = "_blank"; a.textContent = "Open PDF";
      fig.append(a, cap);
    } else {
      const a = document.createElement("a");
      a.href = url; a.target = "_blank";
      const img = document.createElement("img");
      img.src = url; img.alt = h.name; img.loading = "lazy";
      a.append(img);
      fig.append(a, cap);
    }
    list.append(fig);
  }
}

$("photo-form").onsubmit = async (e) => {
  e.preventDefault();
  if (!folder) { $("photo-status").textContent = "Open the board folder on the Board tab first."; return; }
  const date = $("photo-date").value;
  const files = [...$("photo-file").files];
  try {
    const dir = await photoDir();
    for (const f of files) {
      const name = `${date}_${f.name.replace(/[^\w.\-]+/g, "_")}`;
      const w = await (await dir.getFileHandle(name, { create: true })).createWritable();
      await w.write(f);
      await w.close();
    }
    $("photo-status").textContent = `Added ${files.length} file(s) to photo-log/.`;
    e.target.reset();
    $("photo-date").value = today();
    loadPhotos();
  } catch (err) {
    $("photo-status").textContent = `Couldn't save: ${err.message}`;
  }
};

// ---------- start ----------

document.body.classList.toggle("editing", EDIT_MODE);
if (EDIT_MODE) {
  $("open-folder").onclick = openFolder;
  $("add-record").onclick = () => openEditor(records.length);
  $("photo-date").value = today();
  // When opened by double-click, show this folder's Windows path so it can be pasted into the picker.
  if (location.protocol === "file:") {
    const dir = decodeURIComponent(location.pathname).replace(/\/[^/]*$/, "");
    $("folder-path").value = dir.replace(/^\/([A-Za-z]:)/, "$1").replace(/\//g, "\\");
    $("folder-path").size = $("folder-path").value.length + 2;
    $("folder-hint").hidden = false;
    $("copy-path").onclick = async () => {
      $("folder-path").select();
      try { await navigator.clipboard.writeText($("folder-path").value); } catch { document.execCommand("copy"); }
      $("copy-path").textContent = "Copied";
      setTimeout(() => ($("copy-path").textContent = "Copy"), 1500);
    };
  }
  document.querySelectorAll(".tab").forEach((t) => (t.onclick = () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === t));
    $("tab-board").hidden = t.dataset.tab !== "board";
    $("tab-photos").hidden = t.dataset.tab !== "photos";
    if (t.dataset.tab === "photos") loadPhotos();
  }));
}
loadPublished();
