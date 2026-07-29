import os
import re
import sqlite3

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, get_user_by_email, init_db, seed_db

app = Flask(__name__)

# Required for ``flask.session`` to sign cookies. Override in production
# by exporting ``SPENDLY_SECRET_KEY`` before the app boots; the literal
# below is a fixed dev fallback and must not be used in any deployed
# environment.
app.secret_key = os.environ.get("SPENDLY_SECRET_KEY", "dev-secret-change-me")

# Bootstrap the database before any route is served. ``init_db`` is
# idempotent (CREATE TABLE IF NOT EXISTS); ``seed_db`` is a no-op once
# the demo user exists, so it is safe to run on every startup.
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


# Loose ``*@*.*`` shape — fine for catching obvious typos without
# pretending to be a full RFC 5322 validator.
_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_MIN_PASSWORD_LEN = 8


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        # ``.get(key, "")`` so a missing field trips the "all required"
        # branch instead of raising ``KeyError`` and 500ing the user.
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return (
                render_template("register.html", error="All fields are required."),
                400,
            )
        if not _EMAIL_RE.fullmatch(email):
            return (
                render_template(
                    "register.html", error="Please enter a valid email address."
                ),
                400,
            )
        if len(password) < _MIN_PASSWORD_LEN:
            return (
                render_template(
                    "register.html",
                    error=f"Password must be at least {_MIN_PASSWORD_LEN} characters.",
                ),
                400,
            )

        # Hash before opening the connection: cheap to compute, keeps
        # the transaction window short on the only slow path.
        password_hash = generate_password_hash(password)

        conn = get_db()
        try:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO users (name, email, password_hash)
                    VALUES (?, ?, ?)
                    """,
                    (name, email, password_hash),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                # UNIQUE(email) violation — surface as a friendly error
                # rather than letting the constraint abort the request.
                conn.rollback()
                return (
                    render_template(
                        "register.html",
                        error="An account with that email already exists.",
                    ),
                    400,
                )
        finally:
            conn.close()

        # Sign the user in immediately and bounce to /profile.
        session["user_id"] = cur.lastrowid
        session["user_name"] = name
        return redirect(url_for("profile"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        # ``.get(key, "")`` so a missing field trips the credential
        # check below (which flashes a generic error) rather than
        # raising ``KeyError`` and 500ing the user. Email is stripped
        # to match the register flow and the stored value.
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Same single error for every failure mode so the form never
        # leaks whether the email exists or the password is wrong.
        row = get_user_by_email(email)
        if row is None or not check_password_hash(row["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html"), 200

        session["user_id"] = row["id"]
        session["user_name"] = row["name"]
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
    # Public per spec — no auth guard. Idempotent: clearing an empty
    # session is a no-op, so visiting /logout twice in a row is safe.
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Static/hardcoded per spec §04 — no DB queries in this step. Values
    # mirror database/db.py's SAMPLE_EXPENSES so the numbers already match
    # what Step 5's real queries will produce once wired up.
    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "initials": "DU",
        "member_since": "January 2026",
    }

    stats = [
        {"label": "Total spent", "value": "₹4,246.50", "icon": "wallet"},
        {"label": "Transactions", "value": "8", "icon": "receipt"},
        {"label": "Top category", "value": "Bills", "icon": "trophy"},
    ]

    transactions = [
        {"date": "14 Jul 2026", "description": "Miscellaneous cash spend", "category": "Other", "category_slug": "other", "amount": "₹120.00"},
        {"date": "13 Jul 2026", "description": "T-shirt from local market", "category": "Shopping", "category_slug": "shopping", "amount": "₹999.00"},
        {"date": "12 Jul 2026", "description": "Weekly groceries run", "category": "Bills", "category_slug": "bills", "amount": "₹612.00"},
        {"date": "11 Jul 2026", "description": "Auto rickshaw to client meeting", "category": "Transport", "category_slug": "transport", "amount": "₹85.50"},
        {"date": "10 Jul 2026", "description": "Lunch at the office canteen", "category": "Food", "category_slug": "food", "amount": "₹250.00"},
        {"date": "9 Jul 2026", "description": "Movie tickets", "category": "Entertainment", "category_slug": "entertainment", "amount": "₹350.00"},
        {"date": "8 Jul 2026", "description": "Pharmacy — vitamins and first-aid", "category": "Health", "category_slug": "health", "amount": "₹380.00"},
        {"date": "5 Jul 2026", "description": "Electricity bill", "category": "Bills", "category_slug": "bills", "amount": "₹1,450.00"},
    ]

    category_breakdown = [
        {"name": "Bills", "slug": "bills", "total": "₹2,062.00", "percent": 49, "bar_width_class": "profile-bar-w-50"},
        {"name": "Shopping", "slug": "shopping", "total": "₹999.00", "percent": 24, "bar_width_class": "profile-bar-w-25"},
        {"name": "Health", "slug": "health", "total": "₹380.00", "percent": 9, "bar_width_class": "profile-bar-w-10"},
        {"name": "Entertainment", "slug": "entertainment", "total": "₹350.00", "percent": 8, "bar_width_class": "profile-bar-w-10"},
        {"name": "Food", "slug": "food", "total": "₹250.00", "percent": 6, "bar_width_class": "profile-bar-w-5"},
        {"name": "Other", "slug": "other", "total": "₹120.00", "percent": 3, "bar_width_class": "profile-bar-w-5"},
        {"name": "Transport", "slug": "transport", "total": "₹85.50", "percent": 2, "bar_width_class": "profile-bar-w-5"},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        category_breakdown=category_breakdown,
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
