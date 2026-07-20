import re

from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


def test_get_user_by_id_valid(seeded_user_id):
    result = get_user_by_id(seeded_user_id)
    assert result["name"] == "Demo User"
    assert result["email"] == "demo@spendly.com"
    assert re.fullmatch(r"[A-Z][a-z]+ \d{4}", result["member_since"])


def test_get_user_by_id_missing():
    assert get_user_by_id(999999) is None


def test_get_summary_stats_with_expenses(seeded_user_id):
    stats = get_summary_stats(seeded_user_id)
    assert stats["total_spent"] == 6869.00
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Shopping"


def test_get_summary_stats_no_expenses(empty_user_id):
    assert get_summary_stats(empty_user_id) == {
        "total_spent": 0, "transaction_count": 0, "top_category": "—",
    }


def test_get_recent_transactions_ordering(seeded_user_id):
    txns = get_recent_transactions(seeded_user_id)
    dates = [t["date"] for t in txns]
    assert dates == sorted(dates, reverse=True)
    assert set(txns[0].keys()) == {"date", "description", "category", "amount"}


def test_get_recent_transactions_empty(empty_user_id):
    assert get_recent_transactions(empty_user_id) == []


def test_get_category_breakdown_percentages(seeded_user_id):
    cats = get_category_breakdown(seeded_user_id)
    assert len(cats) == 7
    totals = [c["amount"] for c in cats]
    assert totals == sorted(totals, reverse=True)
    assert sum(c["pct"] for c in cats) == 100
    assert all(isinstance(c["pct"], int) for c in cats)


def test_get_category_breakdown_empty(empty_user_id):
    assert get_category_breakdown(empty_user_id) == []


def test_profile_redirects_when_unauthenticated(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_authenticated(auth_client):
    resp = auth_client.get("/profile")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body
    assert "Shopping" in body
