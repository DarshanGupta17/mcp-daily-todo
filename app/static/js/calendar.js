const TZ = "Asia/Kolkata";

let viewMode = "month";
let cursor = new Date();
let selectedDate = isoLocalDate(new Date());
let tasksByDate = {};
let openPopoverDate = null;
let flash = false;

function maxChipsForView() {
  return viewMode === "week" ? 4 : 2;
}

const els = {
  shell: () => document.getElementById("calendar-shell"),
  wrap: () => document.getElementById("calendar-wrap"),
  popover: () => document.getElementById("cal-day-popover"),
  popoverDate: () => document.getElementById("cal-popover-date"),
  popoverBody: () => document.getElementById("cal-popover-body"),
  popoverClose: () => document.getElementById("cal-popover-close"),
  monthLabel: () => document.getElementById("month-label"),
};

export function isoLocalDate(d) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(d);
}

function parseYmd(ymd) {
  const [y, m, day] = ymd.split("-").map(Number);
  return new Date(y, m - 1, day);
}

function monthRange(d) {
  const start = new Date(d.getFullYear(), d.getMonth(), 1);
  const end = new Date(d.getFullYear(), d.getMonth() + 1, 0);
  return { start: isoLocalDate(start), end: isoLocalDate(end) };
}

function weekRange(anchorYmd) {
  const d = parseYmd(anchorYmd);
  const day = d.getDay();
  const start = new Date(d);
  start.setDate(d.getDate() - day);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  return { start: isoLocalDate(start), end: isoLocalDate(end) };
}

async function fetchTasksInRange(start, end) {
  const res = await fetch(`/api/tasks?start_date=${start}&end_date=${end}`);
  const data = await res.json();
  const byDate = {};
  for (const t of data.tasks || []) {
    const key = t.task_date;
    if (!byDate[key]) byDate[key] = [];
    byDate[key].push(t);
  }
  for (const key of Object.keys(byDate)) {
    byDate[key].sort((a, b) => a.id - b.id);
  }
  tasksByDate = byDate;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function formatPopoverDate(ymd) {
  const d = parseYmd(ymd);
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function truncateTitle(title, maxLen) {
  const t = String(title).trim();
  if (t.length <= maxLen) return t;
  return `${t.slice(0, maxLen - 1)}…`;
}

function renderChips(ymd) {
  const tasks = tasksByDate[ymd] || [];
  if (!tasks.length) {
    return '<div class="cal-day-chips cal-day-chips--empty"></div>';
  }
  const titleMax = viewMode === "week" ? 28 : 14;
  let visible;
  let extra;
  if (viewMode === "month" && tasks.length > 2) {
    visible = tasks.slice(0, 1);
    extra = tasks.length - 1;
  } else {
    const limit = maxChipsForView();
    visible = tasks.slice(0, limit);
    extra = tasks.length - visible.length;
  }
  const chips = visible
    .map(
      (t) =>
        `<span class="cal-chip cal-chip--${t.status}" title="${escapeHtml(t.title)}">${escapeHtml(
          truncateTitle(t.title, titleMax)
        )}</span>`
    )
    .join("");
  const more =
    extra > 0 ? `<span class="cal-chip cal-chip--more">+${extra} more</span>` : "";
  return `<div class="cal-day-chips">${chips}${more}</div>`;
}

function renderCalendarGrid(days) {
  const today = isoLocalDate(new Date());
  const weekRows = Math.ceil(days.length / 7);
  const gridClass =
    viewMode === "week" ? "cal-grid cal-grid--week" : `cal-grid cal-grid--month cal-grid--rows-${weekRows}`;
  const html = [`<div class="${gridClass}">`];
  const dow = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  dow.forEach((d) => html.push(`<div class="cal-dow">${d}</div>`));

  days.forEach((cell) => {
    const hasTasks = (tasksByDate[cell.ymd] || []).length > 0;
    const classes = [
      "cal-day",
      viewMode === "week" ? "cal-day--week" : "cal-day--month",
      cell.ymd === today ? "today" : "",
      cell.ymd === selectedDate ? "selected" : "",
      cell.ymd === openPopoverDate ? "popover-open" : "",
      hasTasks ? "has-tasks" : "",
      cell.otherMonth ? "other-month" : "",
      flash ? "cal-flash" : "",
    ]
      .filter(Boolean)
      .join(" ");
    html.push(
      `<button type="button" class="${classes}" data-date="${cell.ymd}">
        <span class="num">${cell.day}</span>
        ${renderChips(cell.ymd)}
      </button>`
    );
  });
  html.push("</div>");
  els.wrap().innerHTML = html.join("");

  els.wrap().querySelectorAll("[data-date]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const ymd = btn.dataset.date;
      if (openPopoverDate === ymd) {
        closePopover();
      } else {
        selectedDate = ymd;
        openPopover(btn, ymd);
        syncSelectedClasses();
      }
    });
  });

  if (openPopoverDate) {
    const anchor = els.wrap().querySelector(`[data-date="${openPopoverDate}"]`);
    if (anchor) positionPopover(anchor);
  }
}

function syncSelectedClasses() {
  els.wrap().querySelectorAll(".cal-day").forEach((el) => {
    const isSelected = el.dataset.date === selectedDate;
    const isOpen = el.dataset.date === openPopoverDate;
    el.classList.toggle("selected", isSelected);
    el.classList.toggle("popover-open", isOpen);
  });
}

function buildTaskCards(tasks, withFlash) {
  if (!tasks.length) {
    return '<p class="cal-popover-empty">No tasks. Ask the assistant to add one.</p>';
  }
  return tasks
    .map(
      (t) => `
      <article class="task-card task-card--compact ${t.status} ${withFlash ? "flash" : ""}" data-id="${t.id}">
        <h4 class="task-title">${escapeHtml(t.title)}</h4>
        ${
          t.description
            ? `<p class="task-desc">${escapeHtml(t.description)}</p>`
            : ""
        }
        <div class="task-meta">
          <span class="status-${t.status}">${t.status}</span>
          <span>id: ${t.id}</span>
        </div>
      </article>`
    )
    .join("");
}

function positionPopover(anchor) {
  const pop = els.popover();
  const cellRect = anchor.getBoundingClientRect();
  const panel = els.shell().closest(".panel-calendar");
  const panelRect = panel ? panel.getBoundingClientRect() : { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight };

  const popW = 260;
  const popMaxH = 240;
  let left = cellRect.left;
  let top = cellRect.bottom + 6;

  const maxLeft = panelRect.left + panelRect.width - popW - 8;
  if (left > maxLeft) left = Math.max(panelRect.left + 8, maxLeft);
  if (left < panelRect.left + 8) left = panelRect.left + 8;

  const spaceBelow = panelRect.top + panelRect.height - top;
  if (spaceBelow < popMaxH + 8) {
    top = cellRect.top - popMaxH - 6;
    if (top < panelRect.top + 8) top = cellRect.bottom + 6;
  }

  pop.style.position = "fixed";
  pop.style.width = `${popW}px`;
  pop.style.maxHeight = `${popMaxH}px`;
  pop.style.left = `${left}px`;
  pop.style.top = `${top}px`;
}

function openPopover(anchor, ymd) {
  openPopoverDate = ymd;
  const tasks = tasksByDate[ymd] || [];
  const pop = els.popover();
  els.popoverDate().textContent = formatPopoverDate(ymd);
  els.popoverBody().innerHTML = buildTaskCards(tasks, flash);
  pop.classList.remove("hidden");
  pop.hidden = false;
  positionPopover(anchor);
  anchor.classList.add("popover-open");
}

function closePopover() {
  openPopoverDate = null;
  const pop = els.popover();
  pop.classList.add("hidden");
  pop.hidden = true;
  els.wrap().querySelectorAll(".popover-open").forEach((el) => el.classList.remove("popover-open"));
}

function buildMonthDays(ref) {
  const year = ref.getFullYear();
  const month = ref.getMonth();
  const first = new Date(year, month, 1);
  const startPad = first.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];

  for (let i = 0; i < startPad; i++) {
    const d = new Date(year, month, -startPad + i + 1);
    cells.push({ ymd: isoLocalDate(d), day: d.getDate(), otherMonth: true });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const dt = new Date(year, month, d);
    cells.push({ ymd: isoLocalDate(dt), day: d, otherMonth: false });
  }
  while (cells.length % 7 !== 0) {
    const last = parseYmd(cells[cells.length - 1].ymd);
    last.setDate(last.getDate() + 1);
    cells.push({ ymd: isoLocalDate(last), day: last.getDate(), otherMonth: true });
  }
  return cells;
}

function buildWeekDays(anchorYmd) {
  const { start, end } = weekRange(anchorYmd);
  const cells = [];
  const cur = parseYmd(start);
  const endD = parseYmd(end);
  while (cur <= endD) {
    cells.push({ ymd: isoLocalDate(cur), day: cur.getDate(), otherMonth: false });
    cur.setDate(cur.getDate() + 1);
  }
  return cells;
}

async function render(doFlash = false) {
  flash = doFlash;
  const monthName = cursor.toLocaleString("en-US", { month: "long", year: "numeric" });
  els.monthLabel().textContent = monthName;

  let range;
  let days;
  if (viewMode === "week") {
    range = weekRange(selectedDate);
    days = buildWeekDays(selectedDate);
  } else {
    range = monthRange(cursor);
    days = buildMonthDays(cursor);
  }
  await fetchTasksInRange(range.start, range.end);
  renderCalendarGrid(days);

  if (openPopoverDate) {
    const tasks = tasksByDate[openPopoverDate] || [];
    els.popoverBody().innerHTML = buildTaskCards(tasks, flash);
  }

  flash = false;
}

function onDocumentClick(e) {
  const pop = els.popover();
  if (pop.hidden) return;
  if (
    pop.contains(e.target) ||
    e.target.closest(".cal-day") ||
    e.target.closest("#cal-popover-close")
  ) {
    return;
  }
  closePopover();
}

export function initCalendar() {
  els.popoverClose().addEventListener("click", (e) => {
    e.stopPropagation();
    closePopover();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !els.popover().hidden) closePopover();
  });

  document.addEventListener("click", onDocumentClick);

  window.addEventListener("resize", () => {
    if (!openPopoverDate) return;
    const anchor = els.wrap().querySelector(`[data-date="${openPopoverDate}"]`);
    if (anchor) positionPopover(anchor);
  });

  document.getElementById("prev-month").addEventListener("click", () => {
    if (viewMode === "week") {
      const d = parseYmd(selectedDate);
      d.setDate(d.getDate() - 7);
      selectedDate = isoLocalDate(d);
      cursor = d;
    } else {
      cursor.setMonth(cursor.getMonth() - 1);
    }
    closePopover();
    render();
  });
  document.getElementById("next-month").addEventListener("click", () => {
    if (viewMode === "week") {
      const d = parseYmd(selectedDate);
      d.setDate(d.getDate() + 7);
      selectedDate = isoLocalDate(d);
      cursor = d;
    } else {
      cursor.setMonth(cursor.getMonth() + 1);
    }
    closePopover();
    render();
  });
  document.getElementById("today-btn").addEventListener("click", () => {
    const t = new Date();
    cursor = t;
    selectedDate = isoLocalDate(t);
    closePopover();
    render();
  });
  document.querySelectorAll(".view-toggle .toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".view-toggle .toggle").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      viewMode = btn.dataset.view;
      closePopover();
      render();
    });
  });
  render();
}

export async function refreshTasks() {
  await render(true);
}

export function getSelectedDate() {
  return selectedDate;
}