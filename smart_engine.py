"""
smart_engine.py
----------------
This file contains all the "smart" logic for the planner:
    1. Scoring tasks by urgency + priority
    2. Suggesting which task to do next
    3. Detecting overdue tasks
    4. Calculating a daily productivity score
    5. Building a weekly statistics summary

WHY NOT "REAL" MACHINE LEARNING?
This uses simple, explainable RULES and MATH (not a trained ML model).
That's a completely valid and common approach for this kind of feature,
and it's much easier to explain in an interview:
    "I calculate a score for each task using its priority and how close
     the deadline is, then sort tasks by that score."
That one sentence is a perfectly good answer to "how does your AI
prioritization work?"
"""

from datetime import datetime, timedelta

# Numeric weight for each priority level - higher = more important
PRIORITY_WEIGHTS = {
    "High": 3,
    "Medium": 2,
    "Low": 1
}


def parse_deadline(deadline_str):
    """Converts our stored 'YYYY-MM-DD HH:MM' string into a datetime object."""
    return datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")


def is_overdue(task):
    """A task is overdue if it's still pending AND its deadline has passed."""
    if task["status"] == "completed":
        return False
    return parse_deadline(task["deadline"]) < datetime.now()


def calculate_task_score(task):
    """
    Calculates a single "urgency score" for a task.

    Formula (simple and explainable):
        score = priority_weight * 10  +  urgency_bonus

    urgency_bonus gets BIGGER as the deadline gets CLOSER:
        - overdue tasks              -> +50 (always float to the top)
        - due within 24 hours        -> +40
        - due within 3 days          -> +25
        - due within 7 days          -> +10
        - more than a week away      -> +0

    Higher score = do this task sooner.
    """
    priority_score = PRIORITY_WEIGHTS.get(task["priority"], 2) * 10

    deadline = parse_deadline(task["deadline"])
    time_left = deadline - datetime.now()
    hours_left = time_left.total_seconds() / 3600

    if hours_left < 0:
        urgency_bonus = 50
    elif hours_left <= 24:
        urgency_bonus = 40
    elif hours_left <= 72:
        urgency_bonus = 25
    elif hours_left <= 168:
        urgency_bonus = 10
    else:
        urgency_bonus = 0

    return priority_score + urgency_bonus


def rank_tasks(tasks):
    """
    Takes a list of tasks, adds a 'score' and 'overdue' field to each,
    and returns them sorted with the highest score (most urgent) first.
    """
    for task in tasks:
        task["score"] = calculate_task_score(task)
        task["overdue"] = is_overdue(task)

    return sorted(tasks, key=lambda t: t["score"], reverse=True)


def suggest_next_task(tasks):
    """
    Looks at all PENDING tasks and returns the single best one to work on
    next, along with a plain-English reason.

    Returns None if there are no pending tasks.
    """
    pending = [t for t in tasks if t["status"] == "pending"]
    if not pending:
        return None

    ranked = rank_tasks(pending)
    top_task = ranked[0]

    # Build a friendly explanation for WHY this task was picked
    if top_task["overdue"]:
        reason = "This task is overdue and needs immediate attention."
    else:
        hours_left = (parse_deadline(top_task["deadline"]) - datetime.now()).total_seconds() / 3600
        if hours_left <= 24:
            reason = "Deadline is within 24 hours - it's the most urgent task."
        elif top_task["priority"] == "High":
            reason = "Marked as High priority with an approaching deadline."
        else:
            reason = "Best balance of priority and deadline among your pending tasks."

    return {"task": top_task, "reason": reason}


def get_today_tasks(tasks):
    """Filters tasks whose deadline falls on today's date."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    return [t for t in tasks if t["deadline"].startswith(today_str)]


def calculate_productivity_score(day_tasks):
    """
    Calculates a 0-100 productivity score for a set of tasks (usually
    "today's tasks").

    Formula:
        score = (completed / total) * 70   -> rewards getting things done
               + (on_time / completed) * 30 -> rewards finishing BEFORE deadline

    If there are no tasks at all, we return None (nothing to score yet).
    """
    total = len(day_tasks)
    if total == 0:
        return None

    completed_tasks = [t for t in day_tasks if t["status"] == "completed"]
    completed = len(completed_tasks)

    on_time = 0
    for t in completed_tasks:
        if t["completed_at"] and t["completed_at"] <= t["deadline"]:
            on_time += 1

    completion_part = (completed / total) * 70
    on_time_part = (on_time / completed) * 30 if completed > 0 else 0

    score = round(completion_part + on_time_part)

    return {
        "score": score,
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "on_time": on_time
    }


def get_weekly_stats(all_tasks):
    """
    Builds a 7-day summary (today + previous 6 days) showing how many
    tasks were due and how many were completed each day.
    Used to draw the weekly bar chart on the dashboard.
    """
    days = []
    today = datetime.now().date()

    for i in range(6, -1, -1):  # 6 days ago -> today
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")

        day_tasks = [t for t in all_tasks if t["deadline"].startswith(day_str)]
        completed = len([t for t in day_tasks if t["status"] == "completed"])

        days.append({
            "date": day_str,
            "label": day.strftime("%a"),  # Mon, Tue, Wed...
            "total": len(day_tasks),
            "completed": completed
        })

    total_tasks = sum(d["total"] for d in days)
    total_completed = sum(d["completed"] for d in days)
    completion_rate = round((total_completed / total_tasks) * 100) if total_tasks > 0 else 0

    # Simple, rule-based improvement tips
    suggestions = []
    if total_tasks == 0:
        suggestions.append("No tasks scheduled this week yet - try adding a few to build momentum.")
    else:
        if completion_rate < 50:
            suggestions.append("Your completion rate is below 50%. Try setting fewer, more realistic daily tasks.")
        elif completion_rate >= 85:
            suggestions.append("Excellent completion rate! Consider taking on slightly bigger tasks.")

        low_days = [d for d in days if d["total"] >= 3 and d["completed"] == 0]
        if low_days:
            suggestions.append(f"You had {len(low_days)} day(s) with tasks but nothing completed. Try breaking big tasks into smaller ones.")

    if not suggestions:
        suggestions.append("Solid, consistent week overall. Keep up the current habits!")

    return {
        "days": days,
        "total_tasks": total_tasks,
        "total_completed": total_completed,
        "completion_rate": completion_rate,
        "suggestions": suggestions
    }


def detect_overload(tasks, daily_capacity=6):
    """
    Simple overload check: counts how many PENDING tasks are due on each
    upcoming date. If a date has more than `daily_capacity` tasks stacked
    up, we flag it as overloaded so the user can reschedule some.
    """
    pending = [t for t in tasks if t["status"] == "pending"]
    counts = {}

    for t in pending:
        date_part = t["deadline"].split(" ")[0]
        counts[date_part] = counts.get(date_part, 0) + 1

    overloaded = [
        {"date": date, "task_count": count}
        for date, count in counts.items()
        if count > daily_capacity
    ]

    return sorted(overloaded, key=lambda d: d["date"])
