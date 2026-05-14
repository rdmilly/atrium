"""Public project pages — server-rendered tabbed HTML at /p/{slug}.

Mirrors the structural pattern of build.helixcode.app (Roadmap / Components / ADRs / Journal /
Questions tabs) but renders in the Atrium paper/ink/terracotta aesthetic. Every byte is
server-rendered from Atrium's database; client-side JS only handles tab switching and a few
small toggles.

PRIVACY MODEL
=============
A project is public only if `project.public = True`. Within a public project:
- Project name, glyph, phase, public_summary always render (curated)
- Decisions render only when `decision.public = True`
- Notes tagged `?question` render in the Questions tab only when `note.public = True`
- Tasks render counts/grouping but never titles (privacy posture: roadmap shape, not roadmap text)
- Journal renders the project.journal field truncated/cleaned (or empty if blank)
- Components, patterns, audience, etc. — placeholders for later expansion

The page never exposes internal vision text, raw notes, raw event log, atom refs, or anything
else not explicitly opted in.
"""
import json
from html import escape
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func

from .db import AsyncSessionLocal
from . import models

router = APIRouter()

TEMPLATE_LABELS = {
    "software": "Software",
    "growth": "Growth",
    "services": "Services",
    "investigation": "Investigation",
    "portfolio": "Portfolio",
}

PHASE_LABELS = {
    "active": "In active development",
    "specced": "Specced — build pending",
    "stable": "Stable — in production",
    "paused": "Paused",
    "shipped": "Shipped",
    "retired": "Retired",
}

STATUS_BUCKETS = ["today", "next", "blocked", "later", "done"]
STATUS_LABELS = {
    "today": "In progress now",
    "next": "Up next",
    "blocked": "Blocked",
    "later": "On the horizon",
    "done": "Completed",
}


PHASE_MILESTONES = [
    ("specced",  "Specced",   "PRD written, architecture decided, ready to build"),
    ("active",   "Building",  "Active development in progress"),
    ("stable",   "Stable",    "In production, supported, hardening only"),
    ("shipped",  "Shipped",   "Deployed and complete"),
]

PHASE_RANK = {"specced": 0, "active": 1, "stable": 2, "shipped": 3, "paused": 1, "retired": 4}


def _milestones_section(project):
    """Render the project's progression through lifecycle phases."""
    current_rank = PHASE_RANK.get(project.phase, 0)
    is_paused = project.phase == "paused"
    is_retired = project.phase == "retired"
    parts = []
    for i, (key, label, hint) in enumerate(PHASE_MILESTONES):
        rank = PHASE_RANK[key]
        if is_retired:
            state_class = "milestone-done" if rank <= 2 else "milestone-skip"
            state_label = "complete" if rank <= 2 else "RETIRED"
        elif is_paused and key == "active":
            state_class = "milestone-paused"
            state_label = "paused"
        elif rank < current_rank:
            state_class = "milestone-done"
            state_label = "complete"
        elif rank == current_rank:
            state_class = "milestone-current"
            state_label = "now"
        else:
            state_class = "milestone-future"
            state_label = "upcoming"
        parts.append(f"""
        <div class="milestone {state_class}">
            <div class="milestone-num">{i+1:02d}</div>
            <div class="milestone-body">
                <div class="milestone-head">
                    <h4 class="milestone-label">{escape(label)}</h4>
                    <span class="milestone-state">{escape(state_label)}</span>
                </div>
                <p class="milestone-hint">{escape(hint)}</p>
            </div>
        </div>
        """)
    return "".join(parts)


def _phase_section(buckets, glyph):
    """Render the roadmap as five status columns. Counts only — no task titles for privacy."""
    parts = []
    for s in STATUS_BUCKETS:
        count = buckets.get(s, 0)
        is_active = (s in ("today", "next")) and count > 0
        accent = f"color: {glyph};" if is_active and s == "today" else ""
        parts.append(f'''
        <div class="phase-card{' phase-card-active' if is_active else ''}">
            <div class="phase-num" style="{accent}">{count}</div>
            <div class="phase-name">{escape(STATUS_LABELS[s])}</div>
        </div>
        ''')
    return "".join(parts)


def _decisions_section(decisions):
    if not decisions:
        return '<p class="empty">No decisions are public yet for this project.</p>'
    parts = []
    for i, d in enumerate(decisions, 1):
        adr_id = f"ADR-{i:03d}"
        choice_html = f'<p class="adr-choice">→ {escape(d.choice)}</p>' if d.choice else ''
        reasoning_html = f'<p class="adr-reasoning">{escape(d.reasoning)}</p>' if d.reasoning else ''
        parts.append(f'''
        <article class="adr-card">
            <div class="adr-meta">
                <span class="adr-id">{adr_id}</span>
                <span class="adr-status adr-status-{escape(d.status)}">{escape(d.status)}</span>
            </div>
            <h3>{escape(d.question)}</h3>
            {choice_html}
            {reasoning_html}
        </article>
        ''')
    return "".join(parts)


def _questions_section(questions):
    if not questions:
        return '<p class="empty">No open questions are public yet.</p>'
    parts = []
    for q in questions:
        is_blocker = q.tag == "!blocked"
        icon = "!" if is_blocker else "?"
        klass = "q-icon-block" if is_blocker else "q-icon-open"
        parts.append(f'''
        <div class="q-row">
            <span class="q-icon {klass}">{icon}</span>
            <span class="q-body">{escape(q.body)}</span>
        </div>
        ''')
    return "".join(parts)


def _journal_section(project):
    if not (project.journal or "").strip():
        return '<p class="empty">Journal not yet published.</p>'
    # The journal is rendered as paragraphs split on blank lines.
    paragraphs = [p.strip() for p in project.journal.split("\n\n") if p.strip()]
    if not paragraphs:
        return '<p class="empty">Journal not yet published.</p>'
    parts = []
    for p in paragraphs:
        parts.append(f'<p class="journal-para">{escape(p)}</p>')
    updated = project.updated_at.strftime("%B %d, %Y") if project.updated_at else ""
    return f'''
    <article class="journal-entry">
        <div class="journal-meta">
            <span class="journal-date">Last updated · {escape(updated)}</span>
            <span class="journal-tag">build narrative</span>
        </div>
        {"".join(parts)}
    </article>
    '''


# Component groupings per template — dictates section order on the public page
COMPONENT_GROUPS = {
    "software": [
        ("service",     "Services",      "Long-running processes that handle requests"),
        ("module",      "Modules",       "Internal code units — the building blocks"),
        ("datastore",   "Datastores",    "Where state lives"),
        ("integration", "Integrations",  "External systems we depend on"),
        ("library",     "Libraries",     "Reusable code shared across projects"),
        ("frontend",    "Frontend",      "User-facing surfaces"),
        ("cli",         "CLI tools",     "Command-line entry points"),
    ],
    "growth": [
        ("persona",       "Personas",        "Who the project is for"),
        ("channel",       "Channels",        "Where reach happens"),
        ("funnel_stage",  "Funnel stages",   "Awareness through revenue"),
        ("content_type",  "Content types",   "What we publish, in what cadence"),
        ("metric",        "Metrics",         "What we measure weekly"),
    ],
    "services": [
        ("customer_segment", "Customer segments", "Who we serve"),
        ("service_offering", "Service offerings", "What we deliver"),
        ("tool",             "Tools",             "Software and equipment in use"),
        ("equipment",        "Equipment",         "Physical assets in the field"),
        ("territory",        "Territories",       "Where we operate"),
    ],
    "investigation": [
        ("source",   "Sources",   "Where information comes from"),
        ("location", "Locations", "Where the story takes place"),
        ("witness",  "Witnesses", "People with first-hand knowledge"),
        ("exhibit",  "Exhibits",  "Documents, recordings, artifacts"),
        ("theory",   "Theories",  "What we think happened"),
    ],
    "portfolio": [
        ("page",     "Pages",     "Site sections and entry points"),
        ("asset",    "Assets",    "Resume, one-pager, deliverables"),
        ("story",    "Stories",   "Case studies and narratives"),
        ("skill",    "Skills",    "What I can do"),
        ("audience", "Audience",  "Who this is for"),
    ],
}

STATUS_DOT = {
    "live": "#5B7C45",
    "partial": "#B07A2C",
    "planned": "#A89F93",
    "deprecated": "#7A726A",
}


def _component_card(c):
    """Render one component card. Location field gets a label per kind."""
    location_label = {
        "channel": "platform",
        "persona": "market",
        "source": "reliability",
        "witness": "role",
        "customer_segment": "size",
        "service_offering": "price",
        "page": "url",
        "asset": "format",
    }.get(c.kind, "location")

    location_html = ""
    if c.location:
        location_html = f'''<div class="comp-loc"><span class="comp-loc-label">{location_label}</span><span class="comp-loc-val">{escape(c.location)}</span></div>'''

    desc_html = f'<p class="comp-desc">{escape(c.description)}</p>' if c.description else ""
    dot_color = STATUS_DOT.get(c.status, STATUS_DOT["planned"])

    return f'''
    <article class="comp-item">
        <div class="comp-item-head">
            <span class="comp-dot" style="background: {dot_color};"></span>
            <h4 class="comp-name">{escape(c.name)}</h4>
            <span class="comp-status comp-status-{escape(c.status)}">{escape(c.status)}</span>
        </div>
        {desc_html}
        {location_html}
    </article>
    '''


def _components_section(project, components, decisions, public_questions, all_tasks_by_status):
    """Render components grouped by kind in template-defined order."""
    template_label = TEMPLATE_LABELS.get(project.template, project.template)
    groups = COMPONENT_GROUPS.get(project.template, COMPONENT_GROUPS["software"])

    if not components:
        # Fall back to summary stats when nothing has been catalogued yet
        return f'''
        <div class="components-grid">
            <div class="comp-card">
                <div class="comp-card-num">{len(decisions)}</div>
                <div class="comp-card-label">Decisions published</div>
            </div>
            <div class="comp-card">
                <div class="comp-card-num">{len(public_questions)}</div>
                <div class="comp-card-label">Open questions</div>
            </div>
            <div class="comp-card">
                <div class="comp-card-num">{sum(all_tasks_by_status.values())}</div>
                <div class="comp-card-label">Tasks tracked</div>
            </div>
            <div class="comp-card">
                <div class="comp-card-num">{project.progress}%</div>
                <div class="comp-card-label">Progress</div>
            </div>
        </div>
        <p class="section-hint">A {escape(template_label).lower()} project. Components haven\'t been catalogued yet — they\'ll appear here as they\'re added.</p>
        '''

    by_kind = {}
    for c in components:
        by_kind.setdefault(c.kind, []).append(c)

    parts = []
    for kind, label, hint in groups:
        items = by_kind.get(kind, [])
        if not items:
            continue
        cards = "".join(_component_card(c) for c in items)
        parts.append(f'''
        <div class="comp-group">
            <div class="comp-group-head">
                <h3 class="comp-group-title">{escape(label)}</h3>
                <span class="comp-group-count">{len(items)}</span>
            </div>
            <p class="comp-group-hint">{escape(hint)}</p>
            <div class="comp-list">{cards}</div>
        </div>
        ''')

    if not parts:
        # Components exist but none match the template's known kinds. Render flat.
        cards = "".join(_component_card(c) for c in components)
        return f'<div class="comp-list">{cards}</div>'

    return "".join(parts)


def _render_page(project, components, decisions, public_questions, task_counts):
    name = escape(project.name)
    summary = escape(project.public_summary or project.vision or "")
    phase = project.phase
    phase_label = PHASE_LABELS.get(phase, phase)
    template_label = TEMPLATE_LABELS.get(project.template, project.template)
    glyph = project.glyph_color or "#7A6F62"
    progress = project.progress
    updated = project.updated_at.strftime("%B %d, %Y") if project.updated_at else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{name} · Atrium</title>
  <meta name="description" content="{summary[:160]}" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,500;1,6..72,400&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&family=JetBrains+Mono:wght@400;500&family=Caveat:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --paper:#F4EFE5;--paper-deep:#EBE4D5;--surface:#FBF8F1;
      --ink:#1F1B16;--ink-2:#4A413A;--ink-3:#7A726A;--ink-4:#A89F93;
      --rule:#D9D2C5;--rule-soft:#E8E1D1;
      --terracotta:#B85C38;--terracotta-deep:#8C4326;--terracotta-wash:#F1DDCD;
      --sage:#5B7C45;--sage-wash:#DDE6CF;
      --amber:#B07A2C;--amber-wash:#EFD9B2;
    }}
    *{{box-sizing:border-box}} html,body{{margin:0;padding:0}}
    body{{background:var(--paper);color:var(--ink);font-family:'DM Sans',system-ui,sans-serif;font-size:16px;line-height:1.6;-webkit-font-smoothing:antialiased;letter-spacing:-0.005em}}
    body::before{{content:'';position:fixed;inset:0;pointer-events:none;background-image:radial-gradient(rgba(31,27,22,.025) 1px,transparent 1px);background-size:4px 4px;z-index:0}}
    .container{{max-width:920px;margin:0 auto;padding:48px 32px 96px;position:relative;z-index:1}}
    .breadcrumb{{font-family:'JetBrains Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-3);margin-bottom:32px}}
    .breadcrumb a{{color:var(--ink-3);text-decoration:none}}
    .breadcrumb a:hover{{color:var(--terracotta-deep)}}

    /* HEADER */
    header{{padding-bottom:28px;border-bottom:1px solid var(--rule);margin-bottom:8px}}
    .glyph-row{{display:flex;align-items:baseline;gap:14px;margin-bottom:14px;flex-wrap:wrap}}
    .glyph{{display:inline-block;width:14px;height:14px;border-radius:2px;flex-shrink:0;transform:translateY(2px)}}
    h1{{font-family:'Newsreader',Georgia,serif;font-size:56px;line-height:1.05;letter-spacing:-.02em;margin:0;flex:1;font-weight:400}}
    .phase-pill{{font-family:'JetBrains Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.08em;border:1px solid var(--sage);color:var(--sage);border-radius:999px;padding:5px 11px;font-weight:500}}
    .phase-pill.specced{{border-color:var(--amber);color:var(--amber)}}
    .phase-pill.stable,.phase-pill.shipped,.phase-pill.paused,.phase-pill.retired{{border-color:var(--ink-3);color:var(--ink-3)}}
    .summary{{font-family:'Newsreader',Georgia,serif;font-size:22px;line-height:1.45;color:var(--ink-2);margin-top:8px}}
    .meta-row{{display:flex;gap:18px;align-items:baseline;font-family:'JetBrains Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-3);margin-top:18px;flex-wrap:wrap}}
    .meta-row span:not(:last-child)::after{{content:'·';margin-left:18px;color:var(--ink-4)}}

    /* TABS */
    .tabs{{display:flex;gap:4px;border-bottom:1px solid var(--rule);margin-bottom:48px;overflow-x:auto;-webkit-overflow-scrolling:touch}}
    .tab{{font-family:'JetBrains Mono',monospace;font-size:12px;text-transform:uppercase;letter-spacing:.08em;background:transparent;border:none;color:var(--ink-3);cursor:pointer;padding:18px 16px;transition:color .15s;white-space:nowrap;border-bottom:2px solid transparent;margin-bottom:-1px;font-weight:500}}
    .tab:hover{{color:var(--ink)}}
    .tab.active{{color:var(--terracotta-deep);border-bottom-color:var(--terracotta)}}

    /* PANELS */
    .panel{{display:none;animation:fadeIn .2s ease-out}}
    .panel.active{{display:block}}
    @keyframes fadeIn{{from{{opacity:0;transform:translateY(4px)}}to{{opacity:1;transform:none}}}}
    section{{margin-bottom:48px}}
    h2{{font-family:'JetBrains Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-3);font-weight:500;padding-bottom:10px;border-bottom:1px solid var(--rule-soft);margin-bottom:22px}}
    .empty{{font-style:italic;color:var(--ink-3);font-family:'Newsreader',Georgia,serif;font-size:17px;padding:32px 0}}
    .section-hint{{font-style:italic;color:var(--ink-3);font-size:14px;font-family:'Newsreader',Georgia,serif;margin-top:24px}}

    /* ROADMAP TAB */
    .roadmap-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:36px}}
    .phase-card{{padding:22px 18px;background:var(--surface);border:1px solid var(--rule-soft);border-radius:4px;text-align:center}}
    .phase-card-active{{border-color:var(--terracotta);background:var(--terracotta-wash)}}
    .phase-num{{font-family:'Newsreader',Georgia,serif;font-size:42px;line-height:1;color:var(--ink);font-weight:400}}
    .phase-name{{font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-3);margin-top:8px}}
    .progress-track{{height:6px;background:var(--rule-soft);position:relative;border-radius:3px;overflow:hidden;margin-top:24px}}
    .progress-fill{{position:absolute;inset:0 auto 0 0;border-radius:3px}}
    .progress-label{{display:flex;justify-content:space-between;align-items:baseline;margin-top:14px;font-family:'JetBrains Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-3)}}
    .progress-pct{{font-family:'Newsreader',Georgia,serif;font-size:22px;color:var(--ink);font-weight:400;letter-spacing:0;text-transform:none}}

    /* MILESTONES (lifecycle) */
    .milestones{{display:flex;flex-direction:column;gap:10px;margin-bottom:20px}}
    .milestone{{display:grid;grid-template-columns:48px 1fr;gap:18px;padding:18px 22px;background:var(--surface);border:1px solid var(--rule-soft);border-radius:4px}}
    .milestone-num{{font-family:'Newsreader',Georgia,serif;font-size:24px;line-height:1;color:var(--ink-4);font-weight:400;align-self:center}}
    .milestone-body{{flex:1}}
    .milestone-head{{display:flex;align-items:baseline;gap:12px;margin-bottom:4px}}
    .milestone-label{{font-family:'Newsreader',Georgia,serif;font-size:20px;font-weight:500;margin:0;color:var(--ink);letter-spacing:-.005em}}
    .milestone-state{{font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.08em;padding:2px 9px;border-radius:999px}}
    .milestone-hint{{font-family:'Newsreader',Georgia,serif;font-style:italic;color:var(--ink-3);font-size:14px;margin:0}}
    .milestone-done{{opacity:.55}}
    .milestone-done .milestone-state{{background:var(--sage-wash);color:#2F4824}}
    .milestone-done .milestone-label{{text-decoration:line-through;text-decoration-color:var(--ink-4);text-decoration-thickness:1px}}
    .milestone-current{{border-color:var(--terracotta);background:var(--terracotta-wash)}}
    .milestone-current .milestone-num{{color:var(--terracotta-deep)}}
    .milestone-current .milestone-state{{background:var(--terracotta);color:#fff}}
    .milestone-future{{opacity:.7}}
    .milestone-future .milestone-state{{background:var(--paper-deep);color:var(--ink-3)}}
    .milestone-paused{{border-color:var(--amber)}}
    .milestone-paused .milestone-state{{background:var(--amber-wash);color:#6E4D1A}}
    .milestone-skip{{opacity:.3}}
    .milestone-skip .milestone-state{{background:transparent;color:var(--ink-4);border:1px solid var(--rule)}}

    /* COMPONENTS TAB — fallback summary cards */
    .components-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}}
    .comp-card{{padding:28px 24px;background:var(--surface);border:1px solid var(--rule-soft);border-radius:4px}}
    .comp-card-num{{font-family:'Newsreader',Georgia,serif;font-size:36px;line-height:1;color:var(--ink);font-weight:400}}
    .comp-card-label{{font-family:'JetBrains Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-3);margin-top:10px}}
    /* COMPONENTS TAB — grouped by kind */
    .comp-group{{margin-bottom:42px}}
    .comp-group-head{{display:flex;align-items:baseline;gap:10px;padding-bottom:8px;border-bottom:1px solid var(--rule-soft);margin-bottom:6px}}
    .comp-group-title{{font-family:'Newsreader',Georgia,serif;font-size:24px;font-weight:500;margin:0;letter-spacing:-.005em}}
    .comp-group-count{{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--ink-4);text-transform:uppercase;letter-spacing:.08em}}
    .comp-group-hint{{font-family:'Newsreader',Georgia,serif;font-style:italic;color:var(--ink-3);font-size:15px;margin:0 0 18px}}
    .comp-list{{display:grid;gap:14px}}
    .comp-item{{padding:18px 20px;background:var(--surface);border:1px solid var(--rule-soft);border-radius:4px}}
    .comp-item-head{{display:flex;align-items:baseline;gap:10px;margin-bottom:6px}}
    .comp-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0;transform:translateY(1px)}}
    .comp-name{{font-family:'Newsreader',Georgia,serif;font-size:19px;font-weight:500;margin:0;flex:1;letter-spacing:-.005em}}
    .comp-status{{font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.08em;padding:2px 9px;border-radius:999px;background:var(--paper-deep);color:var(--ink-2)}}
    .comp-status-live{{background:var(--sage-wash);color:#2F4824}}
    .comp-status-partial{{background:var(--amber-wash);color:#6E4D1A}}
    .comp-status-planned{{background:var(--paper-deep);color:var(--ink-3)}}
    .comp-status-deprecated{{background:transparent;color:var(--ink-4);border:1px solid var(--rule)}}
    .comp-desc{{font-size:14px;color:var(--ink-2);line-height:1.55;margin:6px 0 8px}}
    .comp-loc{{display:flex;gap:8px;align-items:baseline;font-family:'JetBrains Mono',monospace;font-size:11px}}
    .comp-loc-label{{color:var(--ink-4);text-transform:uppercase;letter-spacing:.06em;min-width:64px}}
    .comp-loc-val{{color:var(--ink-2);word-break:break-all}}

    /* ADRS TAB */
    .adr-card{{padding:24px 0;border-bottom:1px solid var(--rule-soft)}}
    .adr-card:last-child{{border-bottom:none}}
    .adr-meta{{display:flex;gap:10px;align-items:baseline;margin-bottom:10px}}
    .adr-id{{font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--terracotta-deep);font-weight:500}}
    .adr-status{{font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.08em;padding:2px 9px;border-radius:999px;background:var(--paper-deep);color:var(--ink-2)}}
    .adr-status-resolved{{background:var(--sage-wash);color:#2F4824}}
    .adr-status-revisit{{background:var(--amber-wash);color:#6E4D1A}}
    .adr-card h3{{font-family:'Newsreader',Georgia,serif;font-size:24px;line-height:1.25;margin:4px 0 12px;font-weight:500;letter-spacing:-0.005em}}
    .adr-choice{{font-size:15px;color:var(--ink);margin:0 0 8px}}
    .adr-reasoning{{font-size:14px;color:var(--ink-2);font-style:italic;line-height:1.6;margin:0;font-family:'Newsreader',Georgia,serif;font-size:16px}}

    /* JOURNAL TAB */
    .journal-entry{{padding:8px 0}}
    .journal-meta{{display:flex;gap:12px;align-items:baseline;margin-bottom:18px;font-family:'JetBrains Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-3)}}
    .journal-tag{{padding:2px 9px;border-radius:999px;background:var(--terracotta-wash);color:var(--terracotta-deep)}}
    .journal-para{{font-family:'Newsreader',Georgia,serif;font-size:18px;line-height:1.65;color:var(--ink);margin:0 0 18px;font-style:italic}}

    /* QUESTIONS TAB */
    .q-row{{display:grid;grid-template-columns:32px 1fr;gap:14px;align-items:baseline;padding:14px 0;border-bottom:1px solid var(--rule-soft)}}
    .q-row:last-child{{border-bottom:none}}
    .q-icon{{font-family:'Newsreader',Georgia,serif;font-size:24px;line-height:1;text-align:center;width:32px;height:32px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-weight:500}}
    .q-icon-open{{background:var(--paper-deep);color:var(--ink-3)}}
    .q-icon-block{{background:var(--terracotta-wash);color:var(--terracotta-deep)}}
    .q-body{{font-family:'Newsreader',Georgia,serif;font-size:18px;line-height:1.45;color:var(--ink);font-weight:400}}

    /* FOOTER */
    footer{{margin-top:64px;padding-top:24px;border-top:1px solid var(--rule);font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-4);display:flex;justify-content:space-between;align-items:baseline}}
    footer a{{color:var(--ink-3);text-decoration:none}}
    footer a:hover{{color:var(--terracotta-deep)}}

    @media (max-width:680px){{
      h1{{font-size:40px}}
      .roadmap-grid{{grid-template-columns:repeat(2,1fr)}}
      .components-grid{{grid-template-columns:1fr}}
      .summary{{font-size:18px}}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="breadcrumb"><a href="/p">Atrium</a> · {escape(template_label)} project</div>

    <header>
      <div class="glyph-row">
        <span class="glyph" style="background: {glyph};"></span>
        <h1>{name}</h1>
        <span class="phase-pill {escape(phase)}">{escape(phase)}</span>
      </div>
      <p class="summary">{summary}</p>
      <div class="meta-row">
        <span>{escape(phase_label)}</span>
        <span>{progress}% complete</span>
        <span>updated {escape(updated)}</span>
      </div>
    </header>

    <nav class="tabs" role="tablist">
      <button class="tab active" data-tab="roadmap">Roadmap</button>
      <button class="tab" data-tab="components">Components</button>
      <button class="tab" data-tab="adrs">ADRs</button>
      <button class="tab" data-tab="journal">Journal</button>
      <button class="tab" data-tab="questions">Questions</button>
    </nav>

    <div class="panel active" data-panel="roadmap">
      <section>
        <h2>Lifecycle</h2>
        <div class="milestones">{_milestones_section(project)}</div>
      </section>
      <section>
        <h2>Overall progress</h2>
        <div class="progress-label">
          <span>build progress</span>
          <span class="progress-pct">{progress}%</span>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width: {progress}%; background: {glyph};"></div></div>
      </section>
      <section>
        <h2>Current work</h2>
        <div class="roadmap-grid">{_phase_section(task_counts, glyph)}</div>
      </section>
    </div>

    <div class="panel" data-panel="components">
      <section>
        <h2>Project at a glance</h2>
        {_components_section(project, components, decisions, public_questions, task_counts)}
      </section>
    </div>

    <div class="panel" data-panel="adrs">
      <section>
        <h2>Architecture decisions · the build narrative</h2>
        {_decisions_section(decisions)}
      </section>
    </div>

    <div class="panel" data-panel="journal">
      <section>
        <h2>Build journal</h2>
        {_journal_section(project)}
      </section>
    </div>

    <div class="panel" data-panel="questions">
      <section>
        <h2>Open questions</h2>
        {_questions_section(public_questions)}
      </section>
    </div>

    <footer>
      <span>Atrium · {escape(template_label).lower()} project page</span>
      <a href="/p">view all projects →</a>
    </footer>
  </div>

  <script>
    document.querySelectorAll('.tab').forEach(t => {{
      t.addEventListener('click', () => {{
        document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
        t.classList.add('active');
        document.querySelector(`.panel[data-panel="${{t.dataset.tab}}"]`).classList.add('active');
      }});
    }});
  </script>
</body>
</html>"""


@router.get("/p/{slug}", response_class=HTMLResponse)
async def public_project_page(slug: str):
    async with AsyncSessionLocal() as db:
        project = (await db.execute(
            select(models.Project).where(models.Project.slug == slug)
        )).scalar_one_or_none()
        if not project:
            raise HTTPException(404, "project not found")
        if not project.public:
            raise HTTPException(404, "project not public")

        decisions = (await db.execute(
            select(models.Decision)
            .where(models.Decision.project_id == project.id)
            .where(models.Decision.public == True)
            .order_by(models.Decision.created_at.asc())
        )).scalars().all()

        questions = (await db.execute(
            select(models.Note)
            .where(models.Note.target_type == "project")
            .where(models.Note.target_id == project.id)
            .where(models.Note.tag.in_(["?question", "!blocked"]))
            .where(models.Note.public == True)
            .where(models.Note.status == "open")
            .order_by(models.Note.created_at.desc())
        )).scalars().all()

        task_counts_rows = (await db.execute(
            select(models.Task.status, func.count(models.Task.id))
            .where(models.Task.project_id == project.id)
            .group_by(models.Task.status)
        )).all()
        task_counts = {row[0]: row[1] for row in task_counts_rows}

        components = (await db.execute(
            select(models.Component)
            .where(models.Component.project_id == project.id)
            .where(models.Component.public == True)
            .order_by(models.Component.position, models.Component.created_at)
        )).scalars().all()

        return HTMLResponse(_render_page(project, components, decisions, questions, task_counts))


@router.get("/p", response_class=HTMLResponse)
async def public_index():
    """Index of all public projects."""
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(models.Project)
            .where(models.Project.public == True)
            .order_by(models.Project.position, models.Project.name)
        )).scalars().all()

        cards = "".join(
            f'''
            <a href="/p/{escape(p.slug)}" class="card">
                <div class="card-glyph-row">
                    <span class="card-glyph" style="background: {p.glyph_color};"></span>
                    <h3>{escape(p.name)}</h3>
                </div>
                <p class="card-summary">{escape((p.public_summary or p.vision or '')[:160])}</p>
                <div class="card-meta">{escape(TEMPLATE_LABELS.get(p.template, p.template))} · {escape(PHASE_LABELS.get(p.phase, p.phase))} · {p.progress}%</div>
            </a>
            ''' for p in rows
        )
        if not rows:
            cards = '<p class="empty">No public projects yet.</p>'

        return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Projects · Atrium</title>
<link rel="preconnect" href="https://fonts.googleapis.com" /><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,500&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet" />
<style>
*{{box-sizing:border-box}} html,body{{margin:0;background:#F4EFE5;color:#1F1B16;font-family:'DM Sans',system-ui,sans-serif}}
.container{{max-width:880px;margin:0 auto;padding:64px 32px}}
h1{{font-family:'Newsreader',Georgia,serif;font-size:48px;margin:0 0 8px;letter-spacing:-.02em;font-weight:400}}
.subtitle{{font-family:'JetBrains Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#7A726A;margin-bottom:56px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
.card{{display:block;padding:28px;background:#FBF8F1;border:1px solid #D9D2C5;text-decoration:none;color:inherit;transition:border-color .15s,transform .15s}}
.card:hover{{border-color:#B85C38;transform:translateY(-1px)}}
.card-glyph-row{{display:flex;align-items:baseline;gap:10px;margin-bottom:10px}}
.card-glyph{{width:10px;height:10px;border-radius:2px;flex-shrink:0;transform:translateY(1px)}}
.card h3{{font-family:'Newsreader',Georgia,serif;font-size:26px;margin:0;font-weight:500;letter-spacing:-.01em}}
.card-summary{{font-size:14px;color:#4A413A;line-height:1.5;margin:0 0 14px;min-height:44px}}
.card-meta{{font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#7A726A}}
.empty{{font-style:italic;color:#7A726A;font-family:'Newsreader',Georgia,serif;font-size:18px}}
@media (max-width:720px){{ .grid{{grid-template-columns:1fr}} h1{{font-size:36px}} }}
</style></head><body>
<div class="container">
<h1>Projects</h1>
<div class="subtitle">Atrium · public project pages</div>
<div class="grid">{cards}</div>
</div></body></html>""")
