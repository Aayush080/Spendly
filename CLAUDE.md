# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Spendly is a Flask-based personal expense tracker being built incrementally as a teaching project. `app.py` and `database/db.py` contain step markers (e.g. "coming in Step 3", "Students will write this file in Step 1") — most backend logic (database layer, auth, CRUD for expenses) is intentionally unimplemented scaffolding, not a bug. When asked to "implement" one of these placeholder routes, treat the comment as the spec for what that step should deliver.

## Commands

```bash
# Run the dev server (Windows: use `python`, not `python3` — that resolves to a Store alias stub)
python app.py            # serves on http://127.0.0.1:5001, debug=True (auto-reload)

# Install deps
pip install -r requirements.txt

# Tests (pytest + pytest-flask are declared in requirements.txt; no test files exist yet)
pytest
```

There is no build step, linter, or frontend bundler — templates and CSS/JS are served directly by Flask via Jinja2 and `static/`.

## Architecture

- **`app.py`** — single-file Flask app. All routes live here (no blueprints). Implemented routes: `/` (landing), `/register`, `/login`, `/terms`, `/privacy`. Placeholder routes (`/logout`, `/profile`, `/expenses/add`, `/expenses/<int:id>/edit`, `/expenses/<int:id>/delete`) return plain strings and are stubs for future steps.
- **`database/db.py`** — intended home for `get_db()` (SQLite connection, row_factory + foreign keys enabled), `init_db()`, and `seed_db()`. Currently just comments; no DB is wired up yet, so `register.html`/`login.html` POST to routes that don't yet accept POST or persist data.
- **`templates/base.html`** — the shared layout (navbar + footer). Every page template extends this via `{% extends "base.html" %}` and fills `{% block title %}` / `{% block content %}`. Page-specific JS goes in `{% block scripts %}` (hooked at the bottom of `base.html`, after the shared `static/js/main.js` include) rather than in `main.js` itself — see `templates/landing.html`'s video-modal script for the pattern.
- **Footer links (Terms/Privacy) live in `base.html`, not in individual page templates** — since it's shared chrome, edit there, not per-page.
- **`static/css/style.css`** — the only stylesheet; there is no `landing.css` or per-page CSS. It's a single design system built on CSS custom properties (`--ink`, `--ink-soft`, `--paper`, `--paper-card`, `--accent`, `--accent-2`, `--border`, `--font-display` [DM Serif Display], `--font-body` [DM Sans], `--radius-sm/md/lg`, etc.). New UI work should reuse these tokens rather than introducing new ad-hoc colors/spacing.
- **`templates/terms.html` / `templates/privacy.html`** share a common `.legal-*` class set (`.legal-section`, `.legal-container`, `.legal-title`, `.legal-updated`) defined once in `style.css` — extend that shared block rather than adding page-specific legal CSS.

## Conventions specific to this repo

- Currency is displayed in ₹ (INR), e.g. `₹18,240` — keep this when adding any money-related UI.
- When asked to change "only the hero" (or any other named section) of `landing.html`, don't touch `features` or `cta-section` — these boundaries have been enforced strictly in past requests.
