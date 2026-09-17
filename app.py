"""
app.py
------
This is the MAIN entry point of our Flask application.

It does two jobs:
  1. Serves the single HTML page (the dashboard UI).
  2. Provides a small REST API (JSON endpoints) that our JavaScript
     (static/js/script.js) calls using fetch() to add/edit/delete/complete
     tasks and load statistics - WITHOUT reloading the page.

HOW TO EXPLAIN THIS IN AN INTERVIEW:
"It's a Flask backend with SQLite storage. The frontend is plain
JavaScript that calls my Flask API endpoints with fetch() and updates
the page dynamically - similar to how a React app would talk to a
backend, just without a frontend framework."
"""

from flask import Flask, render_template, request, jsonify
import database as db
import smart_engine as se

app = Flask(__name__)

# Create the database table (if it doesn't exist yet) as soon as the app starts
db.init_db()


# -----------------------------------------------------------------------
# PAGE ROUTE - serves the main HTML page
# -----------------------------------------------------------------------

@app.route("/")
def index():
    """Renders the single-page dashboard. All dynamic data is loaded
    afterwards by JavaScript via the API routes below."""
    return render_template("index.html")


# -----------------------------------------------------------------------
# TASK API ROUTES (CRUD = Create, Read, Update, Delete)
# -----------------------------------------------------------------------

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    """
    Returns all tasks as JSON, optionally filtered by status/priority/category
    using query parameters, e.g. /api/tasks?status=pending
    Each task also gets a 'score' and 'overdue' flag attached by the smart engine.
    """
    tasks = db.get_all_tasks()
    tasks = se.rank_tasks(tasks)  # adds score + overdue flag, sorts by urgency

    status = request.args.get("status")
    priority = request.args.get("priority")
    category = request.args.get("category")

    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if priority:
        tasks = [t for t in tasks if t["priority"] == priority]
    if category:
        tasks = [t for t in tasks if t["category"] == category]

    return jsonify({"success": True, "tasks": tasks})


@app.route("/api/tasks", methods=["POST"])
def add_task():
    """Creates a new task from JSON sent by the frontend form."""
    data = request.get_json()

    title = (data.get("title") or "").strip()
    deadline = (data.get("deadline") or "").strip()

    # Basic server-side validation - never trust the frontend alone
    if not title:
        return jsonify({"success": False, "message": "Title is required"}), 400
    if not deadline:
        return jsonify({"success": False, "message": "Deadline is required"}), 400

    task_id = db.create_task(
        title=title,
        description=data.get("description", ""),
        category=data.get("category") or "General",
        priority=data.get("priority") or "Medium",
        deadline=deadline
    )

    new_task = db.get_task_by_id(task_id)
    return jsonify({"success": True, "task": new_task}), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def edit_task(task_id):
    """Updates an existing task's details."""
    existing = db.get_task_by_id(task_id)
    if not existing:
        return jsonify({"success": False, "message": "Task not found"}), 404

    data = request.get_json()
    title = (data.get("title") or "").strip()
    deadline = (data.get("deadline") or "").strip()

    if not title:
        return jsonify({"success": False, "message": "Title is required"}), 400
    if not deadline:
        return jsonify({"success": False, "message": "Deadline is required"}), 400

    db.update_task(
        task_id=task_id,
        title=title,
        description=data.get("description", ""),
        category=data.get("category") or "General",
        priority=data.get("priority") or "Medium",
        deadline=deadline
    )

    updated_task = db.get_task_by_id(task_id)
    return jsonify({"success": True, "task": updated_task})


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def remove_task(task_id):
    """Deletes a task permanently."""
    existing = db.get_task_by_id(task_id)
    if not existing:
        return jsonify({"success": False, "message": "Task not found"}), 404

    db.delete_task(task_id)
    return jsonify({"success": True, "message": "Task deleted"})


@app.route("/api/tasks/<int:task_id>/toggle", methods=["PATCH"])
def toggle_task(task_id):
    """Flips a task between 'pending' and 'completed'."""
    existing = db.get_task_by_id(task_id)
    if not existing:
        return jsonify({"success": False, "message": "Task not found"}), 404

    new_status = "pending" if existing["status"] == "completed" else "completed"
    db.mark_task_status(task_id, new_status)

    updated_task = db.get_task_by_id(task_id)
    return jsonify({"success": True, "task": updated_task})


# -----------------------------------------------------------------------
# SMART FEATURE ROUTES
# -----------------------------------------------------------------------

@app.route("/api/suggestion", methods=["GET"])
def get_suggestion():
    """Returns the single best 'do this next' task suggestion."""
    tasks = db.get_all_tasks()
    suggestion = se.suggest_next_task(tasks)
    return jsonify({"success": True, "suggestion": suggestion})


@app.route("/api/overload", methods=["GET"])
def get_overload():
    """Returns any upcoming dates that have too many tasks stacked up."""
    tasks = db.get_all_tasks()
    overloaded_days = se.detect_overload(tasks)
    return jsonify({"success": True, "overloaded_days": overloaded_days})


# -----------------------------------------------------------------------
# STATS / DASHBOARD ROUTES
# -----------------------------------------------------------------------

@app.route("/api/stats/today", methods=["GET"])
def stats_today():
    """Returns today's pending/completed counts and productivity score."""
    all_tasks = db.get_all_tasks()
    today_tasks = se.get_today_tasks(all_tasks)
    productivity = se.calculate_productivity_score(today_tasks)

    return jsonify({
        "success": True,
        "today_total": len(today_tasks),
        "today_pending": len([t for t in today_tasks if t["status"] == "pending"]),
        "today_completed": len([t for t in today_tasks if t["status"] == "completed"]),
        "productivity": productivity
    })


@app.route("/api/stats/weekly", methods=["GET"])
def stats_weekly():
    """Returns the 7-day summary used for the weekly chart + suggestions."""
    all_tasks = db.get_all_tasks()
    weekly = se.get_weekly_stats(all_tasks)
    return jsonify({"success": True, "weekly": weekly})


@app.route("/api/stats/overview", methods=["GET"])
def stats_overview():
    """Returns overall counts used for the top dashboard cards + pie chart."""
    all_tasks = db.get_all_tasks()

    total = len(all_tasks)
    completed = len([t for t in all_tasks if t["status"] == "completed"])
    pending = len([t for t in all_tasks if t["status"] == "pending"])
    overdue = len([t for t in all_tasks if se.is_overdue(t)])

    by_priority = {"High": 0, "Medium": 0, "Low": 0}
    by_category = {}
    for t in all_tasks:
        by_priority[t["priority"]] = by_priority.get(t["priority"], 0) + 1
        by_category[t["category"]] = by_category.get(t["category"], 0) + 1

    return jsonify({
        "success": True,
        "total": total,
        "completed": completed,
        "pending": pending,
        "overdue": overdue,
        "completion_rate": round((completed / total) * 100) if total > 0 else 0,
        "by_priority": by_priority,
        "by_category": by_category
    })


# -----------------------------------------------------------------------
# RUN THE APP
# -----------------------------------------------------------------------

if __name__ == "__main__":
    # debug=True gives helpful error pages + auto-reloads when you save a file.
    # Turn this off (debug=False) if you ever deploy this somewhere public.
    app.run(debug=True, port=5000)
