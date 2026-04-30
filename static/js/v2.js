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
      voiceNotes: {},   // { slot: { "engine|voice_id|params_fp": { notes, stars } } }

      // ── UI state ──
      activeSlot: null,
      collapsed: new Set(),
      filterMin: false,
      filterMarked: false,
      advancedOpen: false,
      advancedValues: {},
      popover: { open: null },
      palette: { open: false, query: "" },
      deleteArmed: null,       // group key currently armed for delete
      deleteArmTimer: null,
      focusedGroupKey: null,   // voice-level keyboard focus (data-group-key)
      focusedSampleId: null,   // dialogue-row focus within the focused voice
      helpOpen: false,         // ?-overlay
      lastPlayedSampleId: null, // page-wide marker for the most-recently played dialogue
      otherDialoguesOpen: null, // group key whose "+ dialogues" panel is open
      selectedMissing: new Set(), // passage ids checked in the open panel
      cardSpeeds: {},          // { groupKey: 1.0 }
      regenerating: null,      // groupKey currently regenerating
      savedFlags: {},          // { groupKey: timestamp } — drives transient "saved ✓"
      saveError: null,         // { msg, at } — drives global save-error toast
      pendingDelete: null,     // { slot, g, samples, timer, expiresAt } — 10s undo window

      // ── Generate state ──
      selectedPassageId: null,
      customText: "",
      customOpen: false,
      selectedVoices: new Set(),
      voiceQuery: "",
      generating: false,
      pendingJobs: [],

      // ── Wizard state (3-step Generate flow) ──
      wizard: {
        open: false,
        step: 1,
        filterSlot: null,                 // null = "All"
        selectedPassageIds: new Set(),
        customText: "",
        customTextSlot: null,
        submitting: false,
        // Step 2
        selectedVoicesBySlot: {},          // { slot: { "engine|voice_id": true } }
        voiceQuery: "",
        tryingOut: null,                   // key of sample being tried out
        descDrafts: {},                    // local in-progress description drafts
        filterEngines: {},                 // { engineName: true }  (empty = all)
        filterGenders: {},                 // { 'm'|'f'|'n': true }
        filterAccents: {},                 // { accent: true }
        filterTraits: {},                  // { trait: true }
        // Step 3
        perVoiceParams: {},                // { "slot|engine|voice_id": { key: value } }
        previews: {},                      // { "slot|engine|voice_id": result object }
        previewing: null,                  // key of preview in flight
        expandedParams: {},                // { "slot|engine|voice_id": true }
        // Progress / errors
        progress: null,                    // { current, total, label } during submit
        lastErrors: [],
      },

      // ── Voice profiles / presets (bootstrap-seeded) ──
      voiceProfiles: {},
      presetVoices: {},
      tryoutText: "",

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
        this.voiceNotes = boot.voice_notes || {};
        this.voiceProfiles = boot.voice_profiles || {};
        this.presetVoices = boot.preset_voices || {};
        this.tryoutText = boot.tryout_text || "";

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

        // If a deferred delete is still pending when the tab closes, fire the
        // DELETEs as keepalive so the server eventually catches up.
        window.addEventListener("beforeunload", () => {
          const pd = this.pendingDelete;
          if (!pd) return;
          for (const s of pd.samples) {
            fetch(`/api/results/${s.id}`, { method: "DELETE", keepalive: true });
          }
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
      unassignedResults() {
        return this.results.filter(r => !r.passage_id);
      },
      paramsFp(paramsOrResult) {
        const p = (paramsOrResult && paramsOrResult.params !== undefined)
          ? (paramsOrResult.params || {})
          : (paramsOrResult || {});
        const keys = Object.keys(p).sort();
        if (!keys.length) return "";
        const sorted = {};
        for (const k of keys) sorted[k] = p[k];
        return JSON.stringify(sorted);
      },
      groupKey(engine, voice_id, params_fp) {
        return `${engine}|${voice_id}|${params_fp}`;
      },
      groupedResults(slot) {
        const samples = this.resultsForSlot(slot);
        const groups = new Map();
        for (const r of samples) {
          const fp = this.paramsFp(r);
          const key = this.groupKey(r.engine, r.voice_id, fp);
          if (!groups.has(key)) {
            groups.set(key, {
              key, engine: r.engine, voice_id: r.voice_id,
              params: r.params || {}, params_fp: fp,
              samples: [],
            });
          }
          groups.get(key).samples.push(r);
        }
        const slotNotes = this.voiceNotes[slot] || {};
        let out = Array.from(groups.values()).map(g => {
          const meta = slotNotes[g.key] || {};
          g.notes = meta.notes || "";
          g.stars = meta.stars || 0;
          g.marked = !!meta.marked;
          // Most-recent sample first; drives cast / regenerate template.
          g.samples.sort((a, b) => b.id - a.id);
          return g;
        });
        // Unrated first, then stars desc, then most-recent sample desc.
        out.sort((a, b) => {
          const aa = a.stars || 0, bb = b.stars || 0;
          if (aa === 0 && bb !== 0) return -1;
          if (bb === 0 && aa !== 0) return 1;
          if (aa !== bb) return bb - aa;
          return (b.samples[0]?.id || 0) - (a.samples[0]?.id || 0);
        });
        if (this.filterMin) out = out.filter(g => (g.stars || 0) >= 4);
        if (this.filterMarked) out = out.filter(g => g.marked);
        if (this.pendingDelete && this.pendingDelete.slot === slot) {
          const hideKey = this.pendingDelete.g.key;
          out = out.filter(g => g.key !== hideKey);
        }
        return out;
      },
      slotStarSummary(slot) {
        const groups = this.groupedResults(slot);
        if (!groups.length) return "";
        const highest = groups.reduce((m, g) => Math.max(m, g.stars || 0), 0);
        if (!highest) return "unrated";
        return "★".repeat(highest);
      },
      passageTitleFor(s) {
        return this.passages.find(p => p.id === s.passage_id)?.title || "custom";
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
      paramChipsForGroup(g) {
        const parts = [];
        for (const [k, v] of Object.entries(g.params || {})) {
          const label = PARAM_LABEL_OVERRIDES[k] || k;
          parts.push(`<span class="vt-param">${escapeHtml(label)}=${escapeHtml(String(v))}</span>`);
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
      selectSlot(slot) {
        // Accordion: opening one character collapses the others.
        const next = new Set();
        for (const c of this.characters) if (c.slot !== slot) next.add(c.slot);
        next.add("__unassigned__");
        this.collapsed = next;
        this.activeSlot = slot;
        saveLS(LS_COLLAPSED, Array.from(next));
      },
      collapseAll() {
        this.characters.forEach(c => this.collapsed.add(c.slot));
        this.collapsed.add("__unassigned__");
        saveLS(LS_COLLAPSED, Array.from(this.collapsed));
      },
      expandAll() {
        this.collapsed.clear();
        saveLS(LS_COLLAPSED, []);
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

      // ─────────── wizard (3-step Generate) ───────────
      openWizard() {
        this.wizard.open = true;
        this.wizard.step = 1;
        this.popover.open = null;
      },
      closeWizard() {
        this.wizard.open = false;
      },
      filteredWizardPassages() {
        const f = this.wizard.filterSlot;
        if (!f) return this.passages.slice().sort((a, b) => b.id - a.id);
        return this.passages.filter(p => p.character_slot === f)
          .sort((a, b) => b.id - a.id);
      },
      toggleWizardPassage(id) {
        if (this.wizard.selectedPassageIds.has(id)) {
          this.wizard.selectedPassageIds.delete(id);
        } else {
          this.wizard.selectedPassageIds.add(id);
        }
        // Nudge Alpine to re-render Set-dependent templates.
        this.wizard.selectedPassageIds = new Set(this.wizard.selectedPassageIds);
      },
      selectAllFiltered() {
        const next = new Set(this.wizard.selectedPassageIds);
        for (const p of this.filteredWizardPassages()) next.add(p.id);
        this.wizard.selectedPassageIds = next;
      },
      clearWizardSelection() {
        this.wizard.selectedPassageIds = new Set();
      },
      wizardStep1Ready() {
        if (this.wizard.selectedPassageIds.size > 0) return true;
        if (this.wizard.customText.trim() && this.wizard.customTextSlot) return true;
        return false;
      },
      wizardAdvance() {
        if (this.wizard.step === 1) {
          if (this.wizardStep1Ready()) this.wizard.step = 2;
          return;
        }
        if (this.wizard.step === 2) {
          if (this.wizardStep2Ready()) this.wizard.step = 3;
          return;
        }
        if (this.wizard.step === 3) this.submitCartesianBatch();
      },
      wizardBack() {
        if (this.wizard.step > 1) this.wizard.step -= 1;
      },
      onWizardEnter(ev) {
        // Don't hijack Enter inside text fields (Enter in textarea = newline).
        const tag = (ev.target?.tagName || "").toLowerCase();
        if (tag === "textarea" || tag === "input" || tag === "select") return;
        this.wizardAdvance();
      },
      wizardPassageSummary() {
        const n = this.wizard.selectedPassageIds.size;
        const c = (this.wizard.customText.trim() && this.wizard.customTextSlot) ? 1 : 0;
        const total = n + c;
        if (!total) return "no passages";
        return `${total} passage${total === 1 ? "" : "s"}`;
      },

      // ── Step 2 helpers ──
      distinctWizardSlots() {
        const present = new Set();
        for (const pid of this.wizard.selectedPassageIds) {
          const s = this._passageToSlot[pid];
          if (s) present.add(s);
        }
        if (this.wizard.customText.trim() && this.wizard.customTextSlot) {
          present.add(this.wizard.customTextSlot);
        }
        return this.characters.filter(c => present.has(c.slot));
      },
      wizardFilteredVoices(grp) {
        const q = (this.wizard.voiceQuery || "").trim().toLowerCase();
        const gendersOn = Object.keys(this.wizard.filterGenders);
        const accentsOn = Object.keys(this.wizard.filterAccents);
        const traitsOn = Object.keys(this.wizard.filterTraits);
        return grp.voices.filter(v => {
          if (q) {
            const pf = this.voiceProfileFor(grp.engine, v.id);
            const desc = (pf?.description || "").toLowerCase();
            const hay = [v.id, v.label, v.gender, v.accent, desc]
              .map(x => (x || "").toLowerCase()).join(" ");
            if (!hay.includes(q)) return false;
          }
          if (gendersOn.length) {
            if (!v.gender || !gendersOn.includes(v.gender)) return false;
          }
          if (accentsOn.length) {
            if (!v.accent || !accentsOn.includes(v.accent)) return false;
          }
          if (traitsOn.length) {
            const pf = this.voiceProfileFor(grp.engine, v.id);
            const vt = new Set(pf?.traits || []);
            if (!traitsOn.every(t => vt.has(t))) return false;
          }
          return true;
        });
      },
      isEngineVisible(grp) {
        const engs = Object.keys(this.wizard.filterEngines);
        if (engs.length && !engs.includes(grp.engine)) return false;
        return grp.available;
      },
      toggleFacet(bucket, value) {
        const cur = { ...(this.wizard[bucket] || {}) };
        if (cur[value]) delete cur[value]; else cur[value] = true;
        this.wizard[bucket] = cur;
      },
      clearFacets() {
        this.wizard.filterEngines = {};
        this.wizard.filterGenders = {};
        this.wizard.filterAccents = {};
        this.wizard.filterTraits = {};
        this.wizard.voiceQuery = "";
      },
      availableAccents() {
        const set = new Set();
        for (const e of this.engines) {
          if (!e.available) continue;
          for (const v of e.voices) if (v.accent) set.add(v.accent);
        }
        return Array.from(set).sort();
      },
      availableGenders() {
        const set = new Set();
        for (const e of this.engines) {
          if (!e.available) continue;
          for (const v of e.voices) if (v.gender) set.add(v.gender);
        }
        const order = ["f", "m", "n"];
        return Array.from(set).sort((a, b) => order.indexOf(a) - order.indexOf(b));
      },
      availableTraits() {
        const set = new Set();
        for (const key of Object.keys(this.voiceProfiles || {})) {
          for (const t of (this.voiceProfiles[key].traits || [])) set.add(t);
        }
        return Array.from(set).sort();
      },
      activeFacetCount() {
        return Object.keys(this.wizard.filterEngines).length
          + Object.keys(this.wizard.filterGenders).length
          + Object.keys(this.wizard.filterAccents).length
          + Object.keys(this.wizard.filterTraits).length;
      },
      isWizardVoiceSelected(slot, engine, voice_id) {
        const key = `${engine}|${voice_id}`;
        const obj = this.wizard.selectedVoicesBySlot[slot];
        return !!(obj && obj[key]);
      },
      toggleWizardVoice(slot, engine, voice_id) {
        const key = `${engine}|${voice_id}`;
        const cur = { ...(this.wizard.selectedVoicesBySlot[slot] || {}) };
        if (cur[key]) delete cur[key]; else cur[key] = true;
        this.wizard.selectedVoicesBySlot = {
          ...this.wizard.selectedVoicesBySlot,
          [slot]: cur,
        };
      },
      wizardVoiceCount(slot) {
        return Object.keys(this.wizard.selectedVoicesBySlot[slot] || {}).length;
      },
      voiceProfileFor(engine, voice_id) {
        return this.voiceProfiles[`${engine}|${voice_id}`] || null;
      },
      voiceDescription(engine, voice_id) {
        const key = `${engine}|${voice_id}`;
        if (key in this.wizard.descDrafts) return this.wizard.descDrafts[key];
        const pf = this.voiceProfiles[key];
        return pf?.description || "";
      },
      setVoiceDescriptionDraft(engine, voice_id, value) {
        const key = `${engine}|${voice_id}`;
        this.wizard.descDrafts = { ...this.wizard.descDrafts, [key]: value };
      },
      async commitVoiceDescription(engine, voice_id) {
        const key = `${engine}|${voice_id}`;
        const draft = this.wizard.descDrafts[key];
        if (draft === undefined) return;
        const current = this.voiceProfiles[key]?.description || "";
        if (draft === current) {
          const { [key]: _, ...rest } = this.wizard.descDrafts;
          this.wizard.descDrafts = rest;
          return;
        }
        try {
          await api(`/api/voices/${engine}/${voice_id}/profile`, {
            method: "PUT",
            body: JSON.stringify({ description: draft }),
          });
          this.voiceProfiles = {
            ...this.voiceProfiles,
            [key]: { ...(this.voiceProfiles[key] || {}), engine, voice_id, description: draft },
          };
          const { [key]: _, ...rest } = this.wizard.descDrafts;
          this.wizard.descDrafts = rest;
        } catch (e) {
          console.warn("voice description save failed:", e);
        }
      },
      voiceSampleResultId(engine, voice_id) {
        const pf = this.voiceProfileFor(engine, voice_id);
        if (pf && pf.sample_result_id) return pf.sample_result_id;
        for (const r of this.results) {
          if (r.engine === engine && r.voice_id === voice_id) return r.id;
        }
        return null;
      },
      voiceSampleButtonLabel(engine, voice_id) {
        if (this.wizard.tryingOut === `${engine}|${voice_id}`) return "…";
        return this.voiceSampleResultId(engine, voice_id) ? "▶" : "Try out";
      },
      playOrTryVoice(engine, voice_id) {
        const rid = this.voiceSampleResultId(engine, voice_id);
        if (rid) {
          const r = this.results.find(x => x.id === rid);
          if (r) this.playResult(r);
          return;
        }
        this.tryOutVoice(engine, voice_id);
      },
      async tryOutVoice(engine, voice_id) {
        const key = `${engine}|${voice_id}`;
        if (this.wizard.tryingOut) return;
        this.wizard.tryingOut = key;
        try {
          const { batch_id } = await api("/api/generate", {
            method: "POST",
            body: JSON.stringify({
              text: this.tryoutText,
              jobs: [{ engine, voice_id, speed: 1.0, params: null }],
            }),
          });
          let resultId = null;
          for (let i = 0; i < 120; i++) {
            await new Promise(r => setTimeout(r, 1000));
            const { jobs } = await api(`/api/batch/${batch_id}`);
            const done = jobs.find(j => j.status === "done" && j.result_id);
            if (done) { resultId = done.result_id; break; }
            if (jobs.every(j => j.status === "failed")) break;
          }
          if (!resultId) return;
          await this.refreshResults();
          await api(`/api/voices/${engine}/${voice_id}/profile`, {
            method: "PUT",
            body: JSON.stringify({ sample_result_id: resultId }),
          });
          this.voiceProfiles = {
            ...this.voiceProfiles,
            [key]: {
              ...(this.voiceProfiles[key] || {}),
              engine, voice_id, sample_result_id: resultId,
            },
          };
          const r = this.results.find(x => x.id === resultId);
          if (r) this.playResult(r);
        } finally {
          this.wizard.tryingOut = null;
        }
      },
      isPreviouslyCast(slot, engine, voice_id) {
        return (this.presetVoices[slot] || []).some(
          p => p.engine === engine && p.voice_id === voice_id,
        );
      },
      addPresetVoice(slot, engine, voice_id) {
        this.toggleWizardVoice(slot, engine, voice_id);
      },
      wizardStep2Ready() {
        const slots = this.distinctWizardSlots();
        if (!slots.length) return false;
        return slots.every(c => this.wizardVoiceCount(c.slot) > 0);
      },

      // ── Step 3 helpers ──
      wizardVoiceCombos() {
        // Flattened list of (slot, engine, voice_id) from step 2 selection.
        const out = [];
        for (const c of this.distinctWizardSlots()) {
          const sel = this.wizard.selectedVoicesBySlot[c.slot] || {};
          for (const key of Object.keys(sel)) {
            const [engine, voice_id] = key.split("|");
            out.push({ slot: c.slot, char: c, engine, voice_id, key: `${c.slot}|${engine}|${voice_id}` });
          }
        }
        return out;
      },
      voiceParamValue(slot, engine, voice_id, paramKey, fallback) {
        const k = `${slot}|${engine}|${voice_id}`;
        const obj = this.wizard.perVoiceParams[k];
        if (obj && (paramKey in obj)) return obj[paramKey];
        return fallback;
      },
      setVoiceParam(slot, engine, voice_id, paramKey, val) {
        const k = `${slot}|${engine}|${voice_id}`;
        const next = { ...(this.wizard.perVoiceParams[k] || {}) };
        next[paramKey] = val === "" ? null : (isNaN(+val) ? val : +val);
        this.wizard.perVoiceParams = { ...this.wizard.perVoiceParams, [k]: next };
      },
      resetVoiceParams(slot, engine, voice_id) {
        const k = `${slot}|${engine}|${voice_id}`;
        const { [k]: _drop, ...rest } = this.wizard.perVoiceParams;
        this.wizard.perVoiceParams = rest;
      },
      engineParamSchema(engine) {
        const grp = this.engines.find(g => g.engine === engine);
        return (grp?.param_schema) || [];
      },
      toggleExpandedParams(key) {
        this.wizard.expandedParams = {
          ...this.wizard.expandedParams,
          [key]: !this.wizard.expandedParams[key],
        };
      },
      _buildJobForVoice(slot, engine, voice_id) {
        const k = `${slot}|${engine}|${voice_id}`;
        const params = this.wizard.perVoiceParams[k] || {};
        const schemaKeys = new Set(this.engineParamSchema(engine).map(p => p.key));
        const cleaned = {};
        for (const key of Object.keys(params)) {
          if (schemaKeys.has(key) && params[key] !== null && params[key] !== undefined && params[key] !== "") {
            cleaned[key] = params[key];
          }
        }
        return {
          engine, voice_id, speed: 1.0,
          params: Object.keys(cleaned).length ? cleaned : null,
        };
      },
      async runPreview(slot, engine, voice_id) {
        const key = `${slot}|${engine}|${voice_id}`;
        if (this.wizard.previewing) return;
        const firstPid = Array.from(this.wizard.selectedPassageIds)
          .find(pid => this._passageToSlot[pid] === slot);
        const customText = this.wizard.customText.trim();
        const useCustom = !firstPid && this.wizard.customTextSlot === slot && customText;
        if (!firstPid && !useCustom) return;

        this.wizard.previewing = key;
        try {
          const body = firstPid
            ? { passage_id: firstPid, jobs: [this._buildJobForVoice(slot, engine, voice_id)] }
            : { text: customText, jobs: [this._buildJobForVoice(slot, engine, voice_id)] };
          const { batch_id } = await api("/api/generate", {
            method: "POST", body: JSON.stringify(body),
          });
          let resultId = null;
          for (let i = 0; i < 120; i++) {
            await new Promise(r => setTimeout(r, 1000));
            const { jobs } = await api(`/api/batch/${batch_id}`);
            const done = jobs.find(j => j.status === "done" && j.result_id);
            if (done) { resultId = done.result_id; break; }
            if (jobs.every(j => j.status === "failed")) break;
          }
          if (!resultId) return;
          await this.refreshResults();
          const r = this.results.find(x => x.id === resultId);
          if (r) {
            this.wizard.previews = { ...this.wizard.previews, [key]: r };
            this.playResult(r);
          }
        } finally {
          this.wizard.previewing = null;
        }
      },
      wizardTotalAudios() {
        let total = 0;
        for (const pid of this.wizard.selectedPassageIds) {
          const slot = this._passageToSlot[pid];
          if (!slot) continue;
          total += this.wizardVoiceCount(slot);
        }
        if (this.wizard.customText.trim() && this.wizard.customTextSlot) {
          total += this.wizardVoiceCount(this.wizard.customTextSlot);
        }
        return total;
      },
      async submitCartesianBatch() {
        if (this.wizard.submitting || this.generating) return;
        if (!this.wizardStep1Ready() || !this.wizardStep2Ready()) return;

        const passageEntries = [];
        for (const pid of this.wizard.selectedPassageIds) {
          const slot = this._passageToSlot[pid];
          if (!slot) continue;
          const voices = Object.keys(this.wizard.selectedVoicesBySlot[slot] || {});
          if (!voices.length) continue;
          passageEntries.push({
            pid, slot, voices,
            label: this.passages.find(p => p.id === pid)?.title || `#${pid}`,
          });
        }
        const customText = this.wizard.customText.trim();
        const customSlot = this.wizard.customTextSlot;
        const customVoices = (customText && customSlot)
          ? Object.keys(this.wizard.selectedVoicesBySlot[customSlot] || {})
          : [];

        const total = passageEntries.length + (customVoices.length ? 1 : 0);
        if (!total) return;

        this.wizard.submitting = true;
        this.wizard.lastErrors = [];
        this.wizard.progress = { current: 0, total, label: "" };
        const failures = [];

        try {
          for (let i = 0; i < passageEntries.length; i++) {
            const entry = passageEntries[i];
            this.wizard.progress = { current: i, total, label: entry.label };
            try {
              const jobs = entry.voices.map(key => {
                const [engine, voice_id] = key.split("|");
                return this._buildJobForVoice(entry.slot, engine, voice_id);
              });
              const { batch_id } = await api("/api/generate", {
                method: "POST",
                body: JSON.stringify({ passage_id: entry.pid, jobs }),
              });
              await this.pollBatch(batch_id);
            } catch (e) {
              failures.push(`${entry.label}: ${e.message}`);
            }
          }
          if (customVoices.length) {
            this.wizard.progress = {
              current: passageEntries.length, total, label: "custom text",
            };
            try {
              const jobs = customVoices.map(key => {
                const [engine, voice_id] = key.split("|");
                return this._buildJobForVoice(customSlot, engine, voice_id);
              });
              const { batch_id } = await api("/api/generate", {
                method: "POST",
                body: JSON.stringify({ text: customText, jobs }),
              });
              await this.pollBatch(batch_id);
            } catch (e) {
              failures.push(`custom text: ${e.message}`);
            }
          }

          await this.refreshResults();
          if (failures.length) {
            this.wizard.lastErrors = failures;
            alert(`Batch completed with ${failures.length} failure(s):\n\n${failures.join("\n")}`);
          }

          // Reset wizard so next open starts clean.
          this.wizard.selectedPassageIds = new Set();
          this.wizard.customText = "";
          this.wizard.customTextSlot = null;
          this.wizard.selectedVoicesBySlot = {};
          this.wizard.perVoiceParams = {};
          this.wizard.previews = {};
          this.wizard.step = 1;
        } finally {
          this.wizard.submitting = false;
          this.wizard.progress = null;
          this.wizard.open = false;
        }
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
        // Update keyboard focus + last-played marker for samples that belong to a known group.
        if (r && r.passage_id) {
          const slot = this._passageToSlot[r.passage_id];
          if (slot) {
            this.focusedGroupKey = this.groupKey(r.engine, r.voice_id, this.paramsFp(r));
            this.focusedSampleId = r.id;
          }
        }
        if (r && r.id) this.lastPlayedSampleId = r.id;
        return this._playResult(r);
      },
      _playResult(r) {
        if (!r || !r.audio_url) return;
        const el = this.audioEl;
        if (this.currentAudioId === r.id && !el.paused) { el.pause(); return; }
        el.src = r.audio_url;
        const fp = this.paramsFp(r);
        const slot = r.passage_id ? this._passageToSlot[r.passage_id] : null;
        const g = slot
          ? this.groupedResults(slot).find(x => x.key === this.groupKey(r.engine, r.voice_id, fp))
          : null;
        el.playbackRate = g ? +this.cardSpeed(g) : 1.0;
        this.currentAudioId = r.id;
        el.play().catch(() => {});
      },
      _updateVoiceNote(slot, g, patch) {
        const slotMap = { ...(this.voiceNotes[slot] || {}) };
        slotMap[g.key] = { ...(slotMap[g.key] || {}), ...patch };
        this.voiceNotes = { ...this.voiceNotes, [slot]: slotMap };
      },
      async _putNote(slot, g, body) {
        try {
          await api(`/api/voices/${g.engine}/${g.voice_id}/notes?slot=${encodeURIComponent(slot)}`, {
            method: "PUT",
            body: JSON.stringify({ params_fp: g.params_fp, ...body }),
          });
          this._flagSave(g.key);
          return true;
        } catch (e) {
          this._flagSaveError(e.message);
          return false;
        }
      },
      _flagSave(key) {
        this.savedFlags = { ...this.savedFlags, [key]: Date.now() };
        setTimeout(() => {
          const { [key]: _drop, ...rest } = this.savedFlags;
          this.savedFlags = rest;
        }, 1500);
      },
      _flagSaveError(msg) {
        const at = Date.now();
        this.saveError = { msg, at };
        setTimeout(() => {
          if (this.saveError && this.saveError.at === at) this.saveError = null;
        }, 4000);
      },
      async setVoiceStars(slot, g, n) {
        const nv = (g.stars || 0) === n ? null : n;
        if (await this._putNote(slot, g, { stars: nv })) {
          this._updateVoiceNote(slot, g, { stars: nv });
        }
      },
      async toggleMarked(slot, g) {
        const nv = !g.marked;
        if (await this._putNote(slot, g, { marked: nv })) {
          this._updateVoiceNote(slot, g, { marked: nv });
        }
      },
      async saveVoiceNotes(slot, g, val) {
        if (await this._putNote(slot, g, { notes: val || null })) {
          this._updateVoiceNote(slot, g, { notes: val || null });
        }
      },
      async saveCardSpeed(slot, g) {
        const speed = +this.cardSpeed(g);
        if (await this._putNote(slot, g, { playback_speed: speed })) {
          this._updateVoiceNote(slot, g, { playback_speed: speed });
        }
      },
      cardSpeed(g) {
        if (this.cardSpeeds[g.key] !== undefined) return this.cardSpeeds[g.key];
        const saved = this.savedSpeed(g);
        return saved !== null ? +saved : 1.0;
      },
      savedSpeed(g) {
        // Voice notes are slot-scoped; walk this group's samples to find the
        // owning slot and return its saved playback_speed (or null).
        for (const s of g.samples) {
          const slot = s.passage_id ? this._passageToSlot[s.passage_id] : null;
          if (!slot) continue;
          const v = this.voiceNotes[slot]?.[g.key]?.playback_speed;
          if (v != null) return +v;
        }
        return null;
      },
      setCardSpeed(g, v) {
        const speed = +v;
        this.cardSpeeds = { ...this.cardSpeeds, [g.key]: speed };
        // Live drag: if a sample from this group is currently playing, retune now.
        if (this.currentAudioId && g.samples.some(s => s.id === this.currentAudioId)) {
          if (this.audioEl) this.audioEl.playbackRate = speed;
        }
      },
      missingPassagesFor(slot, g) {
        const haveIds = new Set(g.samples.map(s => s.passage_id).filter(Boolean));
        return this.passages.filter(p => p.character_slot === slot && !haveIds.has(p.id));
      },
      toggleOtherDialogues(g) {
        if (this.otherDialoguesOpen === g.key) {
          this.otherDialoguesOpen = null;
          this.selectedMissing = new Set();
        } else {
          this.otherDialoguesOpen = g.key;
          this.selectedMissing = new Set();
        }
      },
      toggleMissingPassage(pid) {
        const next = new Set(this.selectedMissing);
        if (next.has(pid)) next.delete(pid); else next.add(pid);
        this.selectedMissing = next;
      },
      async generateOtherDialogues(slot, g) {
        if (this.regenerating) return;
        const ids = Array.from(this.selectedMissing);
        if (!ids.length) return;
        const params = Object.keys(g.params).length ? g.params : null;
        this.regenerating = g.key;
        try {
          for (const pid of ids) {
            const { batch_id } = await api("/api/generate", {
              method: "POST",
              body: JSON.stringify({
                passage_id: pid,
                jobs: [{ engine: g.engine, voice_id: g.voice_id, speed: 1.0, params }],
              }),
            });
            await this.pollBatch(batch_id);
          }
          await this.refreshResults();
        } finally {
          this.regenerating = null;
          this.otherDialoguesOpen = null;
          this.selectedMissing = new Set();
        }
      },
      async regenerate(slot, g) {
        if (this.regenerating) return;
        const src = g.samples[0];
        if (!src || !src.passage_id) return;
        this.regenerating = g.key;
        try {
          const { batch_id } = await api("/api/generate", {
            method: "POST",
            body: JSON.stringify({
              passage_id: src.passage_id,
              jobs: [{
                engine: g.engine,
                voice_id: g.voice_id,
                speed: 1.0,
                params: Object.keys(g.params).length ? g.params : null,
              }],
            }),
          });
          await this.pollBatch(batch_id);
          await this.refreshResults();
        } finally {
          this.regenerating = null;
        }
      },
      async castAs(r, slot) {
        const currentId = this.castedResultId(slot);
        const newId = currentId === r.id ? null : r.id;
        await api(`/api/casting/${slot}`, {
          method: "PUT",
          body: JSON.stringify({ result_id: newId, notes: null }),
        });
        const { slots } = await api("/api/casting");
        this.casting = slots;
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
        // Legacy per-sample delete path (unassigned rows keep this).
        if (this.deleteArmed === r.id) {
          this.deleteArmed = null;
          clearTimeout(this.deleteArmTimer);
          this._doDelete([r]);
          return;
        }
        this.deleteArmed = r.id;
        clearTimeout(this.deleteArmTimer);
        this.deleteArmTimer = setTimeout(() => { this.deleteArmed = null; }, 3000);
      },
      confirmDeleteGroup(slot, g) {
        if (this.deleteArmed === g.key) {
          this.deleteArmed = null;
          clearTimeout(this.deleteArmTimer);
          this._doDeleteGroup(slot, g);
          return;
        }
        this.deleteArmed = g.key;
        clearTimeout(this.deleteArmTimer);
        this.deleteArmTimer = setTimeout(() => { this.deleteArmed = null; }, 3000);
      },
      async _doDelete(rs) {
        const ids = new Set(rs.map(r => r.id));
        for (const r of rs) await api(`/api/results/${r.id}`, { method: "DELETE" });
        this.results = this.results.filter(x => !ids.has(x.id));
        this.casting = this.casting.map(c =>
          c.result && ids.has(c.result.id) ? { ...c, result: null } : c
        );
      },
      _doDeleteGroup(slot, g) {
        // Defer the actual DELETE for 10s so the user can hit Undo.
        // The card disappears immediately (groupedResults filters it out).
        if (this.pendingDelete) this._flushPendingDelete();
        const samples = [...g.samples];
        const expiresAt = Date.now() + 10000;
        const timer = setTimeout(() => this._flushPendingDelete(), 10000);
        this.pendingDelete = { slot, g, samples, timer, expiresAt };
      },
      undoDelete() {
        if (!this.pendingDelete) return;
        clearTimeout(this.pendingDelete.timer);
        this.pendingDelete = null;
      },
      async _flushPendingDelete() {
        const pd = this.pendingDelete;
        if (!pd) return;
        this.pendingDelete = null;
        clearTimeout(pd.timer);
        const ids = pd.samples.map(s => s.id);
        for (const id of ids) {
          await api(`/api/results/${id}`, { method: "DELETE" });
        }
        // Clear every voice-note field so backend GCs the row.
        await api(`/api/voices/${pd.g.engine}/${pd.g.voice_id}/notes?slot=${encodeURIComponent(pd.slot)}`, {
          method: "PUT",
          body: JSON.stringify({
            params_fp: pd.g.params_fp,
            notes: null, stars: null, playback_speed: null, marked: false,
          }),
        });
        const idSet = new Set(ids);
        this.results = this.results.filter(r => !idSet.has(r.id));
        this.casting = this.casting.map(c =>
          c.result && idSet.has(c.result.id) ? { ...c, result: null } : c
        );
        const slotMap = { ...(this.voiceNotes[pd.slot] || {}) };
        delete slotMap[pd.g.key];
        this.voiceNotes = { ...this.voiceNotes, [pd.slot]: slotMap };
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

      // ─────────── focus / keyboard helpers ───────────
      visibleGroups() {
        const out = [];
        for (const c of this.characters) {
          if (this.collapsed.has(c.slot)) continue;
          for (const g of this.groupedResults(c.slot)) out.push({ slot: c.slot, g });
        }
        return out;
      },
      focusedEntry() {
        if (!this.focusedGroupKey) return null;
        return this.visibleGroups().find(e => e.g.key === this.focusedGroupKey) || null;
      },
      setFocus(slot, g, sampleId = null) {
        this.focusedGroupKey = g.key;
        this.focusedSampleId = sampleId !== null ? sampleId : (g.samples[0]?.id || null);
        this.activeSlot = slot;
      },
      clearFocus() {
        this.focusedGroupKey = null;
        this.focusedSampleId = null;
      },
      _scrollFocusedIntoView() {
        if (!this.focusedGroupKey) return;
        this.$nextTick(() => {
          const el = document.querySelector(
            `.vt-voice-card[data-group-key="${CSS.escape(this.focusedGroupKey)}"]`
          );
          if (el) el.scrollIntoView({ behavior: "smooth", block: "nearest" });
        });
      },
      focusNextGroup(delta) {
        const list = this.visibleGroups();
        if (!list.length) return;
        let i;
        if (!this.focusedGroupKey) {
          i = 0;
        } else {
          i = list.findIndex(e => e.g.key === this.focusedGroupKey);
          i = i < 0 ? 0 : Math.min(list.length - 1, Math.max(0, i + delta));
        }
        const e = list[i];
        this.setFocus(e.slot, e.g);
        this._scrollFocusedIntoView();
      },
      focusNextSample(delta) {
        const e = this.focusedEntry();
        if (!e) return;
        const samples = e.g.samples;
        if (!samples.length) return;
        let i = samples.findIndex(s => s.id === this.focusedSampleId);
        if (i < 0) i = 0;
        const ni = Math.min(samples.length - 1, Math.max(0, i + delta));
        this.focusedSampleId = samples[ni].id;
      },
      playFocused() {
        const e = this.focusedEntry();
        if (!e) {
          // Auto-focus the first visible voice and play its first dialogue.
          const list = this.visibleGroups();
          if (!list.length) return;
          const first = list[0];
          this.setFocus(first.slot, first.g);
          this._scrollFocusedIntoView();
          const s = first.g.samples[0];
          if (s) this.playResult(s);
          return;
        }
        const s = e.g.samples.find(x => x.id === this.focusedSampleId) || e.g.samples[0];
        if (s) this.playResult(s);
      },
      rateFocused(n) {
        const e = this.focusedEntry();
        if (!e) return;
        this.setVoiceStars(e.slot, e.g, n);
      },
      unrateFocused() {
        const e = this.focusedEntry();
        if (!e || !e.g.stars) return;
        // setVoiceStars(slot, g, sameValue) toggles to null.
        this.setVoiceStars(e.slot, e.g, e.g.stars);
      },
      castFocused() {
        const e = this.focusedEntry();
        if (!e) return;
        const s = e.g.samples.find(x => x.id === this.focusedSampleId) || e.g.samples[0];
        if (s) this.castAs(s, e.slot);
      },
      deleteFocused() {
        const e = this.focusedEntry();
        if (!e) return;
        this.confirmDeleteGroup(e.slot, e.g);
      },
      markFocused() {
        const e = this.focusedEntry();
        if (!e) return;
        this.toggleMarked(e.slot, e.g);
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
        // Don't intercept browser shortcuts.
        if (ev.metaKey || ev.ctrlKey || ev.altKey) return;

        // Esc — close help, disarm delete, or clear focus.
        // (Other modals — wizard, palette — own their own Esc handlers.)
        if (ev.key === "Escape") {
          if (this.helpOpen) { this.helpOpen = false; return; }
          if (this.wizard.open || this.palette.open) return;
          if (this.deleteArmed) {
            this.deleteArmed = null;
            clearTimeout(this.deleteArmTimer);
            return;
          }
          if (this.focusedGroupKey) { this.clearFocus(); return; }
          return;
        }

        // ?-overlay (Shift+/ on US layouts)
        if (ev.key === "?") {
          ev.preventDefault();
          this.helpOpen = !this.helpOpen;
          return;
        }
        // While a modal is open, only Esc / ⌘K / ? above are honored.
        if (this.helpOpen || this.wizard.open || this.palette.open) return;

        // Collapse / expand all (preserve existing).
        if (ev.key === "g") {
          if (this._lastG && Date.now() - this._lastG < 600) {
            this.collapseAll();
            this._lastG = 0;
          } else {
            this._lastG = Date.now();
          }
          return;
        }
        if (ev.key === "G") {
          this.expandAll();
          return;
        }

        // Vim navigation.
        if (ev.key === "j") { ev.preventDefault(); this.focusNextGroup(+1); return; }
        if (ev.key === "k") { ev.preventDefault(); this.focusNextGroup(-1); return; }
        if (ev.key === "l") { ev.preventDefault(); this.focusNextSample(+1); return; }
        if (ev.key === "h") { ev.preventDefault(); this.focusNextSample(-1); return; }

        // Space — toggle play on focused.
        if (ev.key === " " || ev.code === "Space") {
          ev.preventDefault();
          this.playFocused();
          return;
        }

        // Rating.
        if (ev.key >= "1" && ev.key <= "5") {
          this.rateFocused(parseInt(ev.key, 10));
          return;
        }
        if (ev.key === "0") { this.unrateFocused(); return; }

        // Actions.
        if (ev.key === "c") { this.castFocused(); return; }
        if (ev.key === "x") { this.deleteFocused(); return; }
        if (ev.key === "m") { this.markFocused(); return; }
        if (ev.key === "n") { this.openWizard(); return; }
      },
    };
  }

  // Register with Alpine before it starts scanning the DOM.
  document.addEventListener("alpine:init", () => {
    window.Alpine.data("vtApp", vtAppFactory);
  });
})();
