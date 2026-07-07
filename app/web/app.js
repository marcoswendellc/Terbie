const LOGIN_USER = "wendell";
const LOGIN_PASSWORD = "123";
const SESSION_KEY = "terbie.authenticated";

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
  messages.appendChild(createMessage(role, text));
  scrollConversation();
}

function getSimulatedResponse(question) {
  const cleanQuestion = question.trim();
  return (
    "Recebi sua pergunta: \"" +
    cleanQuestion +
    "\". Nesta versao inicial, estou exibindo uma resposta simulada para validar a experiencia visual. A estrutura ja esta pronta para conectar este envio a uma API ou LLM."
  );
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

  window.setTimeout(() => {
    appendMessage("app", getSimulatedResponse(question));
  }, 420);
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
