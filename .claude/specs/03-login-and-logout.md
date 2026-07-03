# Spec: Login and Logout

## Overview

Implement session-based authentication so `POST /login` verifies a user's credentials and establishes a logged-in session, and `GET /logout` tears that session down. This turns `templates/login.html` (already built, currently `GET`-only) into a working sign-in flow, and replaces the `/logout` stub with a real session clear. It also makes the shared navbar in `base.html` aware of whether a visitor is signed in, since that's the only place nav chrome lives. This is the last piece of the auth flow started by [[02-registration]] — accounts can now actually be used, not just created.

## Depends on

- [[01-database-setup]] — `get_db()` and the `users` table (`id`, `name`, `email`, `password_hash`).
- [[02-registration]] — `POST /register` must already create rows with hashed passwords to log into.

## Routes

- `POST /login` (extend existing `/login` view in `app.py`) — verify credentials and start a session — public
- `GET /login` (existing, unchanged) — render the sign-in form — public
- `GET /logout` (replace stub in `app.py`) — clear the session and redirect to `/login` — logged-in (safe to hit while logged out too; just redirects)

## Database changes

None. Reuses the existing `users` table as-is — only reads `id`, `name`, `password_hash` by `email`.

## Templates

**Create:** None.

**Modify:**
- `templates/login.html` — repopulate `value="{{ email or '' }}"` on the email input after a failed submit, matching the pattern already used in `register.html`.
- `templates/base.html` — nav links become conditional: when `session.user_id` is set, show a "Profile" link (`url_for('profile')`) and a "Log out" link (`url_for('logout')`) in place of the current "Sign in" / "Get started" links. Flask injects `session` into Jinja automatically, so no view changes are needed to make it visible in the template.

## Files to change

- `app.py`:
  - Set `app.secret_key` at module level (required for Flask sessions to sign the session cookie) — no secret key exists yet anywhere in the codebase.
  - Import `session` and `check_password_hash` (from `werkzeug.security`).
  - `login()` view gains `methods=["GET", "POST"]` and `POST` handling.
  - `logout()` view stops returning a placeholder string; clears the session and redirects to `/login`.
- `templates/login.html` — repopulate `email` value after a failed submit.
- `templates/base.html` — conditional nav based on `session.user_id`.

## Files to create

None.

## New dependencies

No new dependencies — `check_password_hash` and `session` are already part of Flask/Werkzeug, both already installed.

## Rules for implementation

- No SQLAlchemy or ORMs.
- Parameterised queries only — `SELECT id, name, password_hash FROM users WHERE email = ?`, never string-formatted SQL.
- Passwords hashed with werkzeug — compare with `check_password_hash(user["password_hash"], password)`; never compare plaintext.
- Use CSS variables — never hardcode hex values (only relevant if the nav markup needs new styling; reuse existing `.nav-links` / `nav-cta` classes where possible).
- All templates extend `base.html`.
- On `POST /login`:
  - Read `email`, `password` from `request.form`; normalize email with `.strip().lower()`.
  - Look up the user by email. If no user matches, or `check_password_hash` fails, re-render `login.html` with a single generic error (`"Invalid email or password."`, `HTTP 401`) — never reveal whether the email exists.
  - On success, store `session["user_id"]` and `session["user_name"]`, then redirect (`302`) to `url_for("profile")`.
- On `GET /logout`: call `session.clear()`, then redirect (`302`) to `url_for("login")`. No error if the visitor wasn't logged in.
- Don't add a `login_required` decorator or protect `/profile`/`/expenses/*` routes in this step — those stubs are owned by later steps (Step 4+); this spec only establishes and tears down the session.
- Don't touch `register` — out of scope for this step.
- Keep both routes in `app.py`; this project uses no blueprints (per CLAUDE.md).

## Definition of done

- [ ] `GET /login` still renders the form unchanged when not logged in.
- [ ] Submitting the seeded demo credentials (`demo@spendly.com` / `demo123`) logs in successfully and redirects to `/profile`.
- [ ] Submitting a correct email with the wrong password re-renders `login.html` with "Invalid email or password." and preserves the typed email.
- [ ] Submitting an email that doesn't exist re-renders the same generic error (no "user not found" leak).
- [ ] After a successful login, the navbar (any page) shows "Profile" and "Log out" instead of "Sign in" / "Get started".
- [ ] Visiting `/logout` after logging in clears the session, redirects to `/login`, and the navbar reverts to "Sign in" / "Get started" on the next page load.
- [ ] Visiting `/logout` while already logged out doesn't error — it just redirects to `/login`.
- [ ] No plaintext password is ever compared or logged.
- [ ] All new queries are parameterized.
