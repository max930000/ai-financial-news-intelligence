// Article-input flow: URL → fetch → (failure → paste) → preview → confirm.
// All server text goes through textContent, never innerHTML.
(function () {
  "use strict";

  const main = document.querySelector(".chk-main");
  const limits = {
    min: Number(main.dataset.minChars),
    max: Number(main.dataset.maxChars),
  };
  const $ = (id) => document.getElementById(id);

  const panels = { url: $("panel-url"), paste: $("panel-paste"), review: $("panel-review"), done: $("panel-done") };
  const stepOf = { url: "input", paste: "input", review: "review", done: "done" };
  const headings = { url: "h-url", paste: "h-paste", review: "h-review", done: "h-done" };

  // What the review panel is showing, and where it came from.
  const state = {
    url: null,            // URL the user submitted (kept for provenance)
    fetched: null,        // preview response, when the fetch succeeded
    failureReason: null,  // why the fetch failed, when the user pasted instead
    submitting: false,
  };

  // ---------------------------------------------------------------- helpers

  function show(name) {
    for (const [key, el] of Object.entries(panels)) el.hidden = key !== name;
    const current = stepOf[name];
    const order = ["input", "review", "done"];
    document.querySelectorAll("#steps li").forEach((li) => {
      const step = li.dataset.step;
      li.toggleAttribute("aria-current", step === current);
      if (step === current) li.setAttribute("aria-current", "step");
      li.classList.toggle("is-done", order.indexOf(step) < order.indexOf(current));
    });
    $(headings[name]).focus({ preventScroll: false });
  }

  function showError(el, message) {
    el.textContent = message || "";
    el.hidden = !message;
  }

  const charCount = (text) => text.replace(/\s/g, "").length;
  const paragraphCount = (text) => text.split(/\n\s*\n/).filter((p) => p.trim()).length;
  const normalize = (text) => text.replace(/\r\n?/g, "\n").trim();

  function formatTime(iso) {
    if (!iso) return "未知";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "未知";
    return new Intl.DateTimeFormat("zh-TW", {
      dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Taipei",
    }).format(date) + "（台北時間）";
  }

  function renderMeta(target, rows) {
    target.replaceChildren();
    for (const [label, value, badge] of rows) {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value;
      if (badge) {
        const span = document.createElement("span");
        span.className = "chk-badge";
        span.textContent = badge;
        dd.append(span);
      }
      target.append(dt, dd);
    }
  }

  function updateCount(target, text) {
    const chars = charCount(text);
    const ok = chars >= limits.min && chars <= limits.max;
    target.textContent =
      `目前 ${chars.toLocaleString()} 字・${paragraphCount(text)} 段` +
      `（需 ${limits.min.toLocaleString()}～${limits.max.toLocaleString()} 字）`;
    target.classList.toggle("is-bad", chars > 0 && !ok);
    return ok;
  }

  async function postJson(path, payload) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    let data = null;
    try { data = await response.json(); } catch (_) { /* non-JSON error page */ }
    return { status: response.status, data };
  }

  // ---------------------------------------------------------------- step 1a: URL

  $("url-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (state.submitting) return;
    const url = $("url-input").value.trim();
    showError($("url-error"), "");
    if (!url) { showError($("url-error"), "請貼上新聞網址。"); $("url-input").focus(); return; }

    state.submitting = true;
    state.url = url;
    const button = $("url-submit");
    button.disabled = true;
    button.textContent = "擷取中…";
    try {
      const { status, data } = await postJson("/articles/preview", { url });
      if (status !== 200 || !data) {
        showFailure("伺服器暫時無法處理這個網址。", "server_error", "");
      } else if (data.ok) {
        state.fetched = data;
        state.failureReason = null;
        openReview({ origin: "fetched", title: data.title || "", body: data.body });
      } else {
        showFailure(data.message, data.failure_reason, data.title || "");
      }
    } catch (_) {
      showFailure("無法連線到伺服器，請確認網路後再試。", "network_error", "");
    } finally {
      state.submitting = false;
      button.disabled = false;
      button.textContent = "擷取文章";
    }
  });

  // Direct entry: no URL was fetched, so drop any URL left over from an earlier failed try.
  $("to-paste").addEventListener("click", () => {
    state.url = null;
    state.failureReason = null;
    $("failure").hidden = true;
    showError($("paste-error"), "");
    show("paste");
  });

  // ---------------------------------------------------------------- step 1b: paste
  // Reached from the link above, or automatically after a failed fetch (showFailure).

  function showFailure(message, reason, title) {
    state.fetched = null;
    state.failureReason = reason;
    $("failure-message").textContent = message;
    $("failure").hidden = false;
    showError($("paste-error"), "");
    if (title && !$("paste-title").value) $("paste-title").value = title;
    updateCount($("paste-count"), $("paste-body").value);
    show("paste");
  }

  // A stale error would contradict the corrected text, so clear it on edit.
  $("paste-body").addEventListener("input", () => {
    updateCount($("paste-count"), $("paste-body").value);
    showError($("paste-error"), "");
  });
  $("paste-title").addEventListener("input", () => showError($("paste-error"), ""));

  $("paste-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const title = $("paste-title").value.trim();
    const body = normalize($("paste-body").value);
    if (!title) { showError($("paste-error"), "請填寫標題。"); $("paste-title").focus(); return; }
    if (!updateCount($("paste-count"), body)) {
      showError($("paste-error"),
        `內文需要 ${limits.min.toLocaleString()}～${limits.max.toLocaleString()} 字，請貼上完整正文。`);
      $("paste-body").focus();
      return;
    }
    showError($("paste-error"), "");
    state.fetched = null;
    openReview({ origin: "pasted", title, body });
  });

  $("to-url").addEventListener("click", () => show("url"));

  // ---------------------------------------------------------------- step 2: review

  let original = { title: "", body: "" };

  function openReview({ origin, title, body }) {
    original = { title, body };
    $("review-title").value = title;
    $("review-body").value = body;
    showError($("review-error"), "");

    const fetched = state.fetched;
    const rows = fetched
      ? [
          ["來源", fetched.source || "未知"],
          ["網址", fetched.final_url || fetched.url],
          ["發布時間", formatTime(fetched.published_at)],
          ["擷取時間", formatTime(fetched.fetched_at)],
        ]
      : [
          ["來源", "手動貼上"],
          ["網址", state.url || "未提供"],
          ["發布時間", "未知"],
        ];
    renderMeta($("review-meta"), rows);

    const warnings = $("review-warnings");
    warnings.replaceChildren();
    for (const text of (fetched && fetched.warnings) || []) {
      const li = document.createElement("li");
      li.textContent = text;
      warnings.append(li);
    }
    warnings.hidden = !warnings.children.length;

    refreshReview();
    show("review");
  }

  function refreshReview() {
    const body = $("review-body").value;
    const ok = updateCount($("review-count"), body);
    const edited = normalize(body) !== normalize(original.body) ||
      $("review-title").value.trim() !== original.title.trim();
    const countEl = $("review-count");
    countEl.querySelector(".chk-badge")?.remove();
    if (edited && state.fetched) {
      const badge = document.createElement("span");
      badge.className = "chk-badge";
      badge.textContent = "已編輯";
      countEl.append(badge);
    }
    return ok;
  }

  for (const id of ["review-body", "review-title"]) {
    $(id).addEventListener("input", () => {
      refreshReview();
      showError($("review-error"), "");
    });
  }

  $("confirm-btn").addEventListener("click", async () => {
    if (state.submitting) return;
    const title = $("review-title").value.trim();
    const body = normalize($("review-body").value);
    if (!title) { showError($("review-error"), "請填寫標題。"); $("review-title").focus(); return; }
    if (!refreshReview()) {
      showError($("review-error"),
        `內文需要 ${limits.min.toLocaleString()}～${limits.max.toLocaleString()} 字。`);
      $("review-body").focus();
      return;
    }

    const fetched = state.fetched;
    const button = $("confirm-btn");
    state.submitting = true;
    button.disabled = true;
    showError($("review-error"), "");
    try {
      const { status, data } = await postJson("/articles", {
        url: fetched ? (fetched.final_url || fetched.url) : (state.url || null),
        title,
        body,
        fetched_body_hash: fetched ? fetched.body_hash : null,
        published_at: fetched ? fetched.published_at : null,
        fetched_at: fetched ? fetched.fetched_at : null,
        fetch_failure_reason: fetched ? null : state.failureReason,
      });
      if ((status === 200 || status === 201) && data) {
        openDone(data);
      } else if (status === 422 && data && data.detail && data.detail.message) {
        showError($("review-error"), data.detail.message);
      } else {
        showError($("review-error"), "儲存失敗，請稍後再試。你的內容還在這個頁面上。");
      }
    } catch (_) {
      showError($("review-error"), "無法連線到伺服器。你的內容還在這個頁面上，可以再按一次。");
    } finally {
      state.submitting = false;
      button.disabled = false;
    }
  });

  $("restart-btn").addEventListener("click", reset);

  // ---------------------------------------------------------------- step 3: done

  const originLabel = {
    fetched: "自動擷取",
    fetched_edited: "自動擷取後編輯",
    pasted: "手動貼上",
  };

  function openDone(article) {
    $("done-summary").textContent = article.created
      ? `文章 #${article.id} 已儲存。`
      : `先前已確認過相同內容，沿用文章 #${article.id}。`;
    renderMeta($("done-meta"), [
      ["標題", article.title],
      ["輸入方式", originLabel[article.input_origin] || article.input_origin],
      ["來源", article.source || "未知"],
      ["內文", `${article.char_count.toLocaleString()} 字・${article.paragraph_count} 段`],
      ["內容雜湊", article.content_hash.slice(0, 12)],
    ]);
    show("done");
  }

  $("another-btn").addEventListener("click", reset);

  function reset() {
    state.url = null;
    state.fetched = null;
    state.failureReason = null;
    for (const id of ["url-input", "paste-title", "paste-body", "review-title", "review-body"]) $(id).value = "";
    for (const id of ["url-error", "paste-error", "review-error"]) showError($(id), "");
    $("failure").hidden = true;
    updateCount($("paste-count"), "");
    show("url");
  }

  updateCount($("paste-count"), "");
  $("url-input").focus();
})();
