// Voice-Tuning v2 — single-page Alpine component.
// Backed by server-rendered bootstrap JSON at #vt-boot.

(function () {
  "use strict";

  const LS_ADV_VALUES = "vt_advanced_values";
  const LS_ADV_OPEN   = "vt_advanced_open";
  const LS_COLLAPSED  = "vt_collapsed_slots";

  function api(path, opts = {}) {
    return fetch(path, {
      headers: { "content-type": "application/json", ...(opts.headers || {}) },
      ...opts,
    }).then(async r => {
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}: ${await r.text()}`);
      return r.json();
    });
  }

  function loadLS(key, fallback) {
    try { const v = localStorage.getItem(key); return v === null ? fallback : JSON.parse(v); }
    catch { return fallback; }
  }
  function saveLS(key, val) { localStorage.setItem(key, JSON.stringify(val)); }

  function escapeHtml(s) {
    return String(s ?? "").replace(/[&<>"']/g, c => (
      { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]
    ));
  }

  const PARAM_LABEL_OVERRIDES = {
    temperature: "T", top_p: "top_p", top_k: "top_k",
    repetition_penalty: "rep_pen", repetition_context_size: "rep_ctx",
    num_generations: "n", trailing_silence: "silence",
  };

  function vtAppFactory() {
    return {
      // ── Bootstrap data ──
      characters: [],
      passages: [],
      engines: [],
      results: [],
      casting: [],
      shortlists: {},
      castingHistory: {},

      // ── UI state ──
      activeSlot: null,
      collapsed: new Set(),
      filterMin: false,
      advancedOpen: false,
      advancedValues: {},
      popover: { open: null },
      palette: { open: false, query: "" },
      nudge: { open: false, slot: null, voice: null, label: null, resultId: null },
      deleteArmed: null,
      deleteArmTimer: null,
      focusedResultId: null,

      // ── Generate state ──
      selectedPassageId: null,
      customText: "",
      customOpen: false,
      selectedVoices: new Set(),
      voiceQuery: "",
      generating: false,
      pendingJobs: [],

      // ── Audio ──
      audioEl: null,
      currentAudioId: null,
      audioPlaying: false,

      // ── Derived cache ──
      _passageToSlot: {},

      init() {
        const boot = JSON.parse(document.getElementById("vt-boot").textContent);
        this.characters = boot.characters || [];
        this.passages = boot.passages || [];
        this.engines = boot.engines || [];
        this.results = boot.results || [];
        this.casting = boot.casting || [];
        this.shortlists = boot.shortlists || {};
        this.castingHistory = boot.casting_history || {};

        this._passageToSlot = Object.fromEntries(
          this.passages.map(p => [p.id, p.character_slot || null])
        );

        this.advancedOpen = loadLS(LS_ADV_OPEN, false);
        this.advancedValues = loadLS(LS_ADV_VALUES, {});
        const collapsedArr = loadLS(LS_COLLAPSED, []);
        this.collapsed = new Set(collapsedArr);

        this.activeSlot = this.characters[0]?.slot || null;

        this.audioEl = document.getElementById("vt-audio");
        this.audioEl.addEventListener("play",  () => { this.audioPlaying = true; });
        this.audioEl.addEventListener("pause", () => { this.audioPlaying = false; });
        this.audioEl.addEventListener("ended", () => {
          this.audioPlaying = false;
          this.currentAudioId = null;
        });
      },

      // ─────────── derived ───────────
      activeCharacter() {
        return this.characters.find(c => c.slot === this.activeSlot) || null;
      },
      castForActive() {
        return this.casting.find(c => c.slot === this.activeSlot)?.result || null;
      },
      castedResultId(slot) {
        return this.casting.find(c => c.slot === slot)?.result?.id || null;
      },
      castedVoice(slot) {
        const r = this.casting.find(c => c.slot === slot)?.result;
        return r ? `${r.voice_id} (${r.engine})` : null;
      },
      resultsForSlot(slot) {
        return this.results.filter(r => this._passageToSlot[r.passage_id] === slot);
      },
      visibleResults(slot) {
        const base = this.resultsForSlot(slot);
        const withPending = [
          ...this.pendingJobs.filter(j => j.slot === slot),
          ...base,
        ];
        if (!this.filterMin) return withPending;
        return withPending.filter(r => (r.stars || 0) >= 4);
      },
      unassignedResults() {
        return this.results.filter(r => !r.passage_id);
      },
      isShortlisted(slot, resultId) {
        return (this.shortlists[slot] || []).some(r => r.id === resultId);
      },
      slotStarSummary(slot) {
        const rs = this.resultsForSlot(slot);
        if (!rs.length) return "";
        const highest = rs.reduce((m, r) => Math.max(m, r.stars || 0), 0);
        if (!highest) return "unrated";
        return "★".repeat(highest);
      },
      activeParamSchemas() {
        const used = new Set();
        for (const key of this.selectedVoices) used.add(key.split("|")[0]);
        return this.engines.filter(e => used.has(e.engine) && (e.param_schema || []).length > 0);
      },
      filteredVoices(grp) {
        const q = this.voiceQuery.trim().toLowerCase();
        if (!q) return grp.voices;
        return grp.voices.filter(v =>
          (v.id || "").toLowerCase().includes(q) ||
          (v.label || "").toLowerCase().includes(q) ||
          (v.gender || "").toLowerCase().includes(q) ||
          (v.accent || "").toLowerCase().includes(q)
        );
      },
      passageLabel() {
        if (this.selectedPassageId) {
          return this.passages.find(p => p.id === this.selectedPassageId)?.title || "—";
        }
        if (this.customText) return "custom text";
        return "— none —";
      },
      voicesLabel() {
        const n = this.selectedVoices.size;
        return n === 0 ? "0 selected" : `${n} selected`;
      },
      paletteMatches() {
        const q = this.palette.query.trim().toLowerCase();
        const chars = this.characters;
        if (!q) return chars;
        return chars.filter(c => c.label.toLowerCase().includes(q) || c.slot.includes(q));
      },
      paramChips(r) {
        const p = r.params || {};
        const parts = [];
        for (const [k, v] of Object.entries(p)) {
          const label = PARAM_LABEL_OVERRIDES[k] || k;
          parts.push(`<span class="vt-param">${escapeHtml(label)}=${escapeHtml(String(v))}</span>`);
        }
        if (r.speed != null && r.speed !== 1.0) {
          parts.push(`<span class="vt-param">${(+r.speed).toFixed(2)}×</span>`);
        }
        return parts.join("");
      },
      portraitSrc(char) {
        if (!char) return "";
        return `/static/img/portraits/${char.portrait_key}.png`;
      },
      fmtTime(ms) {
        if (!ms) return "";
        const d = new Date(ms);
        return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      },

      // ─────────── actions ───────────
      toggleGroup(slot) {
        if (this.collapsed.has(slot)) this.collapsed.delete(slot);
        else this.collapsed.add(slot);
        saveLS(LS_COLLAPSED, Array.from(this.collapsed));
      },
      toggleAdvanced() {
        this.advancedOpen = !this.advancedOpen;
        saveLS(LS_ADV_OPEN, this.advancedOpen);
      },
      setParam(engine, key, val) {
        if (!this.advancedValues[engine]) this.advancedValues[engine] = {};
        this.advancedValues[engine][key] = val === "" ? null : (isNaN(+val) ? val : +val);
        saveLS(LS_ADV_VALUES, this.advancedValues);
      },
      resetEngineParams(engine) {
        delete this.advancedValues[engine];
        saveLS(LS_ADV_VALUES, this.advancedValues);
      },
      toggleVoice(engine, voiceId) {
        const key = `${engine}|${voiceId}`;
        if (this.selectedVoices.has(key)) this.selectedVoices.delete(key);
        else this.selectedVoices.add(key);
      },
      pickPassage(id) {
        this.selectedPassageId = id;
        this.customText = "";
        this.popover.open = null;
      },

      // ─────────── generate ───────────
      async onGenerate() {
        if (this.generating) return;
        const passageId = this.selectedPassageId;
        const customText = this.customText.trim();
        if (!passageId && !customText) { alert("Pick a passage or paste custom text."); return; }
        if (!this.selectedVoices.size) { alert("Pick at least one voice."); return; }

        const jobs = Array.from(this.selectedVoices).map(key => {
          const [engine, voice_id] = key.split("|");
          const grp = this.engines.find(g => g.engine === engine);
          const keys = new Set((grp?.param_schema || []).map(p => p.key));
          const vals = this.advancedValues[engine] || {};
          const params = {};
          for (const k of Object.keys(vals)) {
            if (keys.has(k) && vals[k] !== null && vals[k] !== undefined && vals[k] !== "") {
              params[k] = vals[k];
            }
          }
          return { engine, voice_id, speed: 1.0, params: Object.keys(params).length ? params : null };
        });
        const body = passageId ? { passage_id: passageId, jobs } : { text: customText, jobs };

        // Placeholder cards for visual feedback
        const slot = passageId ? this._passageToSlot[passageId] : null;
        const placeholderIds = jobs.map((j, i) => `__p_${Date.now()}_${i}`);
        this.pendingJobs = [
          ...placeholderIds.map((pid, i) => ({
            id: pid,
            voice_id: jobs[i].voice_id,
            engine: jobs[i].engine,
            stars: 0, notes: "", tags: [], params: jobs[i].params || {}, speed: 1.0,
            passage_id: passageId, slot,
            __pending: true,
          })),
        ];

        this.generating = true;
        try {
          const { batch_id } = await api("/api/generate", {
            method: "POST", body: JSON.stringify(body),
          });
          await this.pollBatch(batch_id);
        } catch (e) {
          alert("Generate failed: " + e.message);
        } finally {
          this.generating = false;
          this.pendingJobs = [];
        }
      },
      async pollBatch(batchId) {
        for (let i = 0; i < 600; i++) {
          await new Promise(r => setTimeout(r, 1000));
          const { jobs } = await api(`/api/batch/${batchId}`);
          const pending = jobs.filter(j => j.status !== "done" && j.status !== "failed").length;
          const done = jobs.filter(j => j.status === "done" && j.result_id);
          // Refresh results whenever something finished.
          if (done.length) await this.refreshResults();
          if (pending === 0) break;
        }
      },
      async refreshResults() {
        const { results } = await api("/api/results?limit=500");
        this.results = results;
      },

      // ─────────── per-card actions ───────────
      playResult(r) {
        if (!r || !r.audio_url) return;
        const el = this.audioEl;
        if (this.currentAudioId === r.id && !el.paused) { el.pause(); return; }
        el.src = r.audio_url;
        this.currentAudioId = r.id;
        el.play().catch(() => {});
      },
      async setStars(r, n) {
        r.stars = (r.stars === n) ? null : n;   // click same star to clear
        await api(`/api/ratings/${r.id}`, {
          method: "PUT",
          body: JSON.stringify({ stars: r.stars, notes: r.notes || null, tags: r.tags || null }),
        });
        // 5★ + empty slot nudge
        if (r.stars === 5) {
          const slot = this._passageToSlot[r.passage_id];
          if (slot && !this.castedResultId(slot)) {
            const char = this.characters.find(c => c.slot === slot);
            this.nudge = {
              open: true,
              slot,
              voice: r.voice_id,
              label: char ? char.label + (char.variant ? " · " + char.variant : "") : slot,
              resultId: r.id,
            };
          }
        }
      },
      async saveNotes(r, val) {
        r.notes = val;
        await api(`/api/ratings/${r.id}`, {
          method: "PUT",
          body: JSON.stringify({ stars: r.stars || null, notes: val || null, tags: r.tags || null }),
        });
      },
      async addTag(r, raw) {
        const tag = raw.replace(/^#/, "").trim().toLowerCase().replace(/\s+/g, "-");
        if (!tag) return;
        const tags = [...(r.tags || [])];
        if (tags.includes(tag)) return;
        tags.push(tag);
        r.tags = tags;
        await api(`/api/ratings/${r.id}`, {
          method: "PUT",
          body: JSON.stringify({ stars: r.stars || null, notes: r.notes || null, tags }),
        });
      },
      async removeTag(r, tag) {
        const tags = (r.tags || []).filter(t => t !== tag);
        r.tags = tags;
        await api(`/api/ratings/${r.id}`, {
          method: "PUT",
          body: JSON.stringify({ stars: r.stars || null, notes: r.notes || null, tags: tags.length ? tags : null }),
        });
      },
      async toggleShortlist(r, slot) {
        const { shortlisted } = await api("/api/shortlist/toggle", {
          method: "POST", body: JSON.stringify({ slot, result_id: r.id }),
        });
        const list = (this.shortlists[slot] || []).slice();
        if (shortlisted) {
          if (!list.some(x => x.id === r.id)) list.unshift({ ...r });
        } else {
          const idx = list.findIndex(x => x.id === r.id);
          if (idx >= 0) list.splice(idx, 1);
        }
        this.shortlists = { ...this.shortlists, [slot]: list };
      },
      async castAs(r, slot) {
        const currentId = this.castedResultId(slot);
        const newId = currentId === r.id ? null : r.id;
        await api(`/api/casting/${slot}`, {
          method: "PUT",
          body: JSON.stringify({ result_id: newId, notes: null }),
        });
        // refresh casting + history for this slot
        const { slots } = await api("/api/casting");
        this.casting = slots;
        const { history } = await api(`/api/casting/history/${slot}?limit=3`);
        this.castingHistory = { ...this.castingHistory, [slot]: history };
      },
      async validateAcrossPassages(r, slot) {
        const slotPassages = this.passages.filter(p => p.character_slot === slot && p.id !== r.passage_id);
        if (!slotPassages.length) { alert("No other passages for this slot."); return; }
        this.generating = true;
        try {
          for (const p of slotPassages) {
            await api("/api/generate", {
              method: "POST",
              body: JSON.stringify({
                passage_id: p.id,
                jobs: [{ engine: r.engine, voice_id: r.voice_id, speed: r.speed || 1.0, params: r.params || null }],
              }),
            });
          }
          // Poll the last batch could get complex — simplest: refresh after a short delay
          await new Promise(res => setTimeout(res, 1500));
          await this.refreshResults();
        } finally {
          this.generating = false;
        }
      },
      confirmDelete(r) {
        if (this.deleteArmed === r.id) {
          this.deleteArmed = null;
          clearTimeout(this.deleteArmTimer);
          this._doDelete(r);
          return;
        }
        this.deleteArmed = r.id;
        clearTimeout(this.deleteArmTimer);
        this.deleteArmTimer = setTimeout(() => { this.deleteArmed = null; }, 3000);
      },
      async _doDelete(r) {
        await api(`/api/results/${r.id}`, { method: "DELETE" });
        this.results = this.results.filter(x => x.id !== r.id);
        // Clean references in shortlists & casting in-memory.
        const updatedShortlists = {};
        for (const [slot, list] of Object.entries(this.shortlists)) {
          updatedShortlists[slot] = list.filter(x => x.id !== r.id);
        }
        this.shortlists = updatedShortlists;
        this.casting = this.casting.map(c =>
          c.result?.id === r.id ? { ...c, result: null } : c
        );
      },
      async acceptNudge() {
        const { slot, resultId } = this.nudge;
        const r = this.results.find(x => x.id === resultId);
        if (r && slot) await this.castAs(r, slot);
        this.nudge.open = false;
      },
      async exportCast() {
        window.location.href = "/api/casting/export";
      },

      jumpTo(slot) {
        this.activeSlot = slot;
        this.collapsed.delete(slot);
        saveLS(LS_COLLAPSED, Array.from(this.collapsed));
        const el = document.getElementById("group-" + slot);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
      },

      paletteSubmit() {
        const m = this.paletteMatches();
        if (m.length) { this.jumpTo(m[0].slot); this.palette.open = false; }
      },

      // ─────────── keyboard ───────────
      onKey(ev) {
        // Don't swallow keystrokes in inputs.
        const tag = (ev.target.tagName || "").toLowerCase();
        const isEditable = ev.target.isContentEditable || tag === "input" || tag === "textarea" || tag === "select";

        // ⌘K / Ctrl-K always opens palette
        if ((ev.metaKey || ev.ctrlKey) && ev.key.toLowerCase() === "k") {
          ev.preventDefault();
          this.palette.open = true;
          this.palette.query = "";
          this.$nextTick(() => this.$refs.paletteInput?.focus());
          return;
        }
        if (isEditable) return;

        // Collapse / expand all
        if (ev.key === "g") {
          if (this._lastG && Date.now() - this._lastG < 600) {
            this.characters.forEach(c => this.collapsed.add(c.slot));
            this.collapsed.add("__unassigned__");
            saveLS(LS_COLLAPSED, Array.from(this.collapsed));
            this._lastG = 0;
          } else {
            this._lastG = Date.now();
          }
          return;
        }
        if (ev.key === "G") {
          this.collapsed.clear();
          saveLS(LS_COLLAPSED, []);
          return;
        }

        // Navigation + stars operate on a "focused" card (first visible in active group by default)
        const focused = this._focusedCard();
        if (ev.key === "j" || ev.key === "ArrowDown") {
          this._moveFocus(1);
          return;
        }
        if (ev.key === "k" || ev.key === "ArrowUp") {
          this._moveFocus(-1);
          return;
        }
        if (focused && /^[1-5]$/.test(ev.key)) {
          this.setStars(focused, +ev.key);
          return;
        }
        if (focused && ev.key === "s") {
          this.toggleShortlist(focused, this.activeSlot);
          return;
        }
      },
      _focusedCard() {
        if (!this.focusedResultId) return null;
        return this.results.find(r => r.id === this.focusedResultId) || null;
      },
      _moveFocus(dir) {
        const list = this.visibleResults(this.activeSlot).filter(r => !r.__pending);
        if (!list.length) return;
        if (!this.focusedResultId) { this.focusedResultId = list[0].id; this._scrollToFocused(); return; }
        const idx = list.findIndex(r => r.id === this.focusedResultId);
        const next = list[Math.max(0, Math.min(list.length - 1, idx + dir))];
        this.focusedResultId = next.id;
        this._scrollToFocused();
      },
      _scrollToFocused() {
        const el = document.querySelector(`.vt-card[data-result-id="${this.focusedResultId}"]`);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      },
    };
  }

  // Register with Alpine before it starts scanning the DOM.
  document.addEventListener("alpine:init", () => {
    window.Alpine.data("vtApp", vtAppFactory);
  });
})();
