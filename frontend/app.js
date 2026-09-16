/* Balise — logique front (vanilla). API en relatif /api (nginx proxie vers le back). */
"use strict";

const API = { base: location.origin.includes(":8080") ? "http://localhost:8000" : "" };

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html !== undefined) n.innerHTML = html;
  return n;
};

/* ═══════════ ÉTAT ═══════════ */
const S = {
  profile: "famille",
  dept: null, deptSkipped: false,
  sits: [], age: null,
  falc: false,
  msgs: [], seq: 0,
  history: [],
};

const SITUATIONS = ["Psychique", "Autisme / TND", "Handicap rare", "Moteur", "Sensoriel", "Polyhandicap", "Maladie rare"];
const AGES = ["Enfant", "Adolescent", "Adulte"];

const SUGG = {
  famille: [
    "Comment constituer un premier dossier MDPH ?",
    "Mon enfant attend une place en IME, que faire en attendant ?",
    "Quels droits pour un aidant familial ?",
    "Qui contacter près de chez moi pour être accompagné ?",
    "C'est quoi un PCPE, et qui peut y accéder ?",
  ],
  pro: [
    "Quelle différence entre un SAVS et un SAMSAH ?",
    "Comment mobiliser une Communauté 360 pour une situation sans solution ?",
    "Quel rôle pour un DAC dans un parcours complexe ?",
    "Où trouver une place en ESMS pour une situation complexe ?",
    "Comment orienter vers une PCO pour un TND avant 7 ans ?",
  ],
};

/* Regex données personnelles — reprise de la maquette */
const PERSONAL = /(\b0[1-9](?:[ .-]?\d{2}){4}\b)|(\b\d{1,2}[\/.-]\d{1,2}[\/.-](19|20)\d{2}\b)|(\b\d{13,15}\b)|[\w.+-]+@[\w-]+\.[a-z]{2,}|(mon (fils|fille|mari|épouse|frère|sœur|soeur)\s+[A-ZÉÈÀÂÎÔÛ][a-zéèêàâîïôûü]+)|(s'appelle\s+[A-ZÉÈÀÂÎÔÛ])|(\bné(e)? le\b)|(numéro de sécurité sociale)/;

const DEPTS = [["01","Ain"],["02","Aisne"],["03","Allier"],["04","Alpes-de-Haute-Provence"],["05","Hautes-Alpes"],["06","Alpes-Maritimes"],["07","Ardèche"],["08","Ardennes"],["09","Ariège"],["10","Aube"],["11","Aude"],["12","Aveyron"],["13","Bouches-du-Rhône"],["14","Calvados"],["15","Cantal"],["16","Charente"],["17","Charente-Maritime"],["18","Cher"],["19","Corrèze"],["2A","Corse-du-Sud"],["2B","Haute-Corse"],["21","Côte-d'Or"],["22","Côtes-d'Armor"],["23","Creuse"],["24","Dordogne"],["25","Doubs"],["26","Drôme"],["27","Eure"],["28","Eure-et-Loir"],["29","Finistère"],["30","Gard"],["31","Haute-Garonne"],["32","Gers"],["33","Gironde"],["34","Hérault"],["35","Ille-et-Vilaine"],["36","Indre"],["37","Indre-et-Loire"],["38","Isère"],["39","Jura"],["40","Landes"],["41","Loir-et-Cher"],["42","Loire"],["43","Haute-Loire"],["44","Loire-Atlantique"],["45","Loiret"],["46","Lot"],["47","Lot-et-Garonne"],["48","Lozère"],["49","Maine-et-Loire"],["50","Manche"],["51","Marne"],["52","Haute-Marne"],["53","Mayenne"],["54","Meurthe-et-Moselle"],["55","Meuse"],["56","Morbihan"],["57","Moselle"],["58","Nièvre"],["59","Nord"],["60","Oise"],["61","Orne"],["62","Pas-de-Calais"],["63","Puy-de-Dôme"],["64","Pyrénées-Atlantiques"],["65","Hautes-Pyrénées"],["66","Pyrénées-Orientales"],["67","Bas-Rhin"],["68","Haut-Rhin"],["69","Rhône"],["70","Haute-Saône"],["71","Saône-et-Loire"],["72","Sarthe"],["73","Savoie"],["74","Haute-Savoie"],["75","Paris"],["76","Seine-Maritime"],["77","Seine-et-Marne"],["78","Yvelines"],["79","Deux-Sèvres"],["80","Somme"],["81","Tarn"],["82","Tarn-et-Garonne"],["83","Var"],["84","Vaucluse"],["85","Vendée"],["86","Vienne"],["87","Haute-Vienne"],["88","Vosges"],["89","Yonne"],["90","Territoire de Belfort"],["91","Essonne"],["92","Hauts-de-Seine"],["93","Seine-Saint-Denis"],["94","Val-de-Marne"],["95","Val-d'Oise"],["971","Guadeloupe"],["972","Martinique"],["973","Guyane"],["974","La Réunion"],["976","Mayotte"]].map(d => ({ code: d[0], nom: d[1] }));

/* ═══════════ RENDU MARKUP : citations + sigles ═══════════ */
function esc(s) { return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

function renderRich(text, glossary) {
  let html = esc(text);
  // citations [n] → exposant cliquable
  html = html.replace(/\[(\d+)\]/g, (m, n) => `<a class="cite-n" href="#src-${n}">[${n}]</a>`);
  // sigles du glossaire → bouton tooltip
  if (glossary) {
    for (const [sigle, def] of Object.entries(glossary)) {
      const re = new RegExp(`\\b(${sigle.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&")})\\b`, "g");
      html = html.replace(re, (m) =>
        `<button type="button" class="sigle-btn" data-def="${esc(def)}">${m}</button>`);
    }
  }
  return html;
}

/* ═══════════ ICONES ═══════════ */
const IC = {
  botAvatar: `<svg width="26" height="26" viewBox="0 0 32 32" aria-hidden="true" style="display:block;flex-shrink:0;margin-top:2px"><path d="M12.6 16.9a5 5 0 0 1 0-7.8" fill="none" stroke="var(--petrol-600)" stroke-width="2.6" stroke-linecap="round"/><path d="M19.4 16.9a5 5 0 0 0 0-7.8" fill="none" stroke="var(--petrol-600)" stroke-width="2.6" stroke-linecap="round"/><path d="M16 13.6V27" fill="none" stroke="var(--petrol-800)" stroke-width="2.8" stroke-linecap="round"/><circle cx="16" cy="11.4" r="3.1" fill="var(--petrol-800)"/></svg>`,
  shield: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>`,
  alert: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 9v4M12 17h.01"/><circle cx="12" cy="12" r="10"/></svg>`,
  arrow: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>`,
};

const SCOPE_TONE = { Local: "warm", Régional: "neutral", National: "green" };
const badge = (scope) => {
  const tone = SCOPE_TONE[scope] || "neutral";
  const bg = tone === "warm" ? "var(--warm-yellow-light);color:var(--warm-coral)" : tone === "green" ? "var(--green-50);color:var(--ink-800)" : "var(--bg-cream);color:var(--ink-700)";
  return `<span style="display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:600;background:${bg}">${esc(scope)}</span>`;
};

/* ═══════════ BULLES ═══════════ */
const log = $("#log");
const scrollLog = () => log.scrollTo({ top: log.scrollHeight });

function addMsg(node) { log.appendChild(node); scrollLog(); }

function userBubble(text, personal) {
  if (personal) {
    const t = el("div", "w-full flex gap-2.5 items-start bh-in");
    t.innerHTML = `<span class="text-[var(--petrol-600)] shrink-0 mt-0.5">${IC.shield}</span>
      <p class="m-0 text-[0.9em] leading-[1.55] text-[var(--ink-700)] bg-[var(--petrol-50)] border border-[var(--petrol-100)] rounded-2xl p-3.5">Vous venez d'écrire des informations personnelles. Elles restent en France : hébergement certifié <strong class="font-semibold text-[var(--ink-900)]">HDS</strong>, modèle d'IA français, <strong class="font-semibold text-[var(--ink-900)]">aucune conservation</strong> après la conversation, aucun entraînement sur vos échanges.</p>`;
    addMsg(t);
  }
  const b = el("div", "flex justify-end bh-in");
  const inner = el("div", "max-w-[82%] bg-[var(--petrol-100)] text-[var(--ink-900)] rounded-[18px_18px_5px_18px] px-[15px] py-[11px] leading-normal");
  inner.textContent = text;
  b.appendChild(inner);
  addMsg(b);
}

function typingBubble() {
  const b = el("div", "flex gap-3.5 w-full bh-in");
  b.innerHTML = `${IC.botAvatar}<div class="flex-1 min-w-0">
    <div class="flex items-center gap-2 text-[var(--ink-500)] text-[0.92em] pt-1">
      <span class="inline-flex gap-1" aria-hidden="true"><span class="bh-dot w-[7px] h-[7px] rounded-full bg-[var(--petrol-600)]"></span><span class="bh-dot w-[7px] h-[7px] rounded-full bg-[var(--petrol-600)]" style="animation-delay:.15s"></span><span class="bh-dot w-[7px] h-[7px] rounded-full bg-[var(--petrol-600)]" style="animation-delay:.3s"></span></span>
      Je cherche dans les guides des centres ressources…
    </div></div>`;
  addMsg(b);
  return b;
}

function botBubble(ans, question) {
  const b = el("div", "flex gap-3.5 w-full bh-in");
  const body = el("div", "flex-1 min-w-0");

  let inner = "";
  if (ans.unknown) {
    inner += `<div class="flex gap-2.5 items-start bg-[var(--warm-yellow-light)] rounded-2xl p-3 mb-3.5">
      <span class="text-[var(--warm-coral)] shrink-0 mt-0.5">${IC.alert}</span>
      <p class="m-0 text-[0.92em] leading-normal text-[var(--ink-800)]">Je ne sais pas répondre de façon fiable. Voici vers qui vous tourner.</p>
    </div>`;
  }
  for (const p of ans.paras || []) {
    inner += `<p class="m-0 mb-3 text-[1.02em] leading-[1.68] text-[var(--ink-800)]">${renderRich(p, ans.glossary)}</p>`;
  }
  if (ans.steps && ans.steps.length) {
    inner += `<ol class="m-1 mb-3.5 p-0 list-none flex flex-col gap-0.5">` + ans.steps.map((s, i) =>
      `<li class="flex gap-3 items-start py-2.5 border-t border-[var(--ink-100)]">
        <span class="font-mono text-[0.8em] font-semibold text-[var(--petrol-600)] shrink-0 pt-0.5">${i + 1}</span>
        <span class="text-[0.97em] leading-[1.55] text-[var(--ink-800)]"><strong class="font-semibold text-[var(--ink-900)]">${esc(s.t)}</strong> — ${esc(s.d)}</span>
      </li>`).join("") + `</ol>`;
  }
  if (ans.contacts && ans.contacts.length) {
    inner += `<p class="m-0 mb-2 text-[0.76em] font-semibold tracking-[0.1em] uppercase text-[var(--brand-ink)]">Qui contacter ?</p>
    <div class="grid gap-2.5 mb-3.5" style="grid-template-columns:repeat(auto-fit,minmax(210px,1fr))">` + ans.contacts.map(c =>
      `<div class="border border-[var(--ink-100)] bg-[var(--bg-card)] rounded-2xl p-3 flex flex-col gap-1.5">
        <div class="flex items-center gap-2 justify-between"><span class="text-[0.94em] font-semibold text-[var(--ink-900)]">${esc(c.nom)}</span>${badge(c.scope)}</div>
        <span class="text-[0.87em] leading-[1.45] text-[var(--ink-500)]">${esc(c.role)}</span>
        ${c.url ? `<a href="${esc(c.url)}" target="_blank" rel="noopener" class="text-[0.85em] font-medium">Voir le lien ↗</a>` : ""}
      </div>`).join("") + `</div>`;
  }
  if (ans.sources && ans.sources.length) {
    inner += `<details open class="border-t border-dashed border-[var(--ink-200)] pt-3 mt-1">
      <summary class="cursor-pointer text-[0.76em] font-semibold tracking-[0.1em] uppercase text-[var(--ink-500)]">Sources (${ans.sources.length})</summary>
      <ul class="mt-2.5 mb-0 p-0 list-none flex flex-col gap-2">` + ans.sources.map(s =>
      `<li id="src-${s.n}" class="flex gap-2.5 items-start">
        <span class="text-[0.87em] leading-[1.45]"><a href="${esc(s.url)}" target="_blank" rel="noopener" class="font-medium">${esc(s.doc)}</a>
        <span class="text-[var(--ink-500)]"> · ${esc(s.centre)}</span></span>
      </li>`).join("") + `</ul></details>`;
  }
  // feedback
  inner += `<div class="flex items-center gap-2 flex-wrap mt-3.5">
    <span class="feedback-label text-[0.8em] text-[var(--ink-500)]">Cette réponse vous aide ?</span>
    <button type="button" class="fb-up inline-flex items-center gap-1.5 h-8 px-3 rounded-full border border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-700)] text-[0.82em] cursor-pointer">Utile</button>
    <button type="button" class="fb-down inline-flex items-center gap-1.5 h-8 px-3 rounded-full border border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-700)] text-[0.82em] cursor-pointer">Pas utile</button>
    <span class="flex-1"></span>
    <button type="button" class="simplify-btn inline-flex items-center gap-1.5 h-8 px-3 rounded-full border border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-700)] text-[0.82em] cursor-pointer">Reformuler plus simplement</button>
  </div>`;

  body.innerHTML = inner;
  b.innerHTML = IC.botAvatar;
  b.appendChild(body);
  addMsg(b);

  // sigles tooltips
  body.querySelectorAll(".sigle-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      body.querySelectorAll(".sigle-tip").forEach(t => t.remove());
      if (btn.dataset.open === "1") { btn.dataset.open = "0"; return; }
      body.querySelectorAll(".sigle-btn").forEach(x => x.dataset.open = "0");
      const tip = el("span", "sigle-tip");
      tip.textContent = btn.dataset.def;
      btn.appendChild(tip);
      btn.dataset.open = "1";
    });
  });
  // feedback
  const lbl = body.querySelector(".feedback-label");
  const up = body.querySelector(".fb-up"), down = body.querySelector(".fb-down");
  up.addEventListener("click", () => { up.dataset.on = up.dataset.on === "1" ? "0" : "1"; if (up.dataset.on === "1") { up.classList.add("bh-toggle"); down.classList.remove("bh-toggle"); lbl.textContent = "Merci, c'est noté."; } else { up.classList.remove("bh-toggle"); lbl.textContent = "Cette réponse vous aide ?"; } });
  down.addEventListener("click", () => { down.dataset.on = down.dataset.on === "1" ? "0" : "1"; if (down.dataset.on === "1") { down.classList.add("bh-toggle"); up.classList.remove("bh-toggle"); lbl.textContent = "Merci, nous allons revoir cette réponse."; } else { down.classList.remove("bh-toggle"); lbl.textContent = "Cette réponse vous aide ?"; } });
  // simplification FALC
  body.querySelector(".simplify-btn").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true; btn.textContent = "Reformulation…";
    const ans2 = await postChat("/api/chat/simplify", { question, falc: true, history: [] });
    btn.disabled = false; btn.textContent = "Version détaillée";
    if (ans2) {
      // remplace paras/steps par la version simple (les sources restent)
      const simple = renderAnswerSimple(ans2);
      body.querySelectorAll("p, ol").forEach(n => n.remove());
      body.insertAdjacentHTML("afterbegin", simple);
    }
  });
  return b;
}

function renderAnswerSimple(ans) {
  let inner = "";
  if (ans.unknown) inner += `<p class="m-0 mb-3 text-[1.02em] text-[var(--ink-800)]">Je ne sais pas répondre de façon fiable à cette question.</p>`;
  for (const p of ans.paras || []) inner += `<p class="m-0 mb-3 text-[1.02em] leading-[1.68] text-[var(--ink-800)]">${renderRich(p, ans.glossary)}</p>`;
  return inner;
}

/* ═══════════ ETAT VIDE (suggestions) ═══════════ */
function renderWelcome() {
  log.innerHTML = "";
  const w = el("div", "flex flex-col gap-2.5");
  w.id = "welcome";
  w.innerHTML = `<p class="m-0 mb-1 text-[0.76em] font-semibold tracking-[0.1em] uppercase text-[var(--ink-500)] text-center">Par exemple</p>` +
    SUGG[S.profile].map(label =>
      `<button type="button" class="sugg flex items-center justify-between gap-3.5 w-full py-3 px-1 border-0 border-b border-[var(--ink-100)] bg-transparent text-left cursor-pointer hover:bg-[var(--petrol-50)]">
        <span class="text-[0.97em] leading-tight text-[var(--ink-800)]">${esc(label)}</span>
        <span class="text-[var(--petrol-600)] shrink-0 inline-flex">${IC.arrow}</span>
      </button>`).join("");
  addMsg(w);
  w.querySelectorAll(".sugg").forEach(b => b.addEventListener("click", () => ask(b.textContent.trim())));
}

/* ═══════════ APPEL API ═══════════ */
async function postChat(path, extra) {
  const payload = {
    question: S.pendingQ || extra.question,
    profile: S.profile,
    dept: S.dept,
    deptSkipped: S.deptSkipped,
    situations: S.sits,
    age: S.age,
    falc: S.falc,
    history: S.history.slice(-4),
  };
  Object.assign(payload, extra || {});
  try {
    const r = await fetch(API.base + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

async function ask(question) {
  if (!question || S.busy) return;
  S.busy = true;
  $("#q").value = "";
  const welcome = $("#welcome");
  if (welcome) welcome.remove();
  userBubble(question, PERSONAL.test(question));
  const t = typingBubble();
  const ans = await postChat("/api/chat", { question });
  t.remove();
  if (!ans) {
    const err = el("div", "flex gap-3.5 w-full bh-in");
    err.innerHTML = IC.botAvatar + `<div class="flex-1"><div class="flex gap-2.5 items-start bg-[var(--warm-yellow-light)] rounded-2xl p-3"><span class="text-[var(--warm-coral)] shrink-0 mt-0.5">${IC.alert}</span><p class="m-0 text-[0.92em] text-[var(--ink-800)]">Désolé, la recherche a échoué. Réessayez dans un moment.</p></div></div>`;
    addMsg(err);
  } else {
    botBubble(ans, question);
    S.history.push({ role: "user", content: question });
    S.history.push({ role: "assistant", content: (ans.paras || []).join(" ") });
  }
  S.busy = false;
  $("#reset-btn").classList.remove("hidden");
}

/* ═══════════ SOURCES (section basse) ═══════════ */
async function loadSources() {
  try {
    const r = await fetch(API.base + "/api/sources");
    const d = await r.json();
    $("#sources-grid").innerHTML = (d.sources || []).map(s =>
      `<a href="${esc(s.url)}" target="_blank" rel="noopener" class="block bg-[var(--bg-card)] border border-[var(--ink-100)] rounded-[20px] p-4 flex flex-col gap-1.5 no-underline hover:border-[var(--petrol-600)]">
        <span class="flex items-center justify-between gap-2"><span class="text-[0.94em] font-semibold text-[var(--ink-900)]">${esc(s.nom)}</span>${badge(s.type)}</span>
        <span class="text-[0.86em] leading-[1.45] text-[var(--ink-500)]">${esc(s.desc)}</span>
      </a>`).join("");
  } catch { /* silencieux : la section reste vide */ }
}

/* ═══════════ SIDEBAR / CONTROLS ═══════════ */
function renderSidebar() {
  // profil
  $("#profile-group").innerHTML = [
    ["famille", "Un proche, une famille"], ["pro", "Un professionnel"],
  ].map(([v, l]) => `<button type="button" role="radio" aria-checked="${S.profile === v}" data-v="${v}" class="bh-toggle w-full text-left px-3 py-2.5 rounded-xl border text-[0.86em] cursor-pointer ${S.profile === v ? "border-[var(--petrol-600)] bg-[var(--petrol-100)] text-[var(--brand-ink)] font-medium" : "border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-700)]"}">${l}</button>`).join("");
  $("#profile-group").querySelectorAll("button").forEach(b => b.addEventListener("click", () => { S.profile = b.dataset.v; $("#q").placeholder = S.profile === "pro" ? "Ex. : quelle orientation pour un adulte sans solution après 20 ans ?" : "Écrivez votre question, avec vos mots…"; renderSidebar(); if (!S.msgs.length) renderWelcome(); }));
  // situations
  $("#situations").innerHTML = SITUATIONS.map(x =>
    `<button type="button" aria-pressed="${S.sits.includes(x)}" data-x="${esc(x)}" class="h-[30px] px-2.5 rounded-full border text-[0.78em] cursor-pointer ${S.sits.includes(x) ? "border-[var(--petrol-600)] bg-[var(--petrol-100)] text-[var(--brand-ink)] font-medium" : "border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-700)]"}">${esc(x)}</button>`).join("");
  $("#situations").querySelectorAll("button").forEach(b => b.addEventListener("click", () => { const x = b.dataset.x; S.sits = S.sits.includes(x) ? S.sits.filter(y => y !== x) : [...S.sits, x]; renderSidebar(); }));
  // âges
  $("#ages").innerHTML = AGES.map(x =>
    `<button type="button" aria-pressed="${S.age === x}" data-x="${esc(x)}" class="h-[30px] px-2.5 rounded-full border text-[0.78em] cursor-pointer ${S.age === x ? "border-[var(--petrol-600)] bg-[var(--petrol-100)] text-[var(--brand-ink)] font-medium" : "border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-700)]"}">${esc(x)}</button>`).join("");
  $("#ages").querySelectorAll("button").forEach(b => b.addEventListener("click", () => { S.age = S.age === b.dataset.x ? null : b.dataset.x; renderSidebar(); }));
  // dept
  const db = $("#dept-btn");
  db.textContent = S.dept ? `${S.dept.code} · ${S.dept.nom}` : (S.deptSkipped ? "Non précisé" : "Choisir");
  db.className = `w-full text-left px-3 py-2.5 rounded-xl border text-[0.86em] cursor-pointer ${S.dept ? "border-[var(--petrol-600)] bg-[var(--petrol-100)] text-[var(--brand-ink)] font-medium" : "border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-500)]"}`;
  $("#dept-clear").classList.toggle("hidden", !S.dept);
}

/* modale dept */
function renderDeptList(q) {
  const needle = (q || "").trim().toLowerCase();
  $("#dept-list").innerHTML = DEPTS
    .filter(d => !needle || d.nom.toLowerCase().includes(needle) || d.code.startsWith(needle))
    .slice(0, 15)
    .map(d => `<li><button type="button" role="option" data-c="${d.code}" data-n="${esc(d.nom)}" class="flex items-center gap-3 w-full text-left px-3 py-[11px] rounded-[14px] border-0 cursor-pointer bg-transparent hover:bg-[var(--petrol-50)]"><span class="font-mono text-[0.85em] text-[var(--ink-500)] w-[30px] shrink-0">${d.code}</span><span class="text-[0.97em] text-[var(--ink-900)]">${esc(d.nom)}</span></button></li>`).join("");
  $("#dept-list").querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
    S.dept = { code: b.dataset.c, nom: b.dataset.n }; S.deptSkipped = false;
    $("#dept-modal").classList.add("hidden");
    renderSidebar();
  }));
}

/* ═══════════ INIT ═══════════ */
$("#ask-form").addEventListener("submit", e => { e.preventDefault(); ask($("#q").value.trim()); });
$("#reset-btn").addEventListener("click", () => { S.history = []; S.msgs = []; $("#reset-btn").classList.add("hidden"); renderWelcome(); });
$("#falc-btn").addEventListener("click", e => { S.falc = !S.falc; e.currentTarget.setAttribute("aria-pressed", String(S.falc)); e.currentTarget.classList.toggle("bh-toggle", S.falc); });
$("#theme-btn").addEventListener("click", e => {
  const h = document.documentElement;
  const dark = h.dataset.theme === "dark";
  h.dataset.theme = dark ? "light" : "dark";
  $("#icon-moon").classList.toggle("hidden", !dark);
  $("#icon-sun").classList.toggle("hidden", dark);
  e.currentTarget.setAttribute("aria-label", dark ? "Passer en thème sombre" : "Passer en thème clair");
});
const SCALES = ["s", "m", "l"];
let scaleIdx = 0;
$("#scale-up").addEventListener("click", () => { scaleIdx = Math.min(2, scaleIdx + 1); document.documentElement.dataset.scale = SCALES[scaleIdx]; });
$("#scale-down").addEventListener("click", () => { scaleIdx = Math.max(0, scaleIdx - 1); document.documentElement.dataset.scale = SCALES[scaleIdx]; });
$("#dept-btn").addEventListener("click", () => { $("#dept-modal").classList.remove("hidden"); renderDeptList(""); });
$("#dept-close").addEventListener("click", () => $("#dept-modal").classList.add("hidden"));
$("#dept-skip").addEventListener("click", () => { S.deptSkipped = true; S.dept = null; $("#dept-modal").classList.add("hidden"); renderSidebar(); });
$("#dept-q").addEventListener("input", e => renderDeptList(e.target.value));
$("#dept-modal").addEventListener("click", e => { if (e.target.id === "dept-modal") $("#dept-modal").classList.add("hidden"); });

renderWelcome();
renderSidebar();
loadSources();