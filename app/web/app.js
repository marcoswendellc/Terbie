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
  sessionStorage.setItem(CHAT_SESSION_KEY, crypto.randomUUID());
  messages.innerHTML = "";
  appendMessage(
    "app",
    "Nova conversa iniciada. Pergunte sobre campanhas, vendas, promocoes ou desempenho operacional."
  );
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
    loginForm.reset();
    showChat();
  } catch (_error) {
    loginError.textContent = "Nao foi possivel validar o acesso agora. Tente novamente.";
  } finally {
    submitButton.disabled = false;
  }
});

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = messageInput.value.trim();

  if (!question) {
    messageInput.focus();
    return;
  }

  appendMessage("user", question);
  messages.querySelectorAll(".follow-up-button").forEach((button) => { button.disabled = true; });
  messageInput.value = "";
  messageInput.style.height = "auto";
  messageInput.disabled = true;
  chatForm.querySelector("button").disabled = true;
  const pendingMessage = appendMessage("app", "Consultando...");
  const requestSession = conversationSessionId();

  askBackend(question, requestSession)
    .then((payload) => {
      if (requestSession !== conversationSessionId()) return;
      updateMessage(pendingMessage, formatExecuteResponse(payload));
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
    sessionStorage.removeItem(SESSION_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
  showLogin();
});

newChatButton.addEventListener("click", resetConversation);

if (sessionStorage.getItem(SESSION_KEY) === "true") {
  showChat();
} else {
  showLogin();
}
