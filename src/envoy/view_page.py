"""The local page. One file, no build step."""

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Envoy</title>
<style>
  :root {
    color-scheme: light;
    --ink: #1c1915;
    --muted: #6b645c;
    --line: #e4ddd2;
    --paper: #f7f4ee;
    --panel: #fffdf9;
    --mark: #efe6d6;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    color: var(--ink);
    background: var(--paper);
    font: 15px/1.45 "Segoe UI", sans-serif;
  }
  header {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: baseline;
    padding: 14px 18px;
    border-bottom: 1px solid var(--line);
    background: var(--panel);
  }
  header strong { font-size: 16px; }
  #counts { color: var(--muted); font-size: 13px; }
  .layout {
    display: grid;
    grid-template-columns: 260px 1fr 320px;
    min-height: calc(100vh - 52px);
  }
  aside, main, section {
    min-height: 0;
    padding: 14px 16px 32px;
  }
  aside, section { background: var(--panel); }
  aside { border-right: 1px solid var(--line); }
  section { border-left: 1px solid var(--line); }
  h2 {
    margin: 18px 0 8px;
    font-size: 13px;
    font-weight: 650;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    color: var(--muted);
  }
  h2:first-child { margin-top: 0; }
  button.row, button.link {
    font: inherit;
    color: inherit;
    background: transparent;
    border: 0;
    text-align: left;
  }
  button.row {
    display: block;
    width: 100%;
    padding: 7px 8px;
    border-radius: 6px;
    cursor: pointer;
  }
  button.row:hover, button.row.on { background: var(--mark); }
  button.row .meta { display: block; color: var(--muted); font-size: 12px; }
  button.link { padding: 0; cursor: pointer; color: #3d5a40; }
  ol, ul { margin: 0; padding-left: 18px; }
  li { margin: 6px 0; }
  .due, .state, .quiet { color: var(--muted); }
  .split { display: grid; gap: 12px; }
  .card {
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 10px 12px;
    background: var(--paper);
  }
  .card h3 { margin: 0 0 6px; font-size: 13px; }
  .warn { color: #8a4b08; }
  @media (max-width: 900px) {
    .layout { grid-template-columns: 1fr; }
    aside, section { border: 0; border-top: 1px solid var(--line); }
  }
</style>
</head>
<body>
<header>
  <div id="crumb"><strong>Envoy</strong></div>
  <div id="counts"></div>
</header>
<div class="layout">
  <aside id="tree"></aside>
  <main id="board"></main>
  <section id="detail"></section>
</div>
<script>
let chair = "";
let selected = "";

function esc(value) {
  return String(value ?? "").replace(/[&<>"]/g, (ch) => (
    {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[ch]
  ));
}

function lines(items) {
  const list = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!list.length) return "<p class='quiet'>None.</p>";
  return "<ul>" + list.map((item) => "<li>" + esc(item) + "</li>").join("") + "</ul>";
}

function statusCard(title, doc) {
  if (!doc) return "<div class='card'><h3>" + esc(title) + "</h3><p class='quiet'>Nothing here.</p></div>";
  return "<div class='card'><h3>" + esc(title) + "</h3>"
    + "<p>" + esc(doc.forefront || "No forefront.") + "</p>"
    + (doc.repo ? "<p class='quiet'>" + esc(doc.repo) + "</p>" : "")
    + "<h2>Where I left off</h2>" + lines(doc.where_i_left_off)
    + "<h2>Next steps</h2>" + lines(doc.next_steps)
    + "<h2>Open loops</h2>" + lines(doc.open_loops)
    + "</div>";
}

function week(items, reconcile) {
  if (!items || !items.length) return "<p class='quiet'>Empty.</p>";
  const rows = items.map((item) => {
    const hit = (reconcile || []).find((row) => row.text === item.text && row.node === item.node);
    const due = item.due ? "<span class='due'>due " + esc(item.due) + "</span>" : "";
    const node = item.node ? "<span class='quiet'>" + esc(item.node) + "</span>" : "";
    const state = hit ? "<span class='state'>" + esc(hit.state) + "</span>" : "";
    return "<li><div>" + esc(item.text) + "</div><div>" + [node, due, state].filter(Boolean).join(" · ") + "</div></li>";
  });
  return "<ol>" + rows.join("") + "</ol>";
}

function renderBoard(data) {
  const crumb = document.getElementById("crumb");
  crumb.replaceChildren();
  if (data.parent) {
    const up = document.createElement("button");
    up.className = "link";
    up.textContent = data.parent;
    up.addEventListener("click", () => { chair = data.parent; selected = ""; refresh(); });
    crumb.append(up, document.createTextNode(" / "));
  }
  const here = document.createElement("strong");
  here.textContent = data.chair || "";
  crumb.append(here);

  const mail = Number(data.mail_unacked || 0);
  const inbox = Number(data.inbox_count || 0);
  document.getElementById("counts").textContent =
    inbox + " inbox · " + mail + " mail unseen";

  const tree = document.getElementById("tree");
  tree.replaceChildren();
  const heading = document.createElement("h2");
  heading.textContent = "Nodes";
  tree.append(heading);
  (data.entries || []).forEach((entry) => {
    const row = document.createElement("button");
    row.className = "row" + (entry.name === selected ? " on" : "");
    row.type = "button";
    const label = document.createElement("span");
    label.textContent = entry.name;
    row.append(label);
    const meta = document.createElement("span");
    meta.className = "meta";
    const bits = [entry.kind || "node", entry.status || ""];
    if (entry.sensitive) bits.push("sensitive");
    if (entry.opens) bits.push("opens");
    meta.textContent = bits.filter(Boolean).join(" · ");
    row.append(meta);
    row.addEventListener("click", () => { selected = entry.name; refresh(); });
    row.addEventListener("dblclick", () => {
      if (!entry.opens) return;
      chair = entry.name;
      selected = "";
      refresh();
    });
    tree.append(row);
  });

  const board = document.getElementById("board");
  let html = "";
  if (data.missing_board) html += "<p class='quiet'>No board file yet.</p>";
  if (data.focus) {
    html += "<h2>" + esc(data.focus.node) + "</h2>";
    html += week(data.focus.this_week, data.reconcile);
    if ((data.focus.later || []).length) {
      html += "<h2>Later</h2>" + week(data.focus.later, data.reconcile);
    }
  }
  html += "<h2>This week</h2>" + week((data.now || {}).this_week, data.reconcile);
  if (((data.now || {}).later || []).length) {
    html += "<h2>Later</h2>" + week(data.now.later, data.reconcile);
  }
  html += "<h2>Forefronts</h2>";
  if (!(data.forefronts || []).length) html += "<p class='quiet'>None published.</p>";
  else {
    html += "<ul>" + data.forefronts.map((row) => (
      "<li><div>" + esc(row.node) + "</div><div>" + esc(row.forefront || "") + "</div></li>"
    )).join("") + "</ul>";
  }
  if ((data.always_on_missing || []).length) {
    html += "<p class='warn'>Always-on with no line this week: "
      + data.always_on_missing.map(esc).join(", ") + "</p>";
  }
  board.innerHTML = html;
}

function renderDetail(data) {
  const pane = document.getElementById("detail");
  if (!data || data.ok === false) {
    pane.innerHTML = "<p class='quiet'>" + esc((data && data.error) || "Nothing selected.") + "</p>";
    return;
  }
  let html = "<h2>" + esc(data.address) + (data.sensitive ? " · sensitive" : "") + "</h2>";
  html += "<p class='quiet'>" + Number(data.inbox_count || 0) + " inbox</p>";
  if (data.diverged) {
    html += "<p class='warn'>Local file and published sitrep disagree.</p>";
    html += "<div class='split'>" + statusCard("Published", data.published) + statusCard("Local file", data.local) + "</div>";
  } else if (!data.published && !data.local) {
    html += "<p class='quiet'>No status filed.</p>";
  } else {
    html += statusCard(data.local && !data.published ? "Local file" : "Published", data.published || data.local);
    if (data.local && data.published) html += "<p class='quiet'>Local file matches.</p>";
    if (!data.local) html += "<p class='quiet'>No local status file.</p>";
    if (!data.published) html += "<p class='quiet'>Nothing published.</p>";
  }
  pane.innerHTML = html;
}

async function refresh() {
  const boardUrl = "/api/board" + (chair ? "?chair=" + encodeURIComponent(chair) : "");
  const board = await fetch(boardUrl).then((res) => res.json());
  if (board.ok === false) {
    document.getElementById("board").innerHTML = "<p>" + esc(board.error) + "</p>";
    return;
  }
  if (!chair) chair = board.chair;
  renderBoard(board);
  const node = selected || board.chair;
  const detail = await fetch(
    "/api/node?chair=" + encodeURIComponent(board.chair) + "&node=" + encodeURIComponent(node)
  ).then((res) => res.json());
  renderDetail(detail);
}

refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>
"""
