const app = document.getElementById("app");
const topnav = document.getElementById("topnav");

function currentSlot() {
  return localStorage.getItem("mma_slot");
}
function setSlot(slot, name) {
  localStorage.setItem("mma_slot", slot);
  localStorage.setItem("mma_slot_name", name || slot);
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

function initials(name) {
  return (name || "?").split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase();
}

function portraitTag(slot, fighterId, name, sizeClass) {
  const wrap = el(`<div class="${sizeClass}"><span class="portrait-fallback">${initials(name)}</span></div>`);
  const img = document.createElement("img");
  img.onerror = () => img.remove();
  img.onload = () => {
    img.classList.add("loaded");
    wrap.querySelector(".portrait-fallback")?.remove();
  };
  img.src = `/api/saves/${slot}/fighters/${fighterId}/portrait`;
  wrap.prepend(img);
  return wrap.outerHTML;
}

function renderNav() {
  const slot = currentSlot();
  topnav.innerHTML = "";
  if (slot) {
    topnav.appendChild(el(`<a href="#/roster">Roster</a>`));
    topnav.appendChild(el(`<a href="#/events">Events</a>`));
    topnav.appendChild(el(`<a href="#/rankings">Rankings</a>`));
    topnav.appendChild(el(`<a href="#/free-agents">Free Agents</a>`));
    topnav.appendChild(el(`<a href="#/compare">Compare</a>`));
    topnav.appendChild(el(`<a href="#/calendar">Calendar</a>`));
    topnav.appendChild(el(`<a href="#/hall-of-records">Hall of Records</a>`));
    topnav.appendChild(el(`<a href="#/fight-tester">Fight Tester</a>`));
    topnav.appendChild(el(`<a href="#/">Switch Save</a>`));
  }
}

async function router() {
  renderNav();
  const hash = location.hash || "#/";
  const fighterMatch = hash.match(/^#\/fighter\/(\d+)$/);
  const eventMatch = hash.match(/^#\/events\/(\d+)$/);
  try {
    if (hash === "#/" || hash === "") {
      await renderSaveSelect();
    } else if (hash === "#/roster") {
      await renderRoster();
    } else if (hash === "#/fight-tester") {
      await renderFightTester();
    } else if (hash === "#/events") {
      await renderEventsList();
    } else if (eventMatch) {
      await renderEventDetail(parseInt(eventMatch[1], 10));
    } else if (hash === "#/rankings") {
      await renderRankings();
    } else if (hash === "#/free-agents") {
      await renderFreeAgents();
    } else if (hash === "#/compare") {
      await renderCompare();
    } else if (hash === "#/calendar") {
      await renderCalendar();
    } else if (hash === "#/hall-of-records") {
      await renderHallOfRecords();
    } else if (fighterMatch) {
      await renderFighterProfile(parseInt(fighterMatch[1], 10));
    } else {
      app.innerHTML = `<div class="empty-state">Not found</div>`;
    }
  } catch (err) {
    app.innerHTML = `<div class="error-state">Error: ${err.message}</div>`;
  }
}

window.addEventListener("hashchange", router);
window.addEventListener("DOMContentLoaded", router);

// ---------- Save select ----------

async function renderSaveSelect() {
  const saves = await api("/api/saves");
  app.innerHTML = `
    <div class="panel">
      <h2>Save Slots</h2>
      <div class="save-list">
        ${saves.length ? saves.map(s => `
          <div class="save-row">
            <div>
              <div><strong>${s.name}</strong></div>
              <div class="meta">${s.fighter_count} fighters &middot; created ${s.created_at} &middot; ${s.universe_mode}</div>
            </div>
            <div style="display:flex; gap:8px;">
              <button class="btn" data-slot="${s.slot}" data-name="${s.name}">Load</button>
              <button class="btn secondary" data-delete-slot="${s.slot}" data-delete-name="${s.name}">Delete</button>
            </div>
          </div>
        `).join("") : `<div class="empty-state">No saves yet. Create one below.</div>`}
      </div>
    </div>
    <div class="panel">
      <h2>Create New Universe</h2>
      <form class="create-save">
        <input type="text" name="name" placeholder="Universe name" required>
        <select name="mode">
          <option value="real">Real universe (data/real/ divisions)</option>
          <option value="generate">Generate ~200 fictional fighters</option>
          <option value="import">Import from data/import/</option>
        </select>
        <button class="btn" type="submit">Create</button>
      </form>
      <p class="meta" style="color:var(--text-dim); font-size:13px; margin-top:10px;">
        Import mode reads <code>fighters.csv</code> or <code>fighters.json</code> (plus a <code>portraits/</code> folder)
        from <code>data/import/</code>.
      </p>
    </div>
  `;

  app.querySelectorAll("[data-slot]").forEach(btn => {
    btn.addEventListener("click", () => {
      setSlot(btn.dataset.slot, btn.dataset.name);
      location.hash = "#/roster";
    });
  });

  app.querySelectorAll("[data-delete-slot]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const slot = btn.dataset.deleteSlot;
      const name = btn.dataset.deleteName;
      if (!confirm(`Delete "${name}" permanently? This can't be undone.`)) return;
      try {
        await api(`/api/saves/${slot}`, { method: "DELETE" });
        if (currentSlot() === slot) {
          localStorage.removeItem("mma_slot");
          localStorage.removeItem("mma_slot_name");
        }
        await renderSaveSelect();
      } catch (err) {
        alert(err.message);
      }
    });
  });

  app.querySelector("form.create-save").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const name = form.name.value.trim();
    const mode = form.mode.value;
    if (!name) return;
    const submitBtn = form.querySelector("button[type=submit]");
    submitBtn.disabled = true;
    submitBtn.textContent = "Creating...";
    try {
      const result = await api("/api/saves", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, mode }),
      });
      setSlot(result.slot, name);
      location.hash = "#/roster";
    } catch (err) {
      alert(err.message);
      submitBtn.disabled = false;
      submitBtn.textContent = "Create";
    }
  });
}

// ---------- Roster ----------

async function renderRoster() {
  const slot = currentSlot();
  if (!slot) { location.hash = "#/"; return; }

  const divisions = await api(`/api/saves/${slot}/divisions`);
  app.innerHTML = `
    <div class="toolbar">
      <select id="f-division">
        <option value="">All Divisions</option>
        ${divisions.map(d => `<option value="${d.weight_class}|${d.gender}">${d.weight_class} (${d.count})</option>`).join("")}
      </select>
      <input type="text" id="f-search" placeholder="Search name or nickname...">
      <select id="f-sort">
        <option value="name">Sort: Name</option>
        <option value="wins">Sort: Wins</option>
        <option value="popularity">Sort: Popularity</option>
        <option value="age">Sort: Youngest</option>
      </select>
      <select id="f-roster">
        <option value="">Everyone</option>
        <option value="ufc">UFC Roster</option>
        <option value="non-ufc">Outside the UFC</option>
      </select>
    </div>
    <div class="toolbar">
      <label class="filter-label">Age <input type="number" id="f-age-min" placeholder="min" min="18" max="60" style="width:60px;"></label>
      <label class="filter-label">&ndash; <input type="number" id="f-age-max" placeholder="max" min="18" max="60" style="width:60px;"></label>
      <select id="f-streak">
        <option value="">Any Streak</option>
        <option value="W">On a Win Streak</option>
        <option value="L">On a Losing Streak</option>
      </select>
      <input type="number" id="f-streak-min" value="2" min="1" max="20" style="width:60px;" title="Minimum streak length">
      <label class="filter-label"><input type="checkbox" id="f-ranked-only"> Ranked Only</label>
    </div>
    <div id="roster-grid" class="roster-grid"><div class="empty-state">Loading...</div></div>
  `;

  const grid = document.getElementById("roster-grid");
  const divisionSel = document.getElementById("f-division");
  const searchInput = document.getElementById("f-search");
  const sortSel = document.getElementById("f-sort");
  const ageMinInput = document.getElementById("f-age-min");
  const ageMaxInput = document.getElementById("f-age-max");
  const streakSel = document.getElementById("f-streak");
  const streakMinInput = document.getElementById("f-streak-min");
  const rankedOnlyCheckbox = document.getElementById("f-ranked-only");
  const rosterSel = document.getElementById("f-roster");

  let searchTimer;
  async function load() {
    const params = new URLSearchParams();
    if (divisionSel.value) {
      const [wc, gender] = divisionSel.value.split("|");
      params.set("division", wc);
      params.set("gender", gender);
      if (rankedOnlyCheckbox.checked) params.set("ranked_only", "true");
    }
    if (searchInput.value.trim()) params.set("search", searchInput.value.trim());
    params.set("sort", sortSel.value);
    if (ageMinInput.value) params.set("age_min", ageMinInput.value);
    if (ageMaxInput.value) params.set("age_max", ageMaxInput.value);
    if (streakSel.value) {
      params.set("streak_type", streakSel.value);
      params.set("min_streak", streakMinInput.value || "1");
    }
    if (rosterSel.value) params.set("roster", rosterSel.value);

    const fighters = await api(`/api/saves/${slot}/fighters?${params.toString()}`);
    grid.innerHTML = fighters.length ? fighters.map(f => `
      <div class="fighter-card" data-id="${f.id}">
        <div class="portrait-wrap-holder">${portraitTag(slot, f.id, f.name, "portrait-wrap")}</div>
        <div class="info">
          <div class="name">${f.name}</div>
          ${f.nickname ? `<div class="nickname">"${f.nickname}"</div>` : ""}
          <div class="sub">${f.weight_class} &middot; ${f.record} &middot; age ${f.age}</div>
          ${f.promotion !== "UFC" ? `<div class="promo-badge">${f.promotion}</div>` : ""}
          ${f.streak && f.streak.type && f.streak.count >= 2
            ? `<div class="streak-badge streak-${f.streak.type}">${f.streak.type}${f.streak.count}</div>` : ""}
        </div>
      </div>
    `).join("") : `<div class="empty-state">No fighters match those filters.</div>`;

    grid.querySelectorAll(".fighter-card").forEach(card => {
      card.addEventListener("click", () => { location.hash = `#/fighter/${card.dataset.id}`; });
    });
  }

  [divisionSel, sortSel, streakSel, streakMinInput, rankedOnlyCheckbox, rosterSel].forEach(el => {
    el.addEventListener("change", load);
  });
  [searchInput, ageMinInput, ageMaxInput].forEach(el => {
    el.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(load, 300);
    });
  });

  await load();
}

// ---------- Fighter profile ----------

const ATTR_LABELS = {
  punch_technique: "Punch Technique", kick_technique: "Kick Technique", knee_technique: "Knees",
  elbow_technique: "Elbows", punch_power: "Punch Power", kick_power: "Kick Power",
  striking_defense: "Striking Defense", head_movement: "Head Movement", chin: "Chin",
  takedowns: "Takedowns", takedown_defense: "Takedown Defense", clinch_work: "Clinch Work",
  top_control: "Top Control", bottom_game: "Bottom Game", submissions: "Submissions",
  submission_defense: "Submission Defense", scrambling: "Scrambling",
  strength: "Strength", speed: "Speed", agility: "Agility", cardio: "Cardio",
  recovery: "Recovery", toughness: "Toughness", injury_proneness: "Injury Proneness",
  heart: "Heart", killer_instinct: "Killer Instinct", fight_iq: "Fight IQ",
  composure: "Composure", work_ethic: "Work Ethic", consistency: "Consistency",
};
const ATTR_GROUPS = {
  Striking: ["punch_technique", "kick_technique", "knee_technique", "elbow_technique",
             "punch_power", "kick_power", "striking_defense", "head_movement", "chin"],
  Grappling: ["takedowns", "takedown_defense", "clinch_work", "top_control", "bottom_game",
              "submissions", "submission_defense", "scrambling"],
  Physical: ["strength", "speed", "agility", "cardio", "recovery", "toughness", "injury_proneness"],
  Mental: ["heart", "killer_instinct", "fight_iq", "composure", "work_ethic", "consistency"],
};

function attrRow(label, value) {
  return `
    <div class="attr-row">
      <div class="label">${label}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${value}%"></div></div>
      <div class="value">${value}</div>
    </div>`;
}

async function renderFighterProfile(id, editMode = false) {
  const slot = currentSlot();
  if (!slot) { location.hash = "#/"; return; }
  const [f, history] = await Promise.all([
    api(`/api/saves/${slot}/fighters/${id}`),
    api(`/api/saves/${slot}/fighters/${id}/history`),
  ]);

  if (editMode) {
    app.innerHTML = `
      <div class="panel">
        <a href="#/fighter/${id}" class="badge" id="edit-cancel-top">&larr; Cancel Edit</a>
        <h1 style="margin-top:14px;">Edit ${f.name}</h1>
      </div>
      ${renderFighterEditForm(f)}
    `;
    document.getElementById("edit-cancel-top").addEventListener("click", (e) => {
      e.preventDefault();
      renderFighterProfile(id, false);
    });
    document.getElementById("edit-cancel-btn").addEventListener("click", () => renderFighterProfile(id, false));
    document.getElementById("fighter-edit-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const updates = {};
      for (const [key, value] of fd.entries()) {
        if (key === "division") {
          const [wc, gender] = value.split("|");
          updates.weight_class = wc;
          updates.gender = gender;
        } else if (OPTIONAL_TEXT_FIELDS.has(key) && value.trim() === "") {
          updates[key] = null;
        } else {
          updates[key] = value;
        }
      }
      const submitBtn = e.target.querySelector("button[type=submit]");
      submitBtn.disabled = true;
      submitBtn.textContent = "Saving...";
      try {
        await api(`/api/saves/${slot}/fighters/${id}`, {
          method: "PATCH", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(updates),
        });
        await renderFighterProfile(id, false);
      } catch (err) {
        alert(err.message);
        submitBtn.disabled = false;
        submitBtn.textContent = "Save Changes";
      }
    });
    return;
  }

  const groupsHtml = Object.entries(ATTR_GROUPS).map(([groupName, attrs]) => `
    <div class="attr-group">
      <h3>${groupName}</h3>
      ${attrs.map(a => attrRow(ATTR_LABELS[a], f[a])).join("")}
    </div>
  `).join("");

  const historyHtml = history.length ? `
    <table class="history-table">
      <thead><tr><th>Date</th><th>Event</th><th>Opponent</th><th>Result</th></tr></thead>
      <tbody>
        ${history.map(h => `
          <tr>
            <td>${h.event_date}</td>
            <td>${h.event_name}</td>
            <td><a href="#/fighter/${h.opponent_id}">${h.opponent_name}</a></td>
            <td class="outcome-${h.outcome.toLowerCase()}">
              ${h.outcome} &middot; ${h.method_detail} (R${h.result_round} ${h.result_time})
            </td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  ` : `<div class="empty-state">No fights on record yet.</div>`;

  app.innerHTML = `
    <div class="panel">
      <a href="#/roster" class="badge">&larr; Back to Roster</a>
      <a href="#" class="badge" id="edit-fighter-btn" style="float:right;">Edit Fighter</a>
      <div class="profile-header" style="margin-top:14px;">
        <div class="profile-portrait-holder">${portraitTag(slot, f.id, f.name, "profile-portrait")}</div>
        <div class="profile-title">
          <h1>${f.name}</h1>
          ${f.nickname ? `<div class="nickname">"${f.nickname}"</div>` : ""}
          <div class="record">${f.record}</div>
          <div class="meta-line">${f.weight_class} &middot; ${f.gender === "F" ? "Women's" : "Men's"} Division</div>
          <div class="meta-line">Age ${f.age} &middot; ${f.nationality || "Unknown"} &middot; ${f.hometown || "Unknown"}</div>
          <div class="meta-line">${f.height_in ? f.height_in + '" tall' : ""} ${f.reach_in ? "&middot; " + f.reach_in + '" reach' : ""} ${f.stance ? "&middot; " + f.stance : ""}</div>
          <div style="margin-top:10px;">
            <span class="badge ${f.promotion === "UFC" ? "title-badge" : ""}">${f.promotion}</span>
            <span class="badge">${f.archetype || "Unclassified"}</span>
            <span class="badge">Potential ${f.potential}</span>
            <span class="badge">Popularity ${f.popularity}</span>
            <span class="badge">Momentum ${f.momentum}</span>
            <span class="badge">${f.status}</span>
            ${f.injury_status === "Injured" ? `<span class="badge" style="color:var(--red);">Injured until ${f.injury_return_date}</span>` : ""}
          </div>
          ${f.status === "Active" ? `
            <div style="margin-top:10px;">
              ${f.promotion === "UFC"
                ? `<button class="btn secondary btn-sm" id="cut-fighter-btn">Cut from Roster</button>`
                : `<button class="btn btn-sm" id="sign-fighter-btn">Sign to UFC</button>`}
            </div>
          ` : ""}
        </div>
      </div>
      <div class="attr-groups">${groupsHtml}</div>
    </div>
    <div class="panel">
      <h2>Fight History</h2>
      ${historyHtml}
    </div>
  `;

  document.getElementById("edit-fighter-btn").addEventListener("click", (e) => {
    e.preventDefault();
    renderFighterProfile(id, true);
  });

  document.getElementById("cut-fighter-btn")?.addEventListener("click", async () => {
    if (!confirm(`Cut ${f.name} from the UFC roster? They'll become a free agent (any titles are vacated).`)) return;
    try {
      await api(`/api/saves/${slot}/fighters/${id}/cut`, { method: "POST" });
      await renderFighterProfile(id, false);
    } catch (err) { alert(err.message); }
  });

  document.getElementById("sign-fighter-btn")?.addEventListener("click", async () => {
    try {
      await api(`/api/saves/${slot}/fighters/${id}/sign`, { method: "POST" });
      await renderFighterProfile(id, false);
    } catch (err) { alert(err.message); }
  });
}

// ---------- Fighter editor ----------

const ALL_DIVISIONS = [
  { key: "Flyweight", gender: "M" }, { key: "Bantamweight", gender: "M" }, { key: "Featherweight", gender: "M" },
  { key: "Lightweight", gender: "M" }, { key: "Welterweight", gender: "M" }, { key: "Middleweight", gender: "M" },
  { key: "Light Heavyweight", gender: "M" }, { key: "Heavyweight", gender: "M" },
  { key: "Women's Strawweight", gender: "F" }, { key: "Women's Flyweight", gender: "F" },
  { key: "Women's Bantamweight", gender: "F" },
];
const OPTIONAL_TEXT_FIELDS = new Set([
  "nickname", "nationality", "hometown", "archetype", "height_in", "reach_in", "portrait_filename",
]);
const RECORD_EDIT_FIELDS = [
  "wins", "losses", "draws", "no_contests",
  "wins_ko", "wins_sub", "wins_dec", "losses_ko", "losses_sub", "losses_dec",
];

function editFieldRow(label, name, value, type = "number", extra = "") {
  return `
    <div class="edit-row">
      <label>${label}</label>
      <input type="${type}" name="${name}" value="${value ?? ""}" ${extra}>
    </div>
  `;
}

function renderFighterEditForm(f) {
  const groupsHtml = Object.entries(ATTR_GROUPS).map(([groupName, attrs]) => `
    <div class="attr-group">
      <h3>${groupName}</h3>
      ${attrs.map(a => editFieldRow(ATTR_LABELS[a], a, f[a], "number", 'min="1" max="99"')).join("")}
    </div>
  `).join("");

  const divisionOptions = ALL_DIVISIONS.map(d => `
    <option value="${d.key}|${d.gender}" ${f.weight_class === d.key && f.gender === d.gender ? "selected" : ""}>
      ${d.key}
    </option>
  `).join("");
  const stanceOptions = ["Orthodox", "Southpaw", "Switch"].map(s =>
    `<option ${f.stance === s ? "selected" : ""}>${s}</option>`).join("");
  const statusOptions = ["Active", "Retired"].map(s =>
    `<option ${f.status === s ? "selected" : ""}>${s}</option>`).join("");

  return `
    <form id="fighter-edit-form">
      <div class="panel">
        <h3>Identity</h3>
        <div class="edit-grid">
          ${editFieldRow("Name", "name", f.name, "text", "required")}
          ${editFieldRow("Nickname", "nickname", f.nickname || "", "text")}
          ${editFieldRow("Date of Birth", "dob", f.dob, "date")}
          ${editFieldRow("Nationality", "nationality", f.nationality || "", "text")}
          ${editFieldRow("Hometown", "hometown", f.hometown || "", "text")}
          <div class="edit-row"><label>Division</label><select name="division">${divisionOptions}</select></div>
          ${editFieldRow("Height (in)", "height_in", f.height_in || "", "number", 'step="0.1"')}
          ${editFieldRow("Reach (in)", "reach_in", f.reach_in || "", "number", 'step="0.1"')}
          <div class="edit-row"><label>Stance</label><select name="stance">${stanceOptions}</select></div>
        </div>
      </div>
      <div class="panel">
        <h3>Career</h3>
        <div class="edit-grid">
          ${editFieldRow("Potential", "potential", f.potential, "number", 'min="1" max="99"')}
          ${editFieldRow("Physical Gift", "physical_gift", f.physical_gift, "number", 'min="1" max="99"')}
          ${editFieldRow("Momentum", "momentum", f.momentum, "number", 'min="-20" max="20"')}
          ${editFieldRow("Popularity", "popularity", f.popularity, "number", 'min="1" max="99"')}
          ${editFieldRow("Prime Start Age", "prime_start_age", f.prime_start_age, "number")}
          ${editFieldRow("Prime End Age", "prime_end_age", f.prime_end_age, "number")}
          ${editFieldRow("Archetype", "archetype", f.archetype || "", "text")}
          <div class="edit-row"><label>Status</label><select name="status">${statusOptions}</select></div>
        </div>
      </div>
      <div class="panel">
        <h3>Record</h3>
        <div class="edit-grid">
          ${RECORD_EDIT_FIELDS.map(name => editFieldRow(name.replace(/_/g, " "), name, f[name], "number", 'min="0"')).join("")}
        </div>
      </div>
      <div class="attr-groups">${groupsHtml}</div>
      <div class="panel">
        <button class="btn" type="submit">Save Changes</button>
        <button class="btn secondary" type="button" id="edit-cancel-btn">Cancel</button>
      </div>
    </form>
  `;
}

// ---------- Fight Tester ----------

async function renderFightTester() {
  const slot = currentSlot();
  if (!slot) { location.hash = "#/"; return; }

  const fighters = await api(`/api/saves/${slot}/fighters?sort=name`);
  const grouped = {};
  fighters.forEach(f => { (grouped[f.weight_class] ||= []).push(f); });

  function optionsHtml(selectedId) {
    return Object.entries(grouped).map(([division, list]) => `
      <optgroup label="${division}">
        ${list.map(f => `<option value="${f.id}" ${f.id === selectedId ? "selected" : ""}>
          ${f.name}${f.nickname ? ' "' + f.nickname + '"' : ""} (${f.record})
        </option>`).join("")}
      </optgroup>
    `).join("");
  }

  app.innerHTML = `
    <div class="panel">
      <h2>Fight Tester</h2>
      <div class="toolbar">
        <select id="ft-a">${optionsHtml(fighters[0]?.id)}</select>
        <span style="color:var(--text-dim); font-weight:700;">VS</span>
        <select id="ft-b">${optionsHtml(fighters[1]?.id)}</select>
        <select id="ft-rounds">
          <option value="3">3 Rounds</option>
          <option value="5">5 Rounds (Title)</option>
        </select>
      </div>
      <div class="toolbar">
        <button class="btn" id="ft-sim-one">Simulate Fight</button>
        <input type="number" id="ft-n" value="1000" min="10" max="5000" style="width:90px;">
        <button class="btn secondary" id="ft-sim-many">Simulate N Times</button>
      </div>
    </div>
    <div id="ft-results"></div>
  `;

  document.getElementById("ft-sim-one").addEventListener("click", () => runFightTest(slot, false));
  document.getElementById("ft-sim-many").addEventListener("click", () => runFightTest(slot, true));
}

function _ftParams() {
  return {
    fighter_a_id: parseInt(document.getElementById("ft-a").value, 10),
    fighter_b_id: parseInt(document.getElementById("ft-b").value, 10),
    rounds: parseInt(document.getElementById("ft-rounds").value, 10),
  };
}

async function runFightTest(slot, batch) {
  const results = document.getElementById("ft-results");
  const params = _ftParams();
  if (params.fighter_a_id === params.fighter_b_id) {
    results.innerHTML = `<div class="error-state">Pick two different fighters.</div>`;
    return;
  }

  if (batch) {
    const n = parseInt(document.getElementById("ft-n").value, 10) || 1000;
    results.innerHTML = `<div class="empty-state">Simulating ${n} fights...</div>`;
    try {
      const r = await api(`/api/saves/${slot}/fight-test/batch`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...params, n }),
      });
      results.innerHTML = renderBatchResult(r);
    } catch (err) {
      results.innerHTML = `<div class="error-state">Error: ${err.message}</div>`;
    }
  } else {
    results.innerHTML = `<div class="empty-state">Simulating...</div>`;
    try {
      const r = await api(`/api/saves/${slot}/fight-test`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      results.innerHTML = renderSingleResult(r);
    } catch (err) {
      results.innerHTML = `<div class="error-state">Error: ${err.message}</div>`;
    }
  }
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60), s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function statsTableHtml(r) {
  const a = r.fighter_a, b = r.fighter_b;
  const rows = [
    ["Sig. Strikes", `${a.stats.sig_strikes_landed}/${a.stats.sig_strikes_attempted}`,
     `${b.stats.sig_strikes_landed}/${b.stats.sig_strikes_attempted}`],
    ["Takedowns", `${a.stats.takedowns_landed}/${a.stats.takedowns_attempted}`,
     `${b.stats.takedowns_landed}/${b.stats.takedowns_attempted}`],
    ["Control Time", formatTime(a.stats.control_seconds), formatTime(b.stats.control_seconds)],
    ["Knockdowns", a.stats.knockdowns, b.stats.knockdowns],
    ["Sub Attempts", a.stats.sub_attempts, b.stats.sub_attempts],
  ];
  return `
    <table class="stats-table">
      <thead><tr><th>${a.name}</th><th></th><th>${b.name}</th></tr></thead>
      <tbody>
        ${rows.map(([label, av, bv]) => `<tr><td>${av}</td><td class="stat-label">${label}</td><td>${bv}</td></tr>`).join("")}
      </tbody>
    </table>
  `;
}

function scorecardHtml(sc) {
  return `
    <div class="scorecard">
      <span class="badge">Judges: ${sc.judges.map(j => j[0] + "-" + j[1]).join(" | ")}</span>
      <span class="badge">Effectiveness ${sc.eff_a} - ${sc.eff_b}</span>
    </div>
  `;
}

function renderSingleResult(r) {
  const winnerLine = r.winner_name
    ? `<strong>${r.winner_name}</strong> wins by ${r.method_detail} &middot; Round ${r.round}, ${r.time}`
    : `Draw &middot; ${r.method_detail}`;

  const roundsHtml = r.play_by_play.map((lines, i) => `
    <div class="panel">
      <h3>Round ${i + 1}</h3>
      <div class="pbp">${lines.map(l => `<p>${l}</p>`).join("")}</div>
      ${r.scorecards[i] ? scorecardHtml(r.scorecards[i]) : ""}
    </div>
  `).join("");

  return `
    <div class="panel">
      <h2>${winnerLine}</h2>
      ${statsTableHtml(r)}
    </div>
    ${roundsHtml}
  `;
}

function methodBreakdown(methods, n) {
  const order = ["KO", "TKO", "SUB", "DEC", "DRAW"];
  return order.filter(m => methods[m]).map(m => `${m}: ${methods[m]} (${(methods[m] / n * 100).toFixed(1)}%)`).join(" &middot; ")
    || "&mdash;";
}

function renderBatchResult(r) {
  return `
    <div class="panel">
      <h2>${r.n} Simulations</h2>
      <table class="stats-table">
        <thead><tr><th>${r.fighter_a_name}</th><th></th><th>${r.fighter_b_name}</th></tr></thead>
        <tbody>
          <tr><td>${r.win_pct_a}%</td><td class="stat-label">Win Rate</td><td>${r.win_pct_b}%</td></tr>
          <tr><td colspan="3" style="text-align:center; color:var(--text-dim); padding-top:8px;">
            Draws: ${r.draws} (${r.draw_pct}%)
          </td></tr>
          <tr><td>${methodBreakdown(r.methods_a, r.n)}</td><td class="stat-label">Methods</td>
              <td>${methodBreakdown(r.methods_b, r.n)}</td></tr>
        </tbody>
      </table>
      <p class="meta" style="color:var(--text-dim); margin-top:10px;">
        Average fight length: ${formatTime(r.avg_fight_seconds)}
      </p>
    </div>
  `;
}

// ---------- Events ----------

async function renderEventsList() {
  const slot = currentSlot();
  if (!slot) { location.hash = "#/"; return; }
  const events = await api(`/api/saves/${slot}/events`);

  app.innerHTML = `
    <div class="panel">
      <h2>Events</h2>
      <div class="save-list">
        ${events.length ? events.map(e => `
          <div class="save-row" data-event-id="${e.id}" style="cursor:pointer;">
            <div>
              <div><strong>${e.name}</strong></div>
              <div class="meta">${e.event_date} ${e.venue ? "&middot; " + e.venue : ""}
                &middot; ${e.bouts_completed || 0}/${e.bout_count} bouts simmed</div>
            </div>
            <span class="badge">${e.status}</span>
          </div>
        `).join("") : `<div class="empty-state">No events yet. Create one below.</div>`}
      </div>
    </div>
    <div class="panel">
      <h2>Create Event</h2>
      <form class="create-save" id="create-event-form">
        <input type="text" name="name" placeholder="Event name" required>
        <input type="date" name="event_date" required>
        <input type="text" name="venue" placeholder="Venue (optional)">
        <button class="btn" type="submit">Create</button>
      </form>
    </div>
  `;

  app.querySelectorAll("[data-event-id]").forEach(row => {
    row.addEventListener("click", () => { location.hash = `#/events/${row.dataset.eventId}`; });
  });

  document.getElementById("create-event-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const name = form.name.value.trim();
    const event_date = form.event_date.value;
    const venue = form.venue.value.trim() || null;
    if (!name || !event_date) return;
    try {
      const ev = await api(`/api/saves/${slot}/events`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, event_date, venue }),
      });
      location.hash = `#/events/${ev.id}`;
    } catch (err) {
      alert(err.message);
    }
  });
}

function boutRowHtml(b) {
  const badges = [];
  if (b.is_title_fight) badges.push(`<span class="badge title-badge">${b.is_interim_title_fight ? "Interim Title" : "Title Fight"}</span>`);
  if (b.is_number_one_contender) badges.push(`<span class="badge">#1 Contender</span>`);

  const resultHtml = b.status === "Completed" ? `
    <div class="bout-result">
      <strong>${b.winner_id ? (b.winner_id === b.fighter_a_id ? b.fighter_a_name : b.fighter_b_name) : "Draw"}</strong>
      wins by ${b.method_detail} &middot; R${b.result_round} ${b.result_time}
      <button class="btn secondary btn-sm" data-toggle-pbp="${b.id}">View Play-by-play</button>
      <div class="pbp-container" id="pbp-${b.id}" style="display:none;"></div>
    </div>
  ` : `
    <div class="bout-actions">
      <button class="btn btn-sm" data-sim-bout="${b.id}">Sim Fight</button>
      <button class="btn secondary btn-sm" data-remove-bout="${b.id}">Remove</button>
    </div>
  `;

  return `
    <div class="bout-row">
      <div class="bout-fighters">
        <span>${b.fighter_a_name} (${b.fighter_a_wins}-${b.fighter_a_losses}-${b.fighter_a_draws})</span>
        <span class="vs">vs</span>
        <span>${b.fighter_b_name} (${b.fighter_b_wins}-${b.fighter_b_losses}-${b.fighter_b_draws})</span>
      </div>
      <div class="bout-meta">
        <span class="badge">${b.weight_class}</span>
        <span class="badge">${b.rounds} Rds</span>
        ${badges.join("")}
      </div>
      ${resultHtml}
    </div>
  `;
}

function renderBoutPlayByPlay(bout) {
  if (!bout.play_by_play) return "";
  const statsHtml = statsTableHtml({ fighter_a: bout.stats.fighter_a, fighter_b: bout.stats.fighter_b });
  const roundsHtml = bout.play_by_play.map((lines, i) => `
    <div class="pbp-round">
      <h4>Round ${i + 1}</h4>
      <div class="pbp">${lines.map(l => `<p>${l}</p>`).join("")}</div>
      ${bout.scorecards[i] ? scorecardHtml(bout.scorecards[i]) : ""}
    </div>
  `).join("");
  return statsHtml + roundsHtml;
}

async function renderEventDetail(eventId) {
  const slot = currentSlot();
  if (!slot) { location.hash = "#/"; return; }
  const [ev, fighters] = await Promise.all([
    api(`/api/saves/${slot}/events/${eventId}`),
    api(`/api/saves/${slot}/fighters?sort=name`),
  ]);

  const grouped = {};
  fighters.forEach(f => { (grouped[f.weight_class] ||= []).push(f); });
  const fighterOptionsHtml = Object.entries(grouped).map(([division, list]) => `
    <optgroup label="${division}">
      ${list.map(f => `<option value="${f.id}">${f.name}${f.nickname ? ' "' + f.nickname + '"' : ""} (${f.record})</option>`).join("")}
    </optgroup>
  `).join("");

  const prelims = ev.bouts.filter(b => b.card_segment === "prelim");
  const mainCard = ev.bouts.filter(b => b.card_segment === "main");
  const hasScheduled = ev.bouts.some(b => b.status === "Scheduled");

  app.innerHTML = `
    <div class="panel">
      <a href="#/events" class="badge">&larr; Back to Events</a>
      <h1 style="margin-top:14px;">${ev.name}</h1>
      <div class="meta-line">${ev.event_date} ${ev.venue ? "&middot; " + ev.venue : ""} &middot; <span class="badge">${ev.status}</span></div>
      ${hasScheduled ? `<button class="btn" id="sim-card-btn" style="margin-top:12px;">Sim Entire Card</button>` : ""}
    </div>

    <div class="panel">
      <h2>Main Card</h2>
      ${mainCard.length ? mainCard.map(boutRowHtml).join("") : `<div class="empty-state">No main card bouts yet.</div>`}
    </div>
    <div class="panel">
      <h2>Prelims</h2>
      ${prelims.length ? prelims.map(boutRowHtml).join("") : `<div class="empty-state">No prelim bouts yet.</div>`}
    </div>

    <div class="panel">
      <h2>Book a Bout</h2>
      <form id="add-bout-form" class="add-bout-form">
        <div class="toolbar">
          <select name="fighter_a_id" required>${fighterOptionsHtml}</select>
          <span style="color:var(--text-dim); font-weight:700;">VS</span>
          <select name="fighter_b_id" required>${fighterOptionsHtml}</select>
        </div>
        <div class="toolbar">
          <select name="card_segment">
            <option value="main">Main Card</option>
            <option value="prelim">Prelims</option>
          </select>
          <select name="rounds">
            <option value="3">3 Rounds</option>
            <option value="5">5 Rounds (Title)</option>
          </select>
          <label><input type="checkbox" name="is_title_fight" id="bk-title"> Title Fight</label>
          <label><input type="checkbox" name="is_interim_title_fight" id="bk-interim" disabled> Interim</label>
          <label><input type="checkbox" name="is_number_one_contender"> #1 Contender Fight</label>
        </div>
        <button class="btn" type="submit">Add to Card</button>
      </form>
    </div>
  `;

  document.getElementById("bk-title").addEventListener("change", (e) => {
    const interim = document.getElementById("bk-interim");
    interim.disabled = !e.target.checked;
    if (!e.target.checked) interim.checked = false;
  });

  document.getElementById("sim-card-btn")?.addEventListener("click", async (e) => {
    e.target.disabled = true;
    e.target.textContent = "Simulating...";
    try {
      await api(`/api/saves/${slot}/events/${eventId}/sim`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}),
      });
      await renderEventDetail(eventId);
    } catch (err) {
      alert(err.message);
    }
  });

  app.querySelectorAll("[data-sim-bout]").forEach(btn => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      btn.textContent = "Simulating...";
      try {
        await api(`/api/saves/${slot}/bouts/${btn.dataset.simBout}/sim`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}),
        });
        await renderEventDetail(eventId);
      } catch (err) {
        alert(err.message);
        btn.disabled = false;
        btn.textContent = "Sim Fight";
      }
    });
  });

  app.querySelectorAll("[data-remove-bout]").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm("Remove this bout from the card?")) return;
      try {
        await api(`/api/saves/${slot}/events/${eventId}/bouts/${btn.dataset.removeBout}`, { method: "DELETE" });
        await renderEventDetail(eventId);
      } catch (err) {
        alert(err.message);
      }
    });
  });

  app.querySelectorAll("[data-toggle-pbp]").forEach(btn => {
    btn.addEventListener("click", () => {
      const boutId = btn.dataset.togglePbp;
      const container = document.getElementById(`pbp-${boutId}`);
      if (container.style.display === "none") {
        if (!container.dataset.loaded) {
          const bout = ev.bouts.find(b => String(b.id) === String(boutId));
          container.innerHTML = renderBoutPlayByPlay(bout);
          container.dataset.loaded = "1";
        }
        container.style.display = "block";
        btn.textContent = "Hide Play-by-play";
      } else {
        container.style.display = "none";
        btn.textContent = "View Play-by-play";
      }
    });
  });

  document.getElementById("add-bout-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const fighter_a_id = parseInt(form.fighter_a_id.value, 10);
    const fighter_b_id = parseInt(form.fighter_b_id.value, 10);
    if (fighter_a_id === fighter_b_id) { alert("Pick two different fighters."); return; }
    const body = {
      fighter_a_id, fighter_b_id,
      rounds: parseInt(form.rounds.value, 10),
      card_segment: form.card_segment.value,
      is_title_fight: form.is_title_fight.checked,
      is_interim_title_fight: form.is_interim_title_fight.checked,
      is_number_one_contender: form.is_number_one_contender.checked,
    };
    try {
      await api(`/api/saves/${slot}/events/${eventId}/bouts`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      await renderEventDetail(eventId);
    } catch (err) {
      alert(err.message);
    }
  });
}

// ---------- Rankings ----------

function championCardHtml(champ, label) {
  if (!champ) return `<div class="champion-card empty">${label}: Vacant</div>`;
  return `
    <div class="champion-card">
      <div class="champion-label">${label}</div>
      <a href="#/fighter/${champ.id}" class="champion-name">${champ.name}</a>
      <div class="meta">${champ.wins}-${champ.losses}-${champ.draws}</div>
    </div>
  `;
}

function renderRankingsList(rk, weightClass) {
  return `
    <div class="panel">
      <h2>${weightClass}</h2>
      <div class="champions-row">
        ${championCardHtml(rk.champion, "Champion")}
        ${rk.interim_champion ? championCardHtml(rk.interim_champion, "Interim Champion") : ""}
      </div>
      ${rk.contenders.length ? `
        <table class="stats-table rankings-table">
          <thead><tr><th>#</th><th>Fighter</th><th>Record</th><th>Points</th></tr></thead>
          <tbody>
            ${rk.contenders.map(c => `
              <tr>
                <td>${c.rank}</td>
                <td><a href="#/fighter/${c.fighter.id}">${c.fighter.name}</a></td>
                <td>${c.fighter.wins}-${c.fighter.losses}-${c.fighter.draws}</td>
                <td>${c.points}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      ` : `<div class="empty-state">No ranked contenders yet -- sim some events!</div>`}
    </div>
  `;
}

async function renderRankings() {
  const slot = currentSlot();
  if (!slot) { location.hash = "#/"; return; }
  const divisions = await api(`/api/saves/${slot}/divisions`);

  app.innerHTML = `
    <div class="panel">
      <h2>Rankings</h2>
      <div class="toolbar">
        <select id="rk-division">
          ${divisions.map(d => `<option value="${d.weight_class}|${d.gender}">${d.weight_class}</option>`).join("")}
        </select>
      </div>
    </div>
    <div id="rk-results"></div>
  `;

  const sel = document.getElementById("rk-division");
  async function load() {
    const [wc, gender] = sel.value.split("|");
    const rk = await api(`/api/saves/${slot}/rankings/${encodeURIComponent(wc)}?gender=${gender}`);
    document.getElementById("rk-results").innerHTML = renderRankingsList(rk, wc);
  }
  sel.addEventListener("change", load);
  if (divisions.length) await load();
  else document.getElementById("rk-results").innerHTML = `<div class="empty-state">No active fighters yet.</div>`;
}

// ---------- Calendar / Year in Review ----------

function renderCalendarSummary(summary) {
  const lines = [`<div class="meta-line">Advanced ${summary.weeks_advanced} week(s): ${summary.from} &rarr; ${summary.to}</div>`];

  if (summary.retirements.length) {
    lines.push(`<h4>Retirements</h4><ul>${summary.retirements.map(r =>
      `<li><a href="#/fighter/${r.id}">${r.name}</a></li>`).join("")}</ul>`);
  }
  if (summary.training_injuries.length) {
    lines.push(`<h4>Training Injuries</h4><ul>${summary.training_injuries.map(i =>
      `<li><a href="#/fighter/${i.id}">${i.name}</a> &mdash; ${i.description} (out ${i.weeks}w, back ${i.return_date})</li>`).join("")}</ul>`);
  }
  if (summary.recoveries.length) {
    lines.push(`<h4>Recovered from Injury</h4><ul>${summary.recoveries.map(r =>
      `<li><a href="#/fighter/${r.id}">${r.name}</a></li>`).join("")}</ul>`);
  }
  if (summary.new_prospects.length) {
    lines.push(`<h4>New Prospects (${summary.new_prospects.length})</h4><ul>${summary.new_prospects.map(p =>
      `<li><a href="#/fighter/${p.id}">${p.name}</a> &mdash; ${p.weight_class} (Potential ${p.potential})</li>`).join("")}</ul>`);
  }
  if (!summary.retirements.length && !summary.training_injuries.length
      && !summary.recoveries.length && !summary.new_prospects.length) {
    lines.push(`<div class="empty-state">Quiet stretch &mdash; nothing notable happened.</div>`);
  }
  return `<div class="panel">${lines.join("")}</div>`;
}

function renderAwardsHtml(yearAwards) {
  const foty = yearAwards.fighter_of_the_year;
  const fotyHtml = foty ? `
    <li><a href="#/fighter/${foty.id}">${foty.name}</a> &mdash; ${foty.weight_class},
      ${foty.wins_this_year}-${foty.losses_this_year} this year
      ${foty.won_title_this_year ? "&middot; won a title" : ""}</li>
  ` : `<li class="award-none">No award given.</li>`;

  function finishAwardLi(award) {
    if (!award) return `<li class="award-none">No award given.</li>`;
    return `<li><strong>${award.winner_name}</strong> def. ${award.loser_name}
      &mdash; ${award.event_name}, ${award.event_date} (R${award.round} ${award.time})</li>`;
  }

  return `
    <h3>${yearAwards.year} Awards</h3>
    <ul>
      <li class="award-category">Fighter of the Year</li>
      ${fotyHtml}
      <li class="award-category">Knockout of the Year</li>
      ${finishAwardLi(yearAwards.ko_of_the_year)}
      <li class="award-category">Submission of the Year</li>
      ${finishAwardLi(yearAwards.submission_of_the_year)}
      <li class="award-category">Fight of the Year</li>
      ${finishAwardLi(yearAwards.fight_of_the_year)}
    </ul>
  `;
}

function renderYearReviewHtml(review) {
  const titleHtml = review.title_changes.length ? `
    <ul>${review.title_changes.map(t => `
      <li>${t.event_date}: <strong>${t.winner_name}</strong> defeated ${t.loser_name} for the
        ${t.is_interim ? "Interim " : ""}${t.weight_class} title (${t.method_detail})</li>
    `).join("")}</ul>
  ` : `<div class="empty-state">No title changes this year.</div>`;

  const breakoutHtml = review.breakout_prospects.length ? `
    <ul>${review.breakout_prospects.map(p => `
      <li><a href="#/fighter/${p.id}">${p.name}</a> &mdash; ${p.weight_class}, ${p.wins_this_year} wins, age ${p.age}</li>
    `).join("")}</ul>
  ` : `<div class="empty-state">No standout breakout prospects this year.</div>`;

  const retirementsHtml = review.retirements.length ? `
    <ul>${review.retirements.map(r => `
      <li><a href="#/fighter/${r.id}">${r.name}</a> &mdash; ${r.weight_class}, retired at ${r.record} (${r.retired_date})</li>
    `).join("")}</ul>
  ` : `<div class="empty-state">No retirements this year.</div>`;

  return `
    <h3>${review.year} Title Changes</h3>
    ${titleHtml}
    <h3>Breakout Prospects</h3>
    ${breakoutHtml}
    <h3>Retirements</h3>
    ${retirementsHtml}
  `;
}

async function renderCalendar() {
  const slot = currentSlot();
  if (!slot) { location.hash = "#/"; return; }
  const state = await api(`/api/saves/${slot}/calendar`);
  const currentYear = new Date(state.current_date).getFullYear();

  app.innerHTML = `
    <div class="panel">
      <h2>Calendar</h2>
      <div class="calendar-date" id="cal-date-display">${state.current_date}</div>
      <div class="toolbar" style="margin-top:14px;">
        <button class="btn" data-weeks="1">Advance 1 Week</button>
        <button class="btn" data-weeks="4">Advance 1 Month</button>
        <button class="btn" data-weeks="52">Advance 1 Year</button>
        <input type="number" id="cal-weeks" value="1" min="1" max="520" style="width:80px;">
        <button class="btn secondary" id="cal-advance-custom">Advance Custom</button>
      </div>
    </div>
    <div id="cal-summary"></div>
    <div class="panel">
      <h2>Year in Review</h2>
      <div class="toolbar">
        <input type="number" id="yr-input" placeholder="Year" value="${currentYear}">
        <button class="btn secondary" id="yr-view-btn">View</button>
      </div>
      <div id="yr-results"></div>
    </div>
  `;

  async function advance(weeks) {
    const summaryEl = document.getElementById("cal-summary");
    summaryEl.innerHTML = `<div class="empty-state">Advancing ${weeks} week(s)...</div>`;
    try {
      const summary = await api(`/api/saves/${slot}/calendar/advance`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weeks }),
      });
      summaryEl.innerHTML = renderCalendarSummary(summary);
      document.getElementById("cal-date-display").textContent = summary.to;
    } catch (err) {
      summaryEl.innerHTML = `<div class="error-state">${err.message}</div>`;
    }
  }

  document.querySelectorAll("[data-weeks]").forEach(btn => {
    btn.addEventListener("click", () => advance(parseInt(btn.dataset.weeks, 10)));
  });
  document.getElementById("cal-advance-custom").addEventListener("click", () => {
    advance(parseInt(document.getElementById("cal-weeks").value, 10) || 1);
  });

  document.getElementById("yr-view-btn").addEventListener("click", async () => {
    const year = parseInt(document.getElementById("yr-input").value, 10);
    const resultsEl = document.getElementById("yr-results");
    resultsEl.innerHTML = `<div class="empty-state">Loading...</div>`;
    try {
      const [review, yearAwards] = await Promise.all([
        api(`/api/saves/${slot}/year-review/${year}`),
        api(`/api/saves/${slot}/awards/${year}`),
      ]);
      resultsEl.innerHTML = renderAwardsHtml(yearAwards) + renderYearReviewHtml(review);
    } catch (err) {
      resultsEl.innerHTML = `<div class="error-state">${err.message}</div>`;
    }
  });
}

// ---------- Hall of Records ----------

async function renderHallOfRecords() {
  const slot = currentSlot();
  if (!slot) { location.hash = "#/"; return; }
  const retired = await api(`/api/saves/${slot}/fighters?status=Retired&sort=name`);

  app.innerHTML = `
    <div class="panel">
      <h2>Hall of Records</h2>
      <p class="meta" style="color:var(--text-dim);">${retired.length} retired fighter(s)</p>
    </div>
    <div class="roster-grid">
      ${retired.length ? retired.map(f => `
        <div class="fighter-card" data-id="${f.id}">
          <div class="portrait-wrap-holder">${portraitTag(slot, f.id, f.name, "portrait-wrap")}</div>
          <div class="info">
            <div class="name">${f.name}</div>
            ${f.nickname ? `<div class="nickname">"${f.nickname}"</div>` : ""}
            <div class="sub">${f.weight_class} &middot; ${f.record}</div>
            <div class="sub">Retired ${f.retired_date || ""}</div>
          </div>
        </div>
      `).join("") : `<div class="empty-state">No one has retired yet.</div>`}
    </div>
  `;

  app.querySelectorAll("[data-id]").forEach(card => {
    card.addEventListener("click", () => { location.hash = `#/fighter/${card.dataset.id}`; });
  });
}

// ---------- Compare ----------

function compareAttrRow(label, valueA, valueB) {
  const aClass = valueA > valueB ? "compare-better" : valueA < valueB ? "compare-worse" : "";
  const bClass = valueB > valueA ? "compare-better" : valueB < valueA ? "compare-worse" : "";
  return `
    <div class="compare-row">
      <div class="compare-value ${aClass}">${valueA}</div>
      <div class="compare-label">${label}</div>
      <div class="compare-value ${bClass}">${valueB}</div>
    </div>
  `;
}

async function renderCompare() {
  const slot = currentSlot();
  if (!slot) { location.hash = "#/"; return; }
  const fighters = await api(`/api/saves/${slot}/fighters?sort=name`);

  const grouped = {};
  fighters.forEach(f => { (grouped[f.weight_class] ||= []).push(f); });
  function optionsHtml(selectedId) {
    return Object.entries(grouped).map(([division, list]) => `
      <optgroup label="${division}">
        ${list.map(f => `<option value="${f.id}" ${f.id === selectedId ? "selected" : ""}>${f.name} (${f.record})</option>`).join("")}
      </optgroup>
    `).join("");
  }

  app.innerHTML = `
    <div class="panel">
      <h2>Compare Fighters</h2>
      <div class="toolbar">
        <select id="cmp-a">${optionsHtml(fighters[0]?.id)}</select>
        <span style="color:var(--text-dim); font-weight:700;">VS</span>
        <select id="cmp-b">${optionsHtml(fighters[1]?.id)}</select>
        <button class="btn" id="cmp-btn">Compare</button>
      </div>
    </div>
    <div id="cmp-results"></div>
  `;

  document.getElementById("cmp-btn").addEventListener("click", async () => {
    const aId = parseInt(document.getElementById("cmp-a").value, 10);
    const bId = parseInt(document.getElementById("cmp-b").value, 10);
    const resultsEl = document.getElementById("cmp-results");
    if (aId === bId) {
      resultsEl.innerHTML = `<div class="error-state">Pick two different fighters.</div>`;
      return;
    }
    resultsEl.innerHTML = `<div class="empty-state">Loading...</div>`;
    const [a, b] = await Promise.all([
      api(`/api/saves/${slot}/fighters/${aId}`),
      api(`/api/saves/${slot}/fighters/${bId}`),
    ]);

    const groupsHtml = Object.entries(ATTR_GROUPS).map(([groupName, attrs]) => `
      <div class="attr-group">
        <h3>${groupName}</h3>
        ${attrs.map(attr => compareAttrRow(ATTR_LABELS[attr], a[attr], b[attr])).join("")}
      </div>
    `).join("");

    resultsEl.innerHTML = `
      <div class="panel">
        <div class="compare-header">
          <div class="compare-fighter">
            ${portraitTag(slot, a.id, a.name, "compare-portrait")}
            <h3><a href="#/fighter/${a.id}">${a.name}</a></h3>
            <div class="meta-line">${a.weight_class} &middot; ${a.record} &middot; age ${a.age}</div>
          </div>
          <div class="compare-fighter">
            ${portraitTag(slot, b.id, b.name, "compare-portrait")}
            <h3><a href="#/fighter/${b.id}">${b.name}</a></h3>
            <div class="meta-line">${b.weight_class} &middot; ${b.record} &middot; age ${b.age}</div>
          </div>
        </div>
        <div class="compare-groups">${groupsHtml}</div>
      </div>
    `;
  });
}

// ---------- Free Agents ----------

function freeAgentRowsHtml(agents, startRank) {
  return agents.map((f, i) => `
    <tr>
      <td>${startRank + i}</td>
      <td><a href="#/fighter/${f.id}">${f.name}</a>${f.nickname ? ` <span class="nickname">"${f.nickname}"</span>` : ""}</td>
      <td>${f.weight_class}</td>
      <td>${f.record}</td>
      <td>${f.age}</td>
      <td>${f.promotion}</td>
      <td>${f.fa_score}</td>
      <td><button class="btn btn-sm" data-sign-id="${f.id}" data-sign-name="${f.name}">Sign</button></td>
    </tr>
  `).join("");
}

async function renderFreeAgents(showAll = false) {
  const slot = currentSlot();
  if (!slot) { location.hash = "#/"; return; }
  const agents = await api(`/api/saves/${slot}/free-agents${showAll ? "?limit=0" : ""}`);
  const top20 = agents.slice(0, 20);
  const rest = agents.slice(20);

  app.innerHTML = `
    <div class="panel">
      <h2>Top Free Agents</h2>
      <p class="meta" style="color:var(--text-dim); font-size:13px;">
        The best available fighters outside the UFC, ranked by the game's scouting judgment.
        Their records keep evolving as they fight off-screen.
      </p>
      ${top20.length ? `
        <table class="stats-table rankings-table">
          <thead><tr><th>#</th><th>Fighter</th><th>Division</th><th>Record</th><th>Age</th><th>Promotion</th><th>Score</th><th></th></tr></thead>
          <tbody>${freeAgentRowsHtml(top20, 1)}</tbody>
        </table>
      ` : `<div class="empty-state">No free agents available right now.</div>`}
    </div>
    ${showAll && rest.length ? `
      <div class="panel">
        <h2>Rest of the Available Pool (${rest.length})</h2>
        <table class="stats-table rankings-table">
          <thead><tr><th>#</th><th>Fighter</th><th>Division</th><th>Record</th><th>Age</th><th>Promotion</th><th>Score</th><th></th></tr></thead>
          <tbody>${freeAgentRowsHtml(rest, 21)}</tbody>
        </table>
      </div>
    ` : ""}
    ${!showAll && top20.length === 20 ? `
      <div class="panel" style="text-align:center;">
        <button class="btn secondary" id="fa-show-all">Show the Entire Available Pool</button>
      </div>
    ` : ""}
  `;

  document.getElementById("fa-show-all")?.addEventListener("click", () => renderFreeAgents(true));

  app.querySelectorAll("[data-sign-id]").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm(`Sign ${btn.dataset.signName} to the UFC?`)) return;
      try {
        await api(`/api/saves/${slot}/fighters/${btn.dataset.signId}/sign`, { method: "POST" });
        await renderFreeAgents(showAll);
      } catch (err) { alert(err.message); }
    });
  });
}
