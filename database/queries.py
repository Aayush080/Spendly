from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    """Return {'name', 'email', 'member_since'} for user_id, or None if not found."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    member_since = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
    return {"name": row["name"], "email": row["email"], "member_since": member_since}


def get_summary_stats(user_id):
    """Return {'total_spent': float, 'transaction_count': int, 'top_category': str}.
    Zero-expense users get {'total_spent': 0, 'transaction_count': 0, 'top_category': '—'}.
    """
    conn = get_db()
    try:
        totals_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total_spent, COUNT(*) AS transaction_count "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        transaction_count = totals_row["transaction_count"]

        if transaction_count == 0:
            return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

        category_row = conn.execute(
            "SELECT category, SUM(amount) AS cat_total FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY cat_total DESC, category ASC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    return {
        "total_spent": float(totals_row["total_spent"]),
        "transaction_count": transaction_count,
        "top_category": category_row["category"],
    }


def get_recent_transactions(user_id, limit=10):
    """Return list of {'date', 'description', 'category', 'amount'}, newest-first."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": row["amount"],
        }
        for row in rows
    ]


def get_category_breakdown(user_id):
    """Return list of {'name', 'amount', 'pct'} ordered by amount desc.
    pct values are ints that sum to exactly 100; the largest category absorbs
    the rounding remainder. Empty list if the user has no expenses.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ? GROUP BY category ORDER BY total DESC, category ASC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    grand_total = sum(row["total"] for row in rows)
    result = [
        {
            "name": row["category"],
            "amount": row["total"],
            "pct": round(row["total"] / grand_total * 100),
        }
        for row in rows
    ]

    remainder = 100 - sum(item["pct"] for item in result)
    result[0]["pct"] += remainder

    return result
