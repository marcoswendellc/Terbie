const SESSION_KEY = "terbie.authenticated";
const TOKEN_KEY = "terbie.access_token";
const LOGIN_ENDPOINT = "/auth/login";
const CHAT_SESSION_KEY = "terbie.chat_session_id";
const EXECUTE_ENDPOINT = "/execute";
const DRAFT_ENDPOINT = "/ask/draft";

const loginView = document.querySelector('[data-view="login"]');
const chatView = document.querySelector('[data-view="chat"]');
const loginForm = document.querySelector("[data-login-form]");
const loginError = document.querySelector("[data-login-error]");
const chatForm = document.querySelector("[data-chat-form]");
const messageInput = document.querySelector("[data-message-input]");
const messages = document.querySelector("[data-messages]");
const logoutButton = document.querySelector("[data-logout]");
const newChatButton = document.querySelector("[data-new-chat]");
const welcome = document.querySelector("[data-welcome]");
const menuButton = document.querySelector("[data-menu]");
const REMEMBER_KEY = "terbie.remembered_session";

function rememberedSession() {
  try {
    const value = JSON.parse(localStorage.getItem(REMEMBER_KEY) || "null");
    if (value?.token && value.expiresAt > Date.now()) return value;
    localStorage.removeItem(REMEMBER_KEY);
  } catch (_) { /* Storage can be unavailable in private browsing. */ }
  return null;
}

const remembered = rememberedSession();
if (remembered) {
  sessionStorage.setItem(SESSION_KEY, "true");
  sessionStorage.setItem(TOKEN_KEY, remembered.token);
}

document.querySelector("[data-toggle-password]").addEventListener("click", () => {
  const input = document.querySelector("#login-password");
  const visible = input.type === "password";
  input.type = visible ? "text" : "password";
  const button = document.querySelector("[data-toggle-password]");
  button.setAttribute("aria-label", visible ? "Ocultar senha" : "Mostrar senha");
  button.setAttribute("aria-pressed", String(visible));
});
document.querySelector("[data-forgot-password]").addEventListener("click", () => {
  document.querySelector("[data-recovery-help]").classList.remove("is-hidden");
});

function closeMenu() {
  chatView.classList.remove("menu-open");
  menuButton.setAttribute("aria-expanded", "false");
  menuButton.setAttribute("aria-label", "Abrir menu");
}

function showWelcome() {
  welcome.classList.remove("is-hidden");
  messages.classList.add("is-hidden");
  closeMenu();
}

function showChat() {
  loginView.classList.add("is-hidden");
  chatView.classList.remove("is-hidden");
  messageInput.focus();
}

function showLogin() {
  chatView.classList.add("is-hidden");
  loginView.classList.remove("is-hidden");
}

function scrollConversation() {
  messages.scrollTop = messages.scrollHeight;
}

function markdownCells(line) {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  return trimmed.split("|").map((cell) => cell.trim());
}

function isTableSeparator(line) {
  const cells = markdownCells(line);
  return cells.length > 1 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function buildTable(headerLine, bodyLines) {
  const wrapper = document.createElement("div");
  wrapper.className = "table-scroll";

  const table = document.createElement("table");
  table.className = "analytics-table";
  const head = document.createElement("thead");
  const headerRow = document.createElement("tr");
  markdownCells(headerLine).forEach((value) => {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = value;
    headerRow.appendChild(cell);
  });
  head.appendChild(headerRow);

  const body = document.createElement("tbody");
  bodyLines.forEach((line) => {
    const row = document.createElement("tr");
    markdownCells(line).forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.appendChild(cell);
    });
    body.appendChild(row);
  });

  table.append(head, body);
  wrapper.appendChild(table);
  return wrapper;
}

function renderMessageContent(container, text, role) {
  container.replaceChildren();
  if (role === "user") {
    container.textContent = text;
    return;
  }

  const lines = String(text || "").split(/\r?\n/);
  let paragraphLines = [];
  const flushParagraph = () => {
    if (!paragraphLines.length) return;
    const paragraph = document.createElement("p");
    paragraph.textContent = paragraphLines.join("\n").trim();
    if (paragraph.textContent) container.appendChild(paragraph);
    paragraphLines = [];
  };

  for (let index = 0; index < lines.length; index += 1) {
    const hasTable =
      lines[index].includes("|") &&
      index + 1 < lines.length &&
      isTableSeparator(lines[index + 1]);
    if (!hasTable) {
      paragraphLines.push(lines[index]);
      continue;
    }

    flushParagraph();
    const bodyLines = [];
    index += 2;
    while (index < lines.length && lines[index].includes("|")) {
      if (lines[index].trim()) bodyLines.push(lines[index]);
      index += 1;
    }
    container.appendChild(buildTable(lines[index - bodyLines.length - 2], bodyLines));
    index -= 1;
  }
  flushParagraph();
}

function createMessage(role, text) {
  const article = document.createElement("article");
  article.className = `message message-${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "W" : "T";

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  const author = document.createElement("span");
  author.className = "message-author";
  author.textContent = role === "user" ? "Voce" : "Terbie";

  const content = document.createElement("div");
  content.className = "message-content";
  renderMessageContent(content, text, role);

  bubble.append(author, content);
  article.append(avatar, bubble);
  return article;
}

function appendMessage(role, text) {
  welcome.classList.add("is-hidden");
  messages.classList.remove("is-hidden");
  const message = createMessage(role, text);
  messages.appendChild(message);
  scrollConversation();
  return message;
}

function updateMessage(message, text) {
  const content = message.querySelector(".message-content");
  renderMessageContent(content, text, "app");
  scrollConversation();
}

function conversationSessionId() {
  let sessionId = sessionStorage.getItem(CHAT_SESSION_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem(CHAT_SESSION_KEY, sessionId);
  }
  return sessionId;
}

async function postQuestion(endpoint, question, sessionId = conversationSessionId()) {
  const token = sessionStorage.getItem(TOKEN_KEY);
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question, session_id: sessionId }),
  });

  if (!response.ok) {
    let detail = "Nao foi possivel processar a pergunta agora.";
    try {
      const errorBody = await response.json();
      detail = errorBody.detail || errorBody.error || detail;
    } catch (_error) {
      detail = response.statusText || detail;
    }
    throw new Error(Array.isArray(detail) ? detail[0]?.msg || detail[0] : detail);
  }

  return response.json();
}

function listNames(items) {
  return items
    .map((item) => item.name)
    .filter(Boolean)
    .join(", ");
}

function normalizeText(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function uniqueHighlights(answer, highlights) {
  const normalizedAnswer = normalizeText(answer);
  const seen = new Set();

  return highlights.filter((highlight) => {
    const normalizedHighlight = normalizeText(highlight);
    if (!normalizedHighlight || seen.has(normalizedHighlight)) {
      return false;
    }
    seen.add(normalizedHighlight);
    return normalizedAnswer !== normalizedHighlight;
  });
}

function formatExecuteResponse(payload) {
  const lines = [payload.answer || "Não consegui concluir a análise."];
  if (Array.isArray(payload.assumptions) && payload.assumptions.length) {
    lines.push("", `Recorte considerado: ${payload.assumptions.join(" ")}`);
  }
  if (payload.metadata?.pending_analyses > 0) {
    lines.push("", "Parte da análise ficou pendente pelo limite deste turno. Você pode pedir para continuar com um recorte menor.");
  }
  return lines.join("\n");
}

function appendAnalysisChart(message, payload) {
  const chart = payload.metadata?.chart;
  if (!chart || chart.type !== "line" || !Array.isArray(payload.data)) return;
  const rows = payload.data.filter(row => /^\d{4}-\d{2}$/.test(row[chart.x]) &&
    typeof row[chart.y] === "number" && Number.isFinite(row[chart.y]));
  if (!rows.length) return;
  const ns = "http://www.w3.org/2000/svg";
  const element = (name, attributes, text) => {
    const node = document.createElementNS(ns, name);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value)));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const svg = element("svg", {viewBox: "0 0 720 280", role: "img",
    "aria-label": `${chart.title}: evolução mensal; valores detalhados na tabela.`,
    width: "100%"});
  const monthNumber = row => Number(row[chart.x].slice(0, 4)) * 12 + Number(row[chart.x].slice(5));
  rows.sort((a, b) => monthNumber(a) - monthNumber(b));
  const start = monthNumber(rows[0]);
  const span = Math.max(1, monthNumber(rows[rows.length - 1]) - start);
  const low = Math.min(0, ...rows.map(row => row[chart.y]));
  const high = Math.max(1, ...rows.map(row => row[chart.y]));
  const x = row => 100 + (monthNumber(row) - start) / span * 570;
  const y = row => 225 - (row[chart.y] - low) / (high - low) * 180;
  svg.appendChild(element("text", {x: 100, y: 22, fill: "currentColor", "font-size": 16}, chart.title));
  [low, (low + high) / 2, high].forEach(value => {
    const position = 225 - (value - low) / (high - low) * 180;
    svg.appendChild(element("line", {x1: 95, x2: 680, y1: position, y2: position,
      stroke: "currentColor", opacity: 0.15}));
    svg.appendChild(element("text", {x: 90, y: position + 4, "text-anchor": "end",
      fill: "currentColor", "font-size": 11}, value.toLocaleString("pt-BR", {maximumFractionDigits: 0})));
  });
  svg.appendChild(element("polyline", {points: rows.map(row => `${x(row)},${y(row)}`).join(" "),
    fill: "none", stroke: "#3679d6", "stroke-width": 2}));
  rows.forEach(row => {
    const point = element("circle", {cx: x(row), cy: y(row), r: 4, fill: "#3679d6"});
    point.appendChild(element("title", {}, `${row[chart.x]}: ${row[chart.y].toLocaleString("pt-BR")}`));
    svg.appendChild(point);
    svg.appendChild(element("text", {x: x(row), y: 252, "text-anchor": "middle",
      fill: "currentColor", "font-size": 10}, row[chart.x]));
  });
  message.querySelector(".message-bubble").appendChild(svg);
}

function appendFollowUpSuggestions(message, payload) {
  const suggestions = Array.isArray(payload.suggestions) ? payload.suggestions.slice(0, 2) : [];
  if (!suggestions.length) return;
  const block = document.createElement("div");
  block.className = "follow-up-suggestions";
  const label = document.createElement("p");
  label.textContent = "Podemos aprofundar:";
  block.appendChild(label);
  suggestions.forEach((suggestion) => {
    if (!suggestion.label || !suggestion.question) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "follow-up-button";
    button.textContent = suggestion.label;
    button.title = suggestion.question;
    button.addEventListener("click", () => {
      if (messageInput.disabled || button.disabled) return;
      messageInput.value = suggestion.question;
      chatForm.requestSubmit();
    });
    block.appendChild(button);
  });
  message.querySelector(".message-bubble").appendChild(block);
  scrollConversation();
}

function formatDraftResponse(payload) {
  if (payload.status === "out_of_scope" && payload.response) {
    return payload.response;
  }

  const plan = payload.draft_plan || {};
  const metrics = Array.isArray(plan.metrics) ? listNames(plan.metrics) : "";
  const entities = Array.isArray(plan.entities) ? listNames(plan.entities) : "";
  const operations = Array.isArray(plan.operations)
    ? plan.operations.map((operation) => operation.type).filter(Boolean).join(", ")
    : "";
  const lines = [
    "Consegui interpretar sua pergunta e preparar um caminho de analise.",
    "",
    `Status: ${payload.status || "draft_created"}`,
  ];

  if (plan.intent) {
    lines.push(`Intencao: ${plan.intent}`);
  }
  if (metrics) {
    lines.push(`Metricas: ${metrics}`);
  }
  if (entities) {
    lines.push(`Entidades: ${entities}`);
  }
  if (operations) {
    lines.push(`Operacoes: ${operations}`);
  }
  return lines.join("\n");
}

async function askBackend(question, sessionId = conversationSessionId()) {
  try {
    const executionPayload = await postQuestion(EXECUTE_ENDPOINT, question, sessionId);
    return executionPayload;
  } catch (executeError) {
    try {
      const draftPayload = await postQuestion(DRAFT_ENDPOINT, question, sessionId);
      return {answer: draftPayload.response || "Consegui interpretar a pergunta, mas não concluir a consulta. Tente novamente ou especifique um recorte menor.", suggestions: []};
    } catch (draftError) {
      throw new Error(
        `Nao consegui conectar a conversa ao backend agora. Execucao: ${executeError.message}. Plano: ${draftError.message}.`
      );
    }
  }
}

function resetConversation() {
  if (messageInput.disabled) return;
  sessionStorage.setItem(CHAT_SESSION_KEY, crypto.randomUUID());
  messages.innerHTML = "";
  messageInput.value = "";
  document.querySelector("[data-chat-title]").textContent = "Nova conversa";
  showWelcome();
  messageInput.focus();
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(loginForm);
  const username = String(formData.get("username") || "").trim();
  const password = String(formData.get("password") || "");

  const submitButton = loginForm.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  loginError.textContent = "";

  try {
    const response = await fetch(LOGIN_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!response.ok) throw new Error("login unavailable");

    const result = await response.json();
    if (!result.authenticated) {
      loginError.textContent = "Usuario ou senha incorretos. Confira os dados e tente novamente.";
      return;
    }

    sessionStorage.setItem(SESSION_KEY, "true");
    if (result.access_token) sessionStorage.setItem(TOKEN_KEY, result.access_token);
    try {
      localStorage.removeItem(REMEMBER_KEY);
      if (document.querySelector("[data-remember]").checked && result.access_token && result.expires_in > 0) {
        localStorage.setItem(REMEMBER_KEY, JSON.stringify({
          token: result.access_token,
          expiresAt: Date.now() + result.expires_in * 1000,
        }));
      }
    } catch (_) { /* Keep the current session if persistent storage is unavailable. */ }
    loginForm.reset();
    document.querySelector("#login-password").type = "password";
    document.querySelector("[data-toggle-password]").setAttribute("aria-label", "Mostrar senha");
    document.querySelector("[data-toggle-password]").setAttribute("aria-pressed", "false");
    showChat();
  } catch (_error) {
    loginError.textContent = "Nao foi possivel validar o acesso agora. Tente novamente.";
  } finally {
    submitButton.disabled = false;
  }
});

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (messageInput.disabled) return;
  const question = messageInput.value.trim();

  if (!question) {
    messageInput.focus();
    return;
  }

  closeMenu();
  if (!messages.children.length) {
    document.querySelector("[data-chat-title]").textContent = question.slice(0, 70);
  }
  appendMessage("user", question);
  messages.querySelectorAll(".follow-up-button").forEach((button) => { button.disabled = true; });
  messageInput.value = "";
  messageInput.style.height = "auto";
  messageInput.disabled = true;
  newChatButton.disabled = true;
  chatForm.querySelector("button").disabled = true;
  const pendingMessage = appendMessage("app", "Consultando...");
  const requestSession = conversationSessionId();

  askBackend(question, requestSession)
    .then((payload) => {
      if (requestSession !== conversationSessionId()) return;
      updateMessage(pendingMessage, formatExecuteResponse(payload));
      appendAnalysisChart(pendingMessage, payload);
      appendFollowUpSuggestions(pendingMessage, payload);
    })
    .catch((error) =>
      updateMessage(
        pendingMessage,
        `${error.message} Confira se a API esta rodando e tente novamente.`
      )
    )
    .finally(() => {
      messageInput.disabled = false;
      newChatButton.disabled = false;
      chatForm.querySelector("button").disabled = false;
      messageInput.focus();
    });
});

messageInput.addEventListener("input", () => {
  messageInput.style.height = "auto";
  messageInput.style.height = `${messageInput.scrollHeight}px`;
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

logoutButton.addEventListener("click", () => {
  try { localStorage.removeItem(REMEMBER_KEY); } catch (_) { /* Storage unavailable. */ }
    sessionStorage.removeItem(SESSION_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.setItem(CHAT_SESSION_KEY, crypto.randomUUID());
  messages.replaceChildren();
  messageInput.value = "";
  document.querySelector("[data-chat-title]").textContent = "Nova conversa";
  showWelcome();
  showLogin();
});

newChatButton.addEventListener("click", resetConversation);
document.querySelector("[data-home]").addEventListener("click", showWelcome);
document.querySelector("[data-chat-title]").addEventListener("click", () => {
  if (!messages.children.length) return;
  welcome.classList.add("is-hidden");
  messages.classList.remove("is-hidden");
  closeMenu();
});
document.querySelectorAll("[data-suggestion]").forEach((button) => {
  button.addEventListener("click", () => {
    if (messageInput.disabled) return;
    messageInput.value = button.dataset.suggestion;
    chatForm.requestSubmit();
  });
});
menuButton.addEventListener("click", () => {
  const open = chatView.classList.toggle("menu-open");
  menuButton.setAttribute("aria-expanded", String(open));
  menuButton.setAttribute("aria-label", open ? "Fechar menu" : "Abrir menu");
});
chatView.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeMenu();
});

if (sessionStorage.getItem(SESSION_KEY) === "true") {
  showChat();
} else {
  showLogin();
}
