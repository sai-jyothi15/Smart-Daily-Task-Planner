"""
database.py
-----------
This file handles everything related to talking to our SQLite database.

WHY A SEPARATE FILE?
Keeping all database code in one place (instead of scattering SQL queries
all over app.py) makes the project easier to read, debug, and explain.
Think of this file as the "librarian" - app.py asks it for data, and it
goes and fetches/stores things in the database.

SQLite is a serverless database - it's just a single file (tasks.db) that
sits in our project folder. No installation, no server to run. Perfect
for learning and small projects.
"""

import sqlite3
from datetime import datetime

DB_NAME = "tasks.db"


def get_connection():
    """
    Opens and returns a connection to our SQLite database file.

    row_factory = sqlite3.Row lets us access columns by NAME
    (like row["title"]) instead of just by index (like row[0]),
    which makes the rest of our code much more readable.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Creates the 'tasks' table if it doesn't already exist.
    This function is safe to run every time the app starts -
    'CREATE TABLE IF NOT EXISTS' won't wipe existing data.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT DEFAULT 'General',
            priority TEXT DEFAULT 'Medium',      -- High / Medium / Low
            deadline TEXT NOT NULL,              -- stored as 'YYYY-MM-DD HH:MM'
            status TEXT DEFAULT 'pending',       -- pending / completed
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("Database ready: tasks.db")


def dict_from_row(row):
    """Converts a sqlite3.Row object into a normal Python dictionary."""
    return dict(row) if row else None


# ---------------------------------------------------------------------
# CRUD FUNCTIONS (Create, Read, Update, Delete)
# Each function opens its own connection and closes it when done.
# This is simple and safe for a small app like this.
# ---------------------------------------------------------------------

def create_task(title, description, category, priority, deadline):
    """Insert a new task into the database. Returns the new task's id."""
    conn = get_connection()
    cursor = conn.cursor()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor.execute("""
        INSERT INTO tasks (title, description, category, priority, deadline, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (title, description, category, priority, deadline, created_at))

    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_all_tasks():
    """Fetch every task in the database, most recent deadline first isn't
    guaranteed here - we sort in the smart engine instead, where it matters."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY deadline ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


def get_task_by_id(task_id):
    """Fetch a single task by its id. Returns None if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict_from_row(row)


def update_task(task_id, title, description, category, priority, deadline):
    """Update the editable fields of an existing task."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks
        SET title = ?, description = ?, category = ?, priority = ?, deadline = ?
        WHERE id = ?
    """, (title, description, category, priority, deadline, task_id))
    conn.commit()
    conn.close()


def delete_task(task_id):
    """Permanently remove a task from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def mark_task_status(task_id, status):
    """
    Change a task's status to 'pending' or 'completed'.
    When marking completed, we also stamp completed_at with the current time
    so we can calculate on-time-completion stats later.
    """
    conn = get_connection()
    cursor = conn.cursor()

    if status == "completed":
        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute(
            "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
            (status, completed_at, task_id)
        )
    else:
        cursor.execute(
            "UPDATE tasks SET status = ?, completed_at = NULL WHERE id = ?",
            (status, task_id)
        )

    conn.commit()
    conn.close()
