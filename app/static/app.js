const state = {
  docs: [],
  current: null,
  dirty: false,
  svg: "",
  filename: "diagram",
  title: "diagram",
  catalog: [],
  busy: false,
};

const specEl = document.querySelector("#spec");
const docsEl = document.querySelector("#docs");
const previewEl = document.querySelector("#preview");
const statusEl = document.querySelector("#status");
const warningsEl = document.querySelector("#warnings");
const metaEl = document.querySelector("#preview-meta");
const editorTitle = document.querySelector("#editor-title");
const editorNote = document.querySelector("#editor-note");
const healthEl = document.querySelector("#health");
const bannerEl = document.querySelector("#banner");
const typeEl = document.querySelector("#new-type");

specEl.addEventListener("input", () => {
  state.dirty = true;
});

document.querySelector("#render").addEventListener("click", () => renderCurrent());
document.querySelector("#save").addEventListener("click", () => saveSpec());
document.querySelector("#download-yaml").addEventListener("click", () => downloadText(`${state.filename}.yaml`, specEl.value, "text/yaml"));
document.querySelector("#download-svg").addEventListener("click", () => downloadSvg());
document.querySelector("#download-png").addEventListener("click", () => downloadPng());
document.querySelector("#pack").addEventListener("click", () => renderPack());
document.querySelector("#zip").addEventListener("click", () => downloadZip());
document.querySelector("#doc-filter").addEventListener("input", (event) => paintDocs(event.target.value));
document.querySelector("#icon-filter").addEventListener("input", (event) => paintIcons(event.target.value));
document.querySelector("#create").addEventListener("submit", (event) => {
  event.preventDefault();
  createSpec(typeEl.value);
});

specEl.addEventListener("keydown", (event) => {
  if (event.key === "Tab") {
    event.preventDefault();
    insertAtCursor("  ");
  } else if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    renderCurrent();
  } else if (event.key === "s" && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    saveSpec();
  }
});

boot();

async function boot() {
  const health = await api("/api/health");
  const types = Object.keys(health.types);
  typeEl.innerHTML = types.map((type) => `<option value="${type}">${type}</option>`).join("");
  healthEl.textContent = health.graphviz ? "Graphviz sẵn sàng · chỉ lắng nghe 127.0.0.1" : "Thiếu Graphviz";
  if (!health.graphviz) {
    bannerEl.hidden = false;
    bannerEl.textContent = "Chưa thấy lệnh dot. Roadmap, sequence và stack vẫn kết xuất được. Architecture, flow và context cần Graphviz: winget install Graphviz.Graphviz";
  }
  const data = await api("/api/docs");
  state.docs = data.docs;
  paintDocs("");
  api("/api/catalog").then((catalog) => {
    state.catalog = catalog.groups;
    document.querySelector("#icon-filter").placeholder = `Tìm trong ${catalog.count} icon`;
  }).catch(() => {});
  if (state.docs.length) {
    await openDoc(state.docs[0], true);
    await renderCurrent();
  }
}

function paintDocs(query) {
  const needle = query.trim().toLowerCase();
  docsEl.innerHTML = "";
  state.docs.filter((doc) => {
    const hay = `${doc.title} ${doc.type} ${doc.name}`.toLowerCase();
    return !needle || hay.includes(needle);
  }).forEach((doc) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "doc" + (state.current && state.current.id === doc.id ? " active" : "");
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = (doc.type || "spec").toUpperCase();
    const copy = document.createElement("span");
    copy.innerHTML = `${escapeHtml(doc.title)}<small>${doc.builtin ? "Mẫu" : "Đã lưu"} · ${escapeHtml(doc.renderer || "")}</small>`;
    button.append(badge, copy);
    button.addEventListener("click", () => openDoc(doc, false));
    docsEl.append(button);
  });
}

async function openDoc(doc, force) {
  if (!force && state.dirty && !window.confirm("Spec đang sửa chưa được lưu. Mở spec khác?")) return;
  const loaded = await api(`/api/docs/${doc.kind}/${doc.name}`);
  state.current = doc;
  state.dirty = false;
  specEl.value = loaded.spec;
  editorTitle.textContent = loaded.title;
  editorNote.textContent = `${loaded.builtin ? "Mẫu" : "Spec đã lưu"} · ${loaded.renderer || loaded.type}`;
  paintDocs(document.querySelector("#doc-filter").value);
}

async function createSpec(type) {
  if (state.dirty && !window.confirm("Spec đang sửa chưa được lưu. Tạo spec mới?")) return;
  const data = await api(`/api/skeletons/${type}`);
  state.current = null;
  state.dirty = true;
  specEl.value = data.spec;
  editorTitle.textContent = "Spec mới";
  editorNote.textContent = data.renderer || type;
  paintDocs(document.querySelector("#doc-filter").value);
  setStatus(`Đã tạo khung ${type}`);
}

async function renderCurrent() {
  await withBusy(async () => {
    setStatus("Đang kết xuất…");
    const figure = await api("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec: specEl.value }),
    });
    state.svg = figure.svg;
    state.filename = figure.filename;
    state.title = figure.title;
    showFigure(figure);
    setStatus(`${figure.type} · ${figure.renderer}`);
  });
}

function showFigure(figure) {
  warningsEl.hidden = !figure.warnings.length;
  warningsEl.innerHTML = figure.warnings.map((warning) => `<p>${escapeHtml(warning)}</p>`).join("");
  metaEl.textContent = `${figure.title} · ${figure.renderer}`;
  previewEl.innerHTML = `<div class="sheet">${figure.svg}</div>`;
}

async function renderPack() {
  const builtins = state.docs.filter((doc) => doc.builtin);
  previewEl.innerHTML = "";
  warningsEl.hidden = true;
  await withBusy(async () => {
    for (let index = 0; index < builtins.length; index += 1) {
      const doc = builtins[index];
      setStatus(`Đang kết xuất bộ mẫu ${index + 1}/${builtins.length}…`);
      const loaded = await api(`/api/docs/${doc.kind}/${doc.name}`);
      try {
        const figure = await api("/api/render", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ spec: loaded.spec }),
        });
        const card = document.createElement("article");
        card.className = "figure-card";
        const title = document.createElement("h3");
        title.textContent = figure.title;
        const note = document.createElement("p");
        note.textContent = `${figure.type} · ${figure.renderer}`;
        const sheet = document.createElement("div");
        sheet.className = "sheet";
        sheet.innerHTML = figure.svg;
        card.append(title, note, sheet);
        previewEl.append(card);
      } catch (error) {
        const card = document.createElement("article");
        card.className = "figure-card";
        card.textContent = `${doc.title}: ${error.message}`;
        previewEl.append(card);
      }
    }
    metaEl.textContent = "Cả bộ mẫu dùng chung khung, màu và footer.";
    setStatus(`Đã kết xuất ${builtins.length} diagram`);
  });
}

async function saveSpec() {
  const suggested = state.current && !state.current.builtin ? state.current.name : state.filename || "diagram";
  const name = window.prompt("Tên file spec", suggested);
  if (!name) return;
  await withBusy(async () => {
    const saved = await api(`/api/specs/${encodeURIComponent(name.trim())}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec: specEl.value }),
    });
    const data = await api("/api/docs");
    state.docs = data.docs;
    state.current = state.docs.find((doc) => doc.id === saved.id) || null;
    state.dirty = false;
    editorTitle.textContent = saved.title;
    paintDocs(document.querySelector("#doc-filter").value);
    setStatus(`Đã lưu specs/${saved.name}.yaml`);
  });
}

async function downloadZip() {
  await withBusy(async () => {
    setStatus("Đang đóng gói bộ mẫu…");
    const response = await fetch("/api/pack.zip", { method: "POST" });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(messageOf(data));
    }
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "technology-diagrams.zip";
    link.click();
    setStatus("Đã tải technology-diagrams.zip");
  });
}

function downloadSvg() {
  if (!state.svg) {
    setStatus("Hãy kết xuất trước khi tải", true);
    return;
  }
  downloadText(`${state.filename}.svg`, state.svg, "image/svg+xml");
}

function downloadPng() {
  if (!state.svg) {
    setStatus("Hãy kết xuất trước khi tải", true);
    return;
  }
  const blob = new Blob([state.svg], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const image = new Image();
  image.onload = () => {
    const scale = 2;
    const canvas = document.createElement("canvas");
    canvas.width = image.naturalWidth * scale;
    canvas.height = image.naturalHeight * scale;
    const context = canvas.getContext("2d");
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((png) => {
      const link = document.createElement("a");
      link.href = URL.createObjectURL(png);
      link.download = `${state.filename}.png`;
      link.click();
    }, "image/png");
    URL.revokeObjectURL(url);
  };
  image.onerror = () => setStatus("Không xuất được PNG. File SVG vẫn tải được.", true);
  image.src = url;
}

function paintIcons(query) {
  const box = document.querySelector("#icons");
  const needle = query.trim().toLowerCase();
  box.innerHTML = "";
  if (needle.length < 2) {
    box.textContent = state.catalog.length ? "Gõ ít nhất 2 ký tự." : "Đang tải danh mục…";
    return;
  }
  let shown = 0;
  for (const group of state.catalog) {
    const hits = group.icons.filter((icon) => icon.toLowerCase().includes(needle)).slice(0, 8);
    if (!hits.length) continue;
    const label = document.createElement("div");
    label.className = "group-label";
    label.textContent = group.label;
    box.append(label);
    hits.forEach((icon) => {
      if (shown >= 40) return;
      shown += 1;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "icon";
      const name = icon.split(".").pop();
      button.innerHTML = `<b>${escapeHtml(name)}</b><span>${escapeHtml(icon)}</span>`;
      button.addEventListener("click", () => {
        insertAtCursor(icon);
        setStatus(`Đã chèn ${icon}`);
      });
      box.append(button);
    });
    if (shown >= 40) break;
  }
  if (!shown) box.textContent = "Không có icon khớp.";
}

function insertAtCursor(text) {
  const start = specEl.selectionStart;
  const end = specEl.selectionEnd;
  specEl.value = specEl.value.slice(0, start) + text + specEl.value.slice(end);
  specEl.selectionStart = specEl.selectionEnd = start + text.length;
  specEl.focus();
  state.dirty = true;
}

function downloadText(filename, text, mime) {
  const blob = new Blob([text], { type: mime });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
}

async function withBusy(action) {
  if (state.busy) return;
  state.busy = true;
  document.querySelectorAll("button").forEach((button) => {
    button.disabled = true;
  });
  try {
    await action();
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    state.busy = false;
    document.querySelectorAll("button").forEach((button) => {
      button.disabled = false;
    });
  }
}

async function api(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(messageOf(data));
  return data;
}

function messageOf(data) {
  if (!data || !data.detail) return "Yêu cầu thất bại";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map((item) => item.msg || String(item)).join("; ");
  return "Yêu cầu thất bại";
}

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.classList.toggle("error", isError);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}
