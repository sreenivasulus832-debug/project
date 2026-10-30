"""
database.py
Helper functions to manage SQLite database connections, schema setup, and queries.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

# Path to the SQLite database file in the same directory
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voting_system.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def get_db():
    """
    Opens a connection to the SQLite database.
    Sets row_factory to sqlite3.Row so query results can be accessed by column name.
    Enables foreign keys in SQLite.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(seed_data=True):
    """
    Initializes the database using schema.sql and optionally adds sample data.
    """
    conn = get_db()
    with open(SCHEMA_PATH, mode="r", encoding="utf-8") as schema_file:
        conn.cursor().executescript(schema_file.read())
    conn.commit()

    if seed_data:
        seed_sample_data(conn)

    conn.close()
    print(f"[OK] Database successfully initialized at: {DB_PATH}")


def seed_sample_data(conn):
    """
    Populates sample admin, voters, polls, and candidates for demonstration.
    """
    cursor = conn.cursor()

    # 1. Sample Users (1 Admin, 2 Voters)
    # werkzeug generate_password_hash securely creates a salted cryptographic hash
    admin_hash = generate_password_hash("admin123")
    voter1_hash = generate_password_hash("voter123")
    voter2_hash = generate_password_hash("voter123")

    users_data = [
        ("System Administrator", "ADMIN001", admin_hash, "admin"),
        ("Alice Johnson", "STU1001", voter1_hash, "voter"),
        ("Bob Smith", "STU1002", voter2_hash, "voter")
    ]
    cursor.executemany(
        "INSERT INTO users (name, student_id, password_hash, role) VALUES (?, ?, ?, ?)",
        users_data
    )

    # 2. Sample Polls
    polls_data = [
        ("Student Council President Election 2026", "2026-10-01 09:00:00", "2026-11-15 17:00:00", "active"),
        ("Campus Sports Representative Election", "2026-10-01 09:00:00", "2026-11-20 17:00:00", "active")
    ]
    cursor.executemany(
        "INSERT INTO polls (title, start_time, end_time, status) VALUES (?, ?, ?, ?)",
        polls_data
    )

    # 3. Sample Candidates for Poll 1 (Student Council)
    candidates_poll_1 = [
        ("Alex Rivera", "Focuses on campus sustainability, 24/7 study rooms, and student mental health initiatives.", 1),
        ("Maya Chen", "Advocates for improved campus Wi-Fi infrastructure, gym upgrades, and transparent club funding.", 1),
        ("Jordan Taylor", "Committed to expanding cafeteria food varieties and hosting inter-college cultural fests.", 1)
    ]
    cursor.executemany(
        "INSERT INTO candidates (name, description, poll_id) VALUES (?, ?, ?)",
        candidates_poll_1
    )

    # 4. Sample Candidates for Poll 2 (Sports Rep)
    candidates_poll_2 = [
        ("Marcus Vance", "Varsity basketball captain with a plan to introduce weekend intramural tournaments for all students.", 2),
        ("Elena Rostova", "Badminton club lead focusing on new fitness equipment and self-defense workshops.", 2)
    ]
    cursor.executemany(
        "INSERT INTO candidates (name, description, poll_id) VALUES (?, ?, ?)",
        candidates_poll_2
    )

    # 5. One sample vote from Alice (id=2) in Poll 1 for Candidate 1 to show live results immediately
    cursor.execute(
        "INSERT INTO votes (voter_id, candidate_id, poll_id) VALUES (?, ?, ?)",
        (2, 1, 1)
    )

    conn.commit()
    print("[OK] Sample demonstration accounts and polls loaded.")


if __name__ == "__main__":
    init_db()
