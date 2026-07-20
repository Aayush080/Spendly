# Spec: Date Filter for Profile Page

## Overview
Step 6 adds a date-range filter to the profile page so a user can narrow
their transaction history, summary stats, and category breakdown to a
specific window (e.g. this month, a custom range) instead of always seeing
all-time totals. The filter is expressed as query parameters on the existing
`GET /profile` route — no new route is introduced. When no filter is
supplied, behavior is unchanged from Step 5 (all-time data, transaction list
capped at 10 rows).

## Depends on
- Step 1: Database setup (`expenses.date` column exists, stored as `YYYY-MM-DD`)
- Step 5: Backend connection (`database/queries.py` and the live `/profile`
  route already exist and this step extends them)

## Routes
- `GET /profile` — modified, not new — logged-in only
  - Accepts optional query params `start_date` and `end_date` (both
    `YYYY-MM-DD`, from `<input type="date">`)
  - Both present and valid: all three data sections (summary stats, recent
    transactions, category breakdown) are scoped to `date >= start_date AND
    date <= end_date`, inclusive, and the transaction list shows every
    matching row (not capped at 10)
  - Either param missing or empty: behaves exactly as Step 5 (all-time data,
    transaction list capped at 10)
  - `start_date` after `end_date`: ignore both and fall back to the
    all-time view; pass an `error` message to the template so the user
    knows the range was invalid
  - Malformed date strings (not parseable as `YYYY-MM-DD`): ignore both and
    fall back to the all-time view, same as an invalid range

## Database changes
No schema changes. `expenses.date` is already stored as an ISO `YYYY-MM-DD`
string, so range filtering is a plain string comparison.

## Templates
- **Modify**: `templates/profile.html`
  - Add a filter form (GET, so the range is bookmarkable/shareable) above
    the "Recent transactions" card: two `<input type="date">` fields
    (`start_date`, `end_date`), an "Apply" submit button, and a "Clear"
    link back to plain `/profile`
  - Pre-fill the two date inputs with the current `start_date`/`end_date`
    values so the form reflects the active filter after submit
  - If `error` is passed to the template, show it near the filter form
  - "Recent transactions" card title reflects whether a filter is active
    (e.g. "Recent transactions" vs "Transactions from {start_date} to
    {end_date}")

## Files to change
- `app.py` — in `profile()`: read `start_date`/`end_date` from
  `request.args`, validate them, and pass through to the three query
  functions; pass the (possibly empty) filter values and any `error` string
  to the template
- `database/queries.py`:
  - `get_summary_stats(user_id, start_date=None, end_date=None)`
  - `get_recent_transactions(user_id, limit=10, start_date=None, end_date=None)`
    — when either date is provided, ignore `limit` and return every matching
    row
  - `get_category_breakdown(user_id, start_date=None, end_date=None)`
  - Each function appends `AND date >= ? AND date <= ?` to its `WHERE`
    clause only when both dates are provided, using parameterised values
- `static/css/style.css` — add filter form styles (`.profile-filter`,
  `.profile-filter-error`, etc.) using existing CSS variables only

## Files to create
No new files.

## New dependencies
No new dependencies — plain HTML5 `<input type="date">`, no JS date-picker
library.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — `start_date`/`end_date` are always bound as
  `?` params, never string-formatted into SQL
- Passwords hashed with werkzeug (unaffected by this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles (the existing `style="width: {{ cat.percent }}%"` bar
  fill is pre-existing and out of scope — don't touch it)
- Currency must always display as ₹
- Date validation happens in `app.py`, not in `database/queries.py` — the
  query layer trusts that any dates it receives are valid `YYYY-MM-DD`
  strings or `None`
- A user with zero matching transactions in the selected range must see
  zeroed stats and an empty transaction list/category breakdown, not an
  error

## Definition of done
- [ ] Visiting `/profile` with no query params shows the same all-time data
      and 10-row cap as before this step
- [ ] Visiting `/profile?start_date=2026-07-01&end_date=2026-07-10` shows
      only transactions in that range, with summary stats and category
      breakdown recalculated to match
- [ ] The transaction list is not capped at 10 when a valid date filter is
      active, even if more than 10 transactions fall in the range
- [ ] Submitting `start_date` after `end_date` shows an inline error and
      falls back to the all-time view instead of crashing
- [ ] Submitting a malformed date falls back to the all-time view instead
      of crashing
- [ ] The date inputs are pre-filled with the active filter after
      submitting, so refreshing the page preserves the range
- [ ] The "Clear" link returns to the unfiltered all-time view
- [ ] Selecting a range with zero matching transactions shows ₹0 total
      spent, 0 transactions, and an empty category breakdown — no errors
- [ ] All amounts on the page continue to display the ₹ symbol
