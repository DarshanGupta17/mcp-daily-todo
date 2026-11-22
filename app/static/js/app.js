import { connectWebSocket, onWsEvent } from "./websocket.js";
import { initChat, handleChatWsEvent } from "./chat.js";
import { initCalendar, refreshTasks, isoLocalDate } from "./calendar.js";

const TOOL_ICONS = {
  create_task: "＋",
  list_tasks: "≡",
  update_task: "✎",
  delete_task: "×",
  complete_task: "✓",
  reopen_task: "↺",
};

const executions = new Map();

function el(id) {
  return document.getElementById(id);
}

function renderTools(tools) {
  const grid = el("tools-grid");
  if (!tools?.length) {
    grid.innerHTML = '<p class="empty-state">No MCP tools discovered</p>';
    return;
  }
  grid.innerHTML = tools
    .map((t) => {
      const props = t.inputSchema?.properties || {};
      const argNames = Object.keys(props).join(", ") || "—";
      return `
      <div class="tool-card">
        <div class="tool-icon">${TOOL_ICONS[t.name] || "◇"}</div>
        <div>
          <h4>${t.name}</h4>
          <p>${t.description || ""}</p>
          <div class="tool-args">args: ${argNames}</div>
        </div>
        <div class="tool-exec-count">${t.execution_count ?? 0}×</div>
      </div>`;
    })
    .join("");
}

function upsertExecution(ev) {
  const feed = el("execution-feed");
  let card = executions.get(ev.execution_id);

  if (ev.event === "tool_started") {
    card = document.createElement("div");
    card.className = "exec-card running";
    card.dataset.id = ev.execution_id;
    card.innerHTML = buildExecHtml(ev, "running", false);
    feed.prepend(card);
    executions.set(ev.execution_id, card);
    return;
  }

  if (!card) {
    card = document.createElement("div");
    card.dataset.id = ev.execution_id;
    feed.prepend(card);
    executions.set(ev.execution_id, card);
  }

  const expanded =
    card.querySelector(".exec-toggle")?.getAttribute("aria-expanded") === "true";
  const status = ev.status || (ev.event === "tool_failed" ? "failed" : "success");
  card.className = `exec-card ${status}`;
  card.innerHTML = buildExecHtml(ev, status, expanded);
}

function buildExecHtml(ev, status, expanded) {
  const ts = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : "";
  const args = ev.arguments ? JSON.stringify(ev.arguments, null, 2) : "{}";
  const result = ev.result ? JSON.stringify(ev.result, null, 2) : "—";
  const duration = ev.duration_ms != null ? `${ev.duration_ms}ms` : "…";

  const steps = ["Called", "Arguments", "Executing", "Result"];
  const stepIdx = status === "running" ? 2 : 3;
  const stepPills = steps
    .map((s, i) => `<span class="step-pill ${i <= stepIdx ? "active" : ""}">${s}</span>`)
    .join("");

  const detailsHidden = expanded ? "" : "hidden";

  return `
    <div class="exec-head">
      <span class="exec-summary">
        <span class="exec-name">${ev.tool_name}</span>
        <span class="exec-status ${status}">${status}</span>
      </span>
      <button
        type="button"
        class="exec-toggle ${expanded ? "open" : ""}"
        aria-expanded="${expanded ? "true" : "false"}"
        aria-label="Toggle execution details"
      >
        <svg class="exec-chevron" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
          <path d="M2 4l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
    <div class="exec-details ${detailsHidden}">
      <div class="exec-meta">${ts} · ${duration}</div>
      <div class="exec-label">Arguments</div>
      <pre class="exec-json">${args}</pre>
      ${status !== "running" ? `<div class="exec-label">Result</div><pre class="exec-json">${result}</pre>` : ""}
      <div class="exec-steps">${stepPills}</div>
    </div>
  `;
}

function setMcpStatus(data) {
  const conn = el("mcp-connection");
  if (data.connected) {
    conn.textContent = "Connected";
    conn.className = "badge badge-ok";
  } else {
    conn.textContent = "Disconnected";
    conn.className = "badge badge-warn";
  }
  el("tool-count").textContent = data.tool_count ?? 0;
  el("exec-total").textContent = data.total_executions ?? 0;
}

async function loadPublicConfig() {
  const res = await fetch("/api/config/public");
  const data = await res.json();
  el("model-badge").textContent = data.gemini_model || "Gemini";
  el("top-meta").textContent = `${data.timezone} · today ${isoLocalDate(new Date())}`;
}

onWsEvent(async (ev) => {
  handleChatWsEvent(ev);
  if (ev.event === "mcp_status") setMcpStatus(ev);
  if (ev.event === "tools_catalog") renderTools(ev.tools);
  if (ev.event === "tool_started" || ev.event === "tool_completed" || ev.event === "tool_failed") {
    upsertExecution(ev);
  }
  if (ev.event === "tasks_changed") await refreshTasks();
});

function initExecutionFeed() {
  const feed = el("execution-feed");
  feed.addEventListener("click", (e) => {
    const btn = e.target.closest(".exec-toggle");
    if (!btn) return;
    const card = btn.closest(".exec-card");
    const details = card?.querySelector(".exec-details");
    if (!details) return;
    const open = btn.getAttribute("aria-expanded") === "true";
    const next = !open;
    btn.setAttribute("aria-expanded", next ? "true" : "false");
    btn.classList.toggle("open", next);
    details.classList.toggle("hidden", !next);
    card.classList.toggle("exec-card--expanded", next);
  });
}

initChat();
initCalendar();
initExecutionFeed();
connectWebSocket();
loadPublicConfig();