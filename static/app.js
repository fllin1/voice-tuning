// Voice-Tuning frontend — Compare/A-B/Casting share one file.

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const State = {
  passages: [],
  selectedPassageId: null,
  customText: "",
  voicesByEngine: [],              // [{engine, available, unavailable_reason, pool, voices, param_schema}]
  selectedVoices: new Set(),       // `${engine}|${voice_id}`
  castingSlots: [],                // [{slot, label, result?, notes?}]
  advancedValues: loadAdvancedValues(),  // {engine: {key: value}}
  advancedOpen: localStorage.getItem("vt_advanced_open") === "1",
  speed: 1.0,
  abPicks: loadAbPicks(),
  cardFilter: "all",               // 'all' | engine name | 'rated' | 'unrated'
  cardSort: "newest",              // 'newest' | 'rated' | 'engine' | 'voice'
};

function loadAbPicks() {
  try { return JSON.parse(localStorage.getItem("vt_ab_picks") || "[]"); }
  catch { return []; }
}
function saveAbPicks() { localStorage.setItem("vt_ab_picks", JSON.stringify(State.abPicks)); }
function loadAdvancedValues() {
  try { return JSON.parse(localStorage.getItem("vt_advanced_values") || "{}"); }
  catch { return {}; }
}
function saveAdvancedValues() {
  localStorage.setItem("vt_advanced_values", JSON.stringify(State.advancedValues));
}

async function api(path, opts = {}) {
  const r = await fetch(path, {
    headers: { "content-type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}: ${await r.text()}`);
  return r.json();
}

// ──────────── Compare page ────────────

async function initCompare() {
  if (!$("#btn-passage")) return;

  const [pData, vData, cData] = await Promise.all([
    api("/api/passages"),
    api("/api/voices"),
    api("/api/casting"),
  ]);
  State.passages = pData.passages;
  State.voicesByEngine = vData.engines;
  State.castingSlots = cData.slots;

  initCmdBar();
  renderAdvancedPanel();
  initFilterChips();
  initSortSelect();
  initAbDock();
  refreshAbDock();
  updateEmptyState();
  hydrateAllResults();
}

async function hydrateAllResults() {
  const grid = $("#results-grid");
  if (!grid) return;
  const existing = new Set(
    $$('.card[data-result-id]', grid).map(c => parseInt(c.dataset.resultId, 10))
  );
  const { results } = await api("/api/results?limit=200");
  for (const r of results) {
    if (existing.has(r.id)) continue;
    addHydratedCard(r);
  }
  updateEmptyState();
  applyFilters();
  sortCards();
}

function initCmdBar() {
  $("#btn-passage").addEventListener("click", e => openPassagePopover(e.currentTarget));
  $("#btn-voices").addEventListener("click", e => openVoicePopover(e.currentTarget));

  const speedInput = $("#speed-input");
  speedInput.addEventListener("change", () => {
    State.speed = parseFloat(speedInput.value) || 1.0;
  });

  const advBtn = $("#btn-advanced");
  const advPanel = $("#advanced-panel");
  advBtn.setAttribute("aria-expanded", State.advancedOpen ? "true" : "false");
  advPanel.hidden = !State.advancedOpen;
  advBtn.addEventListener("click", () => {
    State.advancedOpen = !State.advancedOpen;
    advBtn.setAttribute("aria-expanded", State.advancedOpen ? "true" : "false");
    advPanel.hidden = !State.advancedOpen;
    localStorage.setItem("vt_advanced_open", State.advancedOpen ? "1" : "0");
  });

  $("#generate-btn").addEventListener("click", onGenerate);
}

// ──────────── Passage popover ────────────

function openPassagePopover(anchor) {
  closeAllPopovers();
  const pop = document.createElement("div");
  pop.className = "popover passage-popover";
  pop.innerHTML = `
    <div class="popover-tabs">
      <button class="popover-tab active" data-tab="library" type="button">Library</button>
      <button class="popover-tab" data-tab="custom" type="button">Custom text</button>
    </div>
    <div class="popover-body" data-tab-body></div>
  `;
  document.body.appendChild(pop);
  positionPopover(pop, anchor);
  bindPopoverDismiss(pop, anchor);

  const tabBody = $('[data-tab-body]', pop);

  const renderLibrary = () => {
    const rows = State.passages.map(p => `
      <div class="passage-item ${State.selectedPassageId === p.id ? 'selected' : ''}" data-id="${p.id}">
        <div class="title">${escapeHtml(p.title)}</div>
        <div class="slot">${escapeHtml(p.character_slot || "—")}</div>
      </div>
    `).join("");
    tabBody.innerHTML = `<div class="passage-list">${rows}</div>`;
    $$(".passage-item", tabBody).forEach(el => {
      el.addEventListener("click", () => {
        State.selectedPassageId = parseInt(el.dataset.id, 10);
        State.customText = "";
        refreshPassagePill();
        closePopover(pop);
        hydratePriorResults();
      });
    });
  };
  const renderCustom = () => {
    tabBody.innerHTML = `
      <div class="passage-custom">
        <textarea placeholder="Paste or type any text…">${escapeHtml(State.customText)}</textarea>
      </div>
    `;
    const ta = $("textarea", tabBody);
    ta.addEventListener("input", () => {
      State.customText = ta.value;
      State.selectedPassageId = null;
      refreshPassagePill();
    });
    ta.focus();
  };
  renderLibrary();

  $$('.popover-tab', pop).forEach(btn => {
    btn.addEventListener("click", () => {
      $$('.popover-tab', pop).forEach(b => b.classList.toggle("active", b === btn));
      btn.dataset.tab === "library" ? renderLibrary() : renderCustom();
    });
  });
}

function refreshPassagePill() {
  const pill = $('[data-pill-value]', $("#btn-passage"));
  if (State.selectedPassageId) {
    const p = State.passages.find(x => x.id === State.selectedPassageId);
    pill.textContent = p ? p.title : `Passage #${State.selectedPassageId}`;
  } else if (State.customText) {
    pill.textContent = `Custom (${State.customText.length} chars)`;
  } else {
    pill.textContent = "— none —";
  }
}

// ──────────── Voice popover ────────────

const VOICE_PRESETS = {
  "All female":  v => v.gender === "f",
  "All male":    v => v.gender === "m",
  "UK only":     v => v.accent === "uk",
  "US only":     v => v.accent === "us",
};

function openVoicePopover(anchor) {
  closeAllPopovers();
  const pop = document.createElement("div");
  pop.className = "popover voice-popover";
  pop.innerHTML = `
    <div class="popover-header">
      <input type="search" placeholder="Search voices…">
    </div>
    <div class="chip-row" data-filter-chips></div>
    <div class="chip-row" data-presets>
      <span class="chip-group-label">Quick picks</span>
    </div>
    <div class="popover-body" data-voice-body></div>
    <div class="popover-footer">
      <span class="count" data-count>0 selected</span>
      <div style="display:flex; gap:8px;">
        <button class="ghost" data-clear type="button">Clear</button>
        <button class="primary" data-use type="button">Use these</button>
      </div>
    </div>
  `;
  document.body.appendChild(pop);
  positionPopover(pop, anchor);
  bindPopoverDismiss(pop, anchor);

  const filters = { engine: new Set(), gender: new Set(), accent: new Set() };
  const search = $('input[type=search]', pop);

  const availableEngines = State.voicesByEngine.filter(g => g.available).map(g => g.engine);
  const chipContainer = $('[data-filter-chips]', pop);
  const buildChipGroup = (label, key, options, formatLabel) => {
    const wrap = document.createElement("div");
    wrap.style.cssText = "display:flex; gap:4px; align-items:center;";
    wrap.innerHTML = `<span class="chip-group-label">${label}</span>`;
    options.forEach(v => {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.dataset.k = key;
      chip.dataset.v = v;
      chip.textContent = formatLabel ? formatLabel(v) : v;
      wrap.appendChild(chip);
    });
    chipContainer.appendChild(wrap);
  };
  buildChipGroup("Engine", "engine", availableEngines, capitalise);
  buildChipGroup("Gender", "gender", ["f", "m"], v => v === "f" ? "Female" : "Male");
  buildChipGroup("Accent", "accent", ["us", "uk"], v => v.toUpperCase());

  $$('.chip[data-k]', chipContainer).forEach(chip => {
    chip.addEventListener("click", () => {
      const k = chip.dataset.k, v = chip.dataset.v;
      if (filters[k].has(v)) filters[k].delete(v);
      else filters[k].add(v);
      chip.classList.toggle("on");
      render();
    });
  });

  // Presets
  const presetRow = $('[data-presets]', pop);
  Object.keys(VOICE_PRESETS).forEach(name => {
    const el = document.createElement("span");
    el.className = "chip";
    el.textContent = name;
    el.addEventListener("click", () => applyPreset(name));
    presetRow.appendChild(el);
  });

  const body = $('[data-voice-body]', pop);
  const matches = (voice, engine) => {
    const term = search.value.trim().toLowerCase();
    if (term) {
      const hay = `${voice.label} ${voice.id} ${voice.notes || ""}`.toLowerCase();
      if (!hay.includes(term)) return false;
    }
    if (filters.engine.size && !filters.engine.has(engine)) return false;
    if (filters.gender.size && !filters.gender.has(voice.gender)) return false;
    if (filters.accent.size && !filters.accent.has(voice.accent)) return false;
    return true;
  };

  const render = () => {
    const sections = State.voicesByEngine.map(group => {
      if (!group.available) {
        return `<div class="engine-heading disabled">${capitalise(group.engine)} — disabled (${escapeHtml(group.unavailable_reason || "")})</div>`;
      }
      const visible = group.voices.filter(v => matches(v, group.engine));
      if (!visible.length) return "";
      const cards = visible.map(v => {
        const key = `${group.engine}|${v.id}`;
        const on = State.selectedVoices.has(key);
        return `<div class="voice-pick ${on ? 'on' : ''}" data-key="${key}">
          <input type="checkbox" ${on ? 'checked' : ''} tabindex="-1" aria-hidden="true">
          <div class="label">${escapeHtml(v.label)}</div>
          <div class="voice-id">${escapeHtml(v.id)}</div>
        </div>`;
      }).join("");
      return `<div class="engine-heading">${capitalise(group.engine)}</div><div class="voice-grid">${cards}</div>`;
    }).join("");
    body.innerHTML = sections || `<p class="empty-hint" style="padding:24px;text-align:center">No voices match.</p>`;
    $$('.voice-pick[data-key]', body).forEach(el => {
      el.addEventListener("click", () => {
        const key = el.dataset.key;
        if (State.selectedVoices.has(key)) State.selectedVoices.delete(key);
        else State.selectedVoices.add(key);
        el.classList.toggle("on");
        const cb = $('input[type=checkbox]', el);
        if (cb) cb.checked = State.selectedVoices.has(key);
        updateCount();
        renderAdvancedPanel();
        refreshVoicesPill();
      });
    });
    updateCount();
  };

  const updateCount = () => {
    $('[data-count]', pop).textContent = `${State.selectedVoices.size} selected`;
  };

  const applyPreset = (name) => {
    const fn = VOICE_PRESETS[name];
    for (const g of State.voicesByEngine) {
      if (!g.available) continue;
      for (const v of g.voices) {
        const key = `${g.engine}|${v.id}`;
        if (fn(v)) State.selectedVoices.add(key);
      }
    }
    render();
    refreshVoicesPill();
    renderAdvancedPanel();
  };

  search.addEventListener("input", render);
  $('[data-clear]', pop).addEventListener("click", () => {
    State.selectedVoices.clear();
    render();
    refreshVoicesPill();
    renderAdvancedPanel();
  });
  $('[data-use]', pop).addEventListener("click", () => closePopover(pop));

  render();
  setTimeout(() => search.focus(), 0);
}

function refreshVoicesPill() {
  const pill = $('[data-pill-value]', $("#btn-voices"));
  pill.textContent = `${State.selectedVoices.size} selected`;
}

// ──────────── Advanced panel ────────────

function renderAdvancedPanel() {
  const panel = $("#advanced-panel");
  if (!panel) return;
  const selectedEngines = new Set(
    Array.from(State.selectedVoices).map(k => k.split("|")[0])
  );
  const groups = State.voicesByEngine
    .filter(g => g.available)
    .filter(g => selectedEngines.has(g.engine));

  if (!groups.length) {
    panel.innerHTML = `<p class="advanced-note">Pick at least one voice to see engine-specific params.</p>`;
    return;
  }

  panel.innerHTML = groups.map(group => {
    const schema = group.param_schema || [];
    if (!schema.length) {
      return `<div class="advanced-group">
        <h3>${capitalise(group.engine)}</h3>
        <p class="advanced-note">No sampler params — speed only.</p>
      </div>`;
    }
    const rows = schema.map(p => renderParamRow(group.engine, p)).join("");
    return `<div class="advanced-group">
      <h3>${capitalise(group.engine)}</h3>
      ${rows}
    </div>`;
  }).join("");

  $$('.advanced-row[data-key]', panel).forEach(row => {
    const engine = row.dataset.engine;
    const key = row.dataset.key;
    const type = row.dataset.type;
    const defaultV = row.dataset.default;
    const rangeInput = $('input[type=range]', row);
    const numInput = $('input[type=number]', row);
    const textInput = $('input[type=text], textarea', row);
    const resetBtn = $('.reset', row);

    const sync = (val) => {
      State.advancedValues[engine] ??= {};
      State.advancedValues[engine][key] = coerceParam(type, val);
      saveAdvancedValues();
    };
    if (rangeInput && numInput) {
      const update = (src) => {
        (src === rangeInput ? numInput : rangeInput).value = src.value;
        sync(src.value);
      };
      rangeInput.addEventListener("input", () => update(rangeInput));
      numInput.addEventListener("input", () => update(numInput));
    } else if (textInput) {
      textInput.addEventListener("input", () => sync(textInput.value));
    }
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        const resetTo = type === "string" ? "" : defaultV;
        if (rangeInput && numInput) { rangeInput.value = defaultV; numInput.value = defaultV; }
        if (textInput) textInput.value = resetTo;
        sync(resetTo);
      });
    }
  });
}

function renderParamRow(engine, p) {
  const stored = State.advancedValues[engine]?.[p.key];
  const val = stored !== undefined ? stored : p.default;
  const attrs = `data-engine="${engine}" data-key="${p.key}" data-type="${p.type}" data-default="${p.default}"`;
  if (p.type === "string") {
    return `<div class="advanced-row" ${attrs}>
      <label>${escapeHtml(p.label)}</label>
      <input type="text" value="${escapeHtml(val || "")}" placeholder="${escapeHtml(p.placeholder || "")}">
      <span></span>
      <button class="reset" title="Reset" type="button">↺</button>
    </div>`;
  }
  return `<div class="advanced-row" ${attrs}>
    <label>${escapeHtml(p.label)}</label>
    <input type="range" min="${p.min}" max="${p.max}" step="${p.step}" value="${val}">
    <input type="number" min="${p.min}" max="${p.max}" step="${p.step}" value="${val}">
    <button class="reset" title="Reset to ${p.default}" type="button">↺</button>
  </div>`;
}

function coerceParam(type, val) {
  if (type === "int") return parseInt(val, 10);
  if (type === "float") return parseFloat(val);
  return String(val);
}

// ──────────── Popover utilities ────────────

function positionPopover(pop, anchor) {
  const rect = anchor.getBoundingClientRect();
  const popW = pop.offsetWidth;
  let left = rect.left;
  const maxLeft = window.innerWidth - popW - 8;
  if (left > maxLeft) left = Math.max(8, maxLeft);
  if (left < 8) left = 8;
  pop.style.left = `${left}px`;
  pop.style.top = `${rect.bottom + 6 + window.scrollY}px`;
}

function closeAllPopovers() { $$('.popover').forEach(p => p.remove()); }
function closePopover(pop) {
  pop.remove();
  if (pop._escHandler) document.removeEventListener("keydown", pop._escHandler);
  if (pop._outsideHandler) document.removeEventListener("click", pop._outsideHandler, true);
}
function bindPopoverDismiss(pop, anchor) {
  pop._escHandler = (e) => { if (e.key === "Escape") closePopover(pop); };
  pop._outsideHandler = (e) => {
    if (pop.contains(e.target) || anchor.contains(e.target)) return;
    closePopover(pop);
  };
  document.addEventListener("keydown", pop._escHandler);
  setTimeout(() => document.addEventListener("click", pop._outsideHandler, true), 0);
}

// ──────────── Generate flow ────────────

async function onGenerate() {
  const customText = State.customText.trim();
  const passageId = customText ? null : State.selectedPassageId;
  if (!passageId && !customText) {
    alert("Pick a passage or paste custom text first.");
    return;
  }
  if (!State.selectedVoices.size) {
    alert("Pick at least one voice.");
    return;
  }
  const jobs = Array.from(State.selectedVoices).map(key => {
    const [engine, voice_id] = key.split("|");
    const engineGroup = State.voicesByEngine.find(g => g.engine === engine);
    const schemaKeys = new Set((engineGroup?.param_schema || []).map(p => p.key));
    const engineVals = State.advancedValues[engine] || {};
    const params = {};
    for (const k of Object.keys(engineVals)) {
      if (schemaKeys.has(k)) {
        const v = engineVals[k];
        if (v !== "" && v !== null && v !== undefined) params[k] = v;
      }
    }
    return {
      engine, voice_id,
      speed: State.speed,
      params: Object.keys(params).length ? params : null,
    };
  });
  const body = passageId ? { passage_id: passageId, jobs } : { text: customText, jobs };

  const btn = $("#generate-btn");
  btn.disabled = true;
  try {
    const { batch_id, job_ids } = await api("/api/generate", {
      method: "POST", body: JSON.stringify(body),
    });
    job_ids.forEach((jid, i) => addPlaceholderCard(jid, jobs[i]));
    updateEmptyState();
    pollBatch(batch_id);
  } catch (e) {
    alert("Generate failed: " + e.message);
  } finally {
    btn.disabled = false;
  }
}

function updateEmptyState() {
  const grid = $("#results-grid");
  const empty = $("#empty-state");
  const toolbar = $("#results-toolbar");
  if (!grid || !empty) return;
  const hasCards = grid.children.length > 0;
  empty.hidden = hasCards;
  if (toolbar) toolbar.hidden = !hasCards;
}

async function hydratePriorResults() {
  if (!State.selectedPassageId) return;
  const grid = $("#results-grid");
  if (!grid) return;
  const existing = new Set(
    $$('.card[data-result-id]', grid).map(c => parseInt(c.dataset.resultId, 10))
  );
  const { results } = await api(`/api/passages/${State.selectedPassageId}/results`);
  for (const r of results) {
    if (existing.has(r.id)) continue;
    addHydratedCard(r);
  }
  updateEmptyState();
  applyFilters();
  sortCards();
}

function addHydratedCard(r) {
  const grid = $("#results-grid");
  const card = document.createElement("div");
  card.className = "card";
  card.id = `result-${r.id}`;
  card.dataset.engine = r.engine;
  card.dataset.voiceId = r.voice_id;
  card.dataset.created = String(r.generated_at || Date.now());
  card.dataset.stars = String(r.stars || 0);
  card.innerHTML = `
    <div class="card-header">
      <div class="card-title">
        <strong>${escapeHtml(r.voice_id)}</strong>
        <span class="voice-id">${escapeHtml(r.engine)}</span>
      </div>
      <div class="badges">
        <span class="badge done" data-status>done</span>
      </div>
    </div>
    <div data-body></div>
  `;
  grid.appendChild(card);
  fillCard(
    card,
    { result_id: r.id, audio_url: r.audio_url, engine: r.engine, voice_id: r.voice_id },
    { initialStars: r.stars || 0, initialNotes: r.notes || "" },
  );
}

function addPlaceholderCard(jobId, jobSpec) {
  const grid = $("#results-grid");
  const card = document.createElement("div");
  card.className = "card";
  card.id = `job-${jobId}`;
  card.dataset.engine = jobSpec.engine;
  card.dataset.voiceId = jobSpec.voice_id;
  card.dataset.created = String(Date.now());
  card.dataset.stars = "0";
  card.innerHTML = `
    <div class="card-header">
      <div class="card-title">
        <strong>${escapeHtml(jobSpec.voice_id)}</strong>
        <span class="voice-id">${escapeHtml(jobSpec.engine)}</span>
      </div>
      <div class="badges">
        <span class="badge queued" data-status>queued</span>
      </div>
    </div>
    <div data-body><span class="empty-hint">Waiting for slot…</span></div>
  `;
  grid.prepend(card);
  applyFilters();
}

async function pollBatch(batchId) {
  for (let i = 0; i < 600; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const { jobs } = await api(`/api/batch/${batchId}`);
    let pending = 0;
    for (const j of jobs) {
      const card = $(`#job-${j.id}`);
      if (!card) continue;
      const badge = $('[data-status]', card);
      badge.textContent = j.status;
      badge.className = `badge ${j.status}`;
      if (j.status === "done") {
        if (!card.classList.contains("filled")) fillCard(card, j);
      } else if (j.status === "failed") {
        $('[data-body]', card).innerHTML = `<span class="empty-hint">${escapeHtml(j.error || "failed")}</span>`;
      } else {
        pending++;
      }
    }
    if (pending === 0) break;
  }
}

function fillCard(card, job, options = {}) {
  card.classList.add("filled");
  card.dataset.resultId = String(job.result_id);
  const body = $('[data-body]', card);
  const slotOptions = State.castingSlots.map(s =>
    `<option value="${s.slot}">${escapeHtml(s.label)}</option>`
  ).join("");
  body.innerHTML = `
    <audio controls preload="none" src="${job.audio_url}"></audio>
    <div class="speed-row">
      <span>Speed</span>
      <input type="range" min="0.7" max="1.3" step="0.05" value="1.0" data-speed>
      <span data-speed-label>1.00×</span>
      <button class="ghost" data-regen type="button" title="Regenerate at this speed">↻</button>
    </div>
    <div class="stars" data-stars>${"☆".repeat(5)}</div>
    <textarea class="notes" placeholder="Notes…"></textarea>
    <div class="card-actions">
      <select class="assign-select" data-assign>
        <option value="">— assign to slot —</option>
        ${slotOptions}
      </select>
      <button class="ab-stage-btn" data-ab type="button">+ A/B</button>
      <button class="delete-btn" data-delete type="button" title="Delete">✕</button>
    </div>
  `;
  initStars(card, body, job.result_id, options.initialStars || 0);
  initNotes(body, job.result_id, options.initialNotes || "");
  initAbStageBtn(body, job, card);
  initSpeedRegen(card, body, job);
  initAssignSelect(body, job.result_id);
  initDeleteBtn(card, body, job.result_id);
}

function initDeleteBtn(card, scope, resultId) {
  const btn = $('[data-delete]', scope);
  if (!btn) return;
  let armTimer = null;
  const disarm = () => {
    btn.classList.remove("armed");
    btn.textContent = "✕";
    btn.title = "Delete";
    if (armTimer) { clearTimeout(armTimer); armTimer = null; }
  };
  btn.addEventListener("click", async (e) => {
    e.stopPropagation();
    if (!btn.classList.contains("armed")) {
      btn.classList.add("armed");
      btn.textContent = "Delete?";
      btn.title = "Click again to confirm";
      armTimer = setTimeout(disarm, 3000);
      return;
    }
    btn.disabled = true;
    await api(`/api/results/${resultId}`, { method: "DELETE" });
    // Drop from A/B staging if present
    if (State.abPicks.includes(resultId)) {
      State.abPicks = State.abPicks.filter(x => x !== resultId);
      saveAbPicks();
      refreshAbDock();
    }
    card.remove();
    updateEmptyState();
  });
  // Click anywhere else on the page disarms the button.
  document.addEventListener("click", (e) => {
    if (btn.classList.contains("armed") && e.target !== btn) disarm();
  }, true);
}

function initStars(card, scope, resultId, initial = 0) {
  const root = $('[data-stars]', scope);
  let current = initial;
  card.dataset.stars = String(current);
  const draw = () => {
    root.innerHTML = Array.from({length: 5}, (_, i) =>
      `<span class="star${i < current ? ' on' : ''}" data-i="${i+1}">★</span>`
    ).join("");
  };
  draw();
  root.addEventListener("click", async (e) => {
    const t = e.target.closest('.star');
    if (!t) return;
    current = parseInt(t.dataset.i, 10);
    draw();
    card.dataset.stars = String(current);
    applyFilters();
    sortCards();
    await api(`/api/ratings/${resultId}`, {
      method: "PUT",
      body: JSON.stringify({ stars: current, notes: scope.querySelector('.notes').value || null }),
    });
  });
}

function initNotes(scope, resultId, initial = "") {
  const ta = $('.notes', scope);
  if (initial) ta.value = initial;
  let timer = null;
  ta.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const stars = scope.querySelectorAll('.star.on').length || null;
      await api(`/api/ratings/${resultId}`, {
        method: "PUT",
        body: JSON.stringify({ stars, notes: ta.value || null }),
      });
    }, 500);
  });
}

function initAbStageBtn(scope, job, card) {
  const btn = $('[data-ab]', scope);
  const sync = () => {
    const on = State.abPicks.includes(job.result_id);
    btn.classList.toggle("on", on);
    btn.textContent = on ? "✓ Staged" : "+ A/B";
    card.classList.toggle("staged", on);
  };
  sync();
  btn.addEventListener("click", () => {
    State.abPicks = State.abPicks.filter(x => x !== job.result_id);
    if (!btn.classList.contains("on")) State.abPicks.push(job.result_id);
    if (State.abPicks.length > 2) State.abPicks = State.abPicks.slice(-2);
    saveAbPicks();
    // Re-sync staged class on every card (some may have been bumped)
    $$('.card.filled').forEach(c => {
      const id = parseInt(c.dataset.resultId || "0", 10);
      const isStaged = State.abPicks.includes(id);
      c.classList.toggle("staged", isStaged);
      const b = $('[data-ab]', c);
      if (b) {
        b.classList.toggle("on", isStaged);
        b.textContent = isStaged ? "✓ Staged" : "+ A/B";
      }
    });
    refreshAbDock();
  });
}

function initAssignSelect(scope, resultId) {
  const sel = $('[data-assign]', scope);
  // Pre-select if this result is already assigned to a slot
  const assigned = State.castingSlots.find(s => s.result?.id === resultId);
  if (assigned) sel.value = assigned.slot;
  sel.addEventListener("change", async () => {
    const slot = sel.value;
    if (!slot) return;
    await api(`/api/casting/${slot}`, {
      method: "PUT",
      body: JSON.stringify({ result_id: resultId, notes: null }),
    });
    // Update local state so other cards know
    const target = State.castingSlots.find(s => s.slot === slot);
    if (target) target.result = { id: resultId };
    sel.blur();
  });
}

function initSpeedRegen(card, body, job) {
  const slider = $('[data-speed]', body);
  const label = $('[data-speed-label]', body);
  const btn = $('[data-regen]', body);
  slider.addEventListener("input", () => {
    label.textContent = `${parseFloat(slider.value).toFixed(2)}×`;
  });
  btn.addEventListener("click", async () => {
    const speed = parseFloat(slider.value);
    const r = await api(`/api/results/${job.result_id}`);
    btn.disabled = true;
    try {
      const passageId = r.passage_id;
      const customText = passageId ? null : await fetchTextForResult(r);
      const body = passageId
        ? { passage_id: passageId, jobs: [{ engine: r.engine, voice_id: r.voice_id, speed, params: r.params }] }
        : { text: customText, jobs: [{ engine: r.engine, voice_id: r.voice_id, speed, params: r.params }] };
      const { batch_id, job_ids } = await api("/api/generate", {
        method: "POST", body: JSON.stringify(body),
      });
      addPlaceholderCard(job_ids[0], { engine: r.engine, voice_id: r.voice_id });
      updateEmptyState();
      pollBatch(batch_id);
    } finally {
      btn.disabled = false;
    }
  });
}

async function fetchTextForResult(r) {
  if (!r.passage_id) return prompt("Re-enter the custom text:");
  const p = await api(`/api/passages/${r.passage_id}`);
  return p.text;
}

// ──────────── Filter + sort chips ────────────

function initFilterChips() {
  const root = $("#filter-chips");
  if (!root) return;
  const engines = State.voicesByEngine.filter(g => g.available).map(g => g.engine);
  const opts = [
    { v: "all", label: "All" },
    ...engines.map(e => ({ v: e, label: capitalise(e) })),
    { v: "rated", label: "≥ 4★" },
    { v: "unrated", label: "Unrated" },
  ];
  root.innerHTML = opts.map(o =>
    `<span class="chip ${o.v === State.cardFilter ? 'on' : ''}" data-f="${o.v}">${escapeHtml(o.label)}</span>`
  ).join("");
  $$('[data-f]', root).forEach(chip => {
    chip.addEventListener("click", () => {
      State.cardFilter = chip.dataset.f;
      $$('[data-f]', root).forEach(c => c.classList.toggle("on", c.dataset.f === State.cardFilter));
      applyFilters();
    });
  });
}

function applyFilters() {
  const f = State.cardFilter;
  $$('#results-grid .card').forEach(card => {
    let show = true;
    if (f === "rated") show = parseInt(card.dataset.stars || "0", 10) >= 4;
    else if (f === "unrated") show = parseInt(card.dataset.stars || "0", 10) === 0;
    else if (f !== "all") show = card.dataset.engine === f;
    card.classList.toggle("hidden-by-filter", !show);
  });
}

function initSortSelect() {
  const sel = $("#sort-select");
  if (!sel) return;
  sel.value = State.cardSort;
  sel.addEventListener("change", () => {
    State.cardSort = sel.value;
    sortCards();
  });
}

function sortCards() {
  const grid = $("#results-grid");
  if (!grid) return;
  const cards = $$('.card', grid);
  const keyFn = {
    newest: c => -parseInt(c.dataset.created || "0", 10),
    rated: c => -parseInt(c.dataset.stars || "0", 10),
    engine: c => `${c.dataset.engine}|${c.dataset.voiceId}`,
    voice: c => c.dataset.voiceId || "",
  }[State.cardSort] || (c => 0);
  cards.sort((a, b) => {
    const ka = keyFn(a), kb = keyFn(b);
    if (ka < kb) return -1;
    if (ka > kb) return 1;
    return 0;
  });
  cards.forEach(c => grid.appendChild(c));
}

// ──────────── A/B dock + drawer ────────────

function initAbDock() {
  // Dock content rendered on each refresh.
}

function refreshAbDock() {
  const dock = $("#ab-dock");
  if (!dock) return;
  const n = State.abPicks.length;
  if (n === 0) {
    dock.hidden = true;
    return;
  }
  dock.hidden = false;
  dock.innerHTML = `
    <span class="dock-count">${n}/2 staged for A/B</span>
    <button class="dock-action" type="button" ${n === 2 ? "" : "disabled"}>Open A/B</button>
    <button class="dock-clear" type="button">Clear</button>
  `;
  $('.dock-action', dock).addEventListener("click", openAbDrawer);
  $('.dock-clear', dock).addEventListener("click", () => {
    State.abPicks = [];
    saveAbPicks();
    $$('.card.filled').forEach(c => {
      c.classList.remove("staged");
      const b = $('[data-ab]', c);
      if (b) { b.classList.remove("on"); b.textContent = "+ A/B"; }
    });
    refreshAbDock();
  });
}

async function openAbDrawer() {
  if (State.abPicks.length !== 2) return;
  const drawer = $("#ab-drawer");
  const scrim = $("#drawer-scrim");
  if (!drawer || !scrim) return;
  drawer.innerHTML = `<div class="empty-hint" style="padding:24px">Loading…</div>`;
  drawer.hidden = false;
  scrim.hidden = false;
  scrim.addEventListener("click", closeAbDrawer, { once: true });

  const [a, b] = await Promise.all(State.abPicks.map(id => api(`/api/results/${id}`)));
  const order = Math.random() < 0.5 ? [a, b] : [b, a];
  const m = await api("/api/ab/start", {
    method: "POST",
    body: JSON.stringify({ result_a_id: order[0].id, result_b_id: order[1].id }),
  });

  drawer.innerHTML = `
    <header>
      <h2>A/B blind</h2>
      <button class="close" type="button" aria-label="Close">×</button>
    </header>
    <div class="drawer-body">
      <div class="ab-card">
        <h3>Sample A</h3>
        <audio controls src="${order[0].audio_url}"></audio>
      </div>
      <div class="ab-card">
        <h3>Sample B</h3>
        <audio controls src="${order[1].audio_url}"></audio>
      </div>
      <div class="drawer-actions">
        <button class="primary" data-pick="a" type="button">Prefer A</button>
        <button class="primary" data-pick="tie" type="button">Tie</button>
        <button class="primary" data-pick="b" type="button">Prefer B</button>
      </div>
      <div class="reveal" hidden></div>
    </div>
  `;
  $('.close', drawer).addEventListener("click", closeAbDrawer);
  $$('[data-pick]', drawer).forEach(btn => {
    btn.addEventListener("click", async () => {
      const winner = btn.dataset.pick;
      await api("/api/ab/decide", {
        method: "POST", body: JSON.stringify({ match_id: m.match_id, winner }),
      });
      const winnerLabel =
        winner === "tie" ? "Tie" :
        winner === "a"   ? `A → ${order[0].engine} / ${order[0].voice_id}`
                         : `B → ${order[1].engine} / ${order[1].voice_id}`;
      const reveal = $('.reveal', drawer);
      reveal.hidden = false;
      reveal.innerHTML = `
        <p><strong>A:</strong> ${escapeHtml(order[0].engine)} / ${escapeHtml(order[0].voice_id)}</p>
        <p><strong>B:</strong> ${escapeHtml(order[1].engine)} / ${escapeHtml(order[1].voice_id)}</p>
        <p>You picked: <strong>${escapeHtml(winnerLabel)}</strong></p>
      `;
    });
  });
}

function closeAbDrawer() {
  const drawer = $("#ab-drawer");
  const scrim = $("#drawer-scrim");
  if (drawer) drawer.hidden = true;
  if (scrim) scrim.hidden = true;
}

// ──────────── A/B page (deep-link fallback) ────────────

async function initAb() {
  const root = $("#ab-stage");
  if (!root) return;
  if (State.abPicks.length !== 2) {
    root.innerHTML = `<p>You need exactly two cards added to A/B (currently ${State.abPicks.length}).</p>`;
    return;
  }
  const [a, b] = await Promise.all(State.abPicks.map(id => api(`/api/results/${id}`)));
  const order = Math.random() < 0.5 ? [a, b] : [b, a];

  const m = await api("/api/ab/start", {
    method: "POST",
    body: JSON.stringify({ result_a_id: order[0].id, result_b_id: order[1].id }),
  });

  root.innerHTML = `
    <div class="ab-stage">
      <div class="ab-card">
        <h3>Sample A</h3>
        <audio controls src="${order[0].audio_url}"></audio>
      </div>
      <div class="ab-card">
        <h3>Sample B</h3>
        <audio controls src="${order[1].audio_url}"></audio>
      </div>
    </div>
    <div class="row" style="margin-top:1rem">
      <button class="primary" data-pick="a">Prefer A</button>
      <button class="primary" data-pick="tie">Tie</button>
      <button class="primary" data-pick="b">Prefer B</button>
    </div>
    <div id="ab-reveal" style="margin-top:1rem"></div>
  `;
  $$('[data-pick]', root).forEach(btn => {
    btn.addEventListener("click", async () => {
      const winner = btn.dataset.pick;
      await api("/api/ab/decide", {
        method: "POST", body: JSON.stringify({ match_id: m.match_id, winner }),
      });
      const winnerLabel =
        winner === "tie" ? "Tie" :
        winner === "a"   ? `A → ${order[0].engine} / ${order[0].voice_id}`
                         : `B → ${order[1].engine} / ${order[1].voice_id}`;
      $("#ab-reveal").innerHTML = `
        <p><strong>A: ${order[0].engine} / ${order[0].voice_id}</strong></p>
        <p><strong>B: ${order[1].engine} / ${order[1].voice_id}</strong></p>
        <p>You picked: <strong>${winnerLabel}</strong></p>
      `;
    });
  });
}

// ──────────── Casting page ────────────

async function initCasting() {
  const root = $("#casting-grid");
  if (!root) return;
  const { slots } = await api("/api/casting");
  root.innerHTML = "";
  for (const slot of slots) {
    const card = document.createElement("div");
    card.className = "card";
    const { results: allResults } = await api(`/api/casting/results/${encodeURIComponent(slot.slot)}`);
    card.innerHTML = `
      <div><strong>${escapeHtml(slot.label)}</strong></div>
      <div class="empty-hint">${escapeHtml(slot.slot)}</div>
      ${slot.result ? `
        <div class="empty-hint">Current: ${escapeHtml(slot.result.engine)} / ${escapeHtml(slot.result.voice_id)} @ ${slot.result.speed}×</div>
        <audio controls src="${slot.result.audio_url}"></audio>
      ` : `<div class="empty-hint">No voice assigned.</div>`}
      <select data-pick>
        <option value="">— pick a result —</option>
        ${allResults.map(r => `
          <option value="${r.id}" ${slot.result && slot.result.id === r.id ? "selected" : ""}>
            ${escapeHtml(r.engine)} / ${escapeHtml(r.voice_id)} @ ${r.speed}× ${r.stars ? `(${r.stars}★)` : ""}
          </option>
        `).join("")}
      </select>
      <textarea class="notes" placeholder="Casting notes…">${escapeHtml(slot.notes || "")}</textarea>
      <button class="primary" data-save type="button">Save</button>
    `;
    const sel = $('[data-pick]', card);
    const notes = $('.notes', card);
    $('[data-save]', card).addEventListener("click", async () => {
      await api(`/api/casting/${slot.slot}`, {
        method: "PUT",
        body: JSON.stringify({ result_id: sel.value ? parseInt(sel.value, 10) : null, notes: notes.value || null }),
      });
      location.reload();
    });
    root.appendChild(card);
  }
}

// ──────────── helpers ────────────

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
function capitalise(s) { return s ? s[0].toUpperCase() + s.slice(1) : s; }

window.addEventListener("DOMContentLoaded", () => {
  initCompare();
  initAb();
  initCasting();
});
