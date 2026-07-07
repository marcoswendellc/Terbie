const LOGIN_USER = "wendell";
const LOGIN_PASSWORD = "123";
const SESSION_KEY = "terbie.authenticated";
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

  const paragraph = document.createElement("p");
  paragraph.textContent = text;

  bubble.append(author, paragraph);
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
  const paragraph = message.querySelector("p");
  paragraph.textContent = text;
  scrollConversation();
}

async function postQuestion(endpoint, question) {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
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

function usefulSuggestions() {
  return [
    "Filtrar por periodo",
    "Comparar itens",
    "Detalhar por categoria",
    "Ver faturamento, quantidade de notas e ticket medio",
  ];
}

function appendSuggestions(lines) {
  lines.push("", "Voce tambem pode aprofundar a analise:");
  usefulSuggestions().forEach((suggestion) => lines.push(`- ${suggestion}`));
}

function formatExecuteResponse(payload) {
  const answer = payload.answer || "Analise concluida.";
  const lines = [answer];
  const highlights = Array.isArray(payload.highlights)
    ? uniqueHighlights(answer, payload.highlights)
    : [];

  if (highlights.length > 0) {
    lines.push("", "Destaques:");
    highlights.slice(0, 4).forEach((highlight) => lines.push(`- ${highlight}`));
  }

  if (Array.isArray(payload.recommendations) && payload.recommendations.length > 0) {
    lines.push("", "Recomendacoes:");
    payload.recommendations
      .slice(0, 3)
      .forEach((recommendation) => lines.push(`- ${recommendation}`));
  }

  return lines.join("\n");
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
  appendSuggestions(lines);

  return lines.join("\n");
}

async function askBackend(question) {
  try {
    const executionPayload = await postQuestion(EXECUTE_ENDPOINT, question);
    return formatExecuteResponse(executionPayload);
  } catch (executeError) {
    try {
      const draftPayload = await postQuestion(DRAFT_ENDPOINT, question);
      return `${formatDraftResponse(draftPayload)}\n\nNao executei a consulta completa porque a etapa de execucao retornou: ${executeError.message}`;
    } catch (draftError) {
      throw new Error(
        `Nao consegui conectar a conversa ao backend agora. Execucao: ${executeError.message}. Plano: ${draftError.message}.`
      );
    }
  }
}

function resetConversation() {
  messages.innerHTML = "";
  appendMessage(
    "app",
    "Nova conversa iniciada. Pergunte sobre campanhas, vendas, promocoes ou desempenho operacional."
  );
}

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(loginForm);
  const username = String(formData.get("username") || "").trim();
  const password = String(formData.get("password") || "");

  if (username === LOGIN_USER && password === LOGIN_PASSWORD) {
    sessionStorage.setItem(SESSION_KEY, "true");
    loginError.textContent = "";
    loginForm.reset();
    showChat();
    return;
  }

  loginError.textContent = "Usuario ou senha incorretos. Confira os dados e tente novamente.";
});

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = messageInput.value.trim();

  if (!question) {
    messageInput.focus();
    return;
  }

  appendMessage("user", question);
  messageInput.value = "";
  messageInput.style.height = "auto";
  messageInput.disabled = true;
  chatForm.querySelector("button").disabled = true;
  const pendingMessage = appendMessage("app", "Consultando...");

  askBackend(question)
    .then((answer) => updateMessage(pendingMessage, answer))
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
  showLogin();
});

newChatButton.addEventListener("click", resetConversation);

if (sessionStorage.getItem(SESSION_KEY) === "true") {
  showChat();
} else {
  showLogin();
}
