# User Registration

## Overview

Implement account creation so `POST /register` persists a real user instead of the form submitting into a stub route. This turns `templates/register.html` (already built) into a working signup flow: validate input, hash the password, insert into `users`, and hand the visitor off to `/login` to sign in with their new credentials.

Session/login itself is a separate step — this spec only covers creating the account, not establishing a logged-in session.

## Dependencies

- [[01-database-setup]] — `get_db()`, `init_db()`, and the `users` table must already exist and be working.

## Routes to Implement

### `POST /register` (extend existing `/register` view in `app.py`)

- Current view only handles `GET` (renders `register.html`). Add `methods=["GET", "POST"]` and branch on `request.method`.
- On `POST`:
    - Read `name`, `email`, `password` from `request.form`.
    - Validate:
        - `name` non-empty (after `.strip()`).
        - `email` non-empty and contains `@`.
        - `password` at least 8 characters (matches the placeholder text already in `register.html`: "Min. 8 characters").
        - If validation fails, re-render `register.html` with `error` set and the submitted `name`/`email` preserved in the form (`HTTP 400`).
    - Normalize email with `.strip().lower()` before checking/storing.
    - Check for an existing user with that email (`SELECT 1 FROM users WHERE email = ?`).
        - If found, re-render `register.html` with `error="An account with this email already exists."` (`HTTP 400`).
    - Hash the password with `werkzeug.security.generate_password_hash`.
    - Insert the new row into `users` (`name`, `email`, `password_hash`); let `created_at` use its DB default.
    - Wrap the existence-check + insert in a `try/except sqlite3.IntegrityError` as a second line of defense against a race on the `UNIQUE` email constraint, and treat it the same as the duplicate-email case above.
    - On success, redirect (`302`) to `url_for("login")`. Do **not** log the user in automatically — that belongs to the login step.

## Database Changes

None. Reuses the existing `users` table from [[01-database-setup]] as-is (`id`, `name`, `email`, `password_hash`, `created_at`).

## Templates to Create / Modify

- `templates/register.html` — no structural changes needed; it already posts to `/register` and renders `{{ error }}` via `.auth-error`. Only change: re-populate `value="{{ name or '' }}"` / `value="{{ email or '' }}"` on the `name`/`email` inputs so a failed submission doesn't clear what the user typed.

## Files Modified

- `app.py` — `register()` view gains `POST` handling, imports `request`, `redirect`, `url_for` from `flask`, and `generate_password_hash` from `werkzeug.security`; imports `sqlite3` for the `IntegrityError` guard.
- `templates/register.html` — repopulate `name`/`email` field values after a failed submit.

## New Files Created

- None.

## New Dependencies

- None — `werkzeug.security` is already a transitive Flask dependency and is already used by `database/db.py`.

## Rules of Implementation

- Parameterized queries only — no string-formatted SQL (per [[01-database-setup]]).
- Never store or log a plaintext password; only `password_hash` goes in the DB.
- Always `.strip()` `name` and `.strip().lower()` `email` before validating, comparing, or storing.
- Reuse the existing `.auth-error` / `error` template pattern already present in `register.html` and `login.html` — don't invent a new error-display mechanism.
- Keep the route in `app.py`; this project uses no blueprints (per CLAUDE.md).
- Don't touch `login`, `logout`, or `profile` placeholder routes — out of scope for this step.
- Currency/UI conventions from CLAUDE.md don't apply here (no money values on this screen), but don't introduce new colors/spacing outside `static/css/style.css` tokens if the template needs adjustment.

## Acceptance Criteria (Definition of Done)

- [ ] `GET /register` still renders the form unchanged.
- [ ] Submitting valid `name`/`email`/`password` creates a row in `users` with a hashed password and redirects to `/login`.
- [ ] Submitting a duplicate email re-renders `register.html` with a clear error and does not create a second row.
- [ ] Submitting an empty name, invalid email, or password under 8 characters re-renders the form with an error and preserves the previously typed name/email.
- [ ] No plaintext password ever reaches the database or logs.
- [ ] All new queries are parameterized.
- [ ] Manual check: register a new account, confirm the row exists via `sqlite3 expense_tracker.db "SELECT id, name, email FROM users;"`, then log in isn't required to pass (login is a later step) — just confirm redirect to `/login` happens.
