"""Seed a single random Indian user into the Spendly database.

Generates a realistic Indian first + last name across regions, derives
a unique email, and inserts the user with a werkzeug-hashed password.
"""

import os
import random
import sqlite3
import sys
from datetime import datetime

from werkzeug.security import generate_password_hash

# Re-use the project's DB helper to honor FK enforcement and row factory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.db import DB_PATH, get_db  # noqa: E402

# Realistic Indian first + last names spanning North, South, East, West.
# Drawn from common usage across regions — not exhaustive, but enough
# to produce believable combinations when paired randomly.
FIRST_NAMES = (
    # Male
    "Rahul", "Amit", "Vikram", "Arjun", "Rohan", "Aditya", "Karthik",
    "Rohit", "Suresh", "Pradeep", "Sandeep", "Manoj", "Rajesh", "Sanjay",
    "Nikhil", "Vivek", "Anand", "Deepak", "Mohan", "Prakash", "Ravi",
    "Suresh", "Venkat", "Arun", "Srinivas", "Ganesh", "Manoj", "Pavan",
    # Female
    "Priya", "Anjali", "Pooja", "Sneha", "Divya", "Neha", "Kavita",
    "Sunita", "Anita", "Meera", "Lakshmi", "Deepa", "Rekha", "Shalini",
    "Geeta", "Asha", "Nandini", "Sushma", "Pallavi", "Ananya",
)
LAST_NAMES = (
    "Sharma", "Verma", "Patel", "Gupta", "Iyer", "Reddy", "Nair",
    "Kumar", "Singh", "Mukherjee", "Banerjee", "Chatterjee", "Das",
    "Joshi", "Kulkarni", "Deshpande", "Bhatt", "Mehta", "Shah",
    "Kapoor", "Khanna", "Chopra", "Bhat", "Rao", "Menon", "Pillai",
    "Subramanian", "Krishnan", "Mishra", "Pandey", "Tiwari", "Saxena",
)

DOMAINS = ("gmail.com", "yahoo.com", "outlook.com", "hotmail.com")


def generate_user() -> tuple[str, str]:
    """Return (name, email) for a fresh random Indian user."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    name = f"{first} {last}"
    suffix = random.randint(10, 999)
    # Lowercase + dot-separated local part, like rahul.sharma91@gmail.com
    local = f"{first.lower()}.{last.lower()}"
    email = f"{local}{suffix}@{random.choice(DOMAINS)}"
    return name, email


def email_exists(conn: sqlite3.Connection, email: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM users WHERE email = ? LIMIT 1", (email,)
    ).fetchone()
    return row is not None


def main() -> None:
    conn = get_db()
    try:
        # Regenerate until the email is unique in the users table.
        for _ in range(50):
            name, email = generate_user()
            if not email_exists(conn, email):
                break
        else:
            raise RuntimeError("Could not generate a unique email after 50 attempts")

        password_hash = generate_password_hash("password123")
        created_at = datetime.now().isoformat(sep=" ", timespec="seconds")

        cursor = conn.execute(
            """
            INSERT INTO users (name, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, email, password_hash, created_at),
        )
        conn.commit()
        user_id = cursor.lastrowid

        print(f"id:    {user_id}")
        print(f"name:  {name}")
        print(f"email: {email}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
