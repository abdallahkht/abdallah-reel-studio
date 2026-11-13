const $ = (s) => document.querySelector(s);
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const uid = () => crypto.randomUUID().slice(0, 12);
const clock = (s, precise = false) =>
  `${String(Math.floor(Math.max(0, s) / 60)).padStart(2, "0")}:${(Math.max(0, s) % 60).toFixed(precise ? 3 : 2).padStart(precise ? 6 : 5, "0")}`;
const video = $("#video"),
  canvas = $("#overlay"),
  context = canvas.getContext("2d");
let p,
  token,
  selected,
  active = 0,
  mode = "edit",
  savedTime = 0,
  dirty = false,
  sequence = 0,
  pendingSave = null,
  saveTimer,
  toastTimer,
  peaks = [],
  editPeaks = [],
  undo = [],
  redo = [],
  images = new Map(),
  drag = null;
let state,
  loadedKind = "",
  loading = false,
  exportBusy = false,
  projectEpoch = 0,
  desiredTime = null,
  editingTime = false,
  timeDraft = "";
async function api(path, body, retry = true) {
  const response = await fetch(
    path,
    body
      ? {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Reel-Token": token,
          },
          body: JSON.stringify(body),
        }
      : {},
  );
  if (response.status === 403 && body && retry) {
    token = (await api("/api/state")).token;
    return api(path, body, false);
  }
  const data = await response.json();
  if (!response.ok)
    throw Error(data.error || "Could not complete that action.");
  return data;
}
function toast(message, stay = false, url) {
  clearTimeout(toastTimer);
  $("#status").hidden = false;
  $("#status").textContent = message;
  if (url) {
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    a.textContent = "Open video";
    $("#status").append(a);
  }
  if (!stay) toastTimer = setTimeout(() => ($("#status").hidden = true), 4000);
}
function error(e) {
  console.error(e);
  toast(e.message || String(e), true);
}
function clips() {
  let out = 0;
  return (p?.clips || [])
    .filter((c) => c.enabled)
    .map((c) => {
      const value = { ...c, out };
      out += c.end - c.start;
      return value;
    });
}
function duration() {
  return clips().reduce((n, c) => n + c.end - c.start, 0);
}
function segments() {
  let out = 0,
    result = [];
  const map = [...(p?.rendered?.mapping || [])].sort(
    (a, b) => a.sourceStart - b.sourceStart,
  );
  for (const c of clips()) {
    let cursor = c.start;
    const add = (a, b, m) => {
      if (b - a < 0.000001) return;
      const start = m ? m.editStart + a - m.sourceStart : a;
      result.push({
        clipId: c.id,
        kind: m ? "edit" : "source",
        start,
        end: start + b - a,
        sourceStart: a,
        sourceEnd: b,
        out,
      });
      out += b - a;
    };
    for (const m of map) {
      const a = Math.max(cursor, m.sourceStart),
        b = Math.min(c.end, m.sourceEnd);
      if (b <= a) continue;
      add(cursor, a);
      add(a, b, m);
      cursor = b;
    }
    add(cursor, c.end);
  }
  return result;
}
function fps() {
  return p?.rendered?.media.fps || p?.fps || 30;
}
function current() {
  if (!p) return 0;
  if (desiredTime !== null) return desiredTime;
  if (mode === "source") return video.currentTime;
  const s = segments()[active];
  return s
    ? s.out +
        Math.max(0, Math.min(s.end - s.start, video.currentTime - s.start))
    : 0;
}
function loadTime(kind, t, play = false) {
  const url = `/media/${p.id}/${kind === "edit" ? "edit-preview" : "preview"}.mp4`;
  if (loadedKind === url && video.readyState >= 1) {
    video.currentTime = t;
    if (play) video.play().catch(error);
    return;
  }
  loadedKind = url;
  loading = true;
  video.src = url;
  video.onloadedmetadata = () => {
    loading = false;
    video.currentTime = t;
    if (play) video.play().catch(error);
  };
}
function seek(t, play = false) {
  if (!p) return;
  desiredTime = Math.max(
    0,
    Math.min(mode === "source" ? p.media.duration : duration(), t),
  );
  if (mode === "source") {
    loadTime("source", Math.max(0, Math.min(p.media.duration, t)), play);
    return;
  }
  const list = segments();
  t = Math.max(0, Math.min(duration() - 0.00001, t));
  active = list.findIndex((s) => t < s.out + s.end - s.start - 0.000001);
  if (active < 0) active = list.length - 1;
  const s = list[active];
  if (s) {
    selected = s.clipId;
    document.querySelectorAll('[data-clip]').forEach(el => el.classList.toggle('selected',el.dataset.clip === selected));
    const clip=p.clips.find(c => c.id === selected);
    $('#selection-label').textContent=clip ? `${(clip.end-clip.start).toFixed(2)}s selected` : '';
    loadTime(s.kind, s.start + t - s.out, play);
  }
}
function sourceTime() {
  if (mode === "source") return current();
  const s = segments()[active];
  return s ? s.sourceStart + Math.max(0, current() - s.out) : 0;
}
function mark(reason = "Correction") {
  dirty = true;
  sequence++;
  $("#saved").textContent = "Saving…";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => flush(reason).catch(error), 450);
}
async function flush(reason = "Correction") {
  clearTimeout(saveTimer);
  if (pendingSave) {
    await pendingSave;
    if (dirty) return flush(reason);
    return;
  }
  if (!dirty || !p) return;
  const seq = sequence,
    snapshot = structuredClone(p),
    pid = p.id;
  pendingSave = api(`/api/projects/${pid}/save`, { project: snapshot, reason })
    .then((saved) => {
      if (p?.id === pid) {
        p.revision = saved.revision;
        if (seq === sequence) dirty = false;
        $("#saved").textContent = dirty ? "Saving…" : "Saved";
      }
    })
    .finally(() => (pendingSave = null));
  try {
    await pendingSave;
  } catch (e) {
    $("#saved").textContent = "Not saved";
    throw e;
  }
  if (dirty) return flush(reason);
}
function mutate(fn, reason) {
  const before = structuredClone(p),
    at = current();
  undo.push(before);
  redo = [];
  fn();
  mark(reason);
  render();
  if (mode === "edit") seek(Math.min(at, duration() - 0.001));
}
function historyStep(direction) {
  const from = direction === "undo" ? undo : redo,
    to = direction === "undo" ? redo : undo;
  if (!from.length) return;
  const revision = p.revision,
    at = current();
  to.push(structuredClone(p));
  p = from.pop();
  p.revision = revision;
  selected = p.clips.find((c) => c.enabled)?.id;
  mark(direction === "undo" ? "Undo" : "Redo");
  render();
  seek(Math.min(at, duration() - 0.001));
}
async function listProjects() {
  state = await api("/api/state");
  token = state.token;
  $("#projects").innerHTML = state.projects
    .map((x) => `<option value="${x.id}">${esc(x.name)}</option>`)
    .join("");
  if (p) $("#projects").value = p.id;
}
async function openProject(pid) {
  video.pause();
  const epoch = ++projectEpoch;
  p = await api(`/api/projects/${pid}`);
  mode = "edit";
  dirty = false;
  undo = [];
  redo = [];
  images.clear();
  selected = p.clips.find((c) => c.enabled)?.id;
  loadedKind = "";
  active = 0;
  peaks = [];
  editPeaks = [];
  $("#restore-panel").hidden = true;
  $("#restore-toggle").classList.remove("active");
  localStorage.setItem("reel-review-project", pid);
  $("#empty").hidden = true;
  $("#screen").hidden = false;
  $("#saved").textContent = "Saved";
  render();
  if (!p.previewReady && p.preparation?.state === "running") {
    await poll(p.preparation);
    if (epoch !== projectEpoch) return;
    p = await api(`/api/projects/${pid}`);
  }
  try {
    peaks = await (await fetch(`/media/${pid}/waveform.json`)).json();
    if (p.rendered)
      editPeaks = await (
        await fetch(`/media/${pid}/edit-waveform.json`)
      ).json();
  } catch {}
  if (epoch !== projectEpoch) return;
  seek(0);
  renderTimeline();
  await listProjects();
}
async function poll(j) {
  while (j.state === "running") {
    toast(j.progress, true);
    await new Promise((r) => setTimeout(r, 900));
    j = await api(`/api/jobs/${j.id}`);
  }
  if (j.state === "error") throw Error(j.error);
  $("#status").hidden = true;
  return j.result;
}
function render() {
  const available = !!p;
  for (const s of [
    "#export",
    "#add-note",
    "#split",
    "#remove",
    "#restore-toggle",
    "#notes-toggle",
    "#history-toggle",
  ])
    $(s).disabled = !available;
  $("#undo").disabled = !undo.length;
  $("#redo").disabled = !redo.length;
  if (!p) {
    $("#empty").hidden = false;
    $("#screen").hidden = true;
    return;
  }
  $("#projects").value = p.id;
  $("#duration").textContent =
    "/ " + clock(mode === "source" ? p.media.duration : duration());
  $("#note-count").textContent = p.notes.filter((n) => !n.done).length || "";
  const c = p.clips.find((c) => c.id === selected && c.enabled);
  $("#selection-label").textContent = c
    ? `${(c.end - c.start).toFixed(2)}s selected`
    : "";
  renderTimeline();
  renderNotes();
}
function thumb(kind, t) {
  const info = kind === "edit" ? p.rendered.media : p.media;
  const frame = Math.max(0, Math.min(19, Math.floor((t / info.duration) * 20)));
  return `background-image:url('/media/${p.id}/${kind === "edit" ? "edit" : "source"}-thumbs.jpg');background-position:-${frame * 34}px 0`;
}
function renderTimeline() {
  if (!p) return;
  const width =
      Math.max(300, $("#timeline-scroll").clientWidth) *
      Number($("#zoom").value),
    d = duration();
  $("#timeline").style.width = width + "px";
  const count = Math.max(4, Math.round(width / 100));
  $("#ruler").innerHTML = Array.from(
    { length: count },
    (_, i) =>
      `<span style="left:${(i / count) * 100}%">${clock((d * i) / count).slice(0, 5)}</span>`,
  ).join("");
  const list = segments();
  $("#clips").innerHTML = clips()
    .map((c, i) => {
      const w = ((c.end - c.start) / d) * width,
        frames = Math.max(1, Math.ceil(w / 34)),
        members = list.filter((s) => s.clipId === c.id);
      let strips = "";
      for (let j = 0; j < frames; j++) {
        const time = c.out + ((c.end - c.start) * j) / frames,
          s =
            members.find((s) => time < s.out + s.end - s.start) ||
            members.at(-1);
        strips += `<i style="${thumb(s.kind, s.start + time - s.out)}"></i>`;
      }
      return `<div class="clip ${c.id === selected ? "selected" : ""}" data-clip="${c.id}" style="position:absolute;left:${(c.out / d) * width}px;width:${Math.max(3, w - 2)}px" tabindex="0" role="button" aria-label="Section ${i + 1}"><div class="filmstrip">${strips}</div><span class="clip-name">${i + 1}</span><span class="handle in" data-edge="start" aria-label="Trim start"></span><span class="handle out" data-edge="end" aria-label="Trim end"></span></div>`;
    })
    .join("");
  $("#markers").innerHTML = p.notes
    .filter((n) => n.mode === "edit" && !n.done)
    .map(
      (n) =>
        `<button class="note-marker" data-note="${n.id}" style="left:${(n.time / d) * 100}%" title="${esc(n.text)}" aria-label="Note at ${clock(n.time)}"></button>`,
    )
    .join("");
  const wave = $("#waveform"),
    cx = wave.getContext("2d");
  wave.width = width * 2;
  cx.clearRect(0, 0, wave.width, 40);
  cx.fillStyle = "#628b8b";
  for (let x = 0; x < wave.width; x += 4) {
    const t = (x / wave.width) * d,
      s = list.find((s) => t >= s.out && t < s.out + s.end - s.start);
    if (!s) continue;
    const edit = s.kind === "edit" && editPeaks.length,
      values = edit ? editPeaks : peaks,
      sourceDuration = edit ? p.rendered.media.duration : p.media.duration,
      at = edit ? s.start + t - s.out : s.sourceStart + t - s.out,
      amp = values[Math.floor((at / sourceDuration) * values.length)] || 0.025;
    cx.fillRect(x, 20 - amp * 18, 2, Math.max(1, amp * 36));
  }
}
function renderNotes() {
  $("#notes-list").innerHTML = p.notes
    .map(
      (n) =>
        `<div class="note ${n.done ? "done" : ""}"><button data-note="${n.id}">${clock(n.time)}${n.mode === "source" ? " · original" : ""}</button><span class="note-actions"><button data-resolve="${n.id}">${n.done ? "Reopen" : "Done"}</button><button data-delete-note="${n.id}" aria-label="Delete note" title="Delete note">Delete</button></span><p dir="auto">${esc(n.text)}</p></div>`,
    )
    .join("");
}
function restoreRanges() {
  let end = 0,
    out = [];
  for (const c of [...p.clips]
    .filter((c) => c.enabled)
    .sort((a, b) => a.start - b.start)) {
    if (c.start > end + 0.001)
      out.push({ start: end, end: c.start, gap: true });
    out.push(c);
    end = Math.max(end, c.end);
  }
  if (end < p.media.duration - 0.001)
    out.push({ start: end, end: p.media.duration, gap: true });
  return out;
}
function openRestore() {
  if (!p) return;
  video.pause();
  savedTime = current();
  mode = "source";
  $("#restore-panel").hidden = false;
  $("#restore-toggle").classList.add("active");
  $("#source-strip").innerHTML = restoreRanges()
    .map((r) =>
      r.gap
        ? `<button data-gap="${r.start},${r.end}" style="left:${(r.start / p.media.duration) * 100}%;width:${((r.end - r.start) / p.media.duration) * 100}%" title="${clock(r.start)} – ${clock(r.end)}">${(r.end - r.start).toFixed(1)}s</button>`
        : `<span class="kept" style="left:${(r.start / p.media.duration) * 100}%;width:${((r.end - r.start) / p.media.duration) * 100}%"></span>`,
    )
    .join("");
  const c = p.clips.find((c) => c.id === selected),
    gaps = restoreRanges().filter((r) => r.gap);
  const range = gaps.find((g) => g.start >= (c?.end || 0) - 0.001) || gaps[0];
  if (range) setRestoreRange(range.start, Math.min(range.end, range.start + 1));
  else toast("All original footage is already included.");
  $("#duration").textContent = "/ " + clock(p.media.duration);
}
function setRestoreRange(a, b) {
  $("#restore-in").value = a.toFixed(6);
  $("#restore-out").value = b.toFixed(6);
  seek(a);
}
function closeRestore() {
  video.pause();
  mode = "edit";
  $("#restore-panel").hidden = true;
  $("#restore-toggle").classList.remove("active");
  seek(savedTime);
  render();
}
function openNotes() {
  if (!p) return;
  video.pause();
  $("#notes-panel").hidden = false;
  $("#note-at").textContent =
    `At ${clock(current(), true)}${mode === "source" ? " in original footage" : ""}`;
  $("#note-text").focus();
  renderTimeline();
}
function split() {
  const time = sourceTime(),
    c = p.clips.find((c) => c.id === segments()[active]?.clipId);
  if (c) selected = c.id;
  if (!c || time - c.start < 1 / 30 || c.end - time < 1 / 30) {
    toast("Place the playhead inside a section.");
    return;
  }
  mutate(() => {
    p.clips.splice(p.clips.indexOf(c) + 1, 0, {
      ...c,
      id: uid(),
      start: time,
      locked: true,
    });
    c.end = time;
    c.locked = true;
  }, "Split section");
}
function remove() {
  const c = p.clips.find((c) => c.id === selected);
  if (!c || !c.enabled) return;
  if (clips().length === 1) {
    toast("Keep at least one section.");
    return;
  }
  mutate(() => {
    c.enabled = false;
    c.locked = true;
    selected = p.clips.find((x) => x.enabled)?.id;
  }, "Removed section");
}
function paint() {
  requestAnimationFrame(paint);
  if (!p) return;
  const list = segments();
  if (!loading && !video.seeking && !video.paused) {
    if (mode === "edit") {
      const s = list[active];
      if (s && video.currentTime >= s.end - 0.007) {
        const next = list[active + 1];
        if (next) {
          active++;
          if (
            next.kind !== s.kind ||
            Math.abs(next.start - video.currentTime) > 0.075
          )
            loadTime(next.kind, next.start, true);
        } else video.pause();
      }
    } else if (video.currentTime >= Number($("#restore-out").value))
      video.pause();
  }
  const t = current();
  if (!editingTime) $("#time").value = clock(t, true);
  $("#frame").textContent = `Frame ${Math.floor(t * fps() + 0.00001) + 1}`;
  $("#play").textContent = video.paused ? "▶" : "Ⅱ";
  $("#playhead").style.left =
    `${((mode === "edit" ? t : savedTime) / duration()) * 100}%`;
  context.clearRect(0, 0, 1080, 1920);
  if (mode === "edit")
    for (const g of p.graphics || []) {
      if (!g.image || t < g.start || t > g.end) continue;
      let image = images.get(g.id);
      if (!image) {
        image = new Image();
        image.src = g.image;
        images.set(g.id, image);
      }
      const fade = Math.min(0.24, (g.end - g.start) / 3);
      context.globalAlpha = Math.max(
        0,
        Math.min(1, (t - g.start) / fade, (g.end - t) / fade),
      );
      if (image.complete) context.drawImage(image, 0, 0);
    }
  context.globalAlpha = 1;
}
$("#timeline").addEventListener("pointerdown", (e) => {
  if (!p || mode !== "edit" || e.target.closest(".note-marker")) return;
  video.pause();
  const clip = e.target.closest("[data-clip]"),
    edge = e.target.dataset.edge;
  if (clip) selected = clip.dataset.clip;
  if (edge) {
    const c = p.clips.find((c) => c.id === selected);
    drag = {
      type: "trim",
      edge,
      id: c.id,
      x: e.clientX,
      before: structuredClone(p),
      start: c.start,
      end: c.end,
      width: $("#timeline").clientWidth,
      duration: duration(),
    };
  } else {
    drag = { type: "seek" };
    const x = e.clientX - $("#timeline").getBoundingClientRect().left;
    seek((x / $("#timeline").clientWidth) * duration());
    render();
  }
  e.preventDefault();
});
window.addEventListener("pointermove", (e) => {
  if (!drag) return;
  if (drag.type === "seek") {
    seek(
      ((e.clientX - $("#timeline").getBoundingClientRect().left) /
        $("#timeline").clientWidth) *
        duration(),
    );
    return;
  }
  const c = p.clips.find((c) => c.id === drag.id),
    delta = ((e.clientX - drag.x) / drag.width) * drag.duration;
  const value = Math.round((drag[drag.edge] + delta) * fps()) / fps();
  if (drag.edge === "start")
    c.start = Math.max(0, Math.min(c.end - 1 / fps(), value));
  else c.end = Math.max(c.start + 1 / fps(), Math.min(p.media.duration, value));
  renderTimeline();
});
window.addEventListener("pointerup", () => {
  if (drag?.type === "trim") {
    undo.push(drag.before);
    redo = [];
    const c = p.clips.find((c) => c.id === drag.id);
    c.locked = true;
    mark("Trimmed section");
    render();
    seek(clips().find((c) => c.id === selected)?.out || 0);
  }
  drag = null;
});
$("#timeline").addEventListener("dblclick", () => split());
$("#play").onclick = () => {
  if (!p) return;
  if (video.paused) {
    if (mode === "edit" && current() >= duration() - 0.04) seek(0);
    video.play().catch(error);
  } else video.pause();
};
$("#back").onclick = () => {
  video.pause();
  seek(current() - 1 / fps());
};
$("#forward").onclick = () => {
  video.pause();
  seek(current() + 1 / fps());
};
$("#time").onfocus = () => {
  editingTime = true;
  timeDraft = $("#time").value;
};
$("#time").oninput = () => {
  editingTime = true;
  timeDraft = $("#time").value;
};
function commitTime() {
  const parts = (timeDraft || $("#time").value).split(":").map(Number),
    t = parts.length === 2 ? parts[0] * 60 + parts[1] : parts[0];
  editingTime = false;
  timeDraft = "";
  if (Number.isFinite(t)) {
    video.pause();
    seek(t);
  }
}
$("#time").onblur = commitTime;
$("#time").onkeydown = (e) => {
  if (e.key === "Enter") {
    commitTime();
    $("#time").blur();
  }
};
video.addEventListener("seeked", () => {
  desiredTime = null;
});

$("#undo").onclick = () => historyStep("undo");
$("#redo").onclick = () => historyStep("redo");
$("#split").onclick = split;
$("#remove").onclick = remove;
$("#restore-toggle").onclick = () =>
  $("#restore-panel").hidden ? openRestore() : closeRestore();
$("#close-restore").onclick = closeRestore;
$("#preview-restore").onclick = () =>
  seek(Number($("#restore-in").value), true);
$("#restore").onclick = () => {
  const snap = (t) => {
    const bounds = p.clips
      .filter((c) => c.enabled)
      .flatMap((c) => [c.start, c.end]);
    return bounds.find((b) => Math.abs(b - t) < 0.002) ?? t;
  };
  const start = snap(Number($("#restore-in").value)),
    end = snap(Number($("#restore-out").value));
  if (start < 0 || end > p.media.duration || end - start < 1 / fps()) {
    toast("Select a valid range in the original.");
    return;
  }
  if (
    p.clips.some(
      (c) =>
        c.enabled && Math.min(end, c.end) - Math.max(start, c.start) > 0.002,
    )
  ) {
    toast("That overlaps a kept section. Drag its edge to extend it.");
    return;
  }
  mutate(() => {
    const c = {
      id: uid(),
      label: "Restored",
      start,
      end,
      enabled: true,
      locked: true,
    };
    const i = p.clips.findIndex((c) => c.start > start);
    p.clips.splice(i < 0 ? p.clips.length : i, 0, c);
    selected = c.id;
  }, "Restored original footage");
  closeRestore();
  seek(clips().find((c) => c.id === selected).out);
};
$("#zoom").oninput = renderTimeline;
$("#add-note").onclick = openNotes;
$("#notes-toggle").onclick = () => {
  if ($("#notes-panel").hidden) openNotes();
  else {
    $("#notes-panel").hidden = true;
    renderTimeline();
  }
};
$("#close-notes").onclick = () => {
  $("#notes-panel").hidden = true;
  renderTimeline();
};
$("#note-form").onsubmit = (e) => {
  e.preventDefault();
  const text = $("#note-text").value.trim();
  if (!text) return;
  mutate(
    () =>
      p.notes.push({
        id: uid(),
        time: current(),
        sourceTime: sourceTime(),
        mode,
        text,
        done: false,
      }),
    "Review note",
  );
  $("#note-text").value = "";
};
$("#copy-notes").onclick = async () => {
  try {
    await flush();
    await navigator.clipboard.writeText(
      p.notes
        .filter((n) => !n.done)
        .map(
          (n) =>
            `[${clock(n.time, true)} ${n.mode === "source" ? "original" : "edited"}] ${n.text}`,
        )
        .join("\n"),
    );
    toast("Notes copied. Paste them into your chat.");
  } catch (e) {
    error(e);
  }
};
document.addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  try {
    if (b.dataset.close) $("#" + b.dataset.close).close();
    if (b.dataset.gap) {
      const [a, z] = b.dataset.gap.split(",").map(Number);
      setRestoreRange(a, z);
    }
    if (b.dataset.note) {
      const n = p.notes.find((n) => n.id === b.dataset.note);
      if (n.mode === "source") {
        if (mode !== "source") openRestore();
        seek(n.time);
      } else {
        if (mode === "source") closeRestore();
        seek(n.time);
      }
      $("#notes-panel").hidden = false;
      renderTimeline();
    }
    if (b.dataset.resolve)
      mutate(() => {
        const n = p.notes.find((n) => n.id === b.dataset.resolve);
        n.done = !n.done;
      }, "Updated note");
    if (b.dataset.deleteNote) {
      mutate(() => {p.notes=p.notes.filter(n => n.id!==b.dataset.deleteNote);}, 'Deleted note');
      toast('Note deleted. Undo will bring it back.');
    }
    if (b.dataset.revision) {
      await flush();
      const saved = await api(`/api/projects/${p.id}/restore`, {
        revision: p.revision,
        target: Number(b.dataset.revision),
      });
      await openProject(saved.id);
      $("#history-dialog").close();
    }
  } catch (e) {
    error(e);
  }
});
$("#projects").onchange = async (e) => {
  const pid = e.target.value;
  try {
    await flush();
    await openProject(pid);
  } catch (e) {
    error(e);
  }
};
$("#open").onclick = $("#empty-open").onclick = () => $("#file").click();
$("#file").onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    await flush();
    toast("Opening video…", true);
    const r = await fetch("/api/upload", {
      method: "POST",
      headers: {
        "Content-Type": "application/octet-stream",
        "X-Reel-Token": token,
        "X-Filename": encodeURIComponent(file.name),
      },
      body: file,
    });
    const result = await r.json();
    if (!r.ok) throw Error(result.error);
    await openProject(result.project.id);
  } catch (e) {
    error(e);
  } finally {
    $("#file").value = "";
  }
};
$("#history-toggle").onclick = async () => {
  try {
    await flush();
    const list = await api(`/api/projects/${p.id}/history`);
    $("#history-list").innerHTML = list
      .map(
        (v) =>
          `<div class="history-item"><div>${esc(v.reason)}<small>${new Date(v.updated * 1000).toLocaleTimeString()} · version ${v.revision}</small>${(v.exports || []).map((u) => `<a href="${u}" target="_blank">Exported video</a>`).join("")}</div><button data-revision="${v.revision}" ${v.revision === p.revision ? "disabled" : ""}>${v.revision === p.revision ? "Current" : "Restore"}</button></div>`,
      )
      .join("");
    $("#history-dialog").showModal();
  } catch (e) {
    error(e);
  }
};
function exportInfo() {
  const source=p.rendered?.media||p.media;
  const h=Number($('#resolution').value);
  $('#export-info').textContent=h>source.height?'Larger than your source video; upscaled.':'';
}
$('#export').onclick=async()=>{
  if(exportBusy){toast('Your export is still rendering.');return;}
  video.pause();
  try {
    const prefs=await api('/api/export-preferences');
    $('#export-folder').value=prefs.export_directory||'';
    $('#export-name').value=p.name.replace(/[\\/:*?"<>|]/g,'-')+'.mp4';
    const source=p.rendered?.media||p.media;
    $('#resolution').value=String([1280,1920,2560,3840].filter(h=>h<=source.height).at(-1)||1280);
    exportInfo();$('#export-dialog').showModal();
  } catch(e){error(e);}
};
$('#resolution').onchange=exportInfo;
$('#choose-folder').onclick=async()=>{
  const button=$('#choose-folder');
  button.disabled=true;button.textContent='Choosing…';
  try {
    const result=await api('/api/choose-export-folder',{});
    if(result.directory)$('#export-folder').value=result.directory;
  } catch(e){error(e);}
  finally {button.disabled=false;button.textContent='Choose folder';}
};
$("#export-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    if(!$('#export-folder').value.trim()){toast('Choose a folder first.');return;}
    await flush();
    exportBusy = true;
    $("#export-dialog").close();
    const job = await api(`/api/projects/${p.id}/export`, {
      revision: p.revision,
      settings: {
        height: Number($("#resolution").value),
        fps: Number($("#fps").value),
        quality: $("#quality").value,
        directory: $("#export-folder").value.trim(),
        filename: $("#export-name").value.trim(),
      },
    });
    const result = await poll(job);
    toast(`Saved: ${result.filename}`, false, result.url);
  } catch (e) {
    error(e);
  } finally {
    exportBusy = false;
  }
};
document.addEventListener("keydown", (e) => {
  if (
    ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName) ||
    document.querySelector("dialog[open]")
  )
    return;
  if (e.code === "Space") {
    e.preventDefault();
    $("#play").click();
  }
  if (e.key === "ArrowLeft") {
    e.preventDefault();
    $("#back").click();
  }
  if (e.key === "ArrowRight") {
    e.preventDefault();
    $("#forward").click();
  }
  if (e.key.toLowerCase() === "s" && !e.metaKey && !e.ctrlKey) split();
  if (["Delete", "Backspace"].includes(e.key)) {
    e.preventDefault();
    remove();
  }
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") {
    e.preventDefault();
    historyStep(e.shiftKey ? "redo" : "undo");
  }
  if ((e.metaKey || e.ctrlKey) && e.key === "s") {
    e.preventDefault();
    flush().catch(error);
  }
});
window.addEventListener("resize", () => p && renderTimeline());
window.addEventListener("beforeunload", (e) => {
  if (dirty) {
    e.preventDefault();
    e.returnValue = "";
  }
});
await listProjects();
const requested = new URLSearchParams(location.search).get("project"),
  remembered = localStorage.getItem("reel-review-project");
const start = [requested, remembered, state.projects[0]?.id].find((id) =>
  state.projects.some((x) => x.id === id),
);
if (start) await openProject(start);
else render();
paint();
// Claude can deliver a new version while the review page is open.
setInterval(async () => {
  if (
    !p ||
    dirty ||
    pendingSave ||
    !video.paused ||
    drag ||
    document.querySelector("dialog[open]") ||
    document.activeElement.tagName === "TEXTAREA"
  )
    return;
  try {
    const latest = await api(`/api/projects/${p.id}`);
    if (latest.revision !== p.revision) {
      const time = current();
      await openProject(p.id);
      seek(time);
      toast("Claude’s update is ready.");
    }
  } catch {}
}, 4000);
