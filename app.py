import os
import re
import sqlite3

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash

from database.db import get_db, init_db, seed_db

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

        # Sign the user in immediately and bounce to /profile. The
        # /profile route is still a Step 4 stub, so a successful
        # registration currently lands on its placeholder text — that
        # is the expected behaviour at this point in the roadmap.
        session["user_id"] = cur.lastrowid
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login")
def login():
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
    return "Logout — coming in Step 3"


@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


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
