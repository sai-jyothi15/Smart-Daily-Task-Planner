/* ==========================================================================
   script.js
   All frontend logic for the Smart Daily Task Planner.

   HOW THIS WORKS (for your interview explanation):
   This is plain JavaScript - no React, no frameworks. We use the built-in
   fetch() function to call our Flask API (defined in app.py), get JSON
   data back, and then manually update the HTML using DOM methods like
   document.getElementById() and innerHTML. This is the same fundamental
   idea frameworks like React automate for you, just done by hand.
   ========================================================================== */

const API_BASE = "/api";

// Keep the currently loaded tasks in memory so we don't re-fetch on every
// small UI interaction like toggling "Smart Sort".
let currentTasks = [];
let smartSortOn = true;

// ---------------------------------------------------------------------
// PAGE LOAD - fetch everything we need as soon as the page opens
// ---------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  loadTasks();
  loadSuggestion();
  loadOverloadWarning();
  loadTodayStats();
  loadWeeklyStats();
  loadOverviewStats();
  setupTaskModal();
  setupFilters();
  setupPomodoro();
});


// ---------------------------------------------------------------------
// TOAST NOTIFICATIONS (small popup messages)
// ---------------------------------------------------------------------
function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 2500);
}


// ---------------------------------------------------------------------
// FETCH HELPERS
// ---------------------------------------------------------------------
async function apiGet(url) {
  const res = await fetch(API_BASE + url);
  return res.json();
}

async function apiSend(url, method, body) {
  const res = await fetch(API_BASE + url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined
  });
  return res.json();
}


// ---------------------------------------------------------------------
// LOAD + RENDER TASKS
// ---------------------------------------------------------------------
async function loadTasks() {
  const status = document.getElementById("filterStatus").value;
  const priority = document.getElementById("filterPriority").value;

  let url = "/tasks?";
  if (status) url += `status=${status}&`;
  if (priority) url += `priority=${priority}&`;

  const data = await apiGet(url);
  currentTasks = data.tasks;
  renderTasks();
}

function renderTasks() {
  const listEl = document.getElementById("taskList");
  const search = document.getElementById("filterSearch").value.toLowerCase();

  let tasks = [...currentTasks];

  if (search) {
    tasks = tasks.filter(t => t.title.toLowerCase().includes(search));
  }

  if (!smartSortOn) {
    // Fall back to plain deadline order (already sorted that way from the API)
    tasks = tasks.slice().sort((a, b) => a.deadline.localeCompare(b.deadline));
  }
  // if smartSortOn, tasks are already sorted by score from the backend

  if (tasks.length === 0) {
    listEl.innerHTML = `<div class="empty-state">No tasks found. Click "+ New Task" to add one!</div>`;
    return;
  }

  listEl.innerHTML = tasks.map(taskCardHTML).join("");

  // Attach event listeners AFTER inserting the HTML (elements must exist first)
  tasks.forEach(task => {
    document.getElementById(`check-${task.id}`).addEventListener("click", () => toggleTask(task.id));
    document.getElementById(`edit-${task.id}`).addEventListener("click", () => openEditModal(task));
    document.getElementById(`delete-${task.id}`).addEventListener("click", () => deleteTask(task.id));
  });
}

function taskCardHTML(task) {
  const isCompleted = task.status === "completed";
  const priorityClass = `badge-priority-${task.priority.toLowerCase()}`;
  const statusClass = `badge-status-${task.status}`;

  return `
    <div class="task-card ${isCompleted ? "completed" : ""} ${task.overdue ? "overdue" : ""}">
      <button id="check-${task.id}" class="check-btn ${isCompleted ? "checked" : ""}" title="Toggle complete">
        ${isCompleted ? "✓" : ""}
      </button>

      <div class="task-body">
        <div class="task-top">
          <p class="task-title">${escapeHTML(task.title)}</p>
          ${smartSortOn ? `<span class="task-score">🔥 ${task.score}</span>` : ""}
        </div>

        ${task.description ? `<p class="task-desc">${escapeHTML(task.description)}</p>` : ""}

        <div class="badges">
          <span class="badge ${priorityClass}">${task.priority}</span>
          <span class="badge ${statusClass}">${task.status}</span>
          <span class="badge badge-category">${escapeHTML(task.category)}</span>
          ${task.overdue ? `<span class="badge badge-overdue">Overdue</span>` : ""}
        </div>

        <p class="task-meta">📅 Due: ${formatDeadline(task.deadline)}</p>
      </div>

      <div class="task-actions">
        <button id="edit-${task.id}" class="icon-btn" title="Edit">✏️</button>
        <button id="delete-${task.id}" class="icon-btn delete" title="Delete">🗑️</button>
      </div>
    </div>
  `;
}

function escapeHTML(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function formatDeadline(deadlineStr) {
  // deadlineStr looks like "2026-09-15 14:30"
  const [datePart, timePart] = deadlineStr.split(" ");
  const date = new Date(`${datePart}T${timePart}`);
  return date.toLocaleString("en-IN", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
  });
}


// ---------------------------------------------------------------------
// TASK ACTIONS: toggle complete, delete
// ---------------------------------------------------------------------
async function toggleTask(id) {
  const result = await apiSend(`/tasks/${id}/toggle`, "PATCH");
  if (result.success) {
    refreshEverything();
  }
}

async function deleteTask(id) {
  if (!confirm("Delete this task?")) return;
  const result = await apiSend(`/tasks/${id}`, "DELETE");
  if (result.success) {
    showToast("Task deleted");
    refreshEverything();
  }
}

function refreshEverything() {
  loadTasks();
  loadSuggestion();
  loadOverloadWarning();
  loadTodayStats();
  loadWeeklyStats();
  loadOverviewStats();
}


// ---------------------------------------------------------------------
// ADD / EDIT MODAL
// ---------------------------------------------------------------------
function setupTaskModal() {
  const modal = document.getElementById("taskModal");
  const form = document.getElementById("taskForm");

  document.getElementById("addTaskBtn").addEventListener("click", openAddModal);
  document.getElementById("closeModalBtn").addEventListener("click", closeModal);
  document.getElementById("cancelModalBtn").addEventListener("click", closeModal);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const id = document.getElementById("taskId").value;
    const payload = {
      title: document.getElementById("taskTitle").value,
      description: document.getElementById("taskDescription").value,
      category: document.getElementById("taskCategory").value,
      priority: document.getElementById("taskPriority").value,
      // datetime-local gives "2026-09-15T14:30" - we convert the "T" to a space
      // to match the format we store in SQLite: "2026-09-15 14:30"
      deadline: document.getElementById("taskDeadline").value.replace("T", " ")
    };

    let result;
    if (id) {
      result = await apiSend(`/tasks/${id}`, "PUT", payload);
    } else {
      result = await apiSend("/tasks", "POST", payload);
    }

    if (result.success) {
      showToast(id ? "Task updated" : "Task created");
      closeModal();
      refreshEverything();
    } else {
      showToast(result.message || "Something went wrong");
    }
  });
}

function openAddModal() {
  document.getElementById("modalTitle").textContent = "New Task";
  document.getElementById("saveTaskBtn").textContent = "Create Task";
  document.getElementById("taskId").value = "";
  document.getElementById("taskTitle").value = "";
  document.getElementById("taskDescription").value = "";
  document.getElementById("taskCategory").value = "General";
  document.getElementById("taskPriority").value = "Medium";

  // Default deadline: 3 hours from now, formatted for the datetime-local input
  const defaultDeadline = new Date(Date.now() + 3 * 60 * 60 * 1000);
  document.getElementById("taskDeadline").value = toDatetimeLocalValue(defaultDeadline);

  document.getElementById("taskModal").classList.remove("hidden");
}

function openEditModal(task) {
  document.getElementById("modalTitle").textContent = "Edit Task";
  document.getElementById("saveTaskBtn").textContent = "Save Changes";
  document.getElementById("taskId").value = task.id;
  document.getElementById("taskTitle").value = task.title;
  document.getElementById("taskDescription").value = task.description || "";
  document.getElementById("taskCategory").value = task.category;
  document.getElementById("taskPriority").value = task.priority;
  document.getElementById("taskDeadline").value = task.deadline.replace(" ", "T");

  document.getElementById("taskModal").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("taskModal").classList.add("hidden");
}

function toDatetimeLocalValue(date) {
  const pad = n => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}


// ---------------------------------------------------------------------
// FILTERS
// ---------------------------------------------------------------------
function setupFilters() {
  document.getElementById("filterStatus").addEventListener("change", loadTasks);
  document.getElementById("filterPriority").addEventListener("change", loadTasks);
  document.getElementById("filterSearch").addEventListener("input", renderTasks);

  document.getElementById("smartSortToggle").addEventListener("click", (e) => {
    smartSortOn = !smartSortOn;
    e.target.classList.toggle("active", smartSortOn);
    renderTasks();
  });
}


// ---------------------------------------------------------------------
// SMART SUGGESTION BANNER
// ---------------------------------------------------------------------
async function loadSuggestion() {
  const data = await apiGet("/suggestion");
  const banner = document.getElementById("suggestionBanner");

  if (data.suggestion) {
    document.getElementById("suggestionTitle").textContent = data.suggestion.task.title;
    document.getElementById("suggestionReason").textContent = data.suggestion.reason;
    banner.classList.remove("hidden");
  } else {
    banner.classList.add("hidden");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("startFocusFromSuggestion").addEventListener("click", () => {
    document.querySelector(".focus-card").scrollIntoView({ behavior: "smooth" });
  });
});


// ---------------------------------------------------------------------
// OVERLOAD WARNING BANNER
// ---------------------------------------------------------------------
async function loadOverloadWarning() {
  const data = await apiGet("/overload");
  const banner = document.getElementById("overloadBanner");
  const list = document.getElementById("overloadList");

  if (data.overloaded_days && data.overloaded_days.length > 0) {
    list.innerHTML = data.overloaded_days
      .map(d => `<li>${d.date}: ${d.task_count} tasks scheduled - consider rescheduling some.</li>`)
      .join("");
    banner.classList.remove("hidden");
  } else {
    banner.classList.add("hidden");
  }
}


// ---------------------------------------------------------------------
// TODAY'S PRODUCTIVITY SCORE
// ---------------------------------------------------------------------
async function loadTodayStats() {
  const data = await apiGet("/stats/today");
  const ring = document.getElementById("scoreRingFill");
  const valueEl = document.getElementById("scoreValue");
  const detailEl = document.getElementById("scoreDetail");

  if (data.productivity) {
    const score = data.productivity.score;
    valueEl.textContent = score;

    // Circle circumference = 2 * PI * r(42) ≈ 264
    const circumference = 264;
    const offset = circumference - (score / 100) * circumference;
    ring.style.strokeDashoffset = offset;

    detailEl.textContent = `${data.productivity.completed}/${data.productivity.total} tasks completed today`;
  } else {
    valueEl.textContent = "--";
    ring.style.strokeDashoffset = 264;
    detailEl.textContent = "No tasks due today yet";
  }
}


// ---------------------------------------------------------------------
// OVERVIEW STATS (top cards + priority pie chart)
// ---------------------------------------------------------------------
let priorityChartInstance = null;

async function loadOverviewStats() {
  const data = await apiGet("/stats/overview");

  document.getElementById("statTotal").textContent = data.total;
  document.getElementById("statCompleted").textContent = data.completed;
  document.getElementById("statPending").textContent = data.pending;
  document.getElementById("statOverdue").textContent = data.overdue;

  const ctx = document.getElementById("priorityChart");
  const labels = Object.keys(data.by_priority);
  const values = Object.values(data.by_priority);

  if (priorityChartInstance) priorityChartInstance.destroy();
  priorityChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: ["#ef4444", "#6366f1", "#94a3b8"]
      }]
    },
    options: {
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 12 } } } }
    }
  });
}


// ---------------------------------------------------------------------
// WEEKLY STATS (bar chart + suggestions)
// ---------------------------------------------------------------------
let weeklyChartInstance = null;

async function loadWeeklyStats() {
  const data = await apiGet("/stats/weekly");
  const weekly = data.weekly;

  const ctx = document.getElementById("weeklyChart");
  if (weeklyChartInstance) weeklyChartInstance.destroy();
  weeklyChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: weekly.days.map(d => d.label),
      datasets: [
        { label: "Scheduled", data: weekly.days.map(d => d.total), backgroundColor: "#c7d2fe" },
        { label: "Completed", data: weekly.days.map(d => d.completed), backgroundColor: "#6366f1" }
      ]
    },
    options: {
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 12 } } } }
    }
  });

  const suggestionsList = document.getElementById("weeklySuggestions");
  suggestionsList.innerHTML = weekly.suggestions.map(s => `<li>${s}</li>`).join("");
}


// ---------------------------------------------------------------------
// FOCUS MODE - POMODORO TIMER
// ---------------------------------------------------------------------
let timerInterval = null;
let secondsLeft = 25 * 60;
let timerRunning = false;
let currentMode = "focus";
let cyclesDone = 0;

function setupPomodoro() {
  document.querySelectorAll(".mode-btn").forEach(btn => {
    btn.addEventListener("click", () => switchMode(btn.dataset.mode, parseInt(btn.dataset.minutes)));
  });

  document.getElementById("timerStartBtn").addEventListener("click", toggleTimer);
  document.getElementById("timerResetBtn").addEventListener("click", resetTimer);

  updateTimerDisplay();
}

function switchMode(mode, minutes) {
  currentMode = mode;
  secondsLeft = minutes * 60;
  timerRunning = false;
  clearInterval(timerInterval);
  document.getElementById("timerStartBtn").textContent = "Start";

  document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
  document.querySelector(`.mode-btn[data-mode="${mode}"]`).classList.add("active");

  updateTimerDisplay();
}

function toggleTimer() {
  timerRunning = !timerRunning;
  const btn = document.getElementById("timerStartBtn");

  if (timerRunning) {
    btn.textContent = "Pause";
    timerInterval = setInterval(() => {
      secondsLeft--;
      updateTimerDisplay();

      if (secondsLeft <= 0) {
        clearInterval(timerInterval);
        timerRunning = false;
        handleTimerComplete();
      }
    }, 1000);
  } else {
    btn.textContent = "Start";
    clearInterval(timerInterval);
  }
}

function resetTimer() {
  clearInterval(timerInterval);
  timerRunning = false;
  document.getElementById("timerStartBtn").textContent = "Start";

  const activeBtn = document.querySelector(".mode-btn.active");
  secondsLeft = parseInt(activeBtn.dataset.minutes) * 60;
  updateTimerDisplay();
}

function handleTimerComplete() {
  if (currentMode === "focus") {
    cyclesDone++;
    document.getElementById("cyclesCount").textContent = cyclesDone;
    showToast("Focus session complete! Time for a break 🎉");
    // After every 4th focus session, take a long break; otherwise a short one
    const nextMode = cyclesDone % 4 === 0 ? "long" : "short";
    const nextMinutes = nextMode === "long" ? 15 : 5;
    switchMode(nextMode, nextMinutes);
    document.querySelector(`.mode-btn[data-mode="${nextMode}"]`).classList.add("active");
  } else {
    showToast("Break's over - back to focus!");
    switchMode("focus", 25);
  }
}

function updateTimerDisplay() {
  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  document.getElementById("timerDisplay").textContent =
    `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}
