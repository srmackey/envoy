import { html, render, createContext, useContext, useState, useEffect, useRef, useMemo, useCallback } from "/vendor/preact-htm.js";

const POLL_MS = 2000;

const store = {
  get(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {}
  },
};

// Icons ----------------------------------------------------------------------

const svg = (body) => html`<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${body}</svg>`;
const icon = {
  right: svg(html`<polyline points="9 6 15 12 9 18" />`),
  down: svg(html`<polyline points="6 9 12 15 18 9" />`),
  lock: svg(html`<rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" />`),
  mail: svg(html`<rect x="3" y="5" width="18" height="14" rx="2" /><polyline points="3 7 12 13 21 7" />`),
  inbox: svg(html`<path d="M3 13h5l2 3h4l2-3h5" /><path d="M5.5 5h13L21 13v6H3v-6z" />`),
  search: svg(html`<circle cx="11" cy="11" r="7" /><line x1="16.5" y1="16.5" x2="21" y2="21" />`),
  eye: svg(html`<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" />`),
  eyeOff: svg(html`<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /><line x1="3" y1="3" x2="21" y2="21" />`),
  check: svg(html`<circle cx="12" cy="12" r="9" /><polyline points="8 12.5 11 15.5 16 9.5" />`),
  branch: svg(html`<circle cx="6" cy="5" r="2" /><circle cx="6" cy="19" r="2" /><circle cx="18" cy="7" r="2" /><path d="M6 7v10" /><path d="M18 9c0 5-7 4-11 8" />`),
  clock: svg(html`<circle cx="12" cy="12" r="9" /><polyline points="12 7 12 12 15.5 14" />`),
  flag: svg(html`<path d="M5 21V4" /><path d="M5 4h11l-2 4 2 4H5" />`),
  file: svg(html`<path d="M6 3h8l4 4v14H6z" /><polyline points="14 3 14 7 18 7" />`),
  split: svg(html`<path d="M12 3v18" /><rect x="3" y="6" width="18" height="12" rx="2" />`),
  menu: svg(html`<line x1="4" y1="7" x2="20" y2="7" /><line x1="4" y1="12" x2="20" y2="12" /><line x1="4" y1="17" x2="20" y2="17" />`),
};

// Words ----------------------------------------------------------------------

const STATE = {
  current: { text: "matches its Forefront", tone: "good" },
  accounted: { text: "in its trail", tone: "good" },
  satisfied: { text: "done per repo", tone: "good" },
  unaccounted: { text: "not in its sitrep", tone: "drift" },
  no_trail: { text: "no sitrep", tone: "quiet" },
};

const KIND = {
  overdue: "Overdue",
  due: "Due soon",
  mail: "Mail",
  inbox: "Inbox",
  unaccounted: "Not in sitrep",
  drift: "Files disagree",
  always_on: "Always-on gap",
  stale: "Stale",
};

const FIELD = {
  forefront: "Forefront",
  where_i_left_off: "Where I left off",
  next_steps: "Next steps",
  open_loops: "Open loops",
  repo: "Repo",
};

const plural = (n, one, many = one + "s") => `${n} ${n === 1 ? one : many}`;

function shortDate(iso) {
  if (!iso) return "";
  const day = new Date(iso.slice(0, 10) + "T00:00:00");
  if (Number.isNaN(day.getTime())) return iso;
  return day.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function dueText(days, due) {
  if (days === null || days === undefined) return null;
  if (days < -1) return { text: `overdue ${-days} days`, tone: "danger" };
  if (days === -1) return { text: "overdue since yesterday", tone: "danger" };
  if (days === 0) return { text: "due today", tone: "warn" };
  if (days === 1) return { text: "due tomorrow", tone: "warn" };
  if (days <= 7) return { text: `due in ${days} days`, tone: "warn" };
  return { text: `due ${shortDate(due)}`, tone: "quiet" };
}

function ageText(days) {
  if (days === null || days === undefined) return "never updated";
  if (days <= 0) return "updated today";
  if (days === 1) return "updated yesterday";
  return `updated ${days} days ago`;
}

function reason(item, kind) {
  switch (kind) {
    case "overdue":
    case "due":
      return dueText(item.days, item.due)?.text;
    case "mail":
      return plural(item.mail, "unseen note");
    case "inbox":
      return plural(item.inbox, "letter") + " waiting";
    case "unaccounted":
      return `not in ${item.node}'s sitrep`;
    case "drift":
      return "local file and sitrep differ";
    case "always_on":
      return "always-on, no line this week";
    case "stale":
      return item.reason === "past_date" ? "Forefront date has passed" : `sitrep ${item.age_days} days old`;
    default:
      return "";
  }
}

function cardDetail(item, own = false) {
  const reasons = item.kinds.map((kind) => reason(item, kind)).filter(Boolean);
  if (!own && item.text && item.node && !item.kinds.includes("unaccounted")) reasons.push(item.node);
  return reasons.join(" · ");
}

// Tree helpers -----------------------------------------------------------------

function walk(nodes, out = [], parent = null) {
  for (const node of nodes || []) {
    out.push({ node, parent });
    walk(node.children, out, node.address);
  }
  return out;
}

function visible(nodes, collapsed, out = []) {
  for (const node of nodes || []) {
    out.push(node.address);
    if (node.children?.length && !collapsed.has(node.address)) visible(node.children, collapsed, out);
  }
  return out;
}

function subsequence(needle, hay) {
  let i = 0;
  for (const ch of hay) if (ch === needle[i]) i += 1;
  return i === needle.length;
}

// Inline text: `code` and **bold**, nothing else. Preact escapes the text. -------

function Fmt({ text }) {
  const parts = String(text ?? "").split(/(`[^`]+`|\*\*.+?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) return html`<code key=${i}>${part.slice(1, -1)}</code>`;
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) return html`<strong key=${i}><${Fmt} text=${part.slice(2, -2)} /></strong>`;
    return part;
  });
}

// Small pieces -------------------------------------------------------------------

function Dot({ state }) {
  const label = { fresh: "Up to date", stale: "Stale", drift: "Files disagree", silent: "No sitrep" }[state] || state;
  return html`<span class=${"dot " + state} title=${label} role="img" aria-label=${label}></span>`;
}

function Chip({ tone = "", children, onClick, title }) {
  if (onClick) return html`<button type="button" class=${"chip " + tone} onClick=${onClick} title=${title}>${children}</button>`;
  return html`<span class=${"chip " + tone} title=${title}>${children}</span>`;
}

function DueChip({ days, due }) {
  const info = dueText(days, due);
  return info ? html`<${Chip} tone=${info.tone}>${icon.clock}${info.text}<//>` : null;
}

function StateChip({ state }) {
  const info = STATE[state];
  return info ? html`<${Chip} tone=${info.tone}>${info.text}<//>` : null;
}

function NodeChip({ item, go }) {
  if (!item.node) return null;
  const open = item.address ? () => go(item.address) : undefined;
  return html`<${Chip} onClick=${open} title=${item.address || item.node}>${item.node}<//>`;
}

// A block opened by hand stays open until the next hide-all. The eye in the header
// bumps `epoch` to hide everything, and `track` counts what is open so the eye can
// tell whether anything sensitive is showing.
const Reveals = createContext({ epoch: 0, track: () => {} });

function Veil({ on, show, inline = false, children }) {
  const { epoch, track } = useContext(Reveals);
  const [openAt, setOpenAt] = useState(-1);
  const open = on && !show && openAt === epoch;
  useEffect(() => {
    if (!open) return undefined;
    track(1);
    return () => track(-1);
  }, [open]);
  if (!on || show) return children;
  const hide = (event) => {
    event.stopPropagation();
    setOpenAt(-1);
  };
  // Hidden or shown, the lock leads: first on the line inline, first row on a block.
  if (open) {
    if (inline) {
      return html`<span class="veil-open"><button type="button" class="veil-hide inline" title="Hide again" onClick=${hide}>${icon.lock}</button>${children}</span>`;
    }
    return html`<div class="veil-open">
      <button type="button" class="veil-row veil-hide" title="Hide again" onClick=${hide}>${icon.lock}<span>Hide</span></button>
      ${children}
    </div>`;
  }
  const reveal = (event) => {
    event.stopPropagation();
    setOpenAt(epoch);
  };
  if (inline) {
    return html`<span class="veil inline" role="button" tabindex="0" title="Sensitive. Click to show." onClick=${reveal}
      onKeyDown=${(e) => e.key === "Enter" && reveal(e)}>${icon.lock}<span class="bar"></span></span>`;
  }
  return html`<div class="veil" role="button" tabindex="0" title="Sensitive. Click to show." onClick=${reveal}
    onKeyDown=${(e) => e.key === "Enter" && reveal(e)}>
    <span class="veil-row">${icon.lock}<span>Sensitive. Click to show.</span></span>
    <div class="bars" aria-hidden="true"><span class="bar"></span><span class="bar"></span><span class="bar"></span></div>
  </div>`;
}

function Ago({ at }) {
  const [, tick] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(timer);
  }, []);
  if (!at) return "connecting";
  const seconds = Math.max(0, Math.round((Date.now() - at) / 1000));
  return seconds < 2 ? "checked just now" : `checked ${seconds}s ago`;
}

// Header ---------------------------------------------------------------------------

function Header({ snap, online, checked, go, showSensitive, toggleSensitive, openJump, toggleSide }) {
  const path = snap?.path || [];
  const top = snap?.tree?.[0]?.address;
  return html`<header class="top">
    <button type="button" class="tool menu" onClick=${toggleSide} aria-label="Chairs">${icon.menu}</button>
    <button type="button" class="brand" onClick=${() => top && go(top)}><img src="/icon.svg" alt="" /><span class="brand-name">Envoy</span></button>
    <nav class="crumbs" aria-label="Location">
      ${path.map((step, i) =>
        i < path.length - 1
          ? html`<button type="button" key=${step.address} onClick=${() => go(step.address)}>${step.name}</button><span class="sep">/</span>`
          : html`<strong key=${step.address}>${step.name}</strong>`
      )}
    </nav>
    <div class="spacer"></div>
    <button type="button" class="tool" onClick=${openJump} title="Jump to a chair">${icon.search}<span class="label">Jump</span><kbd>/</kbd></button>
    <button type="button" class="tool" aria-pressed=${showSensitive} onClick=${toggleSensitive}
      title=${showSensitive ? "Hide sensitive chairs (s)" : "Show sensitive chairs (s)"}>${showSensitive ? icon.eye : icon.eyeOff}</button>
    <span class=${"live" + (online ? "" : " off")} title=${online ? "Re-reads the bulletin every 2 seconds" : "The local server is not answering"}>
      <span class="pulse"></span><span class="text">${online ? html`<${Ago} at=${checked} />` : "offline"}</span>
    </span>
  </header>`;
}

// Tree -------------------------------------------------------------------------------

function TreeRow({ node, depth, selected, collapsed, toggle, go }) {
  const ref = useRef(null);
  const kids = node.children || [];
  const open = !collapsed.has(node.address);
  const on = selected === node.address;
  const h = node.health;
  useEffect(() => {
    if (on && ref.current) ref.current.scrollIntoView({ block: "nearest" });
  }, [on]);
  return html`<li role="treeitem" aria-selected=${on} aria-expanded=${kids.length ? open : undefined}>
    <div ref=${ref} class=${"row" + (on ? " on" : "") + (node.status !== "active" ? " dim" : "")} style=${`--depth:${depth}`}
      onClick=${() => go(node.address)} title=${node.forefront || node.address}>
      ${kids.length
        ? html`<button type="button" class="caret" aria-label=${open ? "Collapse" : "Expand"}
            onClick=${(e) => { e.stopPropagation(); toggle(node.address); }}>${open ? icon.down : icon.right}</button>`
        : html`<span class="caret-space"></span>`}
      <${Dot} state=${h.state} />
      <span class="name">${node.name}</span>
      ${node.sensitive ? html`<span class="lock" title="Sensitive">${icon.lock}</span>` : null}
      ${h.mail ? html`<span class="badge" title=${plural(h.mail, "unseen mail note")}>${icon.mail}${h.mail}</span>` : null}
      ${h.inbox ? html`<span class="badge" title=${plural(h.inbox, "inbox letter")}>${icon.inbox}${h.inbox}</span>` : null}
    </div>
    ${kids.length && open
      ? html`<ul role="group">${kids.map((kid) => html`<${TreeRow} key=${kid.address} node=${kid} depth=${depth + 1}
          selected=${selected} collapsed=${collapsed} toggle=${toggle} go=${go} />`)}</ul>`
      : null}
  </li>`;
}

function Side({ snap, selected, collapsed, toggle, go, open }) {
  return html`<aside class=${"side" + (open ? " open" : "")}>
    <div class="side-scroll">
      <h2>Chairs</h2>
      <ul class="tree" role="tree">
        ${(snap?.tree || []).map((node) => html`<${TreeRow} key=${node.address} node=${node} depth=${0}
          selected=${selected} collapsed=${collapsed} toggle=${toggle} go=${go} />`)}
      </ul>
    </div>
    <div class="legend">
      <span><${Dot} state="fresh" />Up to date</span>
      <span><${Dot} state="stale" />Stale</span>
      <span><${Dot} state="drift" />Files disagree</span>
      <span><${Dot} state="silent" />No sitrep</span>
    </div>
    <div class="keys"><span><kbd>j</kbd> <kbd>k</kbd> move</span><span><kbd>h</kbd> up</span><span><kbd>/</kbd> jump</span><span><kbd>s</kbd> sensitive</span></div>
  </aside>`;
}

// Main --------------------------------------------------------------------------------

// A need on the open chair's own card names the chair already, so the row drops it.
function NeedRow({ item, go, own, showSensitive }) {
  const what = item.text
    ? html`<${Veil} on=${item.sensitive} show=${showSensitive} inline><${Fmt} text=${item.text} /><//>`
    : own ? null : item.node;
  const body = html`<span class="kind">${item.kinds.map((kind) => KIND[kind]).join(" · ")}</span>
    ${what ? html`<span class="what">${what}</span>` : null}
    <span class="detail">${cardDetail(item, own)}</span>`;
  if (own || !item.address) return html`<div class=${"need " + item.kind}>${body}</div>`;
  return html`<button type="button" class=${"need " + item.kind} onClick=${() => go(item.address)}>${body}</button>`;
}

function Needs({ items, go, own = false, cap = 0, showSensitive }) {
  const [all, setAll] = useState(false);
  const shown = cap && !all ? items.slice(0, cap) : items;
  return html`<ul class="needs">
      ${shown.map((item) => html`<li key=${[item.kind, item.address || item.node, item.text].join("|")}>
        <${NeedRow} item=${item} go=${go} own=${own} showSensitive=${showSensitive} />
      </li>`)}
    </ul>
    ${cap && items.length > cap
      ? html`<button type="button" class="more" onClick=${() => setAll(!all)}>${all ? "Show fewer" : `Show all ${items.length}`}</button>`
      : null}`;
}

function BoardItem({ item, next, go, showSensitive }) {
  return html`<li>
    <div>
      <p class="text"><${Veil} on=${item.sensitive} show=${showSensitive} inline><${Fmt} text=${item.text} /><//></p>
      <div class="chips">
        ${next ? html`<${Chip} tone="good">Next move<//>` : null}
        <${NodeChip} item=${item} go=${go} />
        <${DueChip} days=${item.days} due=${item.due} />
        <${StateChip} state=${item.state} />
      </div>
    </div>
  </li>`;
}

function Board({ board, next, go, showSensitive }) {
  if (!board || board.missing) {
    return html`<div class="block"><h3 class="section-title">This week</h3>
      <p class="quiet">No FOCUS.md for ${board?.nexus || "this nexus"} yet.</p></div>`;
  }
  return html`${board.sections.map((section) => html`<div class="block" key=${section.name}>
      <h3 class="section-title">${section.name === board.nexus ? "This week" : `${section.name} · this week`}
        ${section.sensitive ? html`<span class="lock" title="Sensitive">${icon.lock}</span>` : null}</h3>
      ${section.this_week.length
        ? html`<ol class="week">${section.this_week.map((item, i) => html`<${BoardItem} key=${i + item.text} item=${item}
            next=${i === 0 && next?.board === section.name} go=${go} showSensitive=${showSensitive} />`)}</ol>`
        : html`<p class="quiet">Nothing is ranked this week.</p>`}
      ${section.later.length
        ? html`<details class="later"><summary>Later · ${section.later.length}</summary>
            <ul>${section.later.map((item, i) => html`<li key=${i + item.text}>
              <p class="text"><${Veil} on=${item.sensitive} show=${showSensitive} inline><${Fmt} text=${item.text} /><//></p>
              <div class="chips"><${NodeChip} item=${item} go=${go} /><${DueChip} days=${item.days} due=${item.due} /></div>
            </li>`)}</ul></details>`
        : null}
    </div>`)}
    ${board.always_on_missing.length
      ? html`<p class="gap">Always-on with no line this week: ${board.always_on_missing.join(", ")}</p>`
      : null}`;
}

function Value({ value }) {
  if (Array.isArray(value)) {
    return value.length ? html`<ul>${value.map((line, i) => html`<li key=${i}><${Fmt} text=${line} /></li>`)}</ul>` : html`<span class="quiet">None.</span>`;
  }
  return value ? html`<${Fmt} text=${value} />` : html`<span class="quiet">None.</span>`;
}

function Drift({ brief }) {
  const names = brief.differs.map((field) => FIELD[field] || field);
  return html`<div class="drift-box">
    <p>The local file and the published sitrep differ in <strong>${names.join(", ")}</strong>. A settle run in that chair republishes the sitrep.</p>
    ${brief.differs.map((field) => html`<div key=${field}>
      <div class="field">${FIELD[field] || field}</div>
      <div class="diff">
        <div><span class="side-label">Local file</span><${Value} value=${brief.local?.[field]} /></div>
        <div><span class="side-label">Published</span><${Value} value=${brief.published?.[field]} /></div>
      </div>
    </div>`)}
  </div>`;
}

function Timeline({ items }) {
  if (!items?.length) return null;
  return html`<h3>Where I left off</h3>
    <ol class="timeline">
      ${items.map((line, i) => {
        const match = String(line).match(/^(\d{4}-\d{2}-\d{2})\s*[:·-]?\s*(.*)$/);
        return html`<li key=${i}>
          <span class="when">${match ? shortDate(match[1]) : ""}</span>
          <span class="node"></span>
          <span><${Fmt} text=${match ? match[2] : line} /></span>
        </li>`;
      })}
    </ol>`;
}

function Steps({ title, items, ordered = false }) {
  if (!items?.length) return null;
  const rows = items.map((line, i) => html`<li key=${i}><${Fmt} text=${line} /></li>`);
  return html`<h3>${title}</h3>${ordered ? html`<ol>${rows}</ol>` : html`<ul class="plain">${rows}</ul>`}`;
}

// The open chair leads: its Forefront, its chips, what on it needs you, then its record.
function ChairCard({ brief, go, showSensitive }) {
  if (!brief || brief.ok === false) {
    return html`<section class="panel chair"><p class="quiet">${brief?.error === "forbidden" ? "That chair is outside this nexus." : "Nothing selected."}</p></section>`;
  }
  const doc = brief.local || brief.published;
  const h = brief.health || {};
  const mine = brief.attention || [];
  let source = "From the published sitrep. No local file.";
  if (brief.local && brief.published) source = brief.diverged ? "Showing the local file. The published sitrep differs." : "Local file and published sitrep match.";
  else if (brief.local) source = "From the local file. Nothing is published.";
  const chips = [
    h.repo ? html`<${Chip} key="repo" tone=${h.dirty ? "warn" : "good"} title=${h.repo}>${icon.branch}<span class="clip">${h.repo}</span><//>` : null,
    doc ? html`<${Chip} key="age" tone=${h.stale ? "warn" : "quiet"} title=${h.updated || ""}>${icon.clock}${ageText(h.age_days)}<//>` : null,
    h.drift ? html`<${Chip} key="drift" tone="drift">${icon.split}files disagree<//>` : null,
    brief.inbox_count ? html`<${Chip} key="inbox" tone="good">${icon.inbox}${plural(brief.inbox_count, "letter")}<//>` : null,
    h.mail ? html`<${Chip} key="mail" tone="good">${icon.mail}${plural(h.mail, "unseen note")}<//>` : null,
  ].filter(Boolean);
  const body = html`
    ${doc
      ? html`<p class="ff"><${Fmt} text=${doc.forefront || "No Forefront set."} /></p>`
      : html`<div class="empty-brief">No sitrep yet. This chair has not published one, and there is no local status file.</div>`}
    ${chips.length ? html`<div class="chips">${chips}</div>` : null}
    ${mine.length
      ? html`<h3>Needs you <span class="count">${mine.length}</span></h3>
          <${Needs} items=${mine} go=${go} own=${true} showSensitive=${showSensitive} />`
      : null}
    ${doc
      ? html`${brief.diverged ? html`<${Drift} brief=${brief} />` : null}
          <${Timeline} items=${doc.where_i_left_off} />
          <${Steps} title="Next steps" items=${doc.next_steps} ordered />
          <${Steps} title="Open loops" items=${doc.open_loops} />
          <p class="source">${icon.file}${source}</p>`
      : null}`;
  return html`<section class="panel chair">
    <header class="chair-head">
      <p class="eyebrow">${brief.kind === "nexus" ? "Nexus" : "Chair"}
        ${brief.sensitive ? html`<span class="lock" title="Sensitive">${icon.lock}</span>` : null}</p>
      <h1>${brief.address}</h1>
    </header>
    <${Veil} on=${brief.sensitive && Boolean(doc)} show=${showSensitive}>${body}<//>
  </section>`;
}

// The nexus in view stays in sight, smaller: its board and whatever else under it needs you.
function NexusCard({ snap, go, showSensitive }) {
  const nexus = snap.nexus || { address: snap.view, name: snap.view };
  const self = snap.chair === snap.view;
  const items = snap.attention || [];
  return html`<section class="panel nexus-card">
    <header class="nexus-head">
      <p class="eyebrow">${self ? "Its board" : "Nexus"}
        ${nexus.sensitive ? html`<span class="lock" title="Sensitive">${icon.lock}</span>` : null}</p>
      ${self
        ? html`<h2>${nexus.address}</h2>`
        : html`<h2><button type="button" class="open" onClick=${() => go(snap.view)} title="Open this nexus">${nexus.address}${icon.right}</button></h2>`}
      ${!self && nexus.forefront
        ? html`<p class="nexus-ff"><${Veil} on=${nexus.sensitive} show=${showSensitive} inline><${Fmt} text=${nexus.forefront} /><//></p>`
        : null}
    </header>
    <${Board} board=${snap.board} next=${snap.next} go=${go} showSensitive=${showSensitive} />
    <div class="block">
      <h3 class="section-title">Needs you ${items.length ? html`<span class="count">${items.length}</span>` : null}</h3>
      ${items.length
        ? html`<${Needs} items=${items} go=${go} cap=${6} showSensitive=${showSensitive} />`
        : html`<p class="allquiet">${icon.check}<span>Nothing else under ${nexus.name || nexus.address} needs you.</span></p>`}
    </div>
  </section>`;
}

// Jump -----------------------------------------------------------------------------------

function Jump({ tree, go, close }) {
  const [query, setQuery] = useState("");
  const [at, setAt] = useState(0);
  const input = useRef(null);
  useEffect(() => input.current?.focus(), []);
  const all = useMemo(() => walk(tree).map((row) => row.node), [tree]);
  const needle = query.trim().toLowerCase();
  const hits = all
    .filter((node) => !needle || subsequence(needle, (node.name + " " + node.address).toLowerCase()))
    .sort((a, b) => (needle ? Number(!a.name.toLowerCase().startsWith(needle)) - Number(!b.name.toLowerCase().startsWith(needle)) : 0))
    .slice(0, 12);
  const pick = (node) => {
    if (!node) return;
    go(node.address);
    close();
  };
  const onKey = (event) => {
    if (event.key === "Escape") close();
    else if (event.key === "ArrowDown") { event.preventDefault(); setAt(Math.min(at + 1, hits.length - 1)); }
    else if (event.key === "ArrowUp") { event.preventDefault(); setAt(Math.max(at - 1, 0)); }
    else if (event.key === "Enter") pick(hits[at]);
  };
  return html`<div class="scrim" onClick=${close}>
    <div class="jump" role="dialog" aria-label="Jump to a chair" onClick=${(e) => e.stopPropagation()}>
      <div class="jump-input">${icon.search}<input ref=${input} value=${query} placeholder="Jump to a chair"
        onInput=${(e) => { setQuery(e.target.value); setAt(0); }} onKeyDown=${onKey} /></div>
      ${hits.length
        ? html`<ul>${hits.map((node, i) => html`<li key=${node.address} class=${i === at ? "on" : ""}
            onMouseEnter=${() => setAt(i)} onClick=${() => pick(node)}>
            <${Dot} state=${node.health.state} /><span>${node.name}</span><span class="addr">${node.address}</span></li>`)}</ul>`
        : html`<p class="none">No chair matches.</p>`}
    </div>
  </div>`;
}

// App --------------------------------------------------------------------------------------

const chairInUrl = () => new URLSearchParams(location.search).get("chair") || "";

function App() {
  const [chair, setChair] = useState(chairInUrl());
  const [snap, setSnap] = useState(null);
  const [error, setError] = useState(null);
  const [online, setOnline] = useState(true);
  const [checked, setChecked] = useState(0);
  const [showSensitive, setShowSensitive] = useState(store.get("envoy.showSensitive", false));
  const [collapsed, setCollapsed] = useState(() => new Set(store.get("envoy.collapsed", [])));
  const [jumping, setJumping] = useState(false);
  const [sideOpen, setSideOpen] = useState(false);
  const version = useRef("");

  useEffect(() => {
    let alive = true;
    let timer = 0;
    version.current = "";
    async function tick() {
      try {
        const query = new URLSearchParams();
        if (chair) query.set("chair", chair);
        if (version.current) query.set("since", version.current);
        const data = await fetch("/api/snapshot?" + query).then((res) => res.json());
        if (!alive) return;
        setOnline(true);
        setChecked(Date.now());
        if (data.ok === false) setError(data.error);
        else if (!data.unchanged) {
          version.current = data.version;
          setSnap(data);
          setError(null);
        }
      } catch {
        if (alive) setOnline(false);
      }
      if (alive) timer = setTimeout(tick, POLL_MS);
    }
    tick();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [chair]);

  useEffect(() => {
    const onPop = () => setChair(chairInUrl());
    addEventListener("popstate", onPop);
    return () => removeEventListener("popstate", onPop);
  }, []);

  const go = useCallback((address, { replace = false } = {}) => {
    if (!address) return;
    const url = new URL(location.href);
    url.searchParams.set("chair", address);
    history[replace ? "replaceState" : "pushState"]({}, "", url);
    setChair(address);
    setSideOpen(false);
  }, []);

  const toggle = useCallback((address) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      next.has(address) ? next.delete(address) : next.add(address);
      store.set("envoy.collapsed", [...next]);
      return next;
    });
  }, []);

  const [epoch, setEpoch] = useState(0);
  const [revealed, setRevealed] = useState(0);
  const track = useCallback((delta) => setRevealed((n) => n + delta), []);
  const reveals = useMemo(() => ({ epoch, track }), [epoch, track]);
  const sensitiveShowing = showSensitive || revealed > 0;

  // The eye hides everything if anything sensitive is showing, however it was opened.
  const toggleSensitive = useCallback(() => {
    if (sensitiveShowing) {
      setShowSensitive(false);
      store.set("envoy.showSensitive", false);
      setEpoch((n) => n + 1);
    } else {
      setShowSensitive(true);
      store.set("envoy.showSensitive", true);
    }
  }, [sensitiveShowing]);

  const selected = chair || snap?.chair || "";

  useEffect(() => {
    function onKey(event) {
      if (jumping || event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.target.closest?.("input, textarea, select")) return;
      if (!snap) return;
      const rows = visible(snap.tree, collapsed);
      const parents = new Map(walk(snap.tree).map((row) => [row.node.address, row.parent]));
      const kids = new Map(walk(snap.tree).map((row) => [row.node.address, row.node.children?.length || 0]));
      const at = rows.indexOf(selected);
      const key = event.key;
      if (key === "j" || key === "ArrowDown") go(rows[Math.min(at + 1, rows.length - 1)], { replace: true });
      else if (key === "k" || key === "ArrowUp") go(rows[Math.max(at - 1, 0)], { replace: true });
      else if (key === "l" || key === "ArrowRight") { if (collapsed.has(selected)) toggle(selected); }
      else if (key === "ArrowLeft") {
        if (kids.get(selected) && !collapsed.has(selected)) toggle(selected);
        else go(parents.get(selected));
      } else if (key === "h" || key === "Backspace") go(parents.get(selected));
      else if (key === "/") setJumping(true);
      else if (key === "s") toggleSensitive();
      else return;
      event.preventDefault();
    }
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [snap, collapsed, selected, jumping, go, toggle, toggleSensitive]);

  return html`<${Reveals.Provider} value=${reveals}><div class="shell">
    <${Header} snap=${snap} online=${online} checked=${checked} go=${go} showSensitive=${sensitiveShowing}
      toggleSensitive=${toggleSensitive} openJump=${() => setJumping(true)} toggleSide=${() => setSideOpen(!sideOpen)} />
    <${Side} snap=${snap} selected=${selected} collapsed=${collapsed} toggle=${toggle} go=${go} open=${sideOpen} />
    <main class="main">
      <div class="page">
        ${error ? html`<div class="gap">${error === "unknown_chair" ? "That chair is not in the tree." : error}</div>` : null}
        ${snap
          ? html`
            <div class="columns">
              <${ChairCard} key=${snap.chair} brief=${snap.briefing} go=${go} showSensitive=${showSensitive} />
              <${NexusCard} key=${snap.view} snap=${snap} go=${go} showSensitive=${showSensitive} />
            </div>`
          : html`<p class="quiet">Reading the bulletin…</p>`}
      </div>
    </main>
    ${jumping ? html`<${Jump} tree=${snap?.tree || []} go=${go} close=${() => setJumping(false)} />` : null}
  </div><//>`;
}

render(html`<${App} />`, document.getElementById("app"));
