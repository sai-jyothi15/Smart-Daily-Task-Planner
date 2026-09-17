# 🧠 Smart Daily Task Planner (Flask + SQLite Edition)

A beginner-friendly but genuinely useful task management web app built with
**Python Flask**, **SQLite**, and plain **HTML/CSS/JavaScript** — no React,
no MongoDB, no Docker, no build tools. Just the fundamentals, done well.

This project is designed to be **easy to explain in a college viva or job
interview** while still having real, "smart" features that make it stand
out from a basic to-do list.

---

## ✨ Features

### Core
- Add, edit, delete, and mark tasks complete
- Priority levels: **High / Medium / Low**
- Deadlines and custom categories
- Search and filter tasks (by status, priority, keyword)
- Automatic overdue detection
- Fully responsive, modern UI (works on mobile too)

### Smart Features (rule-based, fully explainable — no black-box ML)
- **Smart Score & Sorting** — every task gets a 0–100+ urgency score based
  on priority + how close the deadline is
- **"Do this next" suggestion** — tells you the single best task to work
  on right now, with a plain-English reason
- **Overload detection** — warns you if too many tasks are due on the
  same day
- **Daily Productivity Score** — 0–100 score based on how much you
  completed today, and how much was on time
- **Weekly statistics + suggestions** — a 7-day chart plus personalized,
  rule-based tips to improve
- **Focus Mode (Pomodoro Timer)** — 25-minute focus sessions with
  automatic short/long breaks

---

## 🛠 Tech Stack

| Layer      | Technology                        |
|------------|------------------------------------|
| Frontend   | HTML5, CSS3, vanilla JavaScript (`fetch` API) |
| Charts     | Chart.js (loaded via a single CDN `<script>` tag — no install needed) |
| Backend    | Python 3 + Flask                  |
| Database   | SQLite (a single local file, `tasks.db`) |

No npm, no webpack, no virtual DOM. Everything is easy to read line by line.

---

## 📁 Project Structure

```
smart-task-planner-flask/
├── app.py                 # Main Flask app — all API routes live here
├── database.py             # SQLite connection + CRUD functions
├── smart_engine.py         # All the "smart" scoring/suggestion logic
├── requirements.txt         # Python packages needed (just Flask)
├── tasks.db                # SQLite database file (auto-created on first run)
│
├── templates/
│   └── index.html          # The single HTML page (dashboard UI)
│
└── static/
    ├── css/
    │   └── style.css       # All styling
    └── js/
        └── script.js       # All frontend logic (fetch calls, DOM updates, timer)
```

---

## 📖 How Each File Works (for your explanation / viva)

**`app.py`** — The main Flask application. Defines all the routes:
- `/` serves the HTML page
- `/api/tasks` (GET/POST) — list all tasks or create a new one
- `/api/tasks/<id>` (PUT/DELETE) — edit or delete a specific task
- `/api/tasks/<id>/toggle` (PATCH) — mark complete/pending
- `/api/suggestion` — returns the "do this next" recommendation
- `/api/overload` — returns any overloaded upcoming days
- `/api/stats/today`, `/api/stats/weekly`, `/api/stats/overview` — dashboard data

**`database.py`** — Every function that touches SQLite lives here:
`init_db()` creates the table, `create_task()` / `get_all_tasks()` /
`update_task()` / `delete_task()` / `mark_task_status()` handle CRUD.
Keeping SQL in one file (instead of scattered through `app.py`) is good
practice and easy to point to in an interview.

**`smart_engine.py`** — The "intelligence" layer. `calculate_task_score()`
combines priority weight + deadline urgency into one number.
`suggest_next_task()` picks the highest-scoring pending task and explains
why. `calculate_productivity_score()` and `get_weekly_stats()` turn raw
task data into the dashboard numbers and charts.

**`templates/index.html`** — One page containing the whole UI: navbar,
suggestion banner, stat cards, charts, Pomodoro timer, filters, task list,
and the add/edit task modal (popup form).

**`static/js/script.js`** — Uses `fetch()` to call the Flask API and
`document.getElementById()` / `innerHTML` to update the page without
reloading it. Also contains the Pomodoro timer's `setInterval()` logic.

---

## 🚀 How to Run Locally (step-by-step, VS Code)

### Prerequisites
- **Python 3.8+** installed → check with:
  ```bash
  python --version
  ```
  (On some systems it's `python3` instead of `python`.)
- VS Code (or any editor)

### Step 1 — Unzip and open the project
Unzip `smart-task-planner-flask.zip`, then in VS Code: **File → Open Folder**
and select the unzipped `smart-task-planner-flask` folder.

### Step 2 — Open a terminal in VS Code
`` Terminal → New Terminal `` (or `` Ctrl+` ``)

### Step 3 — (Recommended) Create a virtual environment
This keeps this project's Python packages separate from everything else
on your system.

```bash
python -m venv venv
```

Activate it:
```bash
# Windows (PowerShell)
venv\Scripts\activate

# Windows (Command Prompt)
venv\Scripts\activate.bat

# macOS/Linux
source venv/bin/activate
```

> **Windows PowerShell script-blocking error?** If you see
> `"...cannot be loaded because running scripts is disabled..."`, run this
> once in PowerShell, then retry:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
> Or simply switch your VS Code terminal to **Command Prompt** instead of
> PowerShell (dropdown next to the `+` in the terminal panel).

You'll know it worked when you see `(venv)` at the start of your terminal line.

### Step 4 — Install the required package
```bash
pip install -r requirements.txt
```
This installs Flask — the only dependency this project needs.

### Step 5 — Run the app
```bash
python app.py
```

You should see:
```
Database ready: tasks.db
 * Running on http://127.0.0.1:5000
```

### Step 6 — Open it in your browser
Go to **http://127.0.0.1:5000** — you'll see the dashboard. Click
**"+ New Task"** to add your first task!

The `tasks.db` SQLite file is created automatically in your project folder
the first time you run the app — no separate database setup needed.

To stop the server, go back to the terminal and press `Ctrl+C`.

---

## 🐛 Troubleshooting

- **`ModuleNotFoundError: No module named 'flask'`** → You forgot to
  activate the virtual environment, or `pip install -r requirements.txt`
  didn't run successfully. Re-check Step 3 and 4.
- **Port 5000 already in use** → Close whatever else is using that port,
  or change `app.run(debug=True, port=5000)` in `app.py` to a different
  port like `5050`.
- **Page loads but no styling / charts** → Make sure you're running the
  app with `python app.py` and opening `http://127.0.0.1:5000` (not just
  double-clicking `index.html`) — Flask needs to serve the static files.
- **Database looks empty after restarting** → It shouldn't be — `tasks.db`
  persists your data between runs. If you want to start completely fresh,
  just delete `tasks.db` and restart the app; it will recreate an empty one.

---

## 🎯 Possible Interview Talking Points

- "I used SQLite because it needs zero setup — it's just a file — which
  made it perfect for a self-contained student project."
- "The 'smart' prioritization isn't a trained ML model — it's a
  transparent scoring formula combining priority weight and deadline
  urgency. I can walk through exactly how any score is calculated."
- "The frontend uses `fetch()` to call a small REST-style API instead of
  reloading the page — the same core idea as how a React app talks to a
  backend, just without the extra framework layer."
- "I separated concerns into three files — `app.py` for routes,
  `database.py` for data access, `smart_engine.py` for business logic —
  which makes the codebase easier to navigate and extend."

---

## 📄 License
Free to use for learning, college projects, and portfolios.
