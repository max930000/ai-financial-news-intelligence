"use strict";
const form = document.getElementById("prepare-form");
const titleInput = document.getElementById("title");
const contentInput = document.getElementById("content");
const modeInput = document.getElementById("paragraph-mode");
const result = document.getElementById("result");
const status = document.getElementById("status");
const error = document.getElementById("error");
const submit = document.getElementById("prepare-button");
let prepared = null;
let revision = 0;

function invalidate() {
  revision += 1;
  prepared = null;
  result.hidden = true;
  error.hidden = true;
  status.textContent = "內容已變更，請重新產生段落預覽。";
}
form.addEventListener("input", invalidate);
modeInput.addEventListener("change", invalidate);
document.getElementById("sample-button").addEventListener("click", () => {
  titleInput.value = "【虛構範例】星河公司全面調漲價格";
  contentInput.value = "星河公司表示，正在評估部分產品的售價調整。\n目前仍未作出最終決定。\n\n這項評估只涉及北美市場。方案中的調整幅度為 3.5%，其他市場不在此次評估範圍。";
  modeInput.value = "blank_lines";
  invalidate();
});

function render(data) {
  const list = document.getElementById("paragraph-list");
  const nav = document.getElementById("paragraph-nav");
  list.replaceChildren();
  nav.replaceChildren();
  for (const paragraph of data.paragraphs) {
    const article = document.createElement("article");
    article.id = paragraph.id;
    article.tabIndex = -1;
    const heading = document.createElement("h3");
    heading.textContent = paragraph.id;
    const text = document.createElement("p");
    text.textContent = paragraph.text;
    article.append(heading, text);
    list.append(article);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = paragraph.id;
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => {
      for (const node of list.children) node.classList.remove("highlight");
      for (const node of nav.children) node.setAttribute("aria-pressed", "false");
      article.classList.add("highlight");
      button.setAttribute("aria-pressed", "true");
      article.focus({ preventScroll: true });
      article.scrollIntoView({ block: "nearest" });
    });
    nav.append(button);
  }
  document.getElementById("original-text").textContent = data.original_text;
  document.getElementById("paragraph-note").textContent = `共 ${data.paragraphs.length} 段。標題獨立保存，不包含在正文證據中。`;
  result.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const currentRevision = ++revision;
  prepared = null;
  result.hidden = true;
  error.hidden = true;
  submit.disabled = true;
  status.textContent = "正在整理段落…";
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch("/articles/prepare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: titleInput.value, content: contentInput.value, paragraph_mode: modeInput.value }),
      signal: controller.signal,
    });
    const data = await response.json();
    if (currentRevision !== revision) return;
    if (!response.ok) {
      const message = typeof data.detail === "string" ? data.detail : "請確認標題及內文長度、內容與分段方式。";
      throw new Error(message);
    }
    prepared = data;
    render(data);
    status.textContent = "段落準備完成。尚未呼叫 AI 模型，資料未寫入新聞資料庫。";
  } catch (failure) {
    if (currentRevision !== revision) return;
    error.textContent = failure.name === "AbortError" ? "連線逾時，請稍後再試。" : failure.message;
    error.hidden = false;
    status.textContent = "段落準備未完成。";
  } finally {
    clearTimeout(timer);
    submit.disabled = false;
  }
});

document.getElementById("download-button").addEventListener("click", () => {
  if (!prepared) return;
  const blob = new Blob([JSON.stringify(prepared, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `article-${prepared.document_id.slice(0, 12)}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
