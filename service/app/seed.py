"""Seed Atrium with Ryan's actual project portfolio.

Run after migrations:  python -m app.seed
"""
import asyncio
from sqlalchemy import select
from .db import AsyncSessionLocal
from . import models


PROJECTS = [
    # Active
    ("Helix Cortex", "Central intelligence platform — twenty MCP tools, unified write pipeline through helix_file_write, Forge atom store, observer event routing.", "#2A5D52", "active", 70, 0),
    ("MemBrain", "Chrome extension v0.5.2 — auto-injecting Tier 1 context on every claude.ai message. Free, paid, and self-hosted tiers.", "#6B5A8A", "active", 85, 1),
    ("Lead Pipeline", "MW Lead Pipeline — Oregon service contractors, currently blocked on Instantly billing. ~10K leads, 500+ emails.", "#B05E2C", "active", 92, 2),
    ("Content Pipeline", "MillyWeb content pipeline v2.1.0 — automated screen recording, per-conversation segment tracking, end-to-end script generation.", "#94704F", "active", 80, 3),
    ("Atrium", "Engineering command center — this. Shared canvas where Ryan and Claude operate on the same project state in real time.", "#BD5C2C", "active", 35, 4),
    ("AOS Investigations", "Adventures of Shanghai — investigative Pacific Northwest content. Anubis case in active research.", "#7A4870", "active", 60, 5),

    # Specced
    ("MillyGate", "Auth and session inheritance layer — currently specced, awaiting design pass on Helix integration.", "#A14A28", "specced", 25, 10),
    ("Shanghai Pipeline", "rclone + Whisper + Claude API classification for ~100 production + 500 raw videos on Google Drive.", "#9B5872", "specced", 30, 11),
    ("ClientFlow", "Client onboarding wizard — first 3 screens drafted, full flow specced.", "#4A6B8A", "specced", 18, 12),

    # Stable
    ("Provisioner", "MCP Provisioner — HOT/WARM/COLD pool, Infisical secret injection, self-healing. 45 servers, 697 tools.", "#3A6E70", "stable", 95, 20),
    ("MW Dev Site", "MW Development site v2.1 — primary marketing surface for the AI automation agency.", "#5C7858", "stable", 100, 21),
    ("helixcode.app", "Live build playground at helixcode.app and build.helixcode.app — design system showcase.", "#486B58", "stable", 100, 22),

    # Paused
    ("Confidence Lighting", "Christmas light installation business — seasonal, ~60-70 families in Yamhill County. Paused until November.", "#8A6B3D", "paused", 60, 30),
    ("Postiz", "Social posting tool — awaiting OAuth setup before deploy.", "#707578", "paused", 50, 31),

    # Shipped
    ("Quiet Conviction", "Personal portfolio at ryanmilly.com — Newsreader/Playfair/Caveat, terracotta accent, three assets.", "#7A6F62", "shipped", 100, 40),

    # Retired
    ("Memory ContextEngine", "Predecessor to Helix Cortex. Retired March 4, 2026. Volumes preserved.", "#A89F93", "retired", 100, 50),
]


SEED_DECISIONS = [
    ("Helix Cortex", "KG storage backend — Postgres vs Neo4j vs SQLite", "Postgres", "Neo4j was overkill for the access patterns; SQLite locks at scale; Postgres has the foreign-key story we want."),
    ("Helix Cortex", "Observer retention window", "30 hot, 90 warm", "Hot needed for active work, warm for retro analysis, archive after."),
    ("Lead Pipeline", "Primary place source — Foursquare vs Azure Maps", "Azure Maps", "Foursquare auth keeps failing; Azure free tier is solid and 5K/month is plenty for our cycle."),
    ("Atrium", "Atrium standalone vs Forge-coupled", "Standalone, Forge gated", "Atrium ships without depending on Forge being healthy. Forge integration is a feature flag."),
    ("MemBrain", "Auto-inject Tier 1 context on every claude.ai message", "Yes, default on", "The latency cost is small, the context win is large, opt-out is one click in settings."),
]


SEED_NOTES = [
    ("project", "Helix Cortex", "@claude", "check if observer event router conflicts with old dispatcher — possible double-fire on scan events"),
    ("project", "Helix Cortex", "?question", "does helix_kb_index need to be idempotent? saw a duplicate row in test run"),
    ("project", "Helix Cortex", "@me", "document the workspace_write deprecation in handoff before next session"),
    ("project", "MemBrain", "@claude", "verify v0.5.2 ships with the intercept fix from yesterday"),
    ("project", "Lead Pipeline", "!blocked", "Instantly billing — workspace needs paid Growth plan before API access is restored"),
]


SEED_TASKS = [
    ("Helix Cortex", "Finish observer event router · verify atom-scan hook still fires", "today", "~30m"),
    ("Helix Cortex", "KG entity dedup pass · 2,184 → expect ~1,800", "today", "~45m"),
    ("Helix Cortex", "Add helix_session_export tool to MCP", "next", "~40m"),
    ("Helix Cortex", "Update handoff.md · close 11d gap", "today", "~15m"),
    ("Helix Cortex", "Migrate SQLite → Postgres for KG storage", "next", "~3h"),
    ("Lead Pipeline", "Fix Instantly billing → unblock email send", "blocked", "external"),
    ("MemBrain", "CWS packaging item 7 — final extension review", "today", "~1h"),
    ("Atrium", "Phase 1 deploy to atrium.millyweb.com", "today", "~2h"),
    ("Atrium", "Notes loop end-to-end with auto-resolve", "next", "~1.5h"),
    ("Atrium", "World board with all four tabs", "next", "~3h"),
]


SEED_PATTERNS = [
    ("unified_write_pipeline", "Single entry point for any file write — Forge versioning, atom scan, KB index, KG entity extraction, observer emission, all in one call.", "promoted", 4),
    ("forge_versioning", "Every file write produces a versioned object in MinIO with a date stamp. Time-travel for any tracked file is a query against bucket history.", "promoted", 3),
    ("cortex_act_recall", "Pre-message context injection — every Claude message gets pre-matched patterns, decisions, and entities relevant to the topic.", "promoted", 2),
    ("infisical_secret_inject", "Pull secrets from Infisical at container boot, never store keys in code or env files. Standard portfolio-wide.", "promoted", 10),
    ("healthcheck_watchdog", "Cron-driven liveness probe that detects dead long-running processes and restarts them. Logs every action.", "candidate", 3),
    ("boot_config_validate", "Validate config at startup, fail loud with structured error, surface to UI when applicable.", "candidate", 3),
]


async def seed():
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(models.Project).limit(1))).scalar_one_or_none()
        if existing:
            print("already seeded; skipping")
            return

        print("seeding projects...")
        proj_map = {}
        for name, vision, glyph, phase, progress, position in PROJECTS:
            p = models.Project(name=name, vision=vision, glyph_color=glyph, phase=phase, progress=progress, position=position)
            db.add(p)
            await db.flush()
            proj_map[name] = p.id

        print("seeding decisions...")
        for proj, q, choice, reasoning in SEED_DECISIONS:
            db.add(models.Decision(project_id=proj_map[proj], question=q, choice=choice, reasoning=reasoning, status="resolved"))

        print("seeding notes...")
        for ttype, tname, tag, body in SEED_NOTES:
            db.add(models.Note(target_type=ttype, target_id=proj_map[tname], body=body, tag=tag))

        print("seeding tasks...")
        for proj, title, status, effort in SEED_TASKS:
            db.add(models.Task(project_id=proj_map[proj], title=title, status=status, effort=effort))

        print("seeding patterns...")
        for name, desc, status, count in SEED_PATTERNS:
            db.add(models.Pattern(name=name, description=desc, status=status, candidate_count=count))

        # focus on Helix Cortex by default
        db.add(models.Focus(id=1, current_project_id=proj_map["Helix Cortex"]))

        await db.commit()
        print(f"seeded {len(PROJECTS)} projects, {len(SEED_DECISIONS)} decisions, {len(SEED_NOTES)} notes, {len(SEED_TASKS)} tasks, {len(SEED_PATTERNS)} patterns")


if __name__ == "__main__":
    asyncio.run(seed())
