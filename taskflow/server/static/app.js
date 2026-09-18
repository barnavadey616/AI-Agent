// F.R.Y.D.A.Y Frontend Client

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
  initAuth();
  fetchStatus();
  loadArtifacts();
  initChatHistory();

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
// User Authentication (Login / Logout Portal)
// ==========================================
const AUTH_USER_KEY = "friday_auth_user";

function initAuth() {
  const savedUser = localStorage.getItem(AUTH_USER_KEY);
  if (savedUser) {
    applyUserLoggedIn(savedUser);
  } else {
    applyUserLoggedOut();
  }
}

function openLoginModal() {
  const modal = document.getElementById("loginModal");
  if (modal) {
    modal.style.display = "flex";
    const emailInput = document.getElementById("loginEmailInput");
    if (emailInput) {
      emailInput.focus();
    }
    const fb = document.getElementById("loginFeedback");
    if (fb) fb.style.display = "none";
  }
}

function closeLoginModal() {
  const modal = document.getElementById("loginModal");
  if (modal) modal.style.display = "none";
}

function handleLoginModalOverlayClick(e) {
  if (e.target.id === "loginModal") {
    closeLoginModal();
  }
}

function handleLoginSubmit() {
  const emailInput = document.getElementById("loginEmailInput");
  const email = (emailInput ? emailInput.value : "").trim();
  const name = email ? email.split("@")[0] : "Stark Agent";
  handleDemoLogin(name);
}

function handleDemoLogin(username) {
  localStorage.setItem(AUTH_USER_KEY, username);
  applyUserLoggedIn(username);
  closeLoginModal();
  logToConsole("info", `User authenticated as ${username}`);
}

function handleLogout() {
  localStorage.removeItem(AUTH_USER_KEY);
  applyUserLoggedOut();
  logToConsole("info", "User logged out");
}

function applyUserLoggedIn(username) {
  const btnLogin = document.getElementById("btnLogin");
  const chip = document.getElementById("userProfileChip");
  const nameEl = document.getElementById("userProfileName");

  if (btnLogin) btnLogin.style.display = "none";
  if (chip) chip.style.display = "inline-flex";
  if (nameEl) nameEl.textContent = username;
}

function applyUserLoggedOut() {
  const btnLogin = document.getElementById("btnLogin");
  const chip = document.getElementById("userProfileChip");

  if (btnLogin) btnLogin.style.display = "inline-flex";
  if (chip) chip.style.display = "none";
}

// ==========================================
// View Switcher
// ==========================================

function switchView(viewName) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".view-section").forEach(s => s.classList.remove("active"));

  const tabId = "tab" + viewName.charAt(0).toUpperCase() + viewName.slice(1);
  const viewId = "view" + viewName.charAt(0).toUpperCase() + viewName.slice(1);
  const tabEl = document.getElementById(tabId);
  const viewEl = document.getElementById(viewId);

  if (tabEl) tabEl.classList.add("active");
  if (viewEl) viewEl.classList.add("active");

  if (viewName === "artifacts") loadArtifacts();
  if (viewName === "knowledge") loadKnowledgeDocuments();
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
// ScamShield Image & Demo Handlers
// ==========================================

let currentChatAttachmentBase64 = null;
let currentChatAttachmentName = null;
let pendingScamSampleId = null;

function handleScamFileSelected(event) {
  const file = event.target.files[0];
  if (!file) return;

  currentChatAttachmentName = file.name;
  const reader = new FileReader();
  reader.onload = function(e) {
    currentChatAttachmentBase64 = e.target.result;
    const preview = document.getElementById("chatAttachmentPreview");
    const nameEl = document.getElementById("chatAttachmentName");
    if (preview && nameEl) {
      nameEl.textContent = file.name;
      preview.style.display = "inline-flex";
    }
    const agentSelector = document.getElementById("chatTargetAgent");
    if (agentSelector) agentSelector.value = "scamshield";

    const input = document.getElementById("chatInputText");
    if (input && !input.value.trim()) {
      input.value = `Investigate attached screenshot: ${file.name}`;
    }
  };
  reader.readAsDataURL(file);
}

function removeChatAttachment() {
  currentChatAttachmentBase64 = null;
  currentChatAttachmentName = null;
  const preview = document.getElementById("chatAttachmentPreview");
  if (preview) preview.style.display = "none";
  const fileInput = document.getElementById("scamFileInput");
  if (fileInput) fileInput.value = "";
}

function runAmazonScenario(scenarioId) {
  pendingScamSampleId = scenarioId;
  const agentSelector = document.getElementById("chatTargetAgent");
  if (agentSelector) agentSelector.value = "amazon_ops";

  const prompts = {
    amz_delays: "Audit middle-mile and last-mile shipments, identify why deliveries are delayed, and suggest autonomous remediation actions.",
    amz_warehouse: "Analyze warehouse metrics across ONT8, JFK8, and ORD4, detect picker rate bottlenecks and conveyor jams, and dispatch RME directives.",
    amz_customer: "Investigate customer order AMZ-1082-93821, analyze transit history and carrier exception, formulate policy-compliant concession, and draft customer response.",
    amz_returns: "Analyze return reasons across high-volume catalog products, isolate defective ASINs, and enforce vendor packaging compliance.",
    amz_seller: "Audit seller inventory health, identify critical stockouts under 5 days of supply, monitor Buy Box win rate, and calculate reorder quantities.",
    amz_supply_chain: "Monitor external NOAA storm events and interstate freight corridors, identify linehaul capacity risks, and execute automated bypass routing.",
    amz_fraud: "Audit order velocity and delivery photo POD scans to flag serial concession abuse and empty-box fraud rings for human investigator review.",
    amz_sops: "Search Amazon internal SOPs and guide operational teams on conveyor emergency stops and safe jam clearance protocols.",
    amz_daily_ops: "Generate the Amazon Operations Daily Executive Briefing and shift handoff report across network OTD, FC bottlenecks, and mitigation actions."
  };

  const input = document.getElementById("chatInputText");
  if (input) {
    input.value = prompts[scenarioId] || `Execute Amazon Operations scenario: ${scenarioId}`;
  }
  submitChatTask();
}

function runScamDemo(sampleId) {
  pendingScamSampleId = sampleId;
  const agentSelector = document.getElementById("chatTargetAgent");
  if (agentSelector) agentSelector.value = "scamshield";

  const sampleNames = {
    upi_refund: "Fake ₹25,000 UPI PIN Cashback Trap (Screenshot)",
    telegram_job: "Telegram YouTube Rating Job Scam (WhatsApp Chat)",
    electricity_cut: "Urgent Electricity Disconnection SMS Extortion",
    fedex_customs: "FedEx Narcotics Digital Arrest Customs Extortion"
  };

  const input = document.getElementById("chatInputText");
  if (input) {
    input.value = `Investigate suspected scam: ${sampleNames[sampleId] || sampleId}`;
  }
  submitChatTask();
}

// ==========================================
// ChatGPT Task Search & Dispatch
// ==========================================

async function submitChatTask() {
  const input = document.getElementById("chatInputText");
  const query = input.value.trim();
  const imageAttachment = currentChatAttachmentBase64;
  const imageName = currentChatAttachmentName;
  const sampleId = pendingScamSampleId;

  if (!query && !imageAttachment && !sampleId) return;

  const targetAgent = document.getElementById("chatTargetAgent").value;
  input.value = "";
  pendingScamSampleId = null;
  removeChatAttachment();

  // Hide hero once chat starts
  const hero = document.getElementById("chatHero");
  if (hero) hero.classList.add("hidden");

  // Create session immediately on search so the query appears in Recent Searches right away
  const queryText = query || "Investigate attached evidence";
  const activeSessionId = createOrUpdateSessionOnSearch(queryText, imageName);

  // Render User Message
  appendUserChatMessage(queryText, imageName);

  // Render Assistant Message with Loading State
  const assistantBubble = appendAssistantChatMessage();
  const reasoningBody = assistantBubble.querySelector(".reasoning-body");
  const answerContainer = assistantBubble.querySelector(".msg-text");
  currentChatAccordionBody = reasoningBody;

  try {
    const data = await safeJsonFetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: query || "Investigate suspected scam",
        target_agent: targetAgent,
        image_base64: imageAttachment,
        sample_id: sampleId
      })
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
        link.innerHTML = `📄 Open ${escapeHtml(art)} ↗`;
        linksContainer.appendChild(link);
      });
      assistantBubble.querySelector(".msg-content").appendChild(linksContainer);
    }

    // Auto-scroll
    scrollChatToBottom();
    loadArtifacts();

    // Persist assistant reply to session
    appendAssistantReplyToSession(activeSessionId, data.reply || "Task processing completed.", data.artifacts || []);

  } catch (err) {
    answerContainer.innerHTML = `<span style="color: #ef4444; font-weight: 500;">⚠️ ${escapeHtml(err.message)}</span>`;
    currentChatAccordionBody = null;
    appendAssistantReplyToSession(activeSessionId, `⚠️ ${err.message}`, []);
  }
}

function appendUserChatMessage(text, attachmentName = null) {
  const container = document.getElementById("chatMessages");
  const msgDiv = document.createElement("div");
  msgDiv.className = "chat-msg user";
  const attachBadge = attachmentName
    ? `<div class="attachment-preview" style="margin-bottom:6px;"><span class="preview-icon">🖼️</span><span>${escapeHtml(attachmentName)}</span></div>`
    : "";
  msgDiv.innerHTML = `
    <div class="msg-avatar">👤</div>
    <div class="msg-content">
      ${attachBadge}
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

// ==========================================
// ChatGPT Sidebar & Real Search History Persistence
// ==========================================

const CHAT_SESSIONS_KEY = "friday_chat_sessions";
const CURRENT_SESSION_ID_KEY = "friday_current_session_id";
const HISTORY_MIGRATION_KEY = "friday_history_v3";

function getStoredSessions() {
  // Migration check: clean up any old dummy seed sessions from previous version
  if (!localStorage.getItem(HISTORY_MIGRATION_KEY)) {
    localStorage.removeItem(CHAT_SESSIONS_KEY);
    localStorage.removeItem(CURRENT_SESSION_ID_KEY);
    localStorage.setItem(HISTORY_MIGRATION_KEY, "true");
    return [];
  }

  const raw = localStorage.getItem(CHAT_SESSIONS_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (e) {
    console.error("Error parsing stored sessions", e);
    return [];
  }
}

function saveStoredSessions(sessions) {
  try {
    localStorage.setItem(CHAT_SESSIONS_KEY, JSON.stringify(sessions));
  } catch (e) {
    console.error("Error saving chat sessions", e);
  }
}

function getCurrentSessionId() {
  return localStorage.getItem(CURRENT_SESSION_ID_KEY) || null;
}

function setCurrentSessionId(id) {
  if (id) {
    localStorage.setItem(CURRENT_SESSION_ID_KEY, id);
  } else {
    localStorage.removeItem(CURRENT_SESSION_ID_KEY);
  }
}

function initChatHistory() {
  const sessions = getStoredSessions();
  const currentId = getCurrentSessionId();

  // Attach recents list click delegation
  const recentsList = document.getElementById("recentsList");
  if (recentsList) {
    recentsList.removeEventListener("click", handleRecentsListClick);
    recentsList.addEventListener("click", handleRecentsListClick);
  }

  renderRecentsList();

  // Only restore previous session if one actually exists in user's saved searches
  if (currentId && sessions.some(s => s.id === currentId)) {
    loadChatSession(currentId);
  } else {
    startNewChat();
  }
}

function renderRecentsList() {
  const container = document.getElementById("recentsList");
  const clearBtn = document.getElementById("btnClearAllRecents");
  if (!container) return;
  const sessions = getStoredSessions();
  const currentId = getCurrentSessionId();

  if (clearBtn) {
    clearBtn.style.display = sessions.length > 0 ? "inline-block" : "none";
  }

  if (sessions.length === 0) {
    container.innerHTML = `
      <div class="empty-recents-state">
        <span class="empty-icon">🔍</span>
        <span>No recent searches yet.<br><small>Your search queries will appear here.</small></span>
      </div>
    `;
    return;
  }

  container.innerHTML = sessions.map(session => {
    const isActive = session.id === currentId ? "active" : "";
    return `
      <div class="recent-chat-item ${isActive}" data-session-id="${escapeHtml(session.id)}" title="${escapeHtml(session.title)}">
        <div class="recent-title-group">
          <span class="recent-dot"></span>
          <span class="recent-title">${escapeHtml(session.title)}</span>
        </div>
        <button class="recent-delete-btn" data-delete-id="${escapeHtml(session.id)}" title="Remove search">✕</button>
      </div>
    `;
  }).join("");
}

function handleRecentsListClick(e) {
  const deleteBtn = e.target.closest("[data-delete-id]");
  if (deleteBtn) {
    e.stopPropagation();
    const id = deleteBtn.getAttribute("data-delete-id");
    deleteChatSession(id);
    return;
  }

  const item = e.target.closest("[data-session-id]");
  if (item) {
    const id = item.getAttribute("data-session-id");
    loadChatSession(id);
  }
}

function startNewChat() {
  setCurrentSessionId(null);
  
  // Clear messages
  const container = document.getElementById("chatMessages");
  if (container) container.innerHTML = "";

  // Show hero
  const hero = document.getElementById("chatHero");
  if (hero) hero.classList.remove("hidden");

  // Focus input
  const input = document.getElementById("chatInputText");
  if (input) {
    input.value = "";
    input.focus();
  }

  removeChatAttachment();
  pendingScamSampleId = null;

  renderRecentsList();
  closeSidebar();
}

function loadChatSession(sessionId) {
  const sessions = getStoredSessions();
  const session = sessions.find(s => s.id === sessionId);
  if (!session) return;

  setCurrentSessionId(sessionId);

  // Hide hero
  const hero = document.getElementById("chatHero");
  if (hero) hero.classList.add("hidden");

  // Clear messages container
  const container = document.getElementById("chatMessages");
  if (!container) return;
  container.innerHTML = "";

  // Render each message from history
  if (session.messages && session.messages.length > 0) {
    session.messages.forEach(msg => {
      if (msg.role === "user") {
        appendUserChatMessage(msg.text, msg.attachmentName);
      } else if (msg.role === "assistant") {
        renderStoredAssistantMessage(msg.text, msg.artifacts);
      }
    });
  }

  scrollChatToBottom();
  renderRecentsList();
  closeSidebar();
}

function renderStoredAssistantMessage(text, artifacts = []) {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  const msgDiv = document.createElement("div");
  msgDiv.className = "chat-msg assistant";
  msgDiv.innerHTML = `
    <div class="msg-avatar">⚡</div>
    <div class="msg-content">
      <div class="msg-text">${formatMarkdown(text || "")}</div>
    </div>
  `;

  if (artifacts && artifacts.length > 0) {
    const linksContainer = document.createElement("div");
    linksContainer.className = "chat-artifacts-links";
    artifacts.forEach(art => {
      if (!art) return;
      const link = document.createElement("a");
      link.className = "artifact-pill-btn";
      const isReport = art.endsWith(".html") || art.endsWith(".md") || art.endsWith(".json");
      link.href = getApiUrl(`/api/artifacts/${encodeURIComponent(art)}?type=${isReport ? 'report' : 'data'}`);
      link.target = "_blank";
      link.innerHTML = `📄 Open ${escapeHtml(art)} ↗`;
      linksContainer.appendChild(link);
    });
    msgDiv.querySelector(".msg-content").appendChild(linksContainer);
  }

  container.appendChild(msgDiv);
}

function createOrUpdateSessionOnSearch(queryText, attachmentName) {
  const sessions = getStoredSessions();
  let currentId = getCurrentSessionId();
  let session = currentId ? sessions.find(s => s.id === currentId) : null;

  if (!session) {
    // Generate new session with title derived from user query
    currentId = "session_" + Date.now();
    let title = (queryText || "Search query").trim().replace(/\s+/g, " ");
    if (title.length > 30) {
      title = title.substring(0, 30) + "…";
    }
    session = {
      id: currentId,
      title: title,
      timestamp: Date.now(),
      messages: []
    };
    sessions.unshift(session);
    setCurrentSessionId(currentId);
  } else {
    // Move active session to top of list and update timestamp
    session.timestamp = Date.now();
    const idx = sessions.findIndex(s => s.id === currentId);
    if (idx > 0) {
      sessions.splice(idx, 1);
      sessions.unshift(session);
    }
  }

  session.messages.push({
    role: "user",
    text: queryText,
    attachmentName: attachmentName || null
  });

  saveStoredSessions(sessions);
  renderRecentsList();
  return currentId;
}

function appendAssistantReplyToSession(sessionId, replyText, artifacts = []) {
  const sessions = getStoredSessions();
  const session = sessions.find(s => s.id === sessionId);
  if (!session) return;

  session.messages.push({
    role: "assistant",
    text: replyText,
    artifacts: artifacts || []
  });

  saveStoredSessions(sessions);
  renderRecentsList();
}

function deleteChatSession(sessionId, event) {
  if (event) event.stopPropagation();
  let sessions = getStoredSessions();
  sessions = sessions.filter(s => s.id !== sessionId);
  saveStoredSessions(sessions);

  const currentId = getCurrentSessionId();
  if (currentId === sessionId) {
    startNewChat();
  } else {
    renderRecentsList();
  }
}

function exportChatHistory() {
  const sessions = getStoredSessions();
  const blob = new Blob([JSON.stringify(sessions, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `friday_chat_history_${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function clearAllChatHistory() {
  if (confirm("Are you sure you want to remove all your recent searches?")) {
    localStorage.removeItem(CHAT_SESSIONS_KEY);
    localStorage.removeItem(CURRENT_SESSION_ID_KEY);
    startNewChat();
    renderRecentsList();
  }
}

// ==========================================
// Sidebar Drawer & Modal Handlers
// ==========================================

function toggleSidebar() {
  const sidebar = document.getElementById("appSidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  if (!sidebar) return;

  if (window.innerWidth <= 900) {
    // Mobile / tablet drawer mode
    const isOpen = sidebar.classList.contains("open");
    if (isOpen) {
      closeSidebar();
    } else {
      sidebar.classList.add("open");
      if (backdrop) backdrop.classList.add("active");
    }
  } else {
    // Desktop collapsible mode
    document.body.classList.toggle("sidebar-collapsed");
  }
}

function closeSidebar() {
  const sidebar = document.getElementById("appSidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  if (sidebar) sidebar.classList.remove("open");
  if (backdrop) backdrop.classList.remove("active");
}

function getSidebarModalEl(typeOrId) {
  if (!typeOrId) return null;
  if (document.getElementById(typeOrId)) return document.getElementById(typeOrId);
  const mapped = "sidebar" + typeOrId.charAt(0).toUpperCase() + typeOrId.slice(1) + "Modal";
  return document.getElementById(mapped);
}

function openSidebarModal(typeOrId) {
  const modal = getSidebarModalEl(typeOrId);
  if (modal) {
    modal.style.display = "flex";
  }
}

function closeSidebarModal(typeOrId) {
  const modal = getSidebarModalEl(typeOrId);
  if (modal) {
    modal.style.display = "none";
  }
}

function handleSidebarModalOverlayClick(e, typeOrId) {
  const modal = getSidebarModalEl(typeOrId);
  if (modal && e.target === modal) {
    closeSidebarModal(typeOrId);
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

async function triggerHubScamInvestigation() {
  const sampleSelect = document.getElementById("hubScamSampleSelect");
  const customInput = document.getElementById("hubScamCustomText");
  const sampleId = sampleSelect ? sampleSelect.value : "upi_refund";
  const customText = customInput ? customInput.value.trim() : "";

  logToConsole("thought", `Launching ScamShield Forensic Investigation (Target: ${customText ? 'Custom Text' : sampleId})...`);
  try {
    const payload = {};
    if (customText) {
      payload.text = customText;
    } else if (sampleId) {
      payload.sample_id = sampleId;
    }

    const data = await safeJsonFetch("/api/run/scam-shield", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    logToConsole("finish", `🛡️ ScamShield Verdict: ${data.verdict} (Risk: ${data.risk_score}/100) — ${data.primary_pattern}`);
    loadArtifacts();
  } catch (err) {
    logToConsole("tool_call", `Error running ScamShield investigation: ${err.message}`);
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
