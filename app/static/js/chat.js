import { isoLocalDate } from "./calendar.js";

let processing = false;
let history = [];
let onStatusCallback = null;

const els = {
  messages: () => document.getElementById("chat-messages"),
  input: () => document.getElementById("chat-input"),
  send: () => document.getElementById("chat-send"),
  thinking: () => document.getElementById("chat-thinking"),
  aiStatus: () => document.getElementById("ai-status"),
  suggestions: () => document.getElementById("chat-suggestions"),
};

function appendMessage(role, content) {
  const div = document.createElement("div");
  div.className = `msg ${role === "user" ? "msg-user" : "msg-assistant"}`;
  div.textContent = content;
  const box = els.messages();
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function setProcessing(active) {
  processing = active;
  els.input().disabled = active;
  els.send().disabled = active;
  els.thinking().classList.toggle("hidden", !active);
  els.aiStatus().textContent = active ? "Thinking" : "Ready";
  els.aiStatus().className = `badge badge-status ${active ? "badge-warn" : "badge-ok"}`;
  els.suggestions()?.querySelectorAll(".chat-suggestion").forEach((btn) => {
    btn.disabled = active;
  });
}

function parseYmd(ymd) {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function weekBoundsFromToday() {
  const today = isoLocalDate(new Date());
  const d = parseYmd(today);
  const day = d.getDay();
  const start = new Date(d);
  start.setDate(d.getDate() - day);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  return { start: isoLocalDate(start), end: isoLocalDate(end) };
}

function buildQuickPrompts() {
  const today = isoLocalDate(new Date());
  const y = parseYmd(today);
  y.setDate(y.getDate() - 1);
  const yesterday = isoLocalDate(y);
  const week = weekBoundsFromToday();

  return [
    {
      label: 'Add "Reply To All Email" for 23 Nov',
      message: 'Add a task titled "Reply To All Email" on 2026-11-23.',
    },
    {
      label: "Remove All the Tasks from Today",
      message: `Delete all tasks scheduled for today (${today}). Use list_tasks first if needed, then delete each one.`,
    },
    {
      label: "Reopen All Tasks from Yesterday",
      message: `Reopen every completed task from yesterday (${yesterday}). Use list_tasks for that date, then reopen_task for each completed task.`,
    },
    {
      label: "List All Tasks This Week",
      message: `List all my tasks from ${week.start} to ${week.end}.`,
    },
    {
      label: "Mark Groceries Task Complete",
      message:
        'Find the task about buying groceries (use list_tasks if needed) and mark it as completed.',
    },
  ];
}

function renderSuggestions(prompts) {
  const wrap = els.suggestions();
  if (!wrap) return;
  wrap.innerHTML = prompts
    .map(
      (p, i) =>
        `<button type="button" class="chat-suggestion" data-idx="${i}" title="${escapeAttr(p.message)}">${escapeHtml(p.label)}</button>`
    )
    .join("");
  wrap.querySelectorAll(".chat-suggestion").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = Number(btn.dataset.idx);
      const item = prompts[idx];
      if (item) sendChatMessage(item.message);
    });
  });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function escapeAttr(s) {
  return escapeHtml(s);
}

export async function sendChatMessage(text) {
  const message = text.trim();
  if (!message || processing) return;

  const requestId = crypto.randomUUID();
  appendMessage("user", message);
  history.push({ role: "user", content: message });
  setProcessing(true);
  onStatusCallback?.({ requestId, status: "started" });

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        history: history.slice(0, -1),
        request_id: requestId,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Chat failed");
    appendMessage("assistant", data.reply);
    history.push({ role: "assistant", content: data.reply });
  } catch (e) {
    appendMessage("assistant", `Sorry, something went wrong: ${e.message}`);
  } finally {
    setProcessing(false);
    onStatusCallback?.({ requestId, status: "done" });
  }
}

export function initChat(onStatus) {
  onStatusCallback = onStatus;
  const prompts = buildQuickPrompts();
  renderSuggestions(prompts);

  const input = els.input();
  const send = els.send();

  async function submit() {
    const text = input.value.trim();
    if (!text || processing) return;
    input.value = "";
    await sendChatMessage(text);
  }

  send.addEventListener("click", submit);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  });
}

export function handleChatWsEvent(ev) {
  if (ev.event === "chat_status" && ev.status === "thinking") {
    setProcessing(true);
  }
  if (ev.event === "chat_status" && ev.status === "idle") {
    setProcessing(false);
  }
}