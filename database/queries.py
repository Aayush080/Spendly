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


def get_summary_stats(user_id, start_date=None, end_date=None):
    """Return {'total_spent': float, 'transaction_count': int, 'top_category': str}.
    Zero-expense users (or zero matches in range) get
    {'total_spent': 0, 'transaction_count': 0, 'top_category': '—'}.
    """
    conn = get_db()
    try:
        where_clause = "WHERE user_id = ?"
        params = [user_id]
        if start_date and end_date:
            where_clause += " AND date >= ? AND date <= ?"
            params.extend([start_date, end_date])

        totals_row = conn.execute(
            f"SELECT COALESCE(SUM(amount), 0) AS total_spent, COUNT(*) AS transaction_count "
            f"FROM expenses {where_clause}",
            params,
        ).fetchone()

        transaction_count = totals_row["transaction_count"]

        if transaction_count == 0:
            return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

        category_row = conn.execute(
            f"SELECT category, SUM(amount) AS cat_total FROM expenses {where_clause} "
            f"GROUP BY category ORDER BY cat_total DESC, category ASC LIMIT 1",
            params,
        ).fetchone()
    finally:
        conn.close()

    return {
        "total_spent": float(totals_row["total_spent"]),
        "transaction_count": transaction_count,
        "top_category": category_row["category"],
    }


def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    """Return list of {'date', 'description', 'category', 'amount'}, newest-first.
    When start_date and end_date are both provided, `limit` is ignored and every
    matching row is returned.
    """
    conn = get_db()
    try:
        where_clause = "WHERE user_id = ?"
        params = [user_id]
        filtered = bool(start_date and end_date)
        if filtered:
            where_clause += " AND date >= ? AND date <= ?"
            params.extend([start_date, end_date])

        sql = f"SELECT date, description, category, amount FROM expenses {where_clause} ORDER BY date DESC, id DESC"
        if not filtered:
            sql += " LIMIT ?"
            params.append(limit)

        rows = conn.execute(sql, params).fetchall()
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


def get_category_breakdown(user_id, start_date=None, end_date=None):
    """Return list of {'name', 'amount', 'pct'} ordered by amount desc.
    pct values are ints that sum to exactly 100; the largest category absorbs
    the rounding remainder. Empty list if there are no matching expenses.
    """
    conn = get_db()
    try:
        where_clause = "WHERE user_id = ?"
        params = [user_id]
        if start_date and end_date:
            where_clause += " AND date >= ? AND date <= ?"
            params.extend([start_date, end_date])

        rows = conn.execute(
            f"SELECT category, SUM(amount) AS total FROM expenses {where_clause} "
            f"GROUP BY category ORDER BY total DESC, category ASC",
            params,
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
