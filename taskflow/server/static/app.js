// TaskFlow AI Frontend Client

let socket = null;
let currentChatAccordionBody = null;

document.addEventListener("DOMContentLoaded", () => {
  initWebSocket();
  fetchStatus();
  loadArtifacts();

  // Watcher checkbox change
  const watcherCheckbox = document.getElementById("watcherCheckbox");
  if (watcherCheckbox) {
    watcherCheckbox.addEventListener("change", async (e) => {
      try {
        const res = await fetch(`/api/watcher/toggle?active=${e.target.checked}`, { method: "POST" });
        const data = await res.json();
        logToConsole("info", `Directory Watcher toggled: ${data.watcher_active ? "ACTIVE" : "STOPPED"}`);
      } catch (err) {
        console.error("Failed to toggle watcher", err);
      }
    });
  }

  // Keyboard shortcut for ChatGPT input: Enter to send, Shift+Enter for newline
  const chatInput = document.getElementById("chatInputText");
  if (chatInput) {
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submitChatTask();
      }
    });
  }
});

// View Switcher
function switchView(viewName) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".view-section").forEach(s => s.classList.remove("active"));

  if (viewName === "chat") {
    document.getElementById("tabChat").classList.add("active");
    document.getElementById("viewChat").classList.add("active");
  } else if (viewName === "dashboard") {
    document.getElementById("tabDashboard").classList.add("active");
    document.getElementById("viewDashboard").classList.add("active");
  } else if (viewName === "artifacts") {
    document.getElementById("tabArtifacts").classList.add("active");
    document.getElementById("viewArtifacts").classList.add("active");
    loadArtifacts();
  }
}

// Suggestion chip shortcut
function useSuggestion(text) {
  const input = document.getElementById("chatInputText");
  input.value = text;
  submitChatTask();
}

// Submit prompt from ChatGPT Search space
async function submitChatTask() {
  const input = document.getElementById("chatInputText");
  const query = input.value.trim();
  if (!query) return;

  const targetAgent = document.getElementById("chatTargetAgent").value;
  input.value = "";

  // Hide hero once chat starts
  const hero = document.getElementById("chatHero");
  if (hero) hero.classList.add("hidden");

  // Render User Message
  appendUserChatMessage(query);

  // Render Assistant Message with Loading State
  const assistantBubble = appendAssistantChatMessage();
  const reasoningBody = assistantBubble.querySelector(".reasoning-body");
  const answerContainer = assistantBubble.querySelector(".msg-text");
  currentChatAccordionBody = reasoningBody;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, target_agent: targetAgent })
    });

    const data = await res.json();
    currentChatAccordionBody = null;

    // Render Answer
    answerContainer.innerHTML = formatMarkdown(data.reply || "Task processing completed.");

    // Render Artifact links if available
    if (data.artifacts && data.artifacts.length > 0) {
      const linksContainer = document.createElement("div");
      linksContainer.className = "chat-artifacts-links";
      
      data.artifacts.forEach(art => {
        if (!art) return;
        const link = document.createElement("a");
        link.className = "artifact-pill-btn";
        const isReport = art.endsWith(".html") || art.endsWith(".md") || art.endsWith(".json");
        link.href = `/api/artifacts/${art}?type=${isReport ? 'report' : 'data'}`;
        link.target = "_blank";
        link.innerHTML = `📄 Open ${escapeHtml(art)} ↗`;
        linksContainer.appendChild(link);
      });
      assistantBubble.querySelector(".msg-content").appendChild(linksContainer);
    }

    // Auto-scroll
    scrollChatToBottom();
    loadArtifacts();

  } catch (err) {
    answerContainer.innerHTML = `<span style="color: #ef4444;">Error executing task: ${escapeHtml(err.message)}</span>`;
    currentChatAccordionBody = null;
  }
}

function appendUserChatMessage(text) {
  const container = document.getElementById("chatMessages");
  const msgDiv = document.createElement("div");
  msgDiv.className = "chat-msg user";
  msgDiv.innerHTML = `
    <div class="msg-avatar">👤</div>
    <div class="msg-content">
      <p>${escapeHtml(text)}</p>
    </div>
  `;
  container.appendChild(msgDiv);
  scrollChatToBottom();
}

function appendAssistantChatMessage() {
  const container = document.getElementById("chatMessages");
  const msgDiv = document.createElement("div");
  msgDiv.className = "chat-msg assistant";
  msgDiv.innerHTML = `
    <div class="msg-avatar">⚡</div>
    <div class="msg-content">
      <details class="reasoning-accordion" open>
        <summary class="reasoning-summary">
          <span class="pulse-dot" style="display: inline-block;"></span>
          <span>Agent Reasoning & Tool Execution Steps</span>
        </summary>
        <div class="reasoning-body">
          <em>Decomposing task and initializing specialized agent...</em>
        </div>
      </details>
      <div class="msg-text">
        <span class="pulsing-text">Analyzing instructions & executing tools...</span>
      </div>
    </div>
  `;
  container.appendChild(msgDiv);
  scrollChatToBottom();
  return msgDiv;
}

function scrollChatToBottom() {
  const container = document.getElementById("chatMessages");
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
}

// WebSocket connection for real-time logs
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
  
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    logToConsole("info", "WebSocket log stream connected.");
  };

  socket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleAgentEvent(msg.event, msg.data);
    } catch (e) {
      console.error("Error parsing WS message", e);
    }
  };

  socket.onclose = () => {
    logToConsole("info", "WebSocket stream disconnected. Reconnecting in 3s...");
    setTimeout(initWebSocket, 3000);
  };
}

function handleAgentEvent(type, data) {
  // 1. Log to the right-hand console
  if (type === "start") {
    logToConsole("thought", `🚀 [${data.agent || 'Agent'}] Initiated task: ${JSON.stringify(data)}`);
  } else if (type === "thought") {
    logToConsole("thought", `🧠 Thought: ${data.thought}`);
  } else if (type === "tool_call") {
    logToConsole("tool_call", `🔧 Action: ${data.tool}(${JSON.stringify(data.parameters || {})})`);
  } else if (type === "tool_result") {
    logToConsole("tool_result", `📦 Observation [${data.tool}]: ${typeof data.observation === 'object' ? JSON.stringify(data.observation) : data.observation}`);
  } else if (type === "finish") {
    logToConsole("finish", `🏁 Task Complete! Final Summary: ${data.summary || data.final_answer || 'Finished successfully.'}`);
    loadArtifacts();
  }

  // 2. Stream steps directly into the active ChatGPT reasoning accordion if open
  if (currentChatAccordionBody) {
    const stepLine = document.createElement("div");
    stepLine.style.marginBottom = "4px";
    if (type === "thought") {
      stepLine.innerHTML = `<span style="color: #60a5fa;">[Reasoning]</span> ${escapeHtml(data.thought)}`;
    } else if (type === "tool_call") {
      stepLine.innerHTML = `<span style="color: #fde047;">[Tool Invoked]</span> <strong>${escapeHtml(data.tool)}</strong>`;
    } else if (type === "tool_result") {
      stepLine.innerHTML = `<span style="color: #86efac;">[Tool Result]</span> ${escapeHtml(typeof data.observation === 'object' ? JSON.stringify(data.observation) : String(data.observation))}`;
    }
    currentChatAccordionBody.appendChild(stepLine);
    scrollChatToBottom();
  }
}

function logToConsole(category, text) {
  const box = document.getElementById("consoleBox");
  if (!box) return;
  const time = new Date().toLocaleTimeString();
  const line = document.createElement("div");
  line.className = `log-line ${category}`;
  line.innerHTML = `<span class="log-badge">[${time}]</span> ${escapeHtml(text)}`;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}

function clearLogs() {
  const box = document.getElementById("consoleBox");
  if (box) {
    box.innerHTML = "";
    logToConsole("info", "Console cleared.");
  }
}

async function fetchStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    const modeEl = document.getElementById("systemModeText");
    if (modeEl) modeEl.textContent = data.mode;
    const watchEl = document.getElementById("watcherCheckbox");
    if (watchEl) watchEl.checked = data.watcher_active;
  } catch (e) {
    const modeEl = document.getElementById("systemModeText");
    if (modeEl) modeEl.textContent = "Offline / Standalone";
  }
}

// Card Trigger Handlers for Dashboard View
async function triggerOrganizer() {
  const source = document.getElementById("organizerSource").value.trim();
  logToConsole("thought", `Starting File Organizer on directory: ${source}`);
  try {
    const res = await fetch("/api/run/organizer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_dir: source })
    });
    const data = await res.json();
    logToConsole("finish", `Organizer Finished: Processed ${data.total_processed || 0} files. ${data.summary || ''}`);
    loadArtifacts();
  } catch (err) {
    logToConsole("tool_call", `Error running organizer: ${err.message}`);
  }
}

async function triggerResearch() {
  const topic = document.getElementById("researchTopic").value.trim();
  if (!topic) return alert("Please enter a research topic.");
  logToConsole("thought", `Launching Research Agent for topic: "${topic}"`);
  try {
    const res = await fetch("/api/run/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: topic })
    });
    const data = await res.json();
    logToConsole("finish", `Research Complete: Generated brief with ${data.sources_analyzed || 0} sources.`);
    loadArtifacts();
  } catch (err) {
    logToConsole("tool_call", `Error running research: ${err.message}`);
  }
}

async function triggerDataClean() {
  const file = document.getElementById("dataCleanFile").value.trim();
  logToConsole("thought", `Triggering Data Hygiene & Anomaly Cleaner on: ${file}`);
  try {
    const res = await fetch("/api/run/data-clean", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_path: file })
    });
    const data = await res.json();
    if (data.success) {
      logToConsole("finish", `Data Scrub Complete: ${data.changes?.duplicates_removed} duplicates removed, ${data.changes?.final_rows} valid records saved.`);
    } else {
      logToConsole("tool_call", `Scrubbing failed: ${data.error}`);
    }
    loadArtifacts();
  } catch (err) {
    logToConsole("tool_call", `Error running data cleaner: ${err.message}`);
  }
}

async function triggerEmailTriage() {
  logToConsole("thought", "Starting Email & Customer Query Triage Agent...");
  try {
    const res = await fetch("/api/run/email-triage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await res.json();
    logToConsole("finish", `Triage Finished: Triaged ${data.total_processed} items. High Urgency: ${data.high_urgency_count}.`);
    loadArtifacts();
  } catch (err) {
    logToConsole("tool_call", `Error running email triage: ${err.message}`);
  }
}

async function triggerCustomTask() {
  const prompt = document.getElementById("customPrompt").value.trim();
  if (!prompt) return alert("Please enter a task instruction.");
  logToConsole("thought", `Executing custom prompt: "${prompt}"`);
  try {
    const res = await fetch("/api/run/custom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: prompt })
    });
    const data = await res.json();
    logToConsole("finish", `Result: ${data.final_answer || 'Completed'}`);
    loadArtifacts();
  } catch (err) {
    logToConsole("tool_call", `Error executing custom task: ${err.message}`);
  }
}

// Load and populate artifacts
async function loadArtifacts() {
  try {
    const res = await fetch("/api/artifacts");
    const artifacts = await res.json();
    
    // 1. Sidebar List
    const container = document.getElementById("artifactsList");
    if (container) {
      if (!artifacts || artifacts.length === 0) {
        container.innerHTML = `<div class="empty-state">No artifacts generated yet. Run an automation agent to see reports and files here.</div>`;
      } else {
        container.innerHTML = artifacts.map(art => {
          const typeClass = art.type === "Report" ? "type-report" : "type-data";
          return `
            <div class="artifact-item">
              <div class="artifact-info">
                <span class="artifact-type ${typeClass}">${art.type}</span>
                <span class="artifact-name">${escapeHtml(art.name)}</span>
              </div>
              <a class="artifact-link" href="${art.path}" target="_blank">View / Open ↗</a>
            </div>
          `;
        }).join("");
      }
    }

    // 2. Full Gallery Grid
    const fullGrid = document.getElementById("artifactsFullGrid");
    if (fullGrid) {
      if (!artifacts || artifacts.length === 0) {
        fullGrid.innerHTML = `<div class="empty-state">No artifacts generated yet.</div>`;
      } else {
        fullGrid.innerHTML = artifacts.map(art => {
          const typeClass = art.type === "Report" ? "type-report" : "type-data";
          const formattedSize = Math.round(art.size_bytes / 1024) + " KB";
          return `
            <div class="artifact-card">
              <div class="card-top">
                <span class="artifact-type ${typeClass}">${art.type}</span>
                <span class="card-meta">${formattedSize}</span>
              </div>
              <div class="card-title">${escapeHtml(art.name)}</div>
              <a class="card-action-btn" href="${art.path}" target="_blank">View & Download ↗</a>
            </div>
          `;
        }).join("");
      }
    }
  } catch (err) {
    console.error("Failed to load artifacts", err);
  }
}

// Helper: Basic Markdown formatting
function formatMarkdown(text) {
  if (!text) return "";
  let html = escapeHtml(text);

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Italic
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  // Code blocks
  html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
  // Inline code
  html = html.replace(/`(.*?)`/g, '<code>$1</code>');
  // Line breaks
  html = html.replace(/\n/g, '<br>');
  // Unordered list items
  html = html.replace(/<br>- (.*?)(?=<br>|$)/g, '<br>• $1');

  return html;
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
