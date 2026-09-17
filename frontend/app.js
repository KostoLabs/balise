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
const SITUATIONS_FALC = ["Maladie psychique", "Autisme", "Handicap rare", "Le corps qui bouge mal", "Voir ou entendre mal", "Plusieurs handicaps", "Maladie rare"];
const AGES = ["Enfant", "Adolescent", "Adulte"];

/* ═══════════ TEXTES STANDARD / FALC (du design v2) ═══════════ */
const T_STD = {
  title: "Comment puis-je vous aider ?",
  examples: "Par exemple",
  searching: "Je cherche dans les guides des centres ressources…",
  placeholder: "Écrivez votre question, avec vos mots…",
  placeholderPro: "Ex. : quelle orientation pour un adulte sans solution après 20 ans ?",
  privacy: ["Hébergement HDS en France · IA française · aucune conservation de vos échanges"],
  trust: ["Vous venez d'écrire des informations personnelles. Elles restent en France : hébergement certifié HDS, modèle d'IA français, aucune conservation après la conversation, aucun entraînement sur vos échanges."],
  sideIntro: "Vous pouvez poser votre question sans rien préciser. Ces indications affinent les réponses.",
  sideProfile: "Vous êtes",
  profFam: "Un proche, une famille",
  profPro: "Un professionnel",
  sideDept: "Département",
  sideSituation: "Situation",
  sideAge: "Âge",
  newConv: "Nouvelle conversation",
  contacts: "Qui contacter ?",
  unknownBanner: "Je ne sais pas répondre de façon fiable avec les sources disponibles.",
  fbUp: "Utile", fbDown: "Pas utile",
  simplify: "Reformuler plus simplement", unsimplify: "Version détaillée",
  feedbackAsk: "Cette réponse vous aide ?",
  feedbackUp: "Merci, c'est noté.", feedbackDown: "Merci, nous allons revoir cette réponse.",
  srcTitle: "Les centres ressources sur lesquels je m'appuie",
  srcIntro: ["Uniquement leurs contenus publics : guides, fiches pratiques, annuaires, FAQ. Chaque réponse renvoie au document d'origine."],
  sitTitle: "Les situations couvertes",
  sitIntro: ["De l'enfance à l'âge adulte, quel que soit le type de handicap."],
  limitsTitle: "Ce que Balise ne fait pas",
  limits: ["Balise oriente : elle ne remplace ni un avis médical, ni un conseil juridique, ni une décision de MDPH. Vos échanges sont traités en France sur une infrastructure certifiée HDS, avec un modèle d'IA français, et ne sont pas conservés après la conversation."],
  deptTitle: "Votre département",
  deptHelp: "Facultatif — sert à proposer les bons interlocuteurs locaux.",
  deptSearch: "Rechercher par nom ou numéro",
  deptSkip: "Ne pas préciser",
  footLegal: "Mentions légales", footA11y: "Accessibilité", footData: "Hébergement & données",
};

const T_FALC = {
  title: "Comment puis-je vous aider ?",
  examples: "Vous pouvez demander :",
  searching: "Je cherche la réponse. Merci de patienter.",
  placeholder: "Écrivez votre question ici.",
  placeholderPro: "Écrivez votre question ici.",
  privacy: [
    "Vos messages restent en France.",
    "Notre ordinateur est agréé pour les données de santé.",
    "Nous utilisons une intelligence artificielle française.",
    "Nous ne gardons pas vos messages.",
  ],
  trust: [
    "Vous avez écrit des informations sur une personne.",
    "Ces informations restent en France.",
    "Nous ne les gardons pas.",
    "Personne d'autre ne les lit.",
  ],
  sideIntro: "Vous pouvez poser votre question tout de suite. Les cases ci-dessous sont utiles, mais pas obligatoires.",
  sideProfile: "Qui êtes-vous ?",
  profFam: "Un parent ou un proche",
  profPro: "Je travaille dans ce domaine",
  sideDept: "Où habitez-vous ?",
  sideSituation: "Quel handicap ?",
  sideAge: "Quel âge ?",
  newConv: "Recommencer",
  contacts: "Qui peut vous aider ?",
  unknownBanner: "Je ne connais pas la réponse dans les guides disponibles.",
  fbUp: "Oui", fbDown: "Non",
  simplify: "Réponse plus simple", unsimplify: "Réponse plus longue",
  feedbackAsk: "Cette réponse vous aide ?",
  feedbackUp: "Merci.", feedbackDown: "Merci. Nous allons corriger.",
  srcTitle: "D'où viennent mes réponses ?",
  srcIntro: [
    "Des centres qui s'y connaissent en handicap.",
    "Ces centres écrivent des guides pour tout le monde.",
    "Je lis ces guides pour vous répondre.",
    "Je vous dis toujours quel guide j'ai lu.",
  ],
  sitTitle: "De quoi je peux parler",
  sitIntro: [
    "Je parle de tous les handicaps.",
    "Je parle des enfants et des adultes.",
  ],
  limitsTitle: "Ce que je ne fais pas",
  limits: [
    "Je ne suis pas un médecin.",
    "Je ne suis pas un avocat.",
    "Je ne décide pas à la place de la MDPH.",
    "En cas de doute, appelez une personne.",
  ],
  deptTitle: "Où habitez-vous ?",
  deptHelp: "Vous pouvez ne pas répondre.",
  deptSearch: "Écrivez le nom ou le numéro",
  deptSkip: "Je ne veux pas le dire",
  footLegal: "Qui écrit ce site", footA11y: "Accessibilité", footData: "Vos informations",
};

/* ═══════════ SUGGESTIONS (std + falc) ═══════════ */
const SUGG = {
  famille: [
    { label: "Comment constituer un premier dossier MDPH ?", falc: "Comment faire mon premier dossier MDPH ?" },
    { label: "Mon enfant attend une place en IME, que faire en attendant ?", falc: "Mon enfant attend une place. Que faire ?" },
    { label: "Quels droits pour un aidant familial ?", falc: "J'aide un proche. Quels sont mes droits ?" },
    { label: "Qui contacter près de chez moi pour être accompagné ?", falc: "Qui peut m'aider près de chez moi ?" },
    { label: "C'est quoi un PCPE, et qui peut y accéder ?", falc: "C'est quoi un PCPE ?" },
  ],
  pro: [
    { label: "Quelle différence entre un SAVS et un SAMSAH ?", falc: "Quelle différence entre SAVS et SAMSAH ?" },
    { label: "Comment mobiliser une Communauté 360 pour une situation sans solution ?", falc: "Comment appeler la Communauté 360 ?" },
    { label: "Quel rôle pour un DAC dans un parcours complexe ?", falc: "À quoi sert un DAC ?" },
    { label: "Où trouver une place en ESMS pour une situation complexe ?", falc: "Où trouver une place près de chez moi ?" },
    { label: "Comment orienter vers une PCO pour un TND avant 7 ans ?", falc: "Comment orienter vers une PCO ?" },
  ],
};

/* Regex données personnelles — du design */
const PERSONAL = /(\b0[1-9](?:[ .-]?\d{2}){4}\b)|(\b\d{1,2}[\/.-]\d{1,2}[\/.-](19|20)\d{2}\b)|(\b\d{13,15}\b)|[\w.+-]+@[\w-]+\.[a-z]{2,}|(mon (fils|fille|mari|épouse|frère|sœur|soeur)\s+[A-ZÉÈÀÂÎÔÛ][a-zéèêàâîïôûü]+)|(s'appelle\s+[A-ZÉÈÀÂÎÔÛ])|(\bné(e)? le\b)|(numéro de sécurité sociale)/;

const DEPTS = [["01","Ain"],["02","Aisne"],["03","Allier"],["04","Alpes-de-Haute-Provence"],["05","Hautes-Alpes"],["06","Alpes-Maritimes"],["07","Ardèche"],["08","Ardennes"],["09","Ariège"],["10","Aube"],["11","Aude"],["12","Aveyron"],["13","Bouches-du-Rhône"],["14","Calvados"],["15","Cantal"],["16","Charente"],["17","Charente-Maritime"],["18","Cher"],["19","Corrèze"],["2A","Corse-du-Sud"],["2B","Haute-Corse"],["21","Côte-d'Or"],["22","Côtes-d'Armor"],["23","Creuse"],["24","Dordogne"],["25","Doubs"],["26","Drôme"],["27","Eure"],["28","Eure-et-Loir"],["29","Finistère"],["30","Gard"],["31","Haute-Garonne"],["32","Gers"],["33","Gironde"],["34","Hérault"],["35","Ille-et-Vilaine"],["36","Indre"],["37","Indre-et-Loire"],["38","Isère"],["39","Jura"],["40","Landes"],["41","Loir-et-Cher"],["42","Loire"],["43","Haute-Loire"],["44","Loire-Atlantique"],["45","Loiret"],["46","Lot"],["47","Lot-et-Garonne"],["48","Lozère"],["49","Maine-et-Loire"],["50","Manche"],["51","Marne"],["52","Haute-Marne"],["53","Mayenne"],["54","Meurthe-et-Moselle"],["55","Meuse"],["56","Morbihan"],["57","Moselle"],["58","Nièvre"],["59","Nord"],["60","Oise"],["61","Orne"],["62","Pas-de-Calais"],["63","Puy-de-Dôme"],["64","Pyrénées-Atlantiques"],["65","Hautes-Pyrénées"],["66","Pyrénées-Orientales"],["67","Bas-Rhin"],["68","Haut-Rhin"],["69","Rhône"],["70","Haute-Saône"],["71","Saône-et-Loire"],["72","Sarthe"],["73","Savoie"],["74","Haute-Savoie"],["75","Paris"],["76","Seine-Maritime"],["77","Seine-et-Marne"],["78","Yvelines"],["79","Deux-Sèvres"],["80","Somme"],["81","Tarn"],["82","Tarn-et-Garonne"],["83","Var"],["84","Vaucluse"],["85","Vendée"],["86","Vienne"],["87","Haute-Vienne"],["88","Vosges"],["89","Yonne"],["90","Territoire de Belfort"],["91","Essonne"],["92","Hauts-de-Seine"],["93","Seine-Saint-Denis"],["94","Val-de-Marne"],["95","Val-d'Oise"],["971","Guadeloupe"],["972","Martinique"],["973","Guyane"],["974","La Réunion"],["976","Mayotte"]].map(d => ({ code: d[0], nom: d[1] }));

/* ═══════════ PICTOS FALC (règles du design v2, jeu Lucide) ═══════════ */
const PICTOS = {
  stethoscope: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6 6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3"/><path d="M3 14v-2a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M15 13v2a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-1a2 2 0 0 0-2-2h-1"/></svg>`,
  school: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 10 12 5 2 10l10 5 10-5z"/><path d="M6 12v5c0 1.7 2.7 3 6 3s6-1.3 6-3v-5"/></svg>`,
  book: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`,
  alert: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>`,
  calendar: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>`,
  home: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/></svg>`,
  file: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M14 2v5h6"/></svg>`,
  chat: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
  check: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg>`,
  sprout: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 20h10"/><path d="M12 20c0-4.4-4-7-8-8 0 5.3 3.6 7.4 8 8z"/><path d="M12 20c0-4.4 4-7 8-8 0 5.3-3.6 7.4-8 8z"/></svg>`,
  lock: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`,
  users: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
  search: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>`,
  info: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>`,
};

const PICTO_RULES = [
  [/médecin|infirmier|soins|santé|hôpital|bilan/, "stethoscope"],
  [/école|classe|élève|scolaire/, "school"],
  [/avocat|juridique|\bloi\b|lire|\blis\b|\blus?\b|guides que/, "book"],
  [/ne sais pas|ne connais pas|fausse|\bfaux\b|difficile|rien ne va|attention|corriger/, "alert"],
  [/\bmois\b|délai|\btemps\b|patienter|attente|attend|\bâge\b|\bans\b|\bun an\b/, "calendar"],
  [/mdph|département|bureau du handicap|habitez/, "home"],
  [/dossier|formulaire|papier|écriv|remplit|document|lettre|\bguide\b|\bguides\b/, "file"],
  [/appelez|appel\b|numéro|0 800|téléphone|parle|répond|demand|question/, "chat"],
  [/droit|argent|payé|gratuit|décide|décision|suffit|accord/, "check"],
  [/repos|répit|souffler|travail/, "sprout"],
  [/france|gardons|informations|sécur|privé|personne d'autre/, "lock"],
  [/famille|proche|parent|enfant|personne|équipe|service|centre|aide|professionnel/, "users"],
  [/cherche|trouve|solution/, "search"],
];

function pickPicto(text) {
  const x = String(text).toLowerCase();
  for (const [re, name] of PICTO_RULES) if (re.test(x)) return name;
  return "info";
}
function picto(name, size) {
  const cls = size === "sm"
    ? "shrink-0 grid place-items-center w-7 h-7 rounded-[9px] bg-[var(--petrol-100)] text-[var(--petrol-800)] mt-px"
    : "shrink-0 grid place-items-center w-[34px] h-[34px] rounded-[11px] bg-[var(--petrol-100)] text-[var(--petrol-800)] mt-0.5";
  return `<span class="${cls}">${PICTOS[name] || PICTOS.info}</span>`;
}

/* ═══════════ OUTILS ═══════════ */
function esc(s) { return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
const T = () => S.falc ? T_FALC : T_STD;

const IC = {
  botAvatar: `<svg width="26" height="26" viewBox="0 0 32 32" aria-hidden="true" style="display:block;flex-shrink:0;margin-top:2px"><path d="M12.6 16.9a5 5 0 0 1 0-7.8" fill="none" stroke="var(--petrol-600)" stroke-width="2.6" stroke-linecap="round"/><path d="M19.4 16.9a5 5 0 0 0 0-7.8" fill="none" stroke="var(--petrol-600)" stroke-width="2.6" stroke-linecap="round"/><path d="M16 13.6V27" fill="none" stroke="var(--petrol-800)" stroke-width="2.8" stroke-linecap="round"/><circle cx="16" cy="11.4" r="3.1" fill="var(--petrol-800)"/></svg>`,
  shield: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>`,
  alert: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>`,
  arrow: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>`,
};

const SCOPE_TONE = { Local: "warm", "Régional": "neutral", National: "green" };
const badge = (scope) => {
  const tone = SCOPE_TONE[scope] || "neutral";
  const bg = tone === "warm" ? "var(--warm-yellow-light);color:var(--warm-coral)" : tone === "green" ? "var(--green-50);color:var(--ink-800)" : "var(--bg-cream);color:var(--ink-700)";
  return `<span style="display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:600;background:${bg}">${esc(scope)}</span>`;
};

/* ═══════════ RENDU TEXTE : citations + sigles (+ glose FALC) ═══════════ */
function renderRich(text, glossary) {
  let html = esc(text);
  html = html.replace(/\[(\d+)\]/g, (m, n) => `<a class="cite-n" href="#src-${n}">[${n}]</a>`);
  if (glossary) {
    for (const [sigle, def] of Object.entries(glossary)) {
      const re = new RegExp(`\\b(${sigle.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&")})\\b`, "g");
      html = html.replace(re, `<button type="button" class="sigle-btn" data-def="${esc(def)}">$1</button>`);
    }
  }
  return html;
}

/* ═══════════ BULLES ═══════════ */
const log = $("#log");
const scrollLog = () => log.scrollTo({ top: log.scrollHeight });
const addMsg = (node) => { log.appendChild(node); scrollLog(); };

function userBubble(text, personal) {
  if (personal) {
    const t = el("div", "w-full flex gap-2.5 items-start bh-in");
    const lines = T().trust.map(l => `<p class="m-0 ${S.falc ? "text-[1.02em] leading-[1.65] text-[var(--ink-800)]" : "text-[0.92em] leading-1.6 text-[var(--ink-700)]"}">${esc(l)}</p>`).join("");
    t.innerHTML = `<span class="text-[var(--petrol-600)] shrink-0 mt-0.5">${IC.shield}</span><div class="flex flex-col ${S.falc ? "gap-[5px]" : "gap-0"}">${lines}</div>`;
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
      ${esc(T().searching)}
    </div></div>`;
  addMsg(b);
  return b;
}

function botBubble(ans, question, falcView = S.falc, alternateAnswer = null) {
  const copy = falcView ? T_FALC : T_STD;
  const b = el("div", "flex gap-3.5 w-full bh-in");
  const body = el("div", "flex-1 min-w-0");
  let inner = "";

  if (ans.unknown) {
    inner += `<div class="flex gap-2.5 items-start bg-[var(--warm-yellow-light)] rounded-2xl p-3 mb-3.5">
      <span class="text-[var(--warm-coral)] shrink-0 mt-0.5">${IC.alert}</span>
      <p class="m-0 text-[0.94em] leading-[1.55] text-[var(--ink-800)]">${esc(copy.unknownBanner)}</p>
    </div>`;
  }

  for (const p of ans.paras || []) {
    if (falcView) {
      inner += `<div class="flex gap-3 items-start mb-3.5">${picto(pickPicto(p))}<p class="m-0 flex-1 min-w-0 text-[1.1em] leading-[1.75] text-[var(--ink-800)] text-left max-w-[46ch]">${renderRich(p, ans.glossary)}</p></div>`;
    } else {
      inner += `<p class="m-0 mb-3 text-[1.02em] leading-[1.68] text-[var(--ink-800)]">${renderRich(p, ans.glossary)}</p>`;
    }
  }

  if (ans.steps && ans.steps.length) {
    inner += `<ol class="m-1.5 mb-4 p-0 list-none flex flex-col gap-0.5">` + ans.steps.map((s, i) =>
      falcView
        ? `<li class="flex gap-3 items-start py-3 border-t border-[var(--ink-100)]">
            <span class="grid place-items-center w-7 h-7 shrink-0 rounded-full bg-[var(--petrol-100)] text-[var(--brand-ink)] font-mono text-[0.9em] font-semibold">${i + 1}</span>
            <span class="text-[1.05em] leading-[1.7] text-[var(--ink-800)] pt-0.5">${esc(s.d || s.t)}</span>
          </li>`
        : `<li class="flex gap-3 items-start py-2.5 border-t border-[var(--ink-100)]">
            <span class="font-mono text-[0.8em] font-semibold text-[var(--petrol-600)] shrink-0 pt-0.5">${i + 1}</span>
            <span class="text-[0.97em] leading-[1.55] text-[var(--ink-800)]"><strong class="font-semibold text-[var(--ink-900)]">${esc(s.t)}</strong> — ${esc(s.d)}</span>
          </li>`).join("") + `</ol>`;
  }

  if (ans.contacts && ans.contacts.length) {
    inner += `<p class="m-0 mb-2 ${falcView ? "text-[0.94em] font-semibold text-[var(--ink-900)]" : "text-[0.78em] font-semibold tracking-[0.1em] uppercase text-[var(--brand-ink)]"}">${esc(copy.contacts)}</p>
    <div class="grid gap-2.5 mb-3.5" style="grid-template-columns:repeat(auto-fit,minmax(210px,1fr))">` + ans.contacts.map(c =>
      `<div class="border border-[var(--ink-100)] bg-[var(--bg-card)] rounded-2xl p-[13px] px-[15px] flex flex-col gap-1.5">
        <div class="flex items-center gap-2 justify-between flex-wrap"><span class="text-[0.96em] font-semibold text-[var(--ink-900)]">${esc(c.nom)}</span>${badge(c.scope)}</div>
        <span class="text-[0.9em] leading-1.5 text-[var(--ink-700)]">${esc(c.role)}</span>
        ${c.url ? `<a href="${esc(c.url)}" target="_blank" rel="noopener" class="text-[0.88em] font-medium">Voir le lien ↗</a>` : ""}
      </div>`).join("") + `</div>`;
  }

  if (ans.sources && ans.sources.length) {
    inner += `<details open class="border-t border-dashed border-[var(--ink-200)] pt-3 mt-1">
      <summary class="cursor-pointer ${falcView ? "text-[0.9em] font-semibold text-[var(--ink-700)]" : "text-[0.8em] font-semibold tracking-[0.06em] text-[var(--ink-500)]"}">${falcView ? "Les guides que j'ai lus" : "SOURCES (" + ans.sources.length + ")"}</summary>
      <ul class="mt-2.5 mb-0 p-0 list-none flex flex-col gap-2.25">` + ans.sources.map(s =>
      `<li id="src-${s.n}" class="flex gap-2.5 items-start">
        <span class="text-[0.89em] leading-1.5"><a href="${esc(s.url)}" target="_blank" rel="noopener" class="font-medium">${esc(s.doc)}</a>
        <span class="text-[var(--ink-500)]"> · ${esc(s.centre)}</span></span>
      </li>`).join("") + `</ul></details>`;
  }

  const fb = falcView;
  inner += `<div class="flex items-center gap-2 flex-wrap mt-3.5">
    <span class="feedback-label text-[${fb ? "0.86" : "0.82"}em] text-[var(--ink-500)]">${esc(copy.feedbackAsk)}</span>
    <button type="button" class="fb-up inline-flex items-center gap-1.5 h-[34px] px-3 rounded-full border border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-700)] text-[0.84em] cursor-pointer">${esc(copy.fbUp)}</button>
    <button type="button" class="fb-down inline-flex items-center gap-1.5 h-[34px] px-3 rounded-full border border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-700)] text-[0.84em] cursor-pointer">${esc(copy.fbDown)}</button>
    <span class="flex-1"></span>
    <button type="button" class="simplify-btn inline-flex items-center gap-1.5 h-[34px] px-3 rounded-full border border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-700)] text-[0.84em] cursor-pointer">${esc(fb ? copy.unsimplify : copy.simplify)}</button>
  </div>`;
  if (ans.followup) {
    inner += `<button type="button" class="followup-btn mt-3 w-full text-left flex items-center gap-2.5 px-4 py-3 rounded-2xl border border-[var(--petrol-100)] bg-[var(--petrol-50)] text-[0.95em] text-[var(--ink-800)] cursor-pointer hover:border-[var(--petrol-600)]"><span class="text-[var(--petrol-600)] shrink-0" aria-hidden="true">↳</span><span>${esc(ans.followup)}</span></button>`;
  }

  body.innerHTML = inner;
  b.innerHTML = IC.botAvatar;
  b.appendChild(body);
  addMsg(b);

  body.querySelectorAll(".sigle-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      body.querySelectorAll(".sigle-tip").forEach(t => t.remove());
      if (btn.dataset.open === "1") { btn.dataset.open = "0"; return; }
      body.querySelectorAll(".sigle-btn").forEach(x => x.dataset.open = "0");
      const tip = el("span", "sigle-tip");
      tip.textContent = btn.dataset.def;
      btn.insertAdjacentElement("afterend", tip);
      btn.dataset.open = "1";
    });
  });
  const lbl = body.querySelector(".feedback-label");
  const up = body.querySelector(".fb-up"), down = body.querySelector(".fb-down");
  const setFb = (kind) => {
    const on = kind === "up" ? up : down, off = kind === "up" ? down : up;
    const was = on.dataset.on === "1";
    up.dataset.on = "0"; down.dataset.on = "0";
    on.classList.remove("bh-toggle"); off.classList.remove("bh-toggle");
    if (!was) { on.dataset.on = "1"; on.classList.add("bh-toggle"); lbl.textContent = kind === "up" ? copy.feedbackUp : copy.feedbackDown; }
    else lbl.textContent = copy.feedbackAsk;
  };
  up.addEventListener("click", () => setFb("up"));
  down.addEventListener("click", () => setFb("down"));
  body.querySelector(".simplify-btn").addEventListener("click", async (e) => {
    if (alternateAnswer) {
      b.remove();
      botBubble(alternateAnswer, question, !falcView, ans);
      return;
    }
    const btn = e.currentTarget;
    btn.disabled = true; btn.textContent = "…";
    const path = falcView ? "/api/chat" : "/api/chat/simplify";
    const ans2 = await postChat(path, {
      question,
      falc: !falcView,
      history: [],
    });
    if (ans2) {
      b.remove();
      botBubble(ans2, question, !falcView, ans);
    } else {
      btn.disabled = false;
      btn.textContent = falcView ? copy.unsimplify : copy.simplify;
    }
  });
  const fu = body.querySelector(".followup-btn");
  if (fu) fu.addEventListener("click", () => ask(fu.textContent.trim()));
  return b;
}

/* ═══════════ ÉTAT VIDE (suggestions) ═══════════ */
function renderWelcome() {
  log.innerHTML = "";
  const w = el("div", "flex flex-col gap-2.5");
  w.id = "welcome";
  const sugg = SUGG[S.profile];
  w.innerHTML = `<p class="m-0 mb-1 ${S.falc ? "text-[1.02em] font-semibold text-[var(--ink-900)] text-left" : "text-[0.78em] font-semibold tracking-[0.1em] uppercase text-[var(--ink-500)] text-center"}">${esc(T().examples)}</p>` +
    sugg.map((x, i) => {
      const label = S.falc ? x.falc : x.label;
      return S.falc
        ? `<button type="button" data-i="${i}" class="sugg flex items-center justify-between gap-3.5 w-full py-[15px] px-3.5 border border-[var(--ink-200)] rounded-[14px] mb-0.5 bg-transparent text-left cursor-pointer hover:border-[var(--petrol-600)]"><span class="flex items-center gap-3">${picto(pickPicto(label), "sm")}<span class="text-[1.05em] leading-1.5 text-[var(--ink-900)]">${esc(label)}</span></span></button>`
        : `<button type="button" data-i="${i}" class="sugg flex items-center justify-between gap-3.5 w-full py-3 px-1 border-0 border-b border-[var(--ink-100)] bg-transparent text-left cursor-pointer hover:bg-[var(--petrol-50)]"><span class="text-[0.99em] leading-1.4 text-[var(--ink-800)]">${esc(label)}</span><span class="text-[var(--petrol-600)] shrink-0 inline-flex">${IC.arrow}</span></button>`;
    }).join("");
  addMsg(w);
  w.querySelectorAll(".sugg").forEach(b => b.addEventListener("click", () => ask(sugg[b.dataset.i][S.falc ? "falc" : "label"])));
}

/* ═══════════ APPEL API ═══════════ */
async function postChat(path, extra) {
  const payload = {
    question: extra.question,
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
  }
  S.busy = false;
  $("#reset-btn").classList.remove("hidden");
}

/* ═══════════ SECTION BASSE ═══════════ */
async function loadSources() {
  try {
    const r = await fetch(API.base + "/api/sources");
    const d = await r.json();
    $("#sources-grid").innerHTML = (d.sources || []).map(s =>
      `<a href="${esc(s.url)}" target="_blank" rel="noopener" class="block bg-[var(--bg-card)] border border-[var(--ink-100)] rounded-[18px] p-4 flex flex-col gap-2 no-underline hover:border-[var(--petrol-600)]">
        <div class="flex items-start justify-between gap-2">
          <span class="flex-1 min-w-0 overflow-wrap-anywhere text-[0.95em] font-semibold leading-[1.3] text-[var(--ink-900)]">${esc(s.nom)}</span>
          <span class="shrink-0">${badge(s.type)}</span>
        </div>
        <span class="text-[0.87em] leading-1.5 text-[var(--ink-500)]">${esc(s.desc)}</span>
      </a>`).join("");
  } catch { /* silencieux */ }
}

function renderIntroBlocks() {
  const t = T();
  const mk = (arr, withPicto) => arr.map(x => {
    const row = S.falc && withPicto
      ? `<div class="flex gap-[11px] items-start">${picto(pickPicto(x), "sm")}<p class="m-0 text-[1.05em] leading-[1.7] text-[var(--ink-800)] text-left">${esc(x)}</p></div>`
      : `<p class="m-0 text-[0.97em] leading-[1.55] text-[var(--ink-500)]">${esc(x)}</p>`;
    return row;
  }).join(S.falc ? `<div class="h-[7px]"></div>` : "");
  $("#src-title").textContent = t.srcTitle;
  $("#src-intro").innerHTML = mk(t.srcIntro, true);
  $("#sit-title").textContent = t.sitTitle;
  $("#sit-intro").innerHTML = mk(t.sitIntro, true);
  $("#limits-title").textContent = t.limitsTitle;
  $("#limits-list").innerHTML = mk(t.limits, true);
  $("#title").textContent = t.title;
  $("#side-intro").textContent = t.sideIntro;
  $("#side-profile-label").textContent = t.sideProfile;
  $("#side-dept-label").textContent = t.sideDept;
  $("#side-sit-label").textContent = t.sideSituation;
  $("#side-age-label").textContent = t.sideAge;
  $("#dept-title").textContent = t.deptTitle;
  $("#dept-help").textContent = t.deptHelp;
  $("#dept-search-label").textContent = t.deptSearch;
  $("#dept-skip").textContent = t.deptSkip;
  $("#foot-legal").textContent = t.footLegal;
  $("#foot-a11y").textContent = t.footA11y;
  $("#foot-data").textContent = t.footData;
  $("#q").placeholder = S.profile === "pro" ? t.placeholderPro : t.placeholder;
  // hint confidentialité
  $("#privacy-lines").innerHTML = t.privacy.map(x =>
    `<p class="m-0 ${S.falc ? "text-[0.98em] leading-[1.6] text-[var(--ink-800)]" : "text-[0.82em] leading-[1.5] text-[var(--ink-500)]"}">${esc(x)}</p>`
  ).join("");
  const pw = $("#privacy-hint");
  pw.className = S.falc
    ? "flex gap-[11px] items-start my-4 mx-0 py-3.5 px-4 bg-[var(--petrol-50)] border border-[var(--petrol-100)] rounded-2xl"
    : "flex gap-[7px] items-center justify-center mt-2.5 mx-0.5";
}

function renderSitTags() {
  const labels = S.falc ? SITUATIONS_FALC : SITUATIONS;
  $("#sit-tags").innerHTML = labels.concat(AGES).map(x =>
    `<span class="inline-flex items-center h-[38px] px-4 rounded-full bg-[var(--petrol-100)] text-[var(--brand-ink)] text-[0.9em] font-medium">${esc(x)}</span>`).join("");
}

/* ═══════════ SIDEBAR / CONTROLS ═══════════ */
function renderSidebar() {
  const t = T();
  const pad = S.falc ? "py-[11px] px-[13px] text-[0.92em]" : "py-2.5 px-3 text-[0.86em]";
  $("#profile-group").innerHTML = [["famille", t.profFam], ["pro", t.profPro]].map(([v, l]) =>
    `<button type="button" role="radio" aria-checked="${S.profile === v}" data-v="${v}" class="bh-toggle w-full text-left ${pad} rounded-xl border cursor-pointer ${S.profile === v ? "border-[var(--petrol-600)] bg-[var(--petrol-100)] text-[var(--brand-ink)] font-medium" : "border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-700)]"}">${esc(l)}</button>`).join("");
  $("#profile-group").querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
    S.profile = b.dataset.v;
    $("#q").placeholder = S.profile === "pro" ? T().placeholderPro : T().placeholder;
    renderSidebar(); if (!S.msgs.length) renderWelcome();
  }));
  const sitLabels = S.falc ? SITUATIONS_FALC : SITUATIONS;
  $("#situations").innerHTML = sitLabels.map((x, i) =>
    `<button type="button" aria-pressed="${S.sits.includes(SITUATIONS[i])}" data-x="${esc(SITUATIONS[i])}" class="h-[${S.falc ? "34px px-[13px] text-[0.86em]" : "30px px-[11px] text-[0.78em]"}] rounded-full border cursor-pointer ${S.sits.includes(SITUATIONS[i]) ? "border-[var(--petrol-600)] bg-[var(--petrol-100)] text-[var(--brand-ink)] font-medium" : "border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-700)]"}">${esc(x)}</button>`).join("");
  $("#situations").querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
    const x = b.dataset.x;
    S.sits = S.sits.includes(x) ? S.sits.filter(y => y !== x) : [...S.sits, x];
    renderSidebar();
  }));
  $("#ages").innerHTML = AGES.map(x =>
    `<button type="button" aria-pressed="${S.age === x}" data-x="${esc(x)}" class="h-[${S.falc ? "34px px-[13px] text-[0.86em]" : "30px px-[11px] text-[0.78em]"}] rounded-full border cursor-pointer ${S.age === x ? "border-[var(--petrol-600)] bg-[var(--petrol-100)] text-[var(--brand-ink)] font-medium" : "border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-700)]"}">${esc(x)}</button>`).join("");
  $("#ages").querySelectorAll("button").forEach(b => b.addEventListener("click", () => { S.age = S.age === b.dataset.x ? null : b.dataset.x; renderSidebar(); }));
  const db = $("#dept-btn");
  db.textContent = S.dept ? `${S.dept.code} · ${S.dept.nom}` : (S.deptSkipped ? (S.falc ? "Je n'ai pas répondu" : "Non précisé") : (S.falc ? "Choisir mon département" : "Choisir"));
  db.className = `w-full text-left ${pad} rounded-xl border cursor-pointer ${S.dept ? "border-[var(--petrol-600)] bg-[var(--petrol-100)] text-[var(--brand-ink)] font-medium" : "border-[var(--ink-200)] bg-[var(--bg-card)] text-[var(--ink-500)]"}`;
  $("#dept-clear").classList.toggle("hidden", !S.dept);
  $("#reset-btn").textContent = t.newConv;
}

function renderDeptList(q) {
  const needle = (q || "").trim().toLowerCase();
  $("#dept-list").innerHTML = DEPTS
    .filter(d => !needle || d.nom.toLowerCase().includes(needle) || d.code.startsWith(needle))
    .slice(0, 15)
    .map(d => `<li><button type="button" role="option" data-c="${d.code}" data-n="${esc(d.nom)}" class="flex items-center gap-3 w-full text-left px-3 py-[11px] rounded-[14px] border-0 cursor-pointer bg-transparent hover:bg-[var(--petrol-50)]"><span class="font-mono text-[0.85em] text-[var(--ink-500)] w-[30px] shrink-0">${d.code}</span><span class="text-[0.97em] text-[var(--ink-900)]">${esc(d.nom)}</span></button></li>`).join("");
  $("#dept-list").querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
    S.dept = { code: b.dataset.c, nom: b.dataset.n }; S.deptSkipped = false;
    closeDeptModal();
    renderSidebar();
    scrollLog();
  }));
}

function openDeptModal() {
  $("#dept-modal").classList.remove("hidden");
  document.body.style.overflow = "hidden";
  renderDeptList("");
}
function closeDeptModal() {
  $("#dept-modal").classList.add("hidden");
  document.body.style.overflow = "";
}

/* ═══════════ MODE FALC : bascule complète ═══════════ */
function applyFalcMode() {
  const h = document.documentElement;
  h.dataset.scale = S.falc && scaleIdx === 0 ? "m" : SCALES[scaleIdx];
  renderIntroBlocks();
  renderSitTags();
  renderSidebar();
  renderWelcome();
  log.classList.toggle("falc-log", S.falc);
}

/* ═══════════ INIT ═══════════ */
$("#ask-form").addEventListener("submit", e => { e.preventDefault(); ask($("#q").value.trim()); });
$("#reset-btn").addEventListener("click", () => { S.history = []; S.msgs = []; $("#reset-btn").classList.add("hidden"); renderWelcome(); });
$("#falc-btn").addEventListener("click", e => {
  S.falc = !S.falc;
  e.currentTarget.setAttribute("aria-pressed", String(S.falc));
  e.currentTarget.classList.toggle("bh-toggle", S.falc);
  applyFalcMode();
});
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
$("#scale-up").addEventListener("click", () => { scaleIdx = Math.min(2, scaleIdx + 1); document.documentElement.dataset.scale = S.falc && scaleIdx === 0 ? "m" : SCALES[scaleIdx]; });
$("#scale-down").addEventListener("click", () => { scaleIdx = Math.max(0, scaleIdx - 1); document.documentElement.dataset.scale = S.falc && scaleIdx === 0 ? "m" : SCALES[scaleIdx]; });
$("#dept-btn").addEventListener("click", openDeptModal);
$("#dept-close").addEventListener("click", closeDeptModal);
$("#dept-skip").addEventListener("click", () => { S.deptSkipped = true; S.dept = null; closeDeptModal(); renderSidebar(); });
$("#dept-q").addEventListener("input", e => renderDeptList(e.target.value));
$("#dept-modal").addEventListener("click", e => { if (e.target.id === "dept-modal") closeDeptModal(); });
document.addEventListener("keydown", e => { if (e.key === "Escape" && !$("#dept-modal").classList.contains("hidden")) closeDeptModal(); });

renderIntroBlocks();
renderSitTags();
renderSidebar();
renderWelcome();
loadSources();