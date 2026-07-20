# Test Writer Notes — Spendly

## Test infra / conftest (tests/conftest.py) — already exists, reuse it
- `database/db.py`'s `get_db()` has **no config seam** — it always connects to
  a fixed `DB_PATH` (a real file on disk, `expense_tracker.db` at repo root).
  There is no `app.config["DATABASE"]` hook, so the generic "DATABASE:
  ':memory:'" fixture pattern from generic Flask advice does NOT apply here.
- `tests/conftest.py` solves isolation by monkeypatching
  `database.db.DB_PATH` to a `tempfile.mkstemp()` path **before** importing
  `app` (must happen at module import time, before `from app import app`).
- conftest.py already provides these fixtures for every test file under
  `tests/` (do not redefine them, just take them as params):
  - `client` — plain `flask_app.test_client()`, `TESTING=True`
  - `seeded_user_id` — id of the demo user seeded by `seed_db()` (email
    `demo@spendly.com`, password `demo123`)
  - `empty_user_id` — freshly inserted user with zero expenses (email
    `empty@spendly.com`)
  - `auth_client` — `client` with session pre-populated
    (`sess["user_id"]`, `sess["user_name"]`) for `seeded_user_id` — bypasses
    the login route entirely via `client.session_transaction()`
  - autouse `_reset_db` — deletes all rows from `expenses`/`users`, then
    re-runs `init_db()` + `seed_db()` before every test (full isolation,
    no shared state)
- To create your own logged-in user with custom data: build a local fixture
  that depends on `empty_user_id`, inserts rows via `get_db()` +
  parameterized SQL, then a second fixture that does the
  `client.session_transaction()` dance (see `many_expenses_auth_client` in
  `test_06-date-filter-for-profile-page.py` for the pattern).

## Seed data (database/db.py `seed_db()`) — demo user, 8 expenses, all July 2026
```
2026-07-01  Food           320.00   "Weekly groceries"
2026-07-02  Transport      450.00   "Fuel refill"
2026-07-05  Bills         1800.00   "Electricity bill"
2026-07-09  Health         650.00   "Pharmacy purchase"
2026-07-12  Entertainment  899.00   "Movie tickets"
2026-07-14  Food           150.00   "Lunch with friends"
2026-07-18  Shopping      2400.00   "New running shoes"
2026-07-22  Other          200.00   "Miscellaneous"
```
All-time: total ₹6,869, count 8, top_category "Shopping".
Handy sub-range: 2026-07-01..2026-07-05 → rows 1,2,3 above → total ₹2,570,
count 3, top_category "Bills" (used across date-filter tests).

## Currency filter
`app.py` registers `@app.template_filter("inr")`:
`f"₹{value:,.0f}"` — no decimals, comma thousands separator, e.g. `₹6,869`,
`₹320`, `₹0`. Any money assertion should match this exact format.

## Routes / auth
- `/profile` — GET only, redirects 302 to `/login` if `session["user_id"]`
  missing. Accepts `start_date`/`end_date` query params (Step 6, date
  filter) — see `.claude/specs/06-date-filter-for-profile-page.md`.
- `/register`, `/login` — implemented, POST-based, session-cookie auth.
- `/logout` clears session, redirects to `/login`.
- `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete` — still
  plain-string stubs as of Step 6, not testable yet.

## Files covering which features (avoid duplicate coverage)
- `tests/test_backend_connection.py` — Step 5 coverage: `get_user_by_id`,
  unfiltered `get_summary_stats`/`get_recent_transactions`/
  `get_category_breakdown`, basic `/profile` auth-guard + authenticated
  render (no date-filter params touched here).
- `tests/test_06-date-filter-for-profile-page.py` — Step 6 coverage: all
  `start_date`/`end_date` query-param behavior on `/profile` (happy path,
  validation/invalid-range/malformed-date fallback, zero-match range,
  uncapped list when filtered, 10-row cap when unfiltered, pre-fill,
  currency-symbol regression, SQL-injection/long-input safety) **plus**
  direct unit tests of the new `start_date=None, end_date=None` kwargs on
  the three `database/queries.py` functions (filtering only triggers when
  *both* dates are supplied — confirmed straight from the spec text, not
  from reading the implementation).

## Template landmarks worth knowing (profile.html)
- Card title toggles between literal strings `"Recent transactions"` and
  `"Transactions from {start_date} to {end_date}"` based on whether a
  filter is active — this exact wording comes straight from the spec, safe
  to assert on directly.
- Transaction rows are plain `<tr>` in a `<table class="profile-table">`;
  counting `body.count("<tr>") - 1` (minus the one header row) is a cheap,
  template-structure-only way to check the 10-row cap / uncapped-when-filtered
  behavior without depending on more specific classes.
- `base.html` navbar always renders one `href="/profile"` (Profile nav
  link) regardless of filter state — don't use raw href-count comparisons
  to prove a "Clear filter" link is conditionally rendered; that's an
  implementation detail (the real template happens to wrap the Clear link
  in `{% if filter_active %}`, but the spec text doesn't mandate that it be
  conditional). Prefer testing the *behavior* the spec actually promises:
  visiting plain `/profile` (what Clear points to) shows the all-time view.
- Zero/empty stat values render as `>0<` (transaction count) and `₹0`
  (total) and `—` (top_category placeholder) — useful literal substrings
  for zero-match-range assertions.
- Exact wording of the inline validation error (start>end / malformed
  date) is NOT specified by the spec — only that "an error message" must
  appear. Assert loosely (`"error" in body.lower() or "invalid" in
  body.lower()`) rather than a literal string, since the actual copy is an
  implementation choice.

## Gotchas
- Windows: use `python`, not `python3`.
- Don't assume `app.config["DATABASE"]` exists — always check
  `database/db.py` for the actual connection seam before writing DB-isolation
  fixtures for a new feature area.
