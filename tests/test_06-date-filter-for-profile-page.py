"""
Tests for Step 6: date-range filter on the profile page.

Spec: .claude/specs/06-date-filter-for-profile-page.md

Scope:
- GET /profile accepts optional `start_date` / `end_date` query params
  (YYYY-MM-DD) and scopes summary stats, recent transactions, and category
  breakdown to that inclusive range.
- Missing/empty params, invalid ranges, and malformed dates must all fall
  back to the pre-existing all-time view (10-row transaction cap) instead
  of crashing.
- A valid range must show every matching transaction, uncapped.
- `database/queries.py`'s get_summary_stats / get_recent_transactions /
  get_category_breakdown all gain optional start_date/end_date kwargs that
  only filter when *both* are supplied.

These tests reuse the shared fixtures from tests/conftest.py:
  - `client`            plain (unauthenticated) Flask test client
  - `auth_client`        client logged in as the seeded demo user
  - `seeded_user_id`     id of the demo user (8 expenses, dates in 2026-07)
  - `empty_user_id`      id of a freshly created user with zero expenses

Known seed data (see database/db.py `seed_db`) for the demo user:
    2026-07-01  Food           320.00
    2026-07-02  Transport      450.00
    2026-07-05  Bills         1800.00
    2026-07-09  Health         650.00
    2026-07-12  Entertainment  899.00
    2026-07-14  Food           150.00
    2026-07-18  Shopping      2400.00
    2026-07-22  Other          200.00
All-time totals: ₹6,869 total spent, 8 transactions, top category "Shopping".
"""

import pytest

from database.db import get_db
from database.queries import (
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)

PROFILE_URL = "/profile"

# All-time figures for the seeded demo user, used as the "fallback" oracle
# whenever a filter should be ignored (missing, invalid range, malformed).
ALL_TIME_TOTAL_INR = "₹6,869"
ALL_TIME_COUNT = 8
ALL_TIME_TOP_CATEGORY = "Shopping"


# ------------------------------------------------------------------ #
# Local fixtures — a second user with > 10 expenses, all inside a    #
# single 5-day window, to exercise the "uncapped when filtered"      #
# behavior described in the spec.                                    #
# ------------------------------------------------------------------ #

@pytest.fixture
def many_expenses_user_id(empty_user_id):
    """A fresh user with 15 expenses dated 2026-08-01 .. 2026-08-05."""
    conn = get_db()
    rows = [
        (empty_user_id, 10.0 + i, "Food", f"2026-08-0{(i % 5) + 1}", f"Item {i}")
        for i in range(15)
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return empty_user_id


@pytest.fixture
def many_expenses_auth_client(client, many_expenses_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = many_expenses_user_id
        sess["user_name"] = "Empty User"
    return client


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #

class TestProfileFilterAuthGuard:
    def test_unauthenticated_request_with_filter_redirects_to_login(self, client):
        resp = client.get(PROFILE_URL, query_string={
            "start_date": "2026-07-01", "end_date": "2026-07-05",
        })
        assert resp.status_code == 302, "Unauthenticated filtered request should redirect"
        assert "/login" in resp.headers["Location"], "Should redirect to login"

    def test_unauthenticated_request_with_invalid_filter_still_redirects_to_login(self, client):
        resp = client.get(PROFILE_URL, query_string={
            "start_date": "not-a-date", "end_date": "2026-07-05",
        })
        assert resp.status_code == 302, "Auth guard must run before date validation"
        assert "/login" in resp.headers["Location"]


# ------------------------------------------------------------------ #
# No filter / missing / empty params -> unchanged Step 5 behavior     #
# ------------------------------------------------------------------ #

class TestProfileNoFilterFallback:
    def test_no_query_params_shows_all_time_data(self, auth_client):
        resp = auth_client.get(PROFILE_URL)
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert ALL_TIME_TOTAL_INR in body, "Expected all-time total spent"
        assert ALL_TIME_TOP_CATEGORY in body, "Expected all-time top category"
        assert "Recent transactions" in body, "Title should be the unfiltered heading"

    @pytest.mark.parametrize("params", [
        {"start_date": "", "end_date": ""},
        {"start_date": "2026-07-01", "end_date": ""},
        {"start_date": "", "end_date": "2026-07-05"},
        {"start_date": "   ", "end_date": "   "},
    ])
    def test_missing_or_empty_param_falls_back_to_all_time(self, auth_client, params):
        resp = auth_client.get(PROFILE_URL, query_string=params)
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert ALL_TIME_TOTAL_INR in body, (
            f"Params {params} should behave as if no filter was supplied"
        )
        assert "Recent transactions" in body

    def test_default_view_caps_transaction_list_at_ten_rows(self, many_expenses_auth_client):
        resp = many_expenses_auth_client.get(PROFILE_URL)
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        # one <tr> belongs to the table header; the rest are data rows
        row_count = body.count("<tr>") - 1
        assert row_count == 10, (
            f"Unfiltered transaction list should be capped at 10 rows, got {row_count} "
            "for a user with 15 total expenses"
        )


# ------------------------------------------------------------------ #
# Valid filter — happy path                                           #
# ------------------------------------------------------------------ #

class TestProfileValidFilter:
    def test_valid_range_scopes_summary_stats(self, auth_client):
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-07-01", "end_date": "2026-07-05",
        })
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        # Only 2026-07-01 (320), 2026-07-02 (450), 2026-07-05 (1800) match.
        assert "₹2,570" in body, "Total spent should be recalculated for the range"
        assert "Bills" in body, "Top category within the range should be Bills"

    def test_valid_range_changes_transaction_list_title(self, auth_client):
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-07-01", "end_date": "2026-07-05",
        })
        body = resp.get_data(as_text=True)
        assert "Transactions from 2026-07-01 to 2026-07-05" in body, (
            "Card title should reflect the active filter, per spec"
        )
        assert "Recent transactions" not in body, (
            "Unfiltered heading should not appear once a filter is active"
        )

    def test_valid_range_scopes_transaction_list_contents(self, auth_client):
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-07-01", "end_date": "2026-07-05",
        })
        body = resp.get_data(as_text=True)
        assert "Weekly groceries" in body
        assert "Fuel refill" in body
        assert "Electricity bill" in body
        # Out-of-range transactions must not leak into the list.
        assert "Movie tickets" not in body
        assert "New running shoes" not in body

    def test_valid_range_scopes_category_breakdown(self, auth_client):
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-07-01", "end_date": "2026-07-05",
        })
        body = resp.get_data(as_text=True)
        assert "Bills" in body
        assert "Transport" in body
        # "Shopping" only occurs from 2026-07-18, outside this range.
        assert "Shopping" not in body

    def test_boundary_dates_are_inclusive(self, auth_client):
        """A single-day range equal to both start and end must include that day."""
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-07-01", "end_date": "2026-07-01",
        })
        body = resp.get_data(as_text=True)
        assert "₹320" in body, "Inclusive single-day range should total just that day's expense"
        assert "Weekly groceries" in body
        assert "Fuel refill" not in body, "2026-07-02 must not be included"

    def test_valid_range_uncaps_transaction_list(self, many_expenses_auth_client):
        resp = many_expenses_auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-08-01", "end_date": "2026-08-05",
        })
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        row_count = body.count("<tr>") - 1
        assert row_count == 15, (
            f"All 15 matching rows should be shown when a valid filter is active, got {row_count}"
        )

    def test_valid_filter_prefills_date_inputs(self, auth_client):
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-07-01", "end_date": "2026-07-05",
        })
        body = resp.get_data(as_text=True)
        assert 'value="2026-07-01"' in body, "start_date input should be pre-filled"
        assert 'value="2026-07-05"' in body, "end_date input should be pre-filled"

    def test_filter_form_includes_a_link_back_to_plain_profile(self, auth_client):
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-07-01", "end_date": "2026-07-05",
        })
        body = resp.get_data(as_text=True)
        assert 'href="/profile"' in body, (
            "Spec requires a 'Clear' link back to plain /profile near the filter form"
        )

    def test_clearing_filter_returns_to_all_time_view(self, auth_client):
        """Simulates following the 'Clear' link: plain /profile is unfiltered."""
        auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-07-01", "end_date": "2026-07-05",
        })
        resp = auth_client.get(PROFILE_URL)
        body = resp.get_data(as_text=True)
        assert ALL_TIME_TOTAL_INR in body
        assert "Recent transactions" in body


# ------------------------------------------------------------------ #
# Invalid ranges / malformed input                                    #
# ------------------------------------------------------------------ #

class TestProfileFilterValidation:
    def test_start_after_end_falls_back_and_shows_error(self, auth_client):
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-07-20", "end_date": "2026-07-01",
        })
        assert resp.status_code == 200, "Invalid range must not crash the page"
        body = resp.get_data(as_text=True)
        assert ALL_TIME_TOTAL_INR in body, "Should fall back to all-time totals"
        assert ALL_TIME_TOP_CATEGORY in body
        assert "error" in body.lower() or "invalid" in body.lower(), (
            "Spec requires an inline error message when start_date is after end_date"
        )

    @pytest.mark.parametrize("start,end", [
        ("2026-13-40", "2026-07-05"),      # not a real calendar date
        ("not-a-date", "2026-07-05"),      # not parseable at all
        ("07/01/2026", "2026-07-05"),      # wrong format
        ("2026-07-01", "also-not-a-date"),
    ])
    def test_malformed_dates_fall_back_to_all_time_without_crashing(self, auth_client, start, end):
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": start, "end_date": end,
        })
        assert resp.status_code == 200, f"Malformed input {start!r}/{end!r} must not crash"
        body = resp.get_data(as_text=True)
        assert ALL_TIME_TOTAL_INR in body, "Should fall back to all-time totals"

    def test_sql_injection_attempt_in_date_param_is_handled_safely(self, auth_client):
        malicious = "2026-07-01'; DROP TABLE expenses; --"
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": malicious, "end_date": "2026-07-10",
        })
        assert resp.status_code == 200, "Malicious input must not crash the server"
        body = resp.get_data(as_text=True)
        assert ALL_TIME_TOTAL_INR in body, "Should fall back to all-time totals, not error"

        # The expenses table must still exist and be intact afterwards.
        conn = get_db()
        try:
            count = conn.execute("SELECT COUNT(*) AS c FROM expenses").fetchone()["c"]
        finally:
            conn.close()
        assert count == ALL_TIME_COUNT, "expenses table must be untouched by the injection attempt"

    def test_very_long_date_string_falls_back_without_crashing(self, auth_client):
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-07-01" + "9" * 5000, "end_date": "2026-07-10",
        })
        assert resp.status_code == 200, "Excessively long input must not crash the page"
        body = resp.get_data(as_text=True)
        assert ALL_TIME_TOTAL_INR in body


# ------------------------------------------------------------------ #
# Zero matching transactions in a valid range                         #
# ------------------------------------------------------------------ #

class TestProfileFilterZeroMatches:
    def test_valid_range_with_no_matches_shows_zeroed_stats(self, auth_client):
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-06-01", "end_date": "2026-06-05",
        })
        assert resp.status_code == 200, "Zero matches must render normally, not error"
        body = resp.get_data(as_text=True)
        assert "₹0" in body, "Total spent should be ₹0 for an empty range"
        assert ">0<" in body, "Transaction count should be 0"
        assert "—" in body, "Top category placeholder should be the em dash"

    def test_valid_range_with_no_matches_shows_empty_transaction_list(self, auth_client):
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-06-01", "end_date": "2026-06-05",
        })
        body = resp.get_data(as_text=True)
        for description in [
            "Weekly groceries", "Fuel refill", "Electricity bill",
            "Pharmacy purchase", "Movie tickets", "Lunch with friends",
            "New running shoes", "Miscellaneous",
        ]:
            assert description not in body, f"{description!r} should not appear for an empty range"

    def test_valid_range_with_no_matches_shows_empty_category_breakdown(self, auth_client):
        resp = auth_client.get(PROFILE_URL, query_string={
            "start_date": "2026-06-01", "end_date": "2026-06-05",
        })
        body = resp.get_data(as_text=True)
        for category in ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]:
            assert category not in body, f"Category {category!r} must not appear for an empty range"


# ------------------------------------------------------------------ #
# Currency formatting must never regress                              #
# ------------------------------------------------------------------ #

class TestProfileFilterCurrencyDisplay:
    @pytest.mark.parametrize("params", [
        {},
        {"start_date": "2026-07-01", "end_date": "2026-07-05"},
        {"start_date": "2026-07-20", "end_date": "2026-07-01"},  # invalid range
        {"start_date": "2026-06-01", "end_date": "2026-06-05"},  # zero matches
    ])
    def test_amounts_always_display_rupee_symbol(self, auth_client, params):
        resp = auth_client.get(PROFILE_URL, query_string=params)
        body = resp.get_data(as_text=True)
        assert "₹" in body, f"Currency symbol missing for params {params}"


# ------------------------------------------------------------------ #
# database/queries.py — direct unit tests for the new kwargs           #
# (behavior explicitly specified in the spec's "Files to change"       #
# section, independent of how app.py wires them up)                    #
# ------------------------------------------------------------------ #

class TestGetSummaryStatsDateFilter:
    def test_filters_to_range(self, seeded_user_id):
        stats = get_summary_stats(seeded_user_id, start_date="2026-07-01", end_date="2026-07-05")
        assert stats["total_spent"] == 2570.0
        assert stats["transaction_count"] == 3
        assert stats["top_category"] == "Bills"

    def test_zero_matches_in_range_returns_zeroed_dict(self, seeded_user_id):
        stats = get_summary_stats(seeded_user_id, start_date="2026-06-01", end_date="2026-06-05")
        assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    def test_only_one_date_supplied_is_not_filtered(self, seeded_user_id):
        with_only_start = get_summary_stats(seeded_user_id, start_date="2026-07-01")
        all_time = get_summary_stats(seeded_user_id)
        assert with_only_start == all_time, "Filtering requires both dates to be present"


class TestGetRecentTransactionsDateFilter:
    def test_filters_to_range_and_orders_newest_first(self, seeded_user_id):
        txns = get_recent_transactions(seeded_user_id, start_date="2026-07-01", end_date="2026-07-05")
        dates = [t["date"] for t in txns]
        assert dates == ["2026-07-05", "2026-07-02", "2026-07-01"]

    def test_zero_matches_returns_empty_list(self, seeded_user_id):
        assert get_recent_transactions(seeded_user_id, start_date="2026-06-01", end_date="2026-06-05") == []

    def test_limit_is_ignored_once_both_dates_are_present(self, many_expenses_user_id):
        txns = get_recent_transactions(
            many_expenses_user_id, limit=10, start_date="2026-08-01", end_date="2026-08-05",
        )
        assert len(txns) == 15, "limit must be ignored when a date range is supplied"

    def test_limit_still_applies_when_only_one_date_supplied(self, many_expenses_user_id):
        txns = get_recent_transactions(many_expenses_user_id, limit=10, start_date="2026-08-01")
        assert len(txns) == 10, "A single date param must not trigger range filtering or uncapping"


class TestGetCategoryBreakdownDateFilter:
    def test_filters_to_range(self, seeded_user_id):
        cats = get_category_breakdown(seeded_user_id, start_date="2026-07-01", end_date="2026-07-05")
        names = {c["name"] for c in cats}
        assert names == {"Bills", "Transport", "Food"}
        assert sum(c["pct"] for c in cats) == 100
        assert cats[0]["name"] == "Bills", "Largest category in range should be first"

    def test_zero_matches_returns_empty_list(self, seeded_user_id):
        assert get_category_breakdown(seeded_user_id, start_date="2026-06-01", end_date="2026-06-05") == []

    def test_only_one_date_supplied_is_not_filtered(self, seeded_user_id):
        with_only_end = get_category_breakdown(seeded_user_id, end_date="2026-07-05")
        all_time = get_category_breakdown(seeded_user_id)
        assert with_only_end == all_time
