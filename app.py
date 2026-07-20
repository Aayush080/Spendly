import sqlite3

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = "spendly-dev-secret-key"


@app.template_filter("inr")
def format_inr(value):
    return f"₹{value:,.0f}"


with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name:
            return render_template("register.html", error="Please enter your name.", name=name, email=email), 400
        if not email or "@" not in email:
            return render_template("register.html", error="Please enter a valid email address.", name=name, email=email), 400
        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters.", name=name, email=email), 400

        conn = get_db()
        try:
            existing = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                return render_template("register.html", error="An account with this email already exists.", name=name, email=email), 400

            password_hash = generate_password_hash(password)
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return render_template("register.html", error="An account with this email already exists.", name=name, email=email), 400
        finally:
            conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        try:
            user = conn.execute(
                "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
            ).fetchone()
        finally:
            conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.", email=email), 401

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "initials": "DU",
        "member_since": "July 2026",
    }

    stats = {
        "total_spent": 6869.00,
        "transaction_count": 8,
        "top_category": "Shopping",
    }

    transactions = [
        {"date": "2026-07-22", "description": "Miscellaneous",       "category": "Other",         "amount": 200.00},
        {"date": "2026-07-18", "description": "New running shoes",   "category": "Shopping",      "amount": 2400.00},
        {"date": "2026-07-14", "description": "Lunch with friends",  "category": "Food",          "amount": 150.00},
        {"date": "2026-07-12", "description": "Movie tickets",       "category": "Entertainment", "amount": 899.00},
        {"date": "2026-07-09", "description": "Pharmacy purchase",   "category": "Health",        "amount": 650.00},
    ]

    categories = [
        {"name": "Shopping",      "total": 2400.00, "percent": 100},
        {"name": "Bills",         "total": 1800.00, "percent": 75},
        {"name": "Entertainment", "total": 899.00,  "percent": 37},
        {"name": "Health",        "total": 650.00,  "percent": 27},
        {"name": "Food",          "total": 470.00,  "percent": 20},
        {"name": "Transport",     "total": 450.00,  "percent": 19},
        {"name": "Other",         "total": 200.00,  "percent": 8},
    ]

    return render_template(
        "profile.html",
        user=user, stats=stats, transactions=transactions, categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
