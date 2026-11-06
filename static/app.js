const $ = (id) => document.getElementById(id);

const EXAMPLES = {
  spam: "CONGRATULATIONS! You have been selected to receive a $1000 Walmart gift card. " +
    "Click here to claim your prize now before it expires: http://bit.ly/claim-now. " +
    "Reply STOP to opt out.",
  ham: "Hi Sam,\n\nThanks for sending over the slides. I've added my comments on the budget " +
    "section. Are we still on for the review meeting tomorrow at 10?\n\nBest,\nPriya",
};

// Every API call goes through here so an expired session sends the user back to login
async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("Not logged in");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body && body.detail;
    throw new Error(typeof detail === "string" ? detail : "Something went wrong. Please try again.");
  }
  return body;
}

function showError(id, message) {
  $(id).textContent = message;
  $(id).hidden = !message;
}

function badge(label) {
  const el = document.createElement("span");
  el.className = `badge ${label}`;
  el.textContent = label === "spam" ? "Spam" : "Not spam";
  return el;
}

function pct(confidence) {
  return `${(confidence * 100).toFixed(1)}%`;
}

function cell(row, content, className) {
  const td = document.createElement("td");
  if (className) td.className = className;
  if (content instanceof Node) td.appendChild(content);
  else td.textContent = content;
  row.appendChild(td);
  return td;
}

// ---------- User ----------
api("/auth/me").then((user) => {
  $("user-email").textContent = user.email;
  $("avatar").textContent = user.email.charAt(0);
}).catch(() => {});

$("logout").addEventListener("click", async () => {
  await fetch("/auth/logout", { method: "POST" }).catch(() => {});
  window.location.href = "/login";
});

// ---------- Tabs ----------
const tabs = ["paste", "upload", "history"];

function selectTab(name) {
  for (const t of tabs) {
    $(`tab-${t}`).setAttribute("aria-selected", String(t === name));
    $(`panel-${t}`).hidden = t !== name;
  }
  if (name === "history") loadHistory();
}

for (const t of tabs) $(`tab-${t}`).addEventListener("click", () => selectTab(t));

// ---------- Paste & check ----------
$("example-spam").addEventListener("click", () => { $("email-text").value = EXAMPLES.spam; });
$("example-ham").addEventListener("click", () => { $("email-text").value = EXAMPLES.ham; });

$("check-btn").addEventListener("click", async () => {
  const text = $("email-text").value;
  showError("check-error", "");
  if (!text.trim()) {
    showError("check-error", "Paste an email first.");
    return;
  }

  $("check-btn").disabled = true;
  $("check-spinner").hidden = false;
  try {
    const result = await api("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const box = $("result");
    box.className = `result ${result.label}`;
    $("result-icon").textContent = result.is_spam ? "!" : "✓";
    $("result-label").textContent = result.is_spam ? "Looks like spam" : "Not spam";
    $("result-meter").style.width = pct(result.confidence);
    $("result-confidence").textContent = `${pct(result.confidence)} confident`;
    box.hidden = false;
  } catch (err) {
    showError("check-error", err.message);
  } finally {
    $("check-btn").disabled = false;
    $("check-spinner").hidden = true;
  }
});

// ---------- Upload .eml ----------
const dropzone = $("dropzone");
const fileInput = $("file-input");

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("over"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("over"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("over");
  uploadFiles(e.dataTransfer.files);
});
fileInput.addEventListener("change", () => {
  uploadFiles(fileInput.files);
  fileInput.value = "";
});

async function uploadFiles(fileList) {
  const files = Array.from(fileList);
  showError("upload-error", "");
  if (!files.length) return;
  if (files.length > 20) {
    showError("upload-error", "Upload at most 20 files at once.");
    return;
  }

  const form = new FormData();
  for (const f of files) form.append("files", f);

  $("upload-spinner").hidden = false;
  $("upload-status").textContent = `Checking ${files.length} file${files.length > 1 ? "s" : ""}…`;
  try {
    const { results } = await api("/predict/eml", { method: "POST", body: form });
    const rows = $("upload-rows");
    rows.replaceChildren();
    let spamCount = 0;
    for (const r of results) {
      const tr = document.createElement("tr");
      cell(tr, r.filename, "clip");
      cell(tr, r.subject || "—", "clip");
      if (r.prediction) {
        if (r.prediction.is_spam) spamCount += 1;
        cell(tr, badge(r.prediction.label));
        cell(tr, pct(r.prediction.confidence), "num");
      } else {
        const err = document.createElement("span");
        err.className = "badge err";
        err.textContent = r.error;
        cell(tr, err);
        cell(tr, "—", "num");
      }
      rows.appendChild(tr);
    }
    $("upload-results").hidden = false;
    $("upload-status").textContent = `${spamCount} of ${results.length} flagged as spam.`;
  } catch (err) {
    $("upload-status").textContent = "";
    showError("upload-error", err.message);
  } finally {
    $("upload-spinner").hidden = true;
  }
}

// ---------- History ----------
async function loadHistory() {
  showError("history-error", "");
  try {
    const items = await api("/history");
    const rows = $("history-rows");
    rows.replaceChildren();
    for (const item of items) {
      const tr = document.createElement("tr");
      cell(tr, new Date(item.created_at).toLocaleString(), "num");
      cell(tr, item.source === "eml" ? ".eml file" : "Pasted");
      cell(tr, item.snippet, "clip");
      cell(tr, badge(item.label));
      cell(tr, pct(item.confidence), "num");
      rows.appendChild(tr);
    }
    $("history-wrap").hidden = items.length === 0;
    $("history-empty").hidden = items.length !== 0;
  } catch (err) {
    showError("history-error", err.message);
  }
}
