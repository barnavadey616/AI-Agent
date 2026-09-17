// TaskFlow AI Frontend Client

let socket = null;
let currentChatAccordionBody = null;
const BACKEND_URL_KEY = "taskflow_backend_url";

// ==========================================
// Backend API Configuration & URL Helpers
// ==========================================

function getBackendUrl() {
  const saved = localStorage.getItem(BACKEND_URL_KEY);
  if (saved && saved.trim()) {
    return saved.trim().replace(/\/+$/, "");
  }
  return "";
}

function isLocalEnvironment() {
  return window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
}

function getApiUrl(path) {
  const base = getBackendUrl();
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return base ? `${base}${cleanPath}` : cleanPath;
}

function getWsUrl(path) {
  const base = getBackendUrl();
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  if (base) {
    const wsProto = base.startsWith("https:") ? "wss:" : "ws:";
    const host = base.replace(/^https?:\/\//, "").replace(/\/.*$/, "");
    return `${wsProto}//${host}${cleanPath}`;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${cleanPath}`;
}

/**
 * Robust JSON fetch wrapper that:
 * 1. Resolves backend host (Render vs localhost)
 * 2. Catches Netlify static 404 HTML responses before crashing JSON parsers
 * 3. Informs user clearly if the Render backend is sleeping or unconfigured
 */
async function safeJsonFetch(pathOrUrl, options = {}) {
  const targetUrl = (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://"))
    ? pathOrUrl
    : getApiUrl(pathOrUrl);

  let res;
  try {
    res = await fetch(targetUrl, options);
  } catch (netErr) {
    if (!isLocalEnvironment() && !getBackendUrl()) {
      showBackendBanner(true);
      openBackendModal();
      throw new Error("Backend URL is not configured. Since you are on Netlify, please click '⚙️ Backend API' above and enter your Render service URL.");
    }
    throw new Error(`Unable to reach backend server (${targetUrl}). If using Render free tier, it spins down when idle and takes ~30-50 seconds to wake up.`);
  }

  const contentType = res.headers.get("content-type") || "";
  const text = await res.text();

  // Handle HTML response (e.g. Netlify 404 Page Not Found)
  if (contentType.includes("text/html") || text.trim().startsWith("<!DOCTYPE") || text.trim().startsWith("<html")) {
    if (!isLocalEnvironment() && !getBackendUrl()) {
      showBackendBanner(true);
      openBackendModal();
      throw new Error("Backend Not Connected: Frontend is hosted on Netlify without a connected API server. Please enter your Render backend URL in ⚙️ Backend API.");
    }
    throw new Error(`Server returned HTML (${res.status} ${res.statusText}). Check if your Render backend is running and the URL is correct.`);
  }

  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = JSON.parse(text);
      errorDetail = errJson.detail || errJson.error || errJson.message || errorDetail;
    } catch (_) {}
    throw new Error(`Server error (${res.status}): ${errorDetail}`);
  }

  try {
    return JSON.parse(text);
  } catch (parseErr) {
    throw new Error("Invalid response format received from server.");
  }
}

// ==========================================
// Initialization & Backend Environment Check
// ==========================================

document.addEventListener("DOMContentLoaded", () => {
  checkBackendEnvironment();
  initWebSocket();
  fetchStatus();
  loadArtifacts();

  // Watcher checkbox change
  const watcherCheckbox = document.getElementById("watcherCheckbox");
  if (watcherCheckbox) {
    watcherCheckbox.addEventListener("change", async (e) => {
      try {
        const data = await safeJsonFetch(`/api/watcher/toggle?active=${e.target.checked}`, { method: "POST" });
        logToConsole("info", `Directory Watcher toggled: ${data.watcher_active ? "ACTIVE" : "STOPPED"}`);
      } catch (err) {
        console.error("Failed to toggle watcher", err);
        logToConsole("tool_call", `Watcher toggle failed: ${err.message}`);
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

function checkBackendEnvironment() {
  const local = isLocalEnvironment();
  const saved = getBackendUrl();
  if (!local) {
    if (!saved) {
      showBackendBanner(true);
      updateBackendIndicator("disconnected");
      const modeEl = document.getElementById("systemModeText");
      if (modeEl) modeEl.textContent = "Backend Disconnected";
    } else {
      updateBackendIndicator("pending");
      showBackendBanner(false);
    }
  } else {
    updateBackendIndicator("connected");
    showBackendBanner(false);
  }
}

// ==========================================
// Backend Settings Modal
// ==========================================

function openBackendModal() {
  const modal = document.getElementById("backendModal");
  if (modal) {
    modal.style.display = "flex";
    const input = document.getElementById("backendUrlInput");
    if (input) {
      input.value = localStorage.getItem(BACKEND_URL_KEY) || "";
      input.focus();
    }
    const fb = document.getElementById("backendTestFeedback");
    if (fb) fb.style.display = "none";
  }
}

function closeBackendModal() {
  const modal = document.getElementById("backendModal");
  if (modal) modal.style.display = "none";
}

function handleModalOverlayClick(e) {
  if (e.target.id === "backendModal") {
    closeBackendModal();
  }
}

function showBackendBanner(show) {
  const banner = document.getElementById("backendBanner");
  if (banner) banner.style.display = show ? "flex" : "none";
}

function updateBackendIndicator(status) {
  const dot = document.getElementById("backendDot");
  if (!dot) return;
  dot.classList.remove("connected", "disconnected", "pending");
  if (status === "connected") dot.classList.add("connected");
  else if (status === "disconnected") dot.classList.add("disconnected");
  else if (status === "pending") dot.classList.add("pending");
}

async function saveAndTestBackendUrl() {
  const input = document.getElementById("backendUrlInput");
  const fb = document.getElementById("backendTestFeedback");
  const saveBtn = document.getElementById("btnSaveBackend");
  const rawUrl = (input ? input.value : "").trim();

  if (!rawUrl) {
    localStorage.removeItem(BACKEND_URL_KEY);
    showBackendBanner(!isLocalEnvironment());
    updateBackendIndicator(isLocalEnvironment() ? "connected" : "disconnected");
    if (fb) {
      fb.className = "test-feedback";
      fb.textContent = "Cleared backend URL. Using relative local requests.";
      fb.style.display = "block";
    }
    setTimeout(closeBackendModal, 1200);
    fetchStatus();
    return;
  }

  let cleanUrl = rawUrl.replace(/\/+$/, "");
  if (!cleanUrl.startsWith("http://") && !cleanUrl.startsWith("https://")) {
    cleanUrl = "https://" + cleanUrl;
  }
  if (input) input.value = cleanUrl;

  if (fb) {
    fb.className = "test-feedback loading";
    fb.innerHTML = `Connecting to <code>${escapeHtml(cleanUrl)}/api/status</code>...<br><small>If Render service was sleeping, free tier wake-up takes ~30-50 seconds.</small>`;
    fb.style.display = "block";
  }
  if (saveBtn) saveBtn.disabled = true;

  try {
    const res = await fetch(`${cleanUrl}/api/status`);
    const data = await res.json();
    localStorage.setItem(BACKEND_URL_KEY, cleanUrl);
    showBackendBanner(false);
    updateBackendIndicator("connected");

    if (fb) {
      fb.className = "test-feedback success";
      fb.innerHTML = `✅ <strong>Connected!</strong> Mode: ${escapeHtml(data.mode || 'Active')}`;
    }

    if (socket) {
      socket.close();
    }
    initWebSocket();
    fetchStatus();
    loadArtifacts();

    setTimeout(closeBackendModal, 1500);
  } catch (err) {
    updateBackendIndicator("disconnected");
    if (fb) {
      fb.className = "test-feedback error";
      fb.innerHTML = `❌ <strong>Connection failed:</strong> ${escapeHtml(err.message)}<br><small>Please verify the URL and confirm the Render Web Service is running.</small>`;
    }
  } finally {
    if (saveBtn) saveBtn.disabled = false;
  }
}

function resetBackendToLocal() {
  localStorage.removeItem(BACKEND_URL_KEY);
  const input = document.getElementById("backendUrlInput");
  if (input) input.value = "";
  const fb = document.getElementById("backendTestFeedback");
  if (fb) {
    fb.className = "test-feedback";
    fb.textContent = "Reset to localhost/relative API routes.";
    fb.style.display = "block";
  }
  const local = isLocalEnvironment();
  showBackendBanner(!local);
  updateBackendIndicator(local ? "connected" : "disconnected");
  setTimeout(closeBackendModal, 1000);
  fetchStatus();
}

// ==========================================
// View Switcher
// ==========================================

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
  } else if (viewName === "knowledge") {
    document.getElementById("tabKnowledge").classList.add("active");
    document.getElementById("viewKnowledge").classList.add("active");
    loadKnowledgeDocuments();
  }
}

// Suggestion chip shortcut
function useSuggestion(text) {
  const input = document.getElementById("chatInputText");
  input.value = text;
  const agentSelector = document.getElementById("chatTargetAgent");
  if (agentSelector) agentSelector.value = "auto";
  submitChatTask();
}

// ==========================================
// ChatGPT Task Search & Dispatch
// ==========================================

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
    const data = await safeJsonFetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, target_agent: targetAgent })
    });

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
        link.href = getApiUrl(`/api/artifacts/${encodeURIComponent(art)}?type=${isReport ? 'report' : 'data'}`);
        link.target = "_blank";
        link.innerHTML = `?? Open ${escapeHtml(art)} ?`;
        linksContainer.appendChild(link);
      });
      assistantBubble.querySelector(".msg-content").appendChild(linksContainer);
    }

    // Auto-scroll
    scrollChatToBottom();
    loadArtifacts();

  } catch (err) {
    answerContainer.innerHTML = `<span style="color: #ef4444; font-weight: 500;">?? ${escapeHtml(err.message)}</span>`;
    currentChatAccordionBody = null;
  }
}

function appendUserChatMessage(text) {
  const container = document.getElementById("chatMessages");
  const msgDiv = document.createElement("div");
  msgDiv.className = "chat-msg user";
  msgDiv.innerHTML = `
    <div class="msg-avatar">??</div>
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
    <div class="msg-avatar">?</div>
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

// ==========================================
// WebSocket Connection for Real-Time Logs
// ==========================================

function initWebSocket() {
  if (!isLocalEnvironment() && !getBackendUrl()) {
    return;
  }

  const wsUrl = getWsUrl("/ws/logs");

  try {
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
      if (isLocalEnvironment() || getBackendUrl()) {
        setTimeout(initWebSocket, 4000);
      }
    };

    socket.onerror = () => {
      // Reconnection handled by onclose
    };
  } catch (err) {
    console.warn("WebSocket init error:", err);
  }
}

function handleAgentEvent(type, data) {
  if (type === "start") {
    logToConsole("thought", `?? [${data.agent || 'Agent'}] Initiated task: ${JSON.stringify(data)}`);
  } else if (type === "thought") {
    logToConsole("thought", `?? Thought: ${data.thought}`);
  } else if (type === "tool_call") {
    logToConsole("tool_call", `?? Action: ${data.tool}(${JSON.stringify(data.parameters || {})})`);
  } else if (type === "tool_result") {
    logToConsole("tool_result", `?? Observation [${data.tool}]: ${typeof data.observation === 'object' ? JSON.stringify(data.observation) : data.observation}`);
  } else if (type === "finish") {
    logToConsole("finish", `?? Task Complete! Final Summary: ${data.summary || data.final_answer || 'Finished successfully.'}`);
    loadArtifacts();
  }

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
    const data = await safeJsonFetch("/api/status");
    const modeEl = document.getElementById("systemModeText");
    if (modeEl) modeEl.textContent = data.mode;
    const badgeEl = document.getElementById("chatModelBadge");
    if (badgeEl && data.model) badgeEl.textContent = `${data.model} • ReAct Tools`;
    const watchEl = document.getElementById("watcherCheckbox");
    if (watchEl) watchEl.checked = data.watcher_active;
    updateBackendIndicator("connected");
    showBackendBanner(false);
  } catch (e) {
    const modeEl = document.getElementById("systemModeText");
    if (modeEl) {
      modeEl.textContent = !isLocalEnvironment() && !getBackendUrl()
        ? "Backend Disconnected"
        : "Reconnecting...";
    }
    updateBackendIndicator("disconnected");
  }
}

// ==========================================
// Dashboard Agent Handlers
// ==========================================

async function triggerOrganizer() {
  const source = document.getElementById("organizerSource").value.trim();
  logToConsole("thought", `Starting File Organizer on directory: ${source}`);
  try {
    const data = await safeJsonFetch("/api/run/organizer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_dir: source })
    });
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
    const data = await safeJsonFetch("/api/run/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: topic })
    });
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
    const data = await safeJsonFetch("/api/run/data-clean", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_path: file })
    });
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
    const data = await safeJsonFetch("/api/run/email-triage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
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
    const data = await safeJsonFetch("/api/run/custom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: prompt })
    });
    logToConsole("finish", `Result: ${data.final_answer || 'Completed'}`);
    loadArtifacts();
  } catch (err) {
    logToConsole("tool_call", `Error executing custom task: ${err.message}`);
  }
}

// ==========================================
// Artifacts & Reports
// ==========================================

async function loadArtifacts() {
  try {
    const artifacts = await safeJsonFetch("/api/artifacts");

    const container = document.getElementById("artifactsList");
    if (container) {
      if (!artifacts || artifacts.length === 0) {
        container.innerHTML = `<div class="empty-state">No artifacts generated yet. Run an automation agent to see reports and files here.</div>`;
      } else {
        container.innerHTML = artifacts.map(art => {
          const typeClass = art.type === "Report" ? "type-report" : "type-data";
          const resolvedUrl = getApiUrl(art.path);
          return `
            <div class="artifact-item">
              <div class="artifact-info">
                <span class="artifact-type ${typeClass}">${art.type}</span>
                <span class="artifact-name">${escapeHtml(art.name)}</span>
              </div>
              <a class="artifact-link" href="${resolvedUrl}" target="_blank">View / Open ?</a>
            </div>
          `;
        }).join("");
      }
    }

    const fullGrid = document.getElementById("artifactsFullGrid");
    if (fullGrid) {
      if (!artifacts || artifacts.length === 0) {
        fullGrid.innerHTML = `<div class="empty-state">No artifacts generated yet.</div>`;
      } else {
        fullGrid.innerHTML = artifacts.map(art => {
          const typeClass = art.type === "Report" ? "type-report" : "type-data";
          const formattedSize = Math.round(art.size_bytes / 1024) + " KB";
          const resolvedUrl = getApiUrl(art.path);
          return `
            <div class="artifact-card">
              <div class="card-top">
                <span class="artifact-type ${typeClass}">${art.type}</span>
                <span class="card-meta">${formattedSize}</span>
              </div>
              <div class="card-title">${escapeHtml(art.name)}</div>
              <a class="card-action-btn" href="${resolvedUrl}" target="_blank">View & Download ?</a>
            </div>
          `;
        }).join("");
      }
    }
  } catch (err) {
    console.error("Failed to load artifacts", err);
  }
}

// ==========================================
// Knowledge Base (RAG)
// ==========================================

async function loadKnowledgeDocuments() {
  const container = document.getElementById("knowledgeDocsList");
  if (!container) return;
  try {
    const docs = await safeJsonFetch("/api/knowledge/documents");
    if (!docs || docs.length === 0) {
      container.innerHTML = `<div class="empty-state">No documents indexed in knowledge base.</div>`;
    } else {
      container.innerHTML = docs.map(d => `
        <div class="knowledge-doc-item">
          <div>
            <div class="doc-item-title">${escapeHtml(d.title)}</div>
            <div class="doc-item-meta">${d.word_count || 0} words � ${escapeHtml((d.tags || []).join(", "))}</div>
          </div>
          <span class="rag-tag">Indexed</span>
        </div>
      `).join("");
    }
  } catch (err) {
    container.innerHTML = `<div class="empty-state" style="color: #ef4444;">Failed to load documents: ${escapeHtml(err.message)}</div>`;
  }
}

async function searchKnowledgeBase() {
  const input = document.getElementById("knowledgeSearchInput");
  const query = (input ? input.value : "").trim();
  const resultsBox = document.getElementById("knowledgeSearchResults");
  if (!query) return;

  resultsBox.innerHTML = `<div class="empty-state">Searching vector knowledge base...</div>`;
  try {
    const data = await safeJsonFetch("/api/knowledge/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, top_k: 3 })
    });
    if (!data.results || data.results.length === 0) {
      resultsBox.innerHTML = `<div class="empty-state">No relevant documents found for "${escapeHtml(query)}" (below semantic similarity threshold).</div>`;
      return;
    }
    resultsBox.innerHTML = data.results.map(r => `
      <div class="search-result-card">
        <div class="search-result-header">
          <span class="search-result-title">${escapeHtml(r.title)}</span>
          <span class="search-result-score">Score: ${r.score}</span>
        </div>
        <div class="search-result-snippet">${escapeHtml(r.snippet)}</div>
        <div class="search-result-tags">
          ${(r.tags || []).map(t => `<span class="rag-tag">#${escapeHtml(t)}</span>`).join("")}
        </div>
      </div>
    `).join("");
  } catch (err) {
    resultsBox.innerHTML = `<div class="empty-state" style="color: #ef4444;">Search error: ${escapeHtml(err.message)}</div>`;
  }
}

async function addKnowledgeDocument() {
  const title = (document.getElementById("newDocTitle")?.value || "").trim();
  const text = (document.getElementById("newDocText")?.value || "").trim();
  const tagsStr = (document.getElementById("newDocTags")?.value || "").trim();
  if (!title || !text) {
    alert("Please provide both a Title and Text content.");
    return;
  }
  const tags = tagsStr ? tagsStr.split(",").map(t => t.trim()).filter(Boolean) : [];
  try {
    const res = await safeJsonFetch("/api/knowledge/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, text, tags })
    });
    alert(`Document indexed successfully: "${res.title}"`);
    document.getElementById("newDocTitle").value = "";
    document.getElementById("newDocText").value = "";
    document.getElementById("newDocTags").value = "";
    loadKnowledgeDocuments();
  } catch (err) {
    alert(`Failed to add document: ${err.message}`);
  }
}

// ==========================================
// Formatting Utilities
// ==========================================

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
  html = html.replace(/<br>- (.*?)(?=<br>|$)/g, '<br>� $1');

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
