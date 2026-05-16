const PHASE_META = [
  { key: "job_collection", label: "岗位收集" },
  { key: "profile_collection", label: "画像补充" },
  { key: "story_simulation", label: "剧情模拟" },
  { key: "completed", label: "结局完成" },
];

const API_BASE = window.location.protocol === "file:" ? "http://localhost:8000" : "";

const state = {
  username: "",
  phase: "",
  lastActive: "",
  createdAt: "",
  jobInput: null,
  userProfile: null,
  profileSkipped: false,
  conversationHistory: [],
  storyState: {
    meta: null,
    current_node_id: null,
    generated_nodes: {},
    choices: [],
    scores: { fit: 0, stress: 0, growth: 0 },
  },
  streaming: false,
  pendingAssistantId: null,
  pendingOptions: null,
};

const els = {
  workspace: document.getElementById("workspace"),
  usernameForm: document.getElementById("username-form"),
  usernameInput: document.getElementById("username-input"),
  startButton: document.getElementById("start-button"),
  entryStatus: document.getElementById("entry-status"),
  sidebarUsername: document.getElementById("sidebar-username"),
  sidebarPhase: document.getElementById("sidebar-phase"),
  sidebarLastActive: document.getElementById("sidebar-last-active"),
  phaseRail: document.getElementById("phase-rail"),
  jobSummary: document.getElementById("job-summary"),
  scoreFit: document.getElementById("score-fit"),
  scoreStress: document.getElementById("score-stress"),
  scoreGrowth: document.getElementById("score-growth"),
  choiceTimeline: document.getElementById("choice-timeline"),
  boardTitle: document.getElementById("board-title"),
  globalStatus: document.getElementById("global-status"),
  restartButton: document.getElementById("restart-button"),
  chatPanel: document.getElementById("chat-panel"),
  chatStream: document.getElementById("chat-stream"),
  chatForm: document.getElementById("chat-form"),
  chatInput: document.getElementById("chat-input"),
  sendButton: document.getElementById("send-button"),
  skipProfileButton: document.getElementById("skip-profile-button"),
  storyPanel: document.getElementById("story-panel"),
  storyMeta: document.getElementById("story-meta"),
  storyStage: document.getElementById("story-stage"),
  resumeDialog: document.getElementById("resume-dialog"),
  resumeTitle: document.getElementById("resume-title"),
  resumeCopy: document.getElementById("resume-copy"),
  resumeContinue: document.getElementById("resume-continue"),
  resumeReset: document.getElementById("resume-reset"),
  adminPanel: document.getElementById("admin-panel"),
  adminUserList: document.getElementById("admin-user-list"),
  adminDetail: document.getElementById("admin-detail"),
  adminLogout: document.getElementById("admin-logout"),
};

els.usernameForm.addEventListener("submit", onUsernameSubmit);
els.chatForm.addEventListener("submit", onChatSubmit);
els.skipProfileButton.addEventListener("click", onSkipProfile);
els.restartButton.addEventListener("click", onRestartJourney);
els.storyStage.addEventListener("click", onStoryStageClick);
els.adminLogout.addEventListener("click", exitAdminMode);
els.resumeContinue.addEventListener("click", (event) => {
  event.preventDefault();
  closeResumeDialog();
  void loadExistingSession(state.username);
});
els.resumeReset.addEventListener("click", (event) => {
  event.preventDefault();
  closeResumeDialog();
  void resetSession(state.username);
});

render();

async function onUsernameSubmit(event) {
  event.preventDefault();
  if (state.streaming) {
    return;
  }

  const input = els.usernameInput.value.trim();
  if (!input) {
    setEntryStatus("请输入用户名。", "error");
    return;
  }

  lockEntry(true);
  setEntryStatus("正在检查历史状态...", "");

  const adminToken = await tryAdminAuth(input);
  if (adminToken) {
    lockEntry(false);
    els.usernameInput.value = "";
    setEntryStatus("", "");
    enterAdminMode(adminToken);
    return;
  }

  try {
    const { response, data } = await requestJson(apiUrl("/api/users"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: input }),
    });

    if (!response.ok) {
      throw new Error(data.error || "无法创建用户");
    }

    state.username = data.username;
    if (data.status === "exists") {
      showResumeDialog(data);
    } else {
      applyFreshSession(data);
      setEntryStatus(`欢迎回来，${data.username}。`, "success");
    }
  } catch (error) {
    setEntryStatus(error.message, "error");
  } finally {
    lockEntry(false);
  }
}

async function onChatSubmit(event) {
  event.preventDefault();
  if (state.streaming) {
    return;
  }

  const message = els.chatInput.value.trim();
  if (!message || !state.username) {
    return;
  }

  els.chatStream.querySelectorAll(".chat-options").forEach((el) => el.remove());
  state.pendingOptions = null;
  addChatMessage("user", message);
  state.conversationHistory.push({ role: "user", content: message });
  els.chatInput.value = "";

  const assistantId = addChatMessage("assistant", "");
  state.pendingAssistantId = assistantId;
  setStreaming(true);
  setGlobalStatus("小可正在回复...", "");

  try {
    await streamJsonEvents(apiUrl(`/api/users/${encodeURIComponent(state.username)}/chat/stream`), {
      message,
    }, handleChatEvent);
    syncPendingAssistant();
  } catch (error) {
    setGlobalStatus(error.message, "error");
    removeEmptyPendingMessage();
  } finally {
    setStreaming(false);
    render();
  }

  refreshState().catch(() => {});
}

async function onSkipProfile() {
  if (state.streaming || !state.username) {
    return;
  }

  setStreaming(true);
  setGlobalStatus("正在跳过画像阶段...", "");
  try {
    const { response, data } = await requestJson(apiUrl(`/api/users/${encodeURIComponent(state.username)}/skip-profile`), {
      method: "POST",
    });
    if (!response.ok) {
      throw new Error(data.error || "跳过画像失败");
    }

    state.phase = data.phase;
    addChatMessage("assistant", data.message);
    state.conversationHistory.push({ role: "assistant", content: data.message });
    await refreshState();
    setGlobalStatus("已进入剧情模拟阶段。", "success");
    render();
  } catch (error) {
    setGlobalStatus(error.message, "error");
  } finally {
    setStreaming(false);
  }
}

async function onRestartJourney() {
  if (!state.username || state.streaming) {
    return;
  }
  await resetSession(state.username);
}

async function loadExistingSession(username) {
  setGlobalStatus("正在恢复你的旅程...", "");
  try {
    const { response, data } = await requestJson(apiUrl(`/api/users/${encodeURIComponent(username)}/state`));
    if (!response.ok) {
      throw new Error(data.error || "恢复失败");
    }
    hydrateState(data);
    setEntryStatus(`已恢复 ${username} 的历史状态。`, "success");
    setGlobalStatus("历史状态已恢复。", "success");
  } catch (error) {
    setEntryStatus(error.message, "error");
    setGlobalStatus(error.message, "error");
  }
}

async function resetSession(username) {
  setGlobalStatus("正在重新开始...", "");
  try {
    const { response, data } = await requestJson(apiUrl(`/api/users/${encodeURIComponent(username)}/reset`), {
      method: "POST",
    });
    if (!response.ok) {
      throw new Error(data.error || "重置失败");
    }
    applyFreshSession(data);
    setEntryStatus(`已重置 ${username} 的旅程。`, "success");
    setGlobalStatus("你可以重新描述岗位信息了。", "success");
  } catch (error) {
    setEntryStatus(error.message, "error");
    setGlobalStatus(error.message, "error");
  }
}

function applyFreshSession(payload) {
  state.username = payload.username;
  state.phase = payload.phase;
  state.createdAt = new Date().toISOString();
  state.lastActive = state.createdAt;
  state.jobInput = null;
  state.userProfile = null;
  state.profileSkipped = false;
  state.conversationHistory = [];
  state.storyState = {
    meta: null,
    current_node_id: null,
    generated_nodes: {},
    choices: [],
    scores: { fit: 0, stress: 0, growth: 0 },
  };
  state.pendingAssistantId = null;

  els.workspace.classList.remove("hidden");
  els.chatStream.innerHTML = "";
  if (payload.greeting) {
    addChatMessage("assistant", payload.greeting);
    state.conversationHistory.push({ role: "assistant", content: payload.greeting });
    const greetingOptions = extractOptionsFromText(payload.greeting);
    if (greetingOptions.length) {
      state.pendingOptions = greetingOptions;
      renderChatOptions(greetingOptions);
    }
  }
  render();
}

function hydrateState(payload) {
  state.username = payload.username;
  const currentIndex = PHASE_META.findIndex((item) => item.key === state.phase);
  const incomingIndex = PHASE_META.findIndex((item) => item.key === payload.phase);
  if (incomingIndex >= currentIndex || currentIndex === -1) {
    state.phase = payload.phase;
  }
  state.createdAt = payload.created_at || "";
  state.lastActive = payload.last_active || "";
  state.jobInput = payload.job_input || null;
  state.userProfile = payload.user_profile || null;
  state.profileSkipped = Boolean(payload.profile_skipped);

  const incomingHistory = Array.isArray(payload.conversation_history)
    ? payload.conversation_history.slice()
    : [];
  const historyChanged =
    incomingHistory.length !== state.conversationHistory.length ||
    JSON.stringify(incomingHistory[incomingHistory.length - 1]) !==
      JSON.stringify(state.conversationHistory[state.conversationHistory.length - 1]);
  state.conversationHistory = incomingHistory;
  state.storyState = payload.story_state || state.storyState;
  state.pendingAssistantId = null;

  if (isChatPhase(state.phase) && state.conversationHistory.length) {
    const lastAssistant = [...state.conversationHistory].reverse().find((m) => m.role === "assistant");
    if (lastAssistant) {
      const opts = extractOptionsFromText(lastAssistant.content);
      state.pendingOptions = opts.length ? opts : null;
    }
  } else {
    state.pendingOptions = null;
  }

  els.workspace.classList.remove("hidden");
  if (historyChanged) {
    rebuildChatStream();
  }
  render();
}

function render() {
  renderSidebar();
  renderBoard();
}

function renderSidebar() {
  els.sidebarUsername.textContent = state.username || "-";
  els.sidebarPhase.textContent = phaseLabel(state.phase);
  els.sidebarLastActive.textContent = state.lastActive
    ? `最近活动：${formatDateTime(state.lastActive)}`
    : "";

  els.phaseRail.innerHTML = PHASE_META.map((phase) => {
    const index = PHASE_META.findIndex((item) => item.key === phase.key);
    const currentIndex = PHASE_META.findIndex((item) => item.key === state.phase);
    const className = currentIndex === index ? "phase-chip active" : currentIndex > index ? "phase-chip done" : "phase-chip";
    return `<div class="${className}">${phase.label}</div>`;
  }).join("");

  if (state.jobInput) {
    els.jobSummary.classList.remove("empty-copy");
    els.jobSummary.innerHTML = [
      renderSummaryLine("岗位", state.jobInput.role_name),
      renderSummaryLine("日常任务", state.jobInput.job_tasks),
      renderSummaryLine("行业", state.jobInput.industry),
      renderSummaryLine("公司规模", state.jobInput.company_size),
      renderSummaryLine("补充信息", state.jobInput.additional_context),
    ].filter(Boolean).join("");
  } else {
    els.jobSummary.className = "summary-block empty-copy";
    els.jobSummary.textContent = "完成岗位收集后会显示。";
  }

  const scores = state.storyState?.scores || { fit: 0, stress: 0, growth: 0 };
  els.scoreFit.textContent = String(scores.fit || 0);
  els.scoreStress.textContent = String(scores.stress || 0);
  els.scoreGrowth.textContent = String(scores.growth || 0);

  const choices = state.storyState?.choices || [];
  if (!choices.length) {
    els.choiceTimeline.className = "timeline empty-copy";
    els.choiceTimeline.textContent = "剧情开始后会逐步记录。";
  } else {
    els.choiceTimeline.className = "timeline";
    els.choiceTimeline.innerHTML = choices.map((choice, index) => {
      return `<div class="timeline-item">${index + 1}. ${escapeHtml(choice.choice_label || choice.choice_key || "")}</div>`;
    }).join("");
  }
}

function renderBoard() {
  els.restartButton.classList.toggle("hidden", !state.username);
  els.chatPanel.classList.toggle("hidden", !isChatPhase(state.phase));
  els.storyPanel.classList.toggle("hidden", !isStoryPhase(state.phase));
  els.skipProfileButton.classList.toggle("hidden", state.phase !== "profile_collection");

  if (state.phase === "job_collection") {
    els.boardTitle.textContent = "先把岗位说清楚";
    els.chatInput.placeholder = "";
  } else if (state.phase === "profile_collection") {
    els.boardTitle.textContent = "再补充一点你的工作画像";
    els.chatInput.placeholder = "";
  } else if (state.phase === "story_simulation") {
    els.boardTitle.textContent = "进入职业剧情";
  } else if (state.phase === "completed") {
    els.boardTitle.textContent = "这段职业旅程已经走完";
  }

  renderStoryPanel();
}

function renderStoryPanel() {
  if (!isStoryPhase(state.phase)) {
    return;
  }
  if (state.streaming) {
    return;
  }

  if (state.storyState?.meta) {
    const displayTitle = state.storyState.meta.plainTitle || state.storyState.meta.title || "职业旅程";
    els.storyMeta.classList.remove("hidden");
    els.storyMeta.innerHTML = `
      <div class="section-kicker">故事设定</div>
      <h3>${escapeHtml(displayTitle)}</h3>
      <div class="story-body"><p>${escapeHtml(state.storyState.meta.description || "")}</p></div>
    `;
  } else {
    els.storyMeta.classList.add("hidden");
    els.storyMeta.innerHTML = "";
  }

  const currentNodeId = state.storyState?.current_node_id;
  const ending = state.storyState?.generated_nodes?.ending;

  if (state.phase === "story_simulation" && !currentNodeId) {
    els.storyStage.innerHTML = `
      <article class="story-card">
        <div class="section-kicker">准备开始</div>
        <h3>现在可以进入剧情了</h3>
        <div class="story-body">
          <p>岗位信息已经准备好。点击下方按钮后，小可会先生成故事背景和开场节点。</p>
        </div>
        <button id="story-start-button" class="primary-btn" type="button">开始剧情</button>
      </article>
    `;
    return;
  }

  if (state.phase === "completed" && ending) {
    els.storyStage.innerHTML = renderEndingCard(ending);
    return;
  }

  const node = state.storyState?.generated_nodes?.[currentNodeId];
  if (!node) {
    els.storyStage.innerHTML = `
      <article class="story-card">
        <div class="section-kicker">状态异常</div>
        <h3>没有找到当前节点</h3>
        <div class="story-body"><p>请尝试重新开始，或恢复一次历史状态。</p></div>
      </article>
    `;
    return;
  }

  els.storyStage.innerHTML = renderNodeCard(currentNodeId, node);
}

async function startStory() {
  if (state.streaming || !state.username) {
    return;
  }
  setStreaming(true);
  setGlobalStatus("正在生成开场节点...", "");
  try {
    await streamJsonEvents(apiUrl(`/api/users/${encodeURIComponent(state.username)}/story/next-node`), {
      action: "start",
    }, handleStoryEvent);
  } catch (error) {
    setGlobalStatus(error.message, "error");
  } finally {
    setStreaming(false);
    render();
  }
  refreshState().catch(() => {});
}

async function submitStoryChoice(currentNode, choiceKey) {
  if (state.streaming || !state.username) {
    return;
  }
  setStreaming(true);
  setGlobalStatus("小可正在推进故事...", "");
  try {
    await streamJsonEvents(apiUrl(`/api/users/${encodeURIComponent(state.username)}/story/next-node`), {
      current_node: currentNode,
      choice_key: choiceKey,
    }, handleStoryEvent);
  } catch (error) {
    setGlobalStatus(error.message, "error");
  } finally {
    setStreaming(false);
    render();
  }
  refreshState().catch(() => {});
}

function onStoryStageClick(event) {
  const startButton = event.target.closest("#story-start-button");
  if (startButton) {
    void startStory();
    return;
  }

  const optionButton = event.target.closest("[data-choice-key]");
  if (!optionButton) {
    return;
  }

  const currentNodeId = state.storyState?.current_node_id;
  const choiceKey = optionButton.dataset.choiceKey;
  if (!currentNodeId || !choiceKey) {
    return;
  }

  void submitStoryChoice(currentNodeId, choiceKey);
}

function handleChatEvent(event) {
  if (event.type === "token") {
    appendToPendingAssistant(event.content || "");
    return;
  }

  if (event.type === "done") {
    syncPendingAssistant();
    state.phase = event.phase || state.phase;
    state.lastActive = new Date().toISOString();
    if (event.phase_complete) {
      setGlobalStatus(event.transition_text || "阶段已完成。", "success");
    } else {
      clearGlobalStatus();
    }
    render();
    return true;
  }

  if (event.type === "options") {
    state.pendingOptions = event.items || [];
    renderChatOptions(state.pendingOptions);
    return;
  }

  if (event.type === "error") {
    throw new Error(event.message || "聊天失败");
  }
}

function handleStoryEvent(event) {
  if (event.type === "progress") {
    setGlobalStatus(event.message || "处理中...", "");
    showStreamingCard();
    return;
  }

  if (event.type === "stream_meta") {
    if (event.meta) {
      state.storyState.meta = event.meta;
      renderStreamingMeta();
    }
    return;
  }

  if (event.type === "stream_title") {
    updateStreamingCardTitle(event.title);
    return;
  }

  if (event.type === "stream_token") {
    appendStreamingToken(event.paragraph_index, event.content);
    return;
  }

  if (event.type === "stream_done") {
    hideStreamingMascot();
    return;
  }

  if (event.type === "complete") {
    if (event.meta) {
      state.storyState.meta = event.meta;
    }
    state.storyState.generated_nodes[event.node_id] = event.node;
    state.storyState.current_node_id = event.node_id;
    state.lastActive = new Date().toISOString();
    clearGlobalStatus();
    render();
    return true;
  }

  if (event.type === "ending") {
    state.storyState.generated_nodes.ending = event.ending;
    state.storyState.current_node_id = "ending";
    state.storyState.scores = event.scores || state.storyState.scores;
    state.phase = "completed";
    state.lastActive = new Date().toISOString();
    setGlobalStatus(`结局已生成，当前匹配档位：${event.bucket || "-"}`, "success");
    render();
    return true;
  }

  if (event.type === "error") {
    throw new Error(event.message || "故事生成失败");
  }
}

function showStreamingCard() {
  els.storyPanel.classList.remove("hidden");
  els.storyStage.innerHTML = `
    <article class="story-card streaming-card">
      <div class="streaming-content">
        <div class="section-kicker streaming-kicker">生成中...</div>
        <h3 class="streaming-title"></h3>
        <div class="story-body streaming-body"></div>
      </div>
    </article>
  `;
}

function updateStreamingCardTitle(title) {
  const el = els.storyStage.querySelector(".streaming-title");
  if (el) {
    el.textContent = title;
    el.classList.add("visible");
  }
}

function appendStreamingToken(paragraphIndex, content) {
  const body = els.storyStage.querySelector(".streaming-body");
  if (!body) return;

  while (body.children.length <= paragraphIndex) {
    const p = document.createElement("p");
    body.appendChild(p);
  }
  body.children[paragraphIndex].textContent += content;

  const card = els.storyStage.querySelector(".streaming-card");
  if (card) {
    card.scrollIntoView({ behavior: "smooth", block: "end" });
  }
}

function hideStreamingMascot() {
  const mascot = els.storyStage.querySelector(".streaming-mascot");
  if (mascot) {
    mascot.classList.add("fade-out");
  }
}

function renderStreamingMeta() {
  if (state.storyState?.meta) {
    const displayTitle = state.storyState.meta.plainTitle || state.storyState.meta.title || "职业旅程";
    els.storyMeta.classList.remove("hidden");
    els.storyMeta.innerHTML = `
      <div class="section-kicker">故事设定</div>
      <h3>${escapeHtml(displayTitle)}</h3>
      <div class="story-body"><p>${escapeHtml(state.storyState.meta.description || "")}</p></div>
    `;
  }
}

function addChatMessage(role, content) {
  const id = `msg-${generateId()}`;
  const wrapper = document.createElement("article");
  wrapper.className = `message ${role}`;
  wrapper.dataset.messageId = id;

  if (role === "assistant") {
    wrapper.innerHTML = `
      <div class="message-with-avatar">
        <div class="chat-mascot${state.streaming ? ' bouncing' : ''}">
          <div class="chat-mascot-inner">
            <div class="mascot-eye left"></div>
            <div class="mascot-eye right"></div>
            <div class="mascot-mouth"></div>
          </div>
        </div>
        <div class="message-body">
          <div class="message-role">小可</div>
          <div class="message-content"></div>
        </div>
      </div>
    `;
  } else {
    wrapper.innerHTML = `
      <div class="message-role">你</div>
      <div class="message-content"></div>
    `;
  }

  wrapper.querySelector(".message-content").textContent = stripOptionsTag(content);
  els.chatStream.appendChild(wrapper);
  els.chatStream.scrollTop = els.chatStream.scrollHeight;
  return id;
}

function appendToPendingAssistant(content) {
  const messageEl = findPendingAssistant();
  if (!messageEl) {
    state.pendingAssistantId = addChatMessage("assistant", content);
    return;
  }
  const contentEl = messageEl.querySelector(".message-content");
  contentEl.textContent += content;
  els.chatStream.scrollTop = els.chatStream.scrollHeight;
}

function syncPendingAssistant() {
  const messageEl = findPendingAssistant();
  if (!messageEl) {
    return;
  }
  const text = messageEl.querySelector(".message-content").textContent.trim();
  if (text) {
    state.conversationHistory.push({ role: "assistant", content: text });
  } else {
    messageEl.remove();
  }
  state.pendingAssistantId = null;
}

function removeEmptyPendingMessage() {
  const messageEl = findPendingAssistant();
  if (messageEl && !messageEl.querySelector(".message-content").textContent.trim()) {
    messageEl.remove();
  }
  state.pendingAssistantId = null;
}

function findPendingAssistant() {
  if (!state.pendingAssistantId) {
    return null;
  }
  return els.chatStream.querySelector(`[data-message-id="${state.pendingAssistantId}"]`);
}

function renderChatOptions(items) {
  if (!items.length) return;
  const wrapper = document.createElement("div");
  wrapper.className = "chat-options";
  items.forEach((item) => {
    const btn = document.createElement("button");
    btn.className = "chat-option-btn";
    btn.type = "button";
    btn.textContent = item;
    btn.addEventListener("click", () => onChatOptionClick(item));
    wrapper.appendChild(btn);
  });
  els.chatStream.appendChild(wrapper);
  els.chatStream.scrollTop = els.chatStream.scrollHeight;
}

function onChatOptionClick(text) {
  els.chatStream.querySelectorAll(".chat-options").forEach((el) => el.remove());
  state.pendingOptions = null;
  els.chatInput.value = text;
  els.chatForm.dispatchEvent(new Event("submit", { cancelable: true }));
}

function rebuildChatStream() {
  els.chatStream.innerHTML = "";
  for (const item of state.conversationHistory) {
    if (item.role === "assistant" || item.role === "user") {
      addChatMessage(item.role, item.content || "");
    }
  }
  if (state.pendingOptions && state.pendingOptions.length) {
    renderChatOptions(state.pendingOptions);
  }
}

async function refreshState() {
  if (!state.username || state.streaming) {
    return;
  }
  const { response, data } = await requestJson(apiUrl(`/api/users/${encodeURIComponent(state.username)}/state`));
  if (!response.ok) {
    throw new Error(data.error || "同步状态失败");
  }
  if (state.streaming) {
    return;
  }
  hydrateState(data);
}

function renderNodeCard(nodeId, node) {
  const paragraphs = Array.isArray(node.paragraphs) ? node.paragraphs : [];
  const options = Array.isArray(node.options) ? node.options : [];
  return `
    <article class="story-card">
      <div class="section-kicker">${escapeHtml(node.tag || "")}</div>
      <h3>${escapeHtml(node.title || "继续旅程")}</h3>
      <div class="story-body">
        ${paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}
      </div>
      <div class="options-grid">
        ${options.map((option) => `
          <button
            class="option-btn"
            type="button"
            data-choice-key="${escapeHtml(option.key || "")}"
            ${state.streaming ? "disabled" : ""}
          >
            ${escapeHtml(option.label || option.key || "继续")}
          </button>
        `).join("")}
      </div>
    </article>
  `;
}

function renderEndingCard(ending) {
  const paragraphs = Array.isArray(ending.paragraphs) ? ending.paragraphs : [];
  return `
    <article class="ending-card">
      <div class="section-kicker">结局</div>
      <h3>${escapeHtml(ending.title || "旅程结束")}</h3>
      <div class="ending-body">
        ${paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}
      </div>
    </article>
  `;
}

function showResumeDialog(payload) {
  els.resumeTitle.textContent = `找到 ${payload.username} 的历史记录`;
  els.resumeCopy.textContent = `当前阶段：${phaseLabel(payload.phase)}。上次节点：${payload.current_node || "尚未进入剧情"}。最近活动：${formatDateTime(payload.last_active)}。`;
  if (typeof els.resumeDialog.showModal === "function") {
    els.resumeDialog.showModal();
  } else {
    els.resumeDialog.setAttribute("open", "open");
  }
}

function closeResumeDialog() {
  if (els.resumeDialog.open) {
    els.resumeDialog.close();
  }
}

function setEntryStatus(message, tone) {
  toggleBanner(els.entryStatus, message, tone);
}

function setGlobalStatus(message, tone) {
  toggleBanner(els.globalStatus, message, tone);
}

function clearGlobalStatus() {
  els.globalStatus.className = "status-banner hidden";
  els.globalStatus.textContent = "";
}

function toggleBanner(element, message, tone) {
  if (!message) {
    element.className = "status-banner hidden";
    element.textContent = "";
    return;
  }
  element.textContent = message;
  element.className = `status-banner ${tone || ""}`.trim();
}

function setStreaming(flag) {
  state.streaming = flag;
  els.startButton.disabled = flag;
  els.sendButton.disabled = flag;
  els.skipProfileButton.disabled = flag;
  els.restartButton.disabled = flag;

  if (!flag) {
    els.chatStream.querySelectorAll(".chat-mascot.bouncing").forEach((el) => {
      el.classList.remove("bouncing");
    });
  } else {
    const pendingMsg = findPendingAssistant();
    if (pendingMsg) {
      const mascot = pendingMsg.querySelector(".chat-mascot");
      if (mascot) {
        mascot.classList.add("bouncing");
      }
    }
  }

  render();
}

function lockEntry(flag) {
  els.startButton.disabled = flag;
  els.usernameInput.disabled = flag;
}

async function streamJsonEvents(url, payload, onEvent) {
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    throw new Error(networkErrorMessage());
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || "请求失败");
  }

  if (!response.body) {
    throw new Error("浏览器不支持流式响应");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let terminated = false;

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      if (rawEvent.startsWith("data:")) {
        const jsonText = rawEvent.slice(5).trim();
        if (jsonText) {
          const result = onEvent(JSON.parse(jsonText));
          if (result === true) {
            terminated = true;
            break;
          }
        }
      }
      boundary = buffer.indexOf("\n\n");
    }

    if (done || terminated) {
      break;
    }
  }
}

function apiUrl(path) {
  return `${API_BASE}${path}`;
}

async function requestJson(url, options = {}) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new Error(networkErrorMessage());
  }

  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    data = {};
  }
  return { response, data };
}

function networkErrorMessage() {
  if (window.location.protocol === "file:") {
    return "无法连接后端。请先在 backend 目录启动 Flask，再刷新当前页面。";
  }
  return "无法连接服务端，请检查后端是否已启动。";
}

function phaseLabel(phase) {
  return PHASE_META.find((item) => item.key === phase)?.label || "尚未开始";
}

function isChatPhase(phase) {
  return phase === "job_collection" || phase === "profile_collection";
}

function isStoryPhase(phase) {
  return phase === "story_simulation" || phase === "completed";
}

function renderSummaryLine(label, value) {
  if (!value) {
    return "";
  }
  return `<p><strong>${escapeHtml(label)}：</strong>${escapeHtml(String(value))}</p>`;
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function stripOptionsTag(text) {
  return String(text).replace(/<options>[\s\S]*?<\/options>/g, "").trimEnd();
}

function extractOptionsFromText(text) {
  const match = String(text).match(/<options>([\s\S]*?)<\/options>/);
  if (!match) return [];
  try {
    return JSON.parse(match[1].trim());
  } catch (e) {
    return [];
  }
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function generateId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

// ─── Admin Mode ───

let adminToken = "";

async function tryAdminAuth(key) {
  try {
    const { response, data } = await requestJson(apiUrl("/api/admin/auth"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key }),
    });
    if (response.ok && data.token) {
      return data.token;
    }
  } catch (e) {}
  return null;
}

function enterAdminMode(token) {
  adminToken = token;
  document.querySelector(".hero-panel").classList.add("hidden");
  els.workspace.classList.add("hidden");
  els.adminPanel.classList.remove("hidden");
  loadAdminUsers();
}

function exitAdminMode() {
  adminToken = "";
  els.adminPanel.classList.add("hidden");
  document.querySelector(".hero-panel").classList.remove("hidden");
  els.adminDetail.innerHTML = `<p class="empty-copy">选择左侧用户查看详情</p>`;
  els.adminUserList.innerHTML = "";
}

async function loadAdminUsers() {
  try {
    const { response, data } = await requestJson(apiUrl("/api/admin/users"), {
      headers: { "X-Admin-Token": adminToken },
    });
    if (!response.ok) return;
    renderAdminUserList(data);
  } catch (e) {}
}

function renderAdminUserList(users) {
  els.adminUserList.innerHTML = `
    <div class="section-kicker">用户列表（${users.length}）</div>
    ${users.map((u) => `
      <div class="admin-user-item" data-username="${escapeHtml(u.username)}">
        <strong>${escapeHtml(u.username)}</strong>
        <span class="admin-user-phase">${escapeHtml(phaseLabel(u.phase))}</span>
        <span class="admin-user-time">${formatDateTime(u.last_active)}</span>
      </div>
    `).join("")}
  `;
  els.adminUserList.querySelectorAll(".admin-user-item").forEach((el) => {
    el.addEventListener("click", () => loadUserDetail(el.dataset.username));
  });
}

async function loadUserDetail(username) {
  els.adminDetail.innerHTML = `<p class="empty-copy">加载中...</p>`;

  const headers = { "X-Admin-Token": adminToken };
  try {
    const [convRes, llmRes, sysRes] = await Promise.all([
      requestJson(apiUrl(`/api/admin/users/${encodeURIComponent(username)}/conversation`), { headers }),
      requestJson(apiUrl(`/api/admin/users/${encodeURIComponent(username)}/llm-log`), { headers }),
      requestJson(apiUrl(`/api/admin/users/${encodeURIComponent(username)}/system-log`), { headers }),
    ]);

    const conversation = convRes.response.ok ? convRes.data : [];
    const llmLog = llmRes.response.ok ? llmRes.data : [];
    const systemLog = sysRes.response.ok ? sysRes.data : [];

    renderAdminDetail(username, conversation, llmLog, systemLog);
  } catch (e) {
    els.adminDetail.innerHTML = `<p class="empty-copy">加载失败</p>`;
  }
}

function renderAdminDetail(username, conversation, llmLog, systemLog) {
  els.adminDetail.innerHTML = `
    <div class="admin-detail-header">
      <h3>${escapeHtml(username)}</h3>
      <div class="admin-tabs">
        <button class="admin-tab active" data-tab="conversation">对话历史（${conversation.length}）</button>
        <button class="admin-tab" data-tab="llm">LLM 日志（${llmLog.length}）</button>
        <button class="admin-tab" data-tab="system">系统日志（${systemLog.length}）</button>
      </div>
    </div>
    <div class="admin-tab-content" id="admin-tab-content"></div>
  `;

  const tabContent = document.getElementById("admin-tab-content");
  const tabs = els.adminDetail.querySelectorAll(".admin-tab");

  function showTab(name) {
    tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
    if (name === "conversation") {
      tabContent.innerHTML = renderAdminConversation(conversation);
    } else if (name === "llm") {
      tabContent.innerHTML = renderAdminLog(llmLog);
    } else {
      tabContent.innerHTML = renderAdminLog(systemLog);
    }
  }

  tabs.forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));
  showTab("conversation");
}

function renderAdminConversation(messages) {
  if (!messages.length) return `<p class="empty-copy">暂无对话</p>`;
  return `<div class="admin-conversation">${messages.map((msg) => `
    <div class="admin-msg admin-msg-${escapeHtml(msg.role)}">
      <span class="admin-msg-role">${msg.role === "assistant" ? "小可" : "用户"}</span>
      <span class="admin-msg-content">${escapeHtml(stripOptionsTag(msg.content || ""))}</span>
    </div>
  `).join("")}</div>`;
}

function renderAdminLog(entries) {
  if (!entries.length) return `<p class="empty-copy">暂无日志</p>`;
  return `<div class="admin-log">${entries.slice().reverse().map((entry) => `
    <details class="admin-log-entry">
      <summary>${escapeHtml(entry.timestamp || "")} — ${escapeHtml(entry.event || entry.model || "entry")}</summary>
      <pre>${escapeHtml(JSON.stringify(entry, null, 2))}</pre>
    </details>
  `).join("")}</div>`;
}
