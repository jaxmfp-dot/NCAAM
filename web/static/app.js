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
    topnav.appendChild(el(`<a href="#/fight-tester">Fight Tester</a>`));
    topnav.appendChild(el(`<a href="#/">Switch Save</a>`));
  }
}

async function router() {
  renderNav();
  const hash = location.hash || "#/";
  const fighterMatch = hash.match(/^#\/fighter\/(\d+)$/);
  try {
    if (hash === "#/" || hash === "") {
      await renderSaveSelect();
    } else if (hash === "#/roster") {
      await renderRoster();
    } else if (hash === "#/fight-tester") {
      await renderFightTester();
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
            <button class="btn" data-slot="${s.slot}" data-name="${s.name}">Load</button>
          </div>
        `).join("") : `<div class="empty-state">No saves yet. Create one below.</div>`}
      </div>
    </div>
    <div class="panel">
      <h2>Create New Universe</h2>
      <form class="create-save">
        <input type="text" name="name" placeholder="Universe name" required>
        <select name="mode">
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
    </div>
    <div id="roster-grid" class="roster-grid"><div class="empty-state">Loading...</div></div>
  `;

  const grid = document.getElementById("roster-grid");
  const divisionSel = document.getElementById("f-division");
  const searchInput = document.getElementById("f-search");
  const sortSel = document.getElementById("f-sort");

  let searchTimer;
  async function load() {
    const params = new URLSearchParams();
    if (divisionSel.value) {
      const [wc, gender] = divisionSel.value.split("|");
      params.set("division", wc);
      params.set("gender", gender);
    }
    if (searchInput.value.trim()) params.set("search", searchInput.value.trim());
    params.set("sort", sortSel.value);

    const fighters = await api(`/api/saves/${slot}/fighters?${params.toString()}`);
    grid.innerHTML = fighters.length ? fighters.map(f => `
      <div class="fighter-card" data-id="${f.id}">
        <div class="portrait-wrap-holder">${portraitTag(slot, f.id, f.name, "portrait-wrap")}</div>
        <div class="info">
          <div class="name">${f.name}</div>
          ${f.nickname ? `<div class="nickname">"${f.nickname}"</div>` : ""}
          <div class="sub">${f.weight_class} &middot; ${f.record} &middot; age ${f.age}</div>
        </div>
      </div>
    `).join("") : `<div class="empty-state">No fighters match those filters.</div>`;

    grid.querySelectorAll(".fighter-card").forEach(card => {
      card.addEventListener("click", () => { location.hash = `#/fighter/${card.dataset.id}`; });
    });
  }

  divisionSel.addEventListener("change", load);
  sortSel.addEventListener("change", load);
  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(load, 250);
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

async function renderFighterProfile(id) {
  const slot = currentSlot();
  if (!slot) { location.hash = "#/"; return; }
  const f = await api(`/api/saves/${slot}/fighters/${id}`);

  const groupsHtml = Object.entries(ATTR_GROUPS).map(([groupName, attrs]) => `
    <div class="attr-group">
      <h3>${groupName}</h3>
      ${attrs.map(a => attrRow(ATTR_LABELS[a], f[a])).join("")}
    </div>
  `).join("");

  app.innerHTML = `
    <div class="panel">
      <a href="#/roster" class="badge">&larr; Back to Roster</a>
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
            <span class="badge">${f.archetype || "Unclassified"}</span>
            <span class="badge">Potential ${f.potential}</span>
            <span class="badge">Popularity ${f.popularity}</span>
            <span class="badge">${f.status}</span>
          </div>
        </div>
      </div>
      <div class="attr-groups">${groupsHtml}</div>
    </div>
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
