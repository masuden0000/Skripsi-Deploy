const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messages = document.getElementById("messages");
const clearButton = document.getElementById("clear-chat");
const statusLabel = document.getElementById("server-status");
const statusDot = document.getElementById("status-dot");
const sendButton = document.getElementById("send-button");
const msgTemplate = document.getElementById("message-template");

const SCOPE_LABELS = {
  grounded: "Bersumber",
  insufficient_context: "Konteks terbatas",
  out_of_scope: "Di luar sumber",
};

const ANSWER_TYPE_LABELS = {
  summary: "Ringkasan",
  format_guidance: "Panduan format",
  procedure: "Prosedur",
  not_in_source: "Tidak ada di sumber",
};

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
});

function appendMessage(role, contentNode, options = {}) {
  const fragment = msgTemplate.content.cloneNode(true);
  const article = fragment.querySelector(".message");
  const roleEl = fragment.querySelector(".msg-role");
  const card = fragment.querySelector(".message-card");

  article.classList.add(role === "user" ? "message--user" : "message--ai");
  if (options.loading) {
    article.classList.add("loading");
  }

  roleEl.textContent = role === "user" ? "Kamu" : "DocRAG";
  card.appendChild(contentNode);
  messages.appendChild(fragment);
  messages.scrollTop = messages.scrollHeight;

  return messages.lastElementChild;
}

function buildParagraph(text) {
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  return paragraph;
}

function buildLoadingNode() {
  const dots = document.createElement("div");
  dots.className = "loading-dots";
  dots.setAttribute("aria-label", "Sedang memproses...");
  for (let index = 0; index < 3; index += 1) {
    dots.appendChild(document.createElement("span"));
  }
  return dots;
}

function createList(items, className, ordered = false) {
  const list = document.createElement(ordered ? "ol" : "ul");
  list.className = className;

  items.forEach((item) => {
    const listItem = document.createElement("li");
    listItem.textContent = item;
    list.appendChild(listItem);
  });

  return list;
}

function createSection(title, node) {
  const section = document.createElement("section");
  section.className = "response-section";

  const heading = document.createElement("p");
  heading.className = "response-section-label";
  heading.textContent = title;

  section.appendChild(heading);
  section.appendChild(node);
  return section;
}

function buildMetaBadges(data) {
  const row = document.createElement("div");
  row.className = "response-meta";

  if (data.scope_status) {
    const badge = document.createElement("span");
    badge.className = `status-badge status-badge--${data.scope_status}`;
    badge.textContent = SCOPE_LABELS[data.scope_status] || data.scope_status;
    row.appendChild(badge);
  }

  if (data.answer_type) {
    const badge = document.createElement("span");
    badge.className = "status-badge status-badge--type";
    badge.textContent = ANSWER_TYPE_LABELS[data.answer_type] || data.answer_type;
    row.appendChild(badge);
  }

  return row;
}

function buildKeywordRow(keywords) {
  const row = document.createElement("div");
  row.className = "keyword-row";

  const label = document.createElement("span");
  label.className = "kw-label";
  label.textContent = "Kata kunci";
  row.appendChild(label);

  keywords.forEach((word) => {
    const badge = document.createElement("span");
    badge.className = "keyword-badge";
    badge.textContent = word;
    row.appendChild(badge);
  });

  return row;
}

function buildCitationSection(citations) {
  const section = document.createElement("section");
  section.className = "citation-section";

  const label = document.createElement("p");
  label.className = "citation-label";
  label.textContent = "Sumber";
  section.appendChild(label);

  const grid = document.createElement("div");
  grid.className = "citation-grid";

  citations.forEach((citation) => {
    const card = document.createElement("div");
    card.className = "citation-card";

    const heading = document.createElement("div");
    heading.className = "citation-heading";
    heading.textContent = citation.chunk_parent || "-";

    const footer = document.createElement("div");
    footer.className = "citation-footer";

    const pageBadge = document.createElement("span");
    pageBadge.className = "page-badge";
    pageBadge.textContent = `hlm. ${citation.page_start}-${citation.page_end}`;

    const chunkRef = document.createElement("span");
    chunkRef.className = "chunk-ref";
    chunkRef.textContent = `#${citation.chunk_index}`;

    footer.appendChild(pageBadge);
    footer.appendChild(chunkRef);
    card.appendChild(heading);
    card.appendChild(footer);
    grid.appendChild(card);
  });

  section.appendChild(grid);
  return section;
}

function buildAssistantContent(data) {
  const wrapper = document.createElement("div");

  const meta = buildMetaBadges(data);
  if (meta.children.length > 0) {
    wrapper.appendChild(meta);
  }

  wrapper.appendChild(buildParagraph(data.answer || "Tidak ada jawaban."));

  if (Array.isArray(data.bullet_points) && data.bullet_points.length) {
    wrapper.appendChild(
      createSection("Poin penting", createList(data.bullet_points, "bullet-list"))
    );
  }

  if (Array.isArray(data.steps) && data.steps.length) {
    wrapper.appendChild(
      createSection("Langkah", createList(data.steps, "step-list", true))
    );
  }

  if (Array.isArray(data.keywords) && data.keywords.length) {
    wrapper.appendChild(buildKeywordRow(data.keywords));
  }

  if (Array.isArray(data.citations) && data.citations.length) {
    wrapper.appendChild(buildCitationSection(data.citations));
  }

  return wrapper;
}

function setBusyState(isBusy) {
  input.disabled = isBusy;
  sendButton.disabled = isBusy;
  if (statusDot) {
    statusDot.classList.toggle("busy", isBusy);
  }
  statusLabel.textContent = isBusy
    ? "Mengambil jawaban dari pipeline RAG PKM..."
    : "Siap menerima pertanyaan";
}

async function sendMessage(message) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Permintaan gagal diproses.");
  }

  return data;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const text = input.value.trim();
  if (!text) {
    return;
  }

  appendMessage("user", buildParagraph(text));
  input.value = "";
  input.style.height = "auto";
  setBusyState(true);

  const loadingEl = appendMessage("ai", buildLoadingNode(), { loading: true });

  try {
    const data = await sendMessage(text);
    loadingEl.remove();
    appendMessage("ai", buildAssistantContent(data));
  } catch (error) {
    loadingEl.remove();
    appendMessage("ai", buildParagraph(error.message));
    statusLabel.textContent = "Terjadi kesalahan saat menghubungi backend";
  } finally {
    setBusyState(false);
    input.focus();
  }
});

clearButton.addEventListener("click", () => {
  messages.innerHTML = "";
  appendMessage(
    "ai",
    buildParagraph(
      "Riwayat chat dibersihkan. Silakan mulai pertanyaan baru tentang dokumen PKM."
    )
  );
  statusLabel.textContent = "Siap menerima pertanyaan";
  if (statusDot) {
    statusDot.classList.remove("busy");
  }
  input.focus();
});

input.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    form.requestSubmit();
  }
});
