/*
  LE ROYAUME EN 3D · moteur de la version immersive (Three.js)

  Le royaume vient de Blender (tools/blender/ile.py et le dossier royaume/) : un fichier ile.glb (la
  géométrie, compressée avec Draco) et des « atlas » de lumière cuite par Cycles. Chaque maillage cuit est
  affiché avec une matière sans calcul d'éclairage (MeshBasicMaterial) : l'image contient déjà le soleil,
  les ombres douces et la lumière qui rebondit. Les arbres sont faits de « cartes » de feuilles.

  Le navigateur ajoute ce qui vit : feuilles et herbe dans le vent, eau qui reflète le ciel, cascade,
  fontaine, feux, fumées, moulin, ciel, mer de nuages, brume, rayons de lumière, faisceau du phare,
  cristaux, lucioles, oiseaux ; et les habitants (moteur/personnages.js), éclairés en temps réel.

  Deux façons de visiter :
  - la visite guidée : la caméra suit un trajet tracé dans Blender (objets vides cam_XX et cible_XX), le
    défilement de la page choisit la position sur ce trajet, chaque chapitre (section HTML) est un arrêt,
    et Ernest attend à chaque lieu ;
  - le mode libre (moteur/exploration.js) : on marche avec Ernest, on entre dans les bâtiments, on parle
    aux habitants (moteur/dialogues.js).
  Les autres visiteurs présents apparaissent en avatars, avec un chat (moteur/multijoueur.js, si réglé).

  Organisation : réglages · langue · outils et GLSL partagé · défilement · chargement · scène (royaume,
  ciel, nuages, eau, herbe, objets vivants, effets, habitants) · rendu · modes · boucle.
*/
import * as THREE from "../lib/three/three.module.js";
import { GLTFLoader } from "../lib/three/loaders/GLTFLoader.js";
import { DRACOLoader } from "../lib/three/loaders/DRACOLoader.js";
import { EffectComposer } from "../lib/three/postprocessing/EffectComposer.js";
import { RenderPass } from "../lib/three/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "../lib/three/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "../lib/three/postprocessing/ShaderPass.js";
import { OutputPass } from "../lib/three/postprocessing/OutputPass.js";
import { Peuple, Royaume, CarteMarche, ERNEST } from "./moteur/personnages.js";
import { Dialogue } from "./moteur/dialogues.js";
import { Exploration } from "./moteur/exploration.js";
import { Multijoueur } from "./moteur/multijoueur.js";
import { MULTIJOUEUR } from "./config-multijoueur.js";

/* =========================================================================
   RÉGLAGES
   ========================================================================= */

const racine = document.documentElement;
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const tactile = window.matchMedia("(pointer: coarse)").matches;
const petitEcran = () => window.innerWidth <= 760;
if (tactile) racine.classList.add("tactile");
const MODESTE = petitEcran() || tactile || (navigator.hardwareConcurrency || 8) <= 4 || (navigator.deviceMemory || 8) <= 4;
const QUALITE = {
  ratio: Math.min(window.devicePixelRatio || 1, MODESTE ? 1.5 : 2),
  msaa: MODESTE ? 0 : 4,
  atlas: MODESTE ? 2048 : 4096,
  feuilles: MODESTE ? 1024 : 2048,
  couchesNuages: MODESTE ? 4 : 7,
  lucioles: MODESTE ? 70 : 160,
  herbe: MODESTE ? 26000 : 80000,
  rayons: !MODESTE,
  habitants: MODESTE ? { humains: 110, animaux: 30 } : { humains: 170, animaux: 40 },
};

// Où se tient Ernest à chaque chapitre de la visite, et qui parle dans la bulle
const GUIDE_CHAPITRE = ["guide_porte", "guide_porte", "guide_atelier", "guide_guilde", "guide_grande_salle", "guide_phare", "guide_phare"];
const BULLE_CHAPITRE = [null, "capitaine", "coach", "bibliothecaire", "intendante", "gardien", null];

// Couleurs du coucher de soleil (sRGB), accordées au ciel utilisé par Blender pour la cuisson
const PALETTE = {
  zenith: 0x221a45,
  haut: 0x4c3a7c,
  milieu: 0xa26c9e,
  horizon: 0xf3c4a2,
  horizonOppose: 0xc99ab8,
  soleil: 0xffc58a,
  bas: 0xd59fa2,
  fond: 0x5c4a78,
  nuageClair: 0xffd9c4,
  nuageOmbre: 0x7e6596,
  brume: 0xc89cb0,
  brumeSoleil: 0xffc79a,
};

/* =========================================================================
   LANGUE (le français est écrit dans la page)
   ========================================================================= */

const EN = {
  "meta.title": "Ernest Afaton · The 3D kingdom",
  "meta.description": "Ernest Afaton's portfolio as an immersive experience: a walled kingdom on a floating island at sunset, modeled and lit in Blender. Take the guided tour or walk around and talk to the townsfolk.",
  "skip": "Skip to content",
  "logo.label": "Back to the classic portfolio",
  "logo.sous": "Portfolio — 2026",
  "nav.label": "Other versions of the portfolio",
  "nav.classic": "Classic version",
  "nav.game": "Game version",
  "libre.entrer": "Explore freely",
  "libre.retour": "Back to the tour",
  "libre.clavier": "<kbd>WASD</kbd> or arrows to walk · <kbd>Shift</kbd> to run · <kbd>Space</kbd> to jump · drag to look around · <kbd>E</kbd> to talk · <kbd>Esc</kbd> to go back",
  "libre.tactile": "Joystick to walk · drag on the right to look around",
  "libre.parler": "Talk",
  "libre.sauter": "Jump",
  "libre.parlerA": "Talk to",
  "dialogue.fermer": "Close",
  "chat.titre": "Visitors here now",
  "chat.fermer": "Close the chat",
  "chat.placeholder": "Write a message…",
  "chat.envoyer": "Send",
  "chat.note": "Nothing is saved: only the visitors here right now see these messages.",
  "presence.label": "Visitors online: open the chat",
  "toc.label": "Chapters",
  "toc.0": "Home", "toc.1": "About", "toc.2": "Experience", "toc.3": "Skills", "toc.4": "Projects", "toc.5": "Contact", "toc.6": "The end",
  "hero.status": "Available for a 4 to 5 week internship",
  "hero.hello": "Hi, I'm",
  "hero.role": "Web and mobile developer · Systems and networks · IoT",
  "hero.lead": "Welcome to my kingdom: my portfolio as an immersive experience. Scroll for the guided tour, or explore freely, walk into the buildings and talk to the townsfolk.",
  "hero.cue": "Scroll for the tour",
  "about.eyebrow": "The kingdom gate · About",
  "about.title": "Understand how things work, then build them.",
  "about.p1": "I'm in the second year of a Computer Science Bachelor's at EPSI Lyon, in the software design and development track, and I'm also preparing the BTS SIO, SLAM option (a French national IT diploma, 2027 exams).",
  "about.p2": "I like going down the layers: from a PHP framework written without any library to a containerized NAS server reachable from anywhere.",
  "facts.city": "Lyon, France",
  "facts.lang": "French (native) · English (B2)",
  "facts.seek": "4 to 5 week internship",
  "exp.eyebrow": "The workshop · Experience",
  "exp.title": "Developer intern and Fablab assistant at MyDil.",
  "exp.when": "April - June 2026 · Digital Innovation Lab",
  "exp.l1": "<strong>InfraHub</strong>, built in 2 weeks: a ticketing platform for students, with role-based access control and automatic incident escalation.",
  "exp.l2": "<strong>Self-hosted NAS</strong> designed, deployed and run on my own, with <strong>99.9%</strong> measured uptime.",
  "exp.l3": "<strong>Scrum Master</strong> on 4 team projects.",
  "skills.eyebrow": "The guild library · Skills",
  "skills.title": "From code to infrastructure.",
  "skills.sub": "Seven banners, seven skill families.",
  "sk.web": "Web development", "sk.cs": "C# and .NET", "sk.mobile": "Mobile", "sk.back": "Back end and data",
  "sk.net": "Systems and networks", "sk.iot": "IoT and embedded", "sk.tools": "Methods", "sk.tests": "unit testing",
  "proj.eyebrow": "The great hall · Projects",
  "proj.title": "What I've built.",
  "p.ecopay": "A SaaS platform that collects school fees for private schools in West Africa, with Mobile Money payments and automatic reminders.",
  "p.boutik": "Checkout, stock and credit sales for small shops, on Android, iPhone and desktop, even offline.",
  "p.worldName": "Ernest's World",
  "p.world": "The game version of this portfolio: a 3D island with 16 places and 5 bosses, written in C# with Blazor.",
  "p.site": "Visit the site",
  "p.play": "Play",
  "proj.all": "See all 16 projects",
  "contact.eyebrow": "The lighthouse · Contact",
  "contact.title": "Have an internship to offer?",
  "contact.title2": "Let's talk.",
  "contact.text": "I'm looking for a 4 to 5 week internship in software development or systems and networks. The easiest way to reach me is by email or on LinkedIn.",
  "contact.mail": "Send an email",
  "contact.classic": "Classic portfolio",
  "contact.game": "Game version",
  "contact.how": "How the kingdom is made",
  "contact.credit": "Kingdom modeled by a Python script in Blender, lighting computed by Cycles, displayed with Three.js.",
  "end.eyebrow": "The end of the journey",
  "end.title": "Thanks for visiting my kingdom.",
  "end.text": "Now walk around on your own: every building can be entered and the townsfolk have plenty to say. The whole journey also exists as a one-page portfolio, and as a game.",
  "end.top": "Back to the start",
  "end.classic": "Classic portfolio",
  "end.game": "Play the game version",
  "load.title": "The kingdom is getting ready…",
  "load.classic": "See the classic version instead",
  "no3d": "3D couldn't start on this device: here is the kingdom as an image, and all the content is still readable.",
};

const FR = {};
let langue = racine.getAttribute("data-lang") === "en" ? "en" : "fr";
const surLangue = [];     // modules à prévenir quand la langue change (dialogues, chat...)

function appliquerLangue(lang) {
  langue = lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const cle = el.getAttribute("data-i18n");
    if (!(cle in FR)) FR[cle] = el.innerHTML;
    el.innerHTML = lang === "en" && EN[cle] ? EN[cle] : FR[cle];
  });
  document.querySelectorAll("[data-i18n-attr]").forEach((el) => {
    el.getAttribute("data-i18n-attr").split(";").forEach((paire) => {
      const [attr, cle] = paire.split("=");
      const id = "@" + cle + "@" + attr;
      if (!(id in FR)) FR[id] = el.getAttribute(attr);
      el.setAttribute(attr, lang === "en" && EN[cle] ? EN[cle] : FR[id]);
    });
  });
  if (!("meta.title" in FR)) {
    FR["meta.title"] = document.title;
    FR["meta.description"] = document.querySelector('meta[name="description"]').content;
  }
  document.title = lang === "en" ? EN["meta.title"] : FR["meta.title"];
  document.querySelector('meta[name="description"]').content = lang === "en" ? EN["meta.description"] : FR["meta.description"];
  racine.lang = lang;
  racine.setAttribute("data-lang", lang);
  document.querySelectorAll("[data-set-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.setLang === lang)));
  racine.classList.remove("i18n-pending");
  for (const f of surLangue) f(lang);
}

document.querySelectorAll("[data-set-lang]").forEach((b) => {
  b.addEventListener("click", () => {
    const lang = b.dataset.setLang;
    try { localStorage.setItem("ernest-lang", lang); } catch (e) { /* navigation privée */ }
    appliquerLangue(lang);
  });
});
appliquerLangue(langue);

/* =========================================================================
   OUTILS ET GLSL PARTAGÉ
   ========================================================================= */

const lisse = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const doux = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const couleur = (hex) => new THREE.Color(hex);

function hasard(graine) {
  return function () {
    graine |= 0; graine = (graine + 0x6d2b79f5) | 0;
    let t = Math.imul(graine ^ (graine >>> 15), 1 | graine);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function textureHalo() {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d");
  const d = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  d.addColorStop(0, "rgba(255,255,255,1)");
  d.addColorStop(0.18, "rgba(255,255,255,0.55)");
  d.addColorStop(0.5, "rgba(255,255,255,0.12)");
  d.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = d;
  g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function textureNuage(rnd) {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const g = c.getContext("2d");
  for (let i = 0; i < 26; i++) {
    const x = 128 + (rnd() - 0.5) * 140, y = 140 + (rnd() - 0.5) * 60, r = 30 + rnd() * 50;
    const d = g.createRadialGradient(x, y, 0, x, y, r);
    d.addColorStop(0, "rgba(255,255,255,0.32)");
    d.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = d;
    g.fillRect(0, 0, 256, 256);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// Bruit de valeur et fbm, utilisés par l'eau, la cascade et les nuages
const GLSL_BRUIT = /* glsl */`
  float h21(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float bruit(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
  }
  float fbm(vec2 p) {
    float v = 0.0, a = 0.5;
    for (int i = 0; i < 5; i++) { v += a * bruit(p); p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; }
    return v;
  }`;

// Couleur du ciel dans une direction : sert au ciel lui-même et aux reflets de l'eau
const U_CIEL = {
  uZenith: { value: couleur(PALETTE.zenith) }, uHaut: { value: couleur(PALETTE.haut) },
  uMilieu: { value: couleur(PALETTE.milieu) }, uHorizon: { value: couleur(PALETTE.horizon) },
  uHorizonOppose: { value: couleur(PALETTE.horizonOppose) },
  uBas: { value: couleur(PALETTE.bas) }, uFond: { value: couleur(PALETTE.fond) },
  uSoleilCouleur: { value: couleur(PALETTE.soleil) }, uSoleil: { value: new THREE.Vector3(0.9034, 0.225, -0.365) },
};
const GLSL_CIEL = /* glsl */`
  uniform vec3 uZenith, uHaut, uMilieu, uHorizon, uHorizonOppose, uBas, uFond, uSoleilCouleur, uSoleil;
  vec3 ciel(vec3 d) {
    float h = d.y;
    float s = max(dot(d, uSoleil), 0.0);
    // Du côté opposé au soleil, l'horizon tire sur le rose (la « ceinture de Vénus »)
    float cote = dot(normalize(d.xz + 1e-4), normalize(uSoleil.xz));
    vec3 horizon = mix(uHorizonOppose, uHorizon, smoothstep(-0.7, 0.75, cote));
    vec3 c = mix(horizon, uMilieu, smoothstep(0.0, 0.16, h));
    c = mix(c, uHaut, smoothstep(0.1, 0.42, h));
    c = mix(c, uZenith, smoothstep(0.35, 0.95, h));
    vec3 b = mix(horizon, uBas, smoothstep(0.0, -0.08, h));
    b = mix(b, uFond, smoothstep(-0.08, -0.5, h));
    c = h < 0.0 ? b : c;
    c += uSoleilCouleur * (pow(s, 6.0) * 0.45 + pow(s, 40.0) * 0.7);
    c += uSoleilCouleur * 0.35 * exp(-abs(h) * 14.0) * pow(s, 3.0);
    return c;
  }`;

// Brume : plus dense au loin et vers le bas (la mer de nuages), dorée du côté du soleil
const U_BRUME = {
  uBrume: { value: couleur(PALETTE.brume) },
  uBrumeSoleil: { value: couleur(PALETTE.brumeSoleil) },
  uSoleilDir: U_CIEL.uSoleil,
  uBrumeDist: { value: new THREE.Vector2(150, 1150) },
};
const GLSL_BRUME = /* glsl */`
  uniform vec3 uBrume, uBrumeSoleil, uSoleilDir;
  uniform vec2 uBrumeDist;
  vec3 brume(vec3 c, vec3 p) {
    float d = distance(p, cameraPosition);
    float f = smoothstep(uBrumeDist.x, uBrumeDist.y, d);
    vec3 v = normalize(p - cameraPosition);
    float s = pow(max(dot(v, uSoleilDir), 0.0), 5.0);
    float basse = smoothstep(-14.0, -78.0, p.y) * 0.55;
    vec3 fc = mix(uBrume, uBrumeSoleil, s * 0.85);
    return mix(c, fc, clamp(f + basse * (1.0 - f), 0.0, 1.0));
  }`;

/* Ajoute la brume à une MeshBasicMaterial (et, pour les feuilles, le vent et le détail de la texture) */
const U_TEMPS = { value: 0 };
function preparerMatiere(mat, options = {}) {
  mat.fog = false;
  mat.customProgramCacheKey = () => "ile3d" + (options.vent ? "-vent" : "") + (options.feuilles ? "-feuilles" : "");
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, U_BRUME, { uTemps: U_TEMPS });
    let vs = sh.vertexShader.replace("#include <common>", "#include <common>\nvarying vec3 vMonde;\nuniform float uTemps;"
      + (options.vent ? "\nattribute vec4 aBalance;" : ""));
    if (options.vent) {
      vs = vs.replace("#include <begin_vertex>", /* glsl */`#include <begin_vertex>
        {
          vec3 wp = (modelMatrix * vec4(transformed, 1.0)).xyz;
          float w = aBalance.r;
          float ph = aBalance.g * 6.2832;
          float s1 = sin(uTemps * 1.2 + ph + wp.x * 0.12 + wp.z * 0.08);
          float s2 = sin(uTemps * 3.1 + ph * 2.3 + wp.y * 0.9 + wp.x * 0.4);
          transformed.x += (s1 * 0.13 + s2 * 0.035) * w;
          transformed.z += (cos(uTemps * 1.0 + ph) * 0.09 + s2 * 0.03) * w;
          transformed.y += s2 * 0.025 * w;
        }`);
    }
    sh.vertexShader = vs.replace("#include <project_vertex>", "#include <project_vertex>\nvMonde = (modelMatrix * vec4(transformed, 1.0)).xyz;");
    let fs = sh.fragmentShader.replace("#include <common>", "#include <common>\nvarying vec3 vMonde;\n" + GLSL_BRUME
      + (options.feuilles ? "\nuniform float uLumFeuille;" : ""));
    if (options.feuilles) {
      sh.uniforms.uLumFeuille = options.feuilles;
      fs = fs.replace("#include <alphamap_fragment>", /* glsl */`
        vec4 feuille = texture2D(alphaMap, vAlphaMapUv);
        diffuseColor.a *= feuille.a;
        float lum = dot(feuille.rgb, vec3(0.299, 0.587, 0.114));
        diffuseColor.rgb *= mix(1.0, lum / uLumFeuille, 0.8);`);
    }
    sh.fragmentShader = fs.replace("#include <dithering_fragment>", "gl_FragColor.rgb = brume(gl_FragColor.rgb, vMonde);\n#include <dithering_fragment>");
  };
  return mat;
}

/* =========================================================================
   DÉFILEMENT : chapitres, panneaux et sommaire
   ========================================================================= */

const sections = [...document.querySelectorAll(".chapitre")];
const panneaux = sections.map((s) => s.querySelector(".panneau"));
const liensSommaire = [...document.querySelectorAll(".sommaire a")];
const voile = document.querySelector(".voile");
const barreProgression = document.querySelector(".progression span");
const CHAPITRES_LARGES = new Set([0, sections.length - 1]);   // vues d'ensemble : on recule sur écran en hauteur

let hauteurVue = window.innerHeight;
let debuts = [];
let arret = 0;
let defilementMax = 1;

function mesurer() {
  hauteurVue = window.innerHeight;
  debuts = sections.map((s) => s.offsetTop);
  arret = 0.5 * hauteurVue;
  defilementMax = Math.max(1, document.documentElement.scrollHeight - hauteurVue);
}

/* Position sur le trajet : un arrêt au début de chaque chapitre, puis un voyage jusqu'au suivant */
function etape(y) {
  const n = debuts.length;
  for (let c = 0; c < n - 1; c++) {
    const finArret = debuts[c] + arret;
    if (y < finArret) return { de: c, vers: c, t: 0 };
    if (y < debuts[c + 1]) return { de: c, vers: c + 1, t: (y - finArret) / (debuts[c + 1] - finArret) };
  }
  return { de: n - 1, vers: n - 1, t: 0 };
}

function opacitePanneau(c, y) {
  const a = debuts[c];
  const entree = c === 0 ? 1 : lisse(a - 0.45 * hauteurVue, a - 0.05 * hauteurVue, y);
  const sortie = c === debuts.length - 1 ? 0 : lisse(a + arret * 0.9, a + arret + 0.3 * hauteurVue, y);
  return entree * (1 - sortie);
}

let chapitreActuel = -1;
function majInterface(y, introPanneau = 1) {
  let meilleur = 0, meilleure = -1;
  panneaux.forEach((p, c) => {
    const o = opacitePanneau(c, y) * (c === 0 ? introPanneau : 1);
    p.style.opacity = o.toFixed(3);
    p.style.transform = `translateY(${((1 - o) * 18).toFixed(1)}px)`;
    p.classList.toggle("cache", o < 0.05);
    if (opacitePanneau(c, y) > meilleure) { meilleure = opacitePanneau(c, y); meilleur = c; }
  });
  if (meilleur !== chapitreActuel) {
    chapitreActuel = meilleur;
    liensSommaire.forEach((a, c) => (c === meilleur ? a.setAttribute("aria-current", "step") : a.removeAttribute("aria-current")));
    voile.classList.toggle("droite", panneaux[meilleur].classList.contains("cote-droite"));
  }
  barreProgression.style.transform = `scaleX(${Math.min(1, y / defilementMax).toFixed(4)})`;
}

mesurer();
window.addEventListener("resize", mesurer);

function allerAuChapitre(c) {
  window.scrollTo({ top: debuts[c] + (c === 0 ? 0 : 2), behavior: reduceMotion ? "auto" : "smooth" });
  history.replaceState(null, "", c === 0 ? location.pathname + location.search : "#" + sections[c].id);
}
liensSommaire.forEach((a, c) => {
  a.addEventListener("click", (e) => { e.preventDefault(); allerAuChapitre(c); });
});
document.querySelectorAll("[data-aller]").forEach((a) => {
  a.addEventListener("click", (e) => { e.preventDefault(); allerAuChapitre(Number(a.dataset.aller)); });
});

/* =========================================================================
   SANS 3D : l'image de l'île reste, et tout le texte est lisible
   ========================================================================= */

function sans3D(raison) {
  if (raison) console.warn("[ile3d] 3D désactivée :", raison);
  racine.classList.add("sans-3d");
  racine.classList.remove("avec-3d");
  panneaux.forEach((p) => { p.style.opacity = ""; p.style.transform = ""; p.classList.remove("cache"); });
}

/* =========================================================================
   CHARGEMENT
   ========================================================================= */

const elPourcent = document.querySelector(".chargement-pourcent");
const elBarre = document.querySelector(".barre-chargement span");
function afficherProgression(p) {
  const v = Math.round(Math.min(1, p) * 100);
  elPourcent.textContent = v + " %";
  elBarre.style.transform = `scaleX(${(v / 100).toFixed(3)})`;
}

function chargerBitmap(url) {
  if (typeof createImageBitmap === "undefined") {
    return new THREE.TextureLoader().loadAsync(url);
  }
  return fetch(url)
    .then((r) => { if (!r.ok) throw new Error(url + " : " + r.status); return r.blob(); })
    .then((b) => createImageBitmap(b, { imageOrientation: "none", premultiplyAlpha: "none", colorSpaceConversion: "none" }))
    .then((bmp) => new THREE.Texture(bmp));
}

/* Pixels d'une image, pour lire la couleur du sol cuit à un endroit donné */
function pixels(image) {
  const c = document.createElement("canvas");
  c.width = image.width;
  c.height = image.height;
  const g = c.getContext("2d", { willReadFrequently: true });
  g.drawImage(image, 0, 0);
  return g.getImageData(0, 0, c.width, c.height);
}

/* =========================================================================
   SCÈNE
   ========================================================================= */

async function demarrer() {
  const canvas = document.getElementById("scene");
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: "high-performance" });
  } catch (e) {
    sans3D(e.message);
    return;
  }
  if (!renderer.capabilities.isWebGL2) {
    sans3D("WebGL 2 indisponible");
    return;
  }
  racine.classList.add("avec-3d");
  mesurer();
  majInterface(window.scrollY);

  renderer.setPixelRatio(QUALITE.ratio);
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(44, window.innerWidth / window.innerHeight, 0.15, 3000);

  /* ----- chargement du royaume, des atlas (taille 1024 d'abord) et des feuilles ----- */
  let progGlb = 0, progTex = 0, nbTex = 5;
  const maj = () => afficherProgression(progGlb * 0.65 + (progTex / nbTex) * 0.35);
  const draco = new DRACOLoader().setDecoderPath("../lib/three/libs/draco/gltf/");
  const chargeur = new GLTFLoader().setDRACOLoader(draco);
  // Carte de marche et chemins des habitants : sans eux, le royaume s'affiche quand même (sans habitants)
  const promesseChemins = fetch("assets/royaume.json").then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const promesseCarte = fetch("assets/royaume_carte.png")
    .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.blob(); })
    .then((b) => createImageBitmap(b, { colorSpaceConversion: "none", premultiplyAlpha: "none" }))
    .catch(() => null);
  let gltf;
  try {
    gltf = await chargeur.loadAsync("assets/ile.glb", (e) => { if (e.total) { progGlb = e.loaded / e.total; maj(); } });
  } catch (e) {
    sans3D(e.message);
    return;
  }
  const ile = gltf.scene;
  ile.updateMatrixWorld(true);
  scene.add(ile);

  const parNom = new Map();
  const atlas = new Map();       // nom de l'atlas -> { matieres, tailleMax, abonnes }
  const vivants = [];
  const flottants = [];
  const terrains = [];
  const pieces = [];             // pièces des personnages (tête, bras, jambes...), recopiées par Peuple
  let feuillage = null;
  ile.traverse((o) => {
    parNom.set(o.name, o);
    if (!o.isMesh) return;
    const d = Object.keys(o.userData).length ? o.userData : (o.parent ? o.parent.userData : {});
    if (d.vivant === "piece") {
      pieces.push({ objet: o, nom: d.piece });
    } else if (d.atlas) {
      if (!atlas.has(d.atlas)) atlas.set(d.atlas, { matiere: null, feuilles: null, tailleMax: d.atlas_max || 4096, abonnes: [] });
      const a = atlas.get(d.atlas);
      if (d.feuilles) {
        feuillage = o;
        const g = o.geometry;
        if (g.getAttribute("color")) { g.setAttribute("aBalance", g.getAttribute("color")); g.deleteAttribute("color"); }
      } else {
        if (!a.matiere) a.matiere = preparerMatiere(new THREE.MeshBasicMaterial({ color: 0xffffff }));
        o.material = a.matiere;
      }
      o.geometry.deleteAttribute("normal");
      if (d.terrain) terrains.push(o);
      if (d.mobile) flottants.push({ objet: o, base: o.position.clone(), ampl: d.flotte || 0.3, phase: Math.random() * 6.28 });
    } else if (d.vivant) {
      vivants.push({ objet: o, type: d.vivant, rang: d.rang || 0, projet: d.projet, donnees: d });
    }
  });
  nbTex = atlas.size + 1;
  // Les pièces sortent de la scène : leur géométrie (rotation et échelle comprises) sert aux instances
  const geometriesPieces = {};
  for (const { objet, nom } of pieces) {
    const m = objet.matrixWorld.clone().setPosition(0, 0, 0);
    geometriesPieces[nom] = objet.geometry.clone().applyMatrix4(m);
    objet.parent.remove(objet);
    objet.geometry.dispose();
  }
  const atlasTerrains = new Set(terrains.map((t) => t.userData.atlas));

  const aniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  const preparer = (tex, srgb = true) => {
    tex.flipY = false;
    tex.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    tex.anisotropy = aniso;
    tex.needsUpdate = true;
    return tex;
  };
  const appliquerAtlas = (a, tex) => {
    if (a.matiere) { a.matiere.map = tex; a.matiere.needsUpdate = true; }
    if (a.feuilles) { a.feuilles.map = tex; a.feuilles.needsUpdate = true; }
    for (const f of a.abonnes) f(tex);
  };

  let texFeuilles;
  const pixelsTerrains = new Map();    // atlas d'un sol -> pixels, pour colorer l'herbe
  const lumFeuille = { value: 0.3 };
  try {
    const promesses = [...atlas.entries()].map(([nom, a]) =>
      chargerBitmap(`assets/${nom}_1024.webp`).then((tex) => {
        a.texture = preparer(tex);
        a.taille = 1024;
        if (atlasTerrains.has(nom)) pixelsTerrains.set(nom, pixels(tex.image));
        progTex++;
        maj();
      }));
    promesses.push(chargerBitmap(`assets/feuilles_${QUALITE.feuilles}.webp`).then((tex) => {
      texFeuilles = preparer(tex);
      texFeuilles.channel = 1;
      // Luminosité moyenne des feuilles : le détail de la texture module la couleur cuite autour de 1
      const petit = document.createElement("canvas");
      petit.width = petit.height = 64;
      const g = petit.getContext("2d", { willReadFrequently: true });
      g.drawImage(tex.image, 0, 0, 64, 64);
      const p = g.getImageData(0, 0, 64, 64).data;
      let somme = 0, n = 0;
      for (let i = 0; i < p.length; i += 4) {
        if (p[i + 3] > 200) { somme += (0.299 * p[i] + 0.587 * p[i + 1] + 0.114 * p[i + 2]) / 255; n++; }
      }
      if (n) lumFeuille.value = somme / n;
      progTex++;
      maj();
    }));
    await Promise.all(promesses);
  } catch (e) {
    sans3D(e.message);
    return;
  }
  for (const a of atlas.values()) {
    if (a.matiere) { a.matiere.map = a.texture; a.matiere.needsUpdate = true; }
  }
  if (feuillage) {
    const a = atlas.get(feuillage.userData.atlas);
    a.feuilles = preparerMatiere(new THREE.MeshBasicMaterial({
      map: a.texture, alphaMap: texFeuilles, alphaTest: 0.45, side: THREE.DoubleSide, alphaToCoverage: QUALITE.msaa > 0,
    }), { vent: !reduceMotion && !!feuillage.geometry.getAttribute("aBalance"), feuilles: lumFeuille });
    feuillage.material = a.feuilles;
  }

  /* ----- repères venus de Blender ----- */
  const position = (nom, defaut) => {
    const o = parNom.get(nom);
    return o ? o.getWorldPosition(new THREE.Vector3()) : defaut;
  };
  const cles = [...parNom.keys()].filter((n) => /^cam_\d+$/.test(n)).sort();
  const ptsCam = cles.map((n) => position(n));
  const ptsCible = cles.map((n) => position(n.replace("cam_", "cible_")));
  const fovs = cles.map((n) => parNom.get(n).userData.fov || 44);
  const chapitreVersIndice = [];
  cles.forEach((n, i) => {
    const c = parNom.get(n).userData.chapitre;
    if (c !== undefined && c >= 0) chapitreVersIndice[c] = i;
  });
  const courbeCam = new THREE.CatmullRomCurve3(ptsCam, false, "centripetal", 0.5);
  const courbeCible = new THREE.CatmullRomCurve3(ptsCible, false, "centripetal", 0.5);
  const uChapitre = (c) => (chapitreVersIndice[Math.min(c, chapitreVersIndice.length - 1)] ?? 0) / (cles.length - 1);
  const fovA = (u) => {
    const x = u * (fovs.length - 1);
    const i = Math.min(fovs.length - 2, Math.floor(x));
    return THREE.MathUtils.lerp(fovs[i], fovs[i + 1], doux(x - i));
  };
  const soleil = position("soleil", U_CIEL.uSoleil.value.clone()).normalize();
  U_CIEL.uSoleil.value.copy(soleil);

  /* ----- carte de marche, chemins des habitants, repères des personnages ----- */
  const [chemins, imageCarte] = await Promise.all([promesseChemins, promesseCarte]);
  const carte = chemins && imageCarte ? new CarteMarche(imageCarte, chemins) : null;
  const dehors = (p) => !carte || carte.interieur(p.x, p.z) === 0;
  // Angle « regard » de Blender (direction cos r, sin r dans le plan XY) vers le cap d'un personnage du site
  const capDepuisRegard = (r) => Math.atan2(Math.cos(r), -Math.sin(r));
  const reperesPnj = {};
  const guides = {};
  for (const [nom, o] of parNom) {
    if (!/^(pnj|guide)_/.test(nom)) continue;
    const r = { pos: o.getWorldPosition(new THREE.Vector3()), regard: capDepuisRegard(o.userData.regard || 0), role: o.userData.role };
    if (nom.startsWith("pnj_")) reperesPnj[nom] = r; else guides[nom] = r;
  }
  // Les lieux des chapitres, dehors : l'herbe y est plus dense, les lucioles s'y rassemblent
  const lieux = [];
  cles.forEach((n, i) => {
    if (!(parNom.get(n).userData.chapitre > 0)) return;
    for (const p of [ptsCible[i], ptsCam[i]]) if (p.length() < 150 && dehors(p)) lieux.push(p);
  });
  for (const g of Object.values(guides)) if (dehors(g.pos)) lieux.push(g.pos);

  /* ----- ciel ----- */
  const ciel = new THREE.Mesh(
    new THREE.SphereGeometry(1500, 48, 24),
    new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false,
      uniforms: { ...U_CIEL, uTemps: U_TEMPS },
      vertexShader: /* glsl */`
        varying vec3 vDir;
        void main() {
          vDir = normalize(position);
          vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          gl_Position = p.xyww;
        }`,
      fragmentShader: /* glsl */`
        uniform float uTemps;
        varying vec3 vDir;
        ${GLSL_CIEL}
        float h31(vec2 p) { return fract(sin(dot(p, vec2(41.3, 289.1))) * 45758.5453); }
        void main() {
          vec3 d = normalize(vDir);
          vec3 c = ciel(d);
          float s = max(dot(d, uSoleil), 0.0);
          c += vec3(1.0, 0.92, 0.78) * smoothstep(0.99935, 0.9997, s) * 5.0;
          vec2 g = floor(vec2(atan(d.z, d.x) * 180.0, d.y * 260.0));
          float e = step(0.9975, h31(g)) * smoothstep(0.45, 0.9, d.y);
          c += vec3(e) * (0.5 + 0.5 * sin(uTemps * 1.5 + h31(g + 3.0) * 30.0)) * 0.6;
          gl_FragColor = vec4(c, 1.0);
        }`,
    }));
  ciel.renderOrder = -10;
  ciel.frustumCulled = false;
  scene.add(ciel);

  /* ----- mer de nuages : couches de bruit animé, sous l'île ----- */
  const nuages = [];
  const matNuage = (k, n) => new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: {
      uTemps: U_TEMPS, uCouche: { value: k / Math.max(1, n - 1) }, uGraine: { value: k * 17.31 },
      uClair: { value: couleur(PALETTE.nuageClair) }, uOmbre: { value: couleur(PALETTE.nuageOmbre) },
      uHorizonN: { value: couleur(PALETTE.horizon) }, uSoleilN: { value: couleur(PALETTE.soleil) },
      uSoleil: U_CIEL.uSoleil, uCamera: { value: new THREE.Vector3() },
    },
    vertexShader: /* glsl */`
      varying vec3 vMonde;
      void main() {
        vec4 m = modelMatrix * vec4(position, 1.0);
        vMonde = m.xyz;
        gl_Position = projectionMatrix * viewMatrix * m;
      }`,
    fragmentShader: /* glsl */`
      uniform float uTemps, uCouche, uGraine;
      uniform vec3 uClair, uOmbre, uHorizonN, uSoleilN, uSoleil, uCamera;
      varying vec3 vMonde;
      ${GLSL_BRUIT}
      void main() {
        vec2 p = vMonde.xz * 0.0062 + vec2(uTemps * 0.005, uTemps * 0.002) + uGraine;
        float n = fbm(p + 0.35 * vec2(fbm(p * 0.7 + 4.0), fbm(p * 0.7 - 3.0)));
        float seuil = mix(0.36, 0.5, uCouche);
        float densite = smoothstep(seuil, seuil + 0.22, n);
        float dist = length(vMonde.xz - uCamera.xz);
        densite *= 1.0 - smoothstep(1100.0, 1450.0, dist);
        vec3 vue = normalize(vMonde - uCamera);
        vec2 vs = normalize(uSoleil.xz);
        float versSoleil = pow(max(dot(normalize(vue.xz), vs), 0.0), 4.0);
        vec3 c = mix(uOmbre, uClair, clamp(uCouche * 0.75 + (n - seuil) * 1.4, 0.0, 1.0));
        c += uSoleilN * versSoleil * 0.45 * uCouche;
        c = mix(c, uHorizonN, smoothstep(160.0, 1100.0, dist) * 0.85);
        gl_FragColor = vec4(c, densite * mix(0.45, 0.8, uCouche));
      }`,
  });
  for (let k = 0; k < QUALITE.couchesNuages; k++) {
    const n = QUALITE.couchesNuages;
    const plan = new THREE.Mesh(new THREE.PlaneGeometry(3000, 3000), matNuage(k, n));
    plan.rotation.x = -Math.PI / 2;
    plan.position.y = -112 + (k / Math.max(1, n - 1)) * 34;
    plan.renderOrder = -5 + k;
    plan.frustumCulled = false;
    scene.add(plan);
    nuages.push(plan);
  }

  /* ----- nuages proches (sprites) : profondeur pendant les vues d'ensemble ----- */
  const rnd = hasard(7);
  const texNuage = textureNuage(rnd);
  const nuagesProches = [];
  for (let i = 0; i < 22; i++) {
    const a = rnd() * Math.PI * 2;
    const r = 150 + rnd() * 170;
    const s = new THREE.Sprite(new THREE.SpriteMaterial({
      map: texNuage, color: couleur(i % 3 ? PALETTE.nuageClair : PALETTE.milieu), transparent: true,
      opacity: 0.2 + rnd() * 0.2, depthWrite: false, fog: false,
    }));
    s.position.set(Math.cos(a) * r, -72 + rnd() * 46, Math.sin(a) * r);
    s.scale.set(90 + rnd() * 90, 32 + rnd() * 24, 1);
    s.userData.vitesse = 0.3 + rnd() * 0.5;
    scene.add(s);
    nuagesProches.push(s);
  }

  /* ----- objets vivants : glyphes, anneau, cristaux, eau, cascade ----- */
  const texHalo = textureHalo();
  const animes = [];
  const couleursCristal = { ecopay: 0x4ade80, boutik: 0xa78bfa, monde: 0xf472b6 };
  const halo = (pos, teinte, taille, opacite) => {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: texHalo, color: couleur(teinte), transparent: true, opacity: opacite, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
    s.position.copy(pos);
    s.scale.set(taille, taille, 1);
    scene.add(s);
    return s;
  };
  const matCristal = (teinte) => new THREE.ShaderMaterial({
    transparent: true,
    uniforms: { uCouleur: { value: teinte }, uPulse: { value: 0 } },
    vertexShader: /* glsl */`
      varying vec3 vN; varying vec3 vV;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        vN = normalize(normalMatrix * normal);
        vV = -mv.xyz;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */`
      uniform vec3 uCouleur; uniform float uPulse;
      varying vec3 vN; varying vec3 vV;
      void main() {
        float f = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.0);
        vec3 c = uCouleur * (0.55 + 2.2 * f + 0.5 * uPulse) + vec3(1.0) * pow(f, 4.0) * 1.5;
        gl_FragColor = vec4(c, 0.88);
      }`,
  });
  const matEau = (ecoulement, bassin = 0) => new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { ...U_CIEL, ...U_BRUME, uTemps: U_TEMPS, uEcoulement: { value: ecoulement }, uBassin: { value: bassin } },
    vertexShader: /* glsl */`
      varying vec2 vUv; varying vec3 vMonde;
      void main() {
        vUv = uv;
        vec4 m = modelMatrix * vec4(position, 1.0);
        vMonde = m.xyz;
        gl_Position = projectionMatrix * viewMatrix * m;
      }`,
    fragmentShader: /* glsl */`
      uniform float uTemps, uEcoulement, uBassin;
      varying vec2 vUv; varying vec3 vMonde;
      ${GLSL_BRUIT}
      ${GLSL_CIEL}
      ${GLSL_BRUME}
      float vagues(vec2 q) { return fbm(q) * 0.6 + fbm(q * 2.7 + 5.0) * 0.4; }
      void main() {
        vec2 q = uEcoulement > 0.5
          ? vec2(vUv.x * 1.6, (1.0 - vUv.y) * 0.55 - uTemps * 0.9)
          : vMonde.xz * 0.55 + vec2(uTemps * 0.04, uTemps * 0.025);
        float e = 0.04;
        float h0 = vagues(q), hx = vagues(q + vec2(e, 0.0)), hy = vagues(q + vec2(0.0, e));
        vec3 N = normalize(vec3((h0 - hx) * 7.0, 1.0, (h0 - hy) * 7.0));
        vec3 V = normalize(cameraPosition - vMonde);
        vec3 R = reflect(-V, N);
        R.y = abs(R.y);
        vec3 reflet = ciel(R);
        float fres = 0.03 + 0.97 * pow(1.0 - max(dot(N, V), 0.0), 5.0);
        vec3 c = mix(vec3(0.02, 0.04, 0.055), reflet, clamp(fres + 0.12, 0.0, 1.0));
        c += uSoleilCouleur * pow(max(dot(R, uSoleil), 0.0), 220.0) * 7.0;
        float bord = min(vUv.x, 1.0 - vUv.x);
        float ecume = smoothstep(0.2, 0.0, bord) * smoothstep(0.35, 0.75, fbm(q * 4.0)) * uEcoulement;
        c = mix(c, vec3(0.9, 0.86, 0.92), ecume * 0.55);
        // Le bassin de la fontaine n'a pas de rive : il est opaque jusqu'à la margelle
        float alpha = mix(smoothstep(0.0, 0.1, bord), 1.0, uBassin) * 0.93;
        gl_FragColor = vec4(brume(c, vMonde), alpha);
      }`,
  });
  // Matière éclairée en temps réel (ailes du moulin) : même brume que le reste
  const matiereEclairee = (teinte) => {
    const m = new THREE.MeshLambertMaterial({ color: couleur(teinte) });
    m.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, U_BRUME);
      sh.vertexShader = sh.vertexShader.replace("#include <common>", "#include <common>\nvarying vec3 vMonde;")
        .replace("#include <project_vertex>", "#include <project_vertex>\nvMonde = (modelMatrix * vec4(transformed, 1.0)).xyz;");
      sh.fragmentShader = sh.fragmentShader.replace("#include <common>", "#include <common>\nvarying vec3 vMonde;\n" + GLSL_BRUME)
        .replace("#include <dithering_fragment>", "gl_FragColor.rgb = brume(gl_FragColor.rgb, vMonde);\n#include <dithering_fragment>");
    };
    m.customProgramCacheKey = () => "eclairee";
    return m;
  };
  for (const v of vivants) {
    const o = v.objet;
    o.geometry.computeBoundingBox();
    if (v.type === "moulin") {
      // Les ailes tournent autour de leur moyeu, sur l'axe horizontal tourné vers l'extérieur
      const moyeu = position("moulin_moyeu");
      const local = moyeu ? o.worldToLocal(moyeu.clone()) : o.geometry.boundingBox.getCenter(new THREE.Vector3());
      o.geometry.translate(-local.x, -local.y, -local.z);
      o.position.add(local);
      const d = v.donnees;
      const axe = new THREE.Vector3(d.axe_x || 1, d.axe_z || 0, -(d.axe_y || 0)).normalize();
      const base = o.quaternion.clone(), tourne = new THREE.Quaternion();
      o.material = matiereEclairee(0x8f7a64);
      animes.push((t) => { o.quaternion.multiplyQuaternions(tourne.setFromAxisAngle(axe, -t * 0.55), base); });
      continue;
    }
    if (v.type === "leds") {
      // Voyants de la baie du NAS : chaque voyant clignote à son rythme. Pour savoir quel sommet appartient
      // à quel voyant, on regroupe les triangles qui se touchent (une face), puis on recule du centre de la
      // face vers le centre du petit cube : les faces d'un même voyant tombent au même endroit.
      const g = o.geometry, P = g.getAttribute("position"), N = g.getAttribute("normal"), I = g.index;
      const parent = Int32Array.from({ length: P.count }, (_, i) => i);
      const chef = (i) => { while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i]; } return i; };
      if (I) {
        for (let k = 0; k < I.count; k += 3) {
          const a = chef(I.getX(k));
          parent[chef(I.getX(k + 1))] = a;
          parent[chef(I.getX(k + 2))] = a;
        }
      }
      const faces = new Map(), p = new THREE.Vector3(), n = new THREE.Vector3();
      for (let k = 0; k < P.count; k++) {
        const r = chef(k);
        if (!faces.has(r)) faces.set(r, { p: new THREE.Vector3(), n: new THREE.Vector3(), c: 0 });
        const f = faces.get(r);
        f.p.add(p.fromBufferAttribute(P, k));
        if (N) f.n.add(n.fromBufferAttribute(N, k));
        f.c++;
      }
      const centres = [], voyantDe = new Map();
      for (const [r, f] of faces) {
        const c = f.p.divideScalar(f.c).addScaledVector(f.n.divideScalar(f.c), -0.0115);
        let j = centres.findIndex((q) => q.distanceToSquared(c) < 0.0004);
        if (j < 0) { centres.push(c); j = centres.length - 1; }
        voyantDe.set(r, j);
      }
      const id = new Float32Array(P.count);
      for (let k = 0; k < P.count; k++) id[k] = voyantDe.get(chef(k));
      g.setAttribute("aVoyant", new THREE.BufferAttribute(id, 1));
      o.material = new THREE.ShaderMaterial({
        uniforms: { uTemps: U_TEMPS },
        vertexShader: /* glsl */`
          attribute float aVoyant; varying float vV;
          void main() { vV = aVoyant; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: /* glsl */`
          uniform float uTemps; varying float vV;
          float h(float x) { return fract(sin(x * 91.17 + 7.3) * 43758.5453); }
          void main() {
            float k = h(floor(vV + 0.5));
            float allume = step(0.3, fract(uTemps * (0.3 + k * 1.9) + k * 7.0));
            vec3 c = k < 0.78 ? vec3(0.35, 1.0, 0.55) : vec3(1.0, 0.68, 0.25);
            gl_FragColor = vec4(c * mix(0.2, 3.0, allume), 1.0);
          }`,
      });
      continue;
    }
    if (["glyphe", "anneau", "cristal", "cristal_roche"].includes(v.type)) {
      // Ces objets sont exportés avec leurs sommets en coordonnées du monde : on les recentre
      const centre = o.geometry.boundingBox.getCenter(new THREE.Vector3());
      o.geometry.translate(-centre.x, -centre.y, -centre.z);
      o.position.add(centre);
    }
    if (v.type === "glyphe") {
      const m = new THREE.MeshBasicMaterial({ color: couleur(0xb79cff) });
      o.material = m;
      animes.push((t) => m.color.setRGB(0.72, 0.6, 1.0).multiplyScalar(1.6 + 0.9 * Math.sin(t * 1.3 + v.rang * 0.9)));
    } else if (v.type === "anneau") {
      const m = new THREE.MeshBasicMaterial({ color: couleur(0xe879f9) });
      o.material = m;
      animes.push((t) => m.color.setRGB(0.9, 0.45, 1.0).multiplyScalar(1.1 + 0.5 * Math.sin(t * 0.9)));
      halo(o.position.clone().add(new THREE.Vector3(0, 0.5, 0)), 0xd946ef, 3.6, 0.2);
    } else if (v.type === "cristal") {
      const teinte = couleur(couleursCristal[v.projet] || 0xffffff);
      const m = matCristal(teinte);
      o.material = m;
      const h = halo(o.position, teinte.getHex(), 1.6, 0.45);
      const base = o.position.clone();
      animes.push((t) => {
        o.rotation.y = t * 0.5 + v.rang;
        o.position.y = base.y + Math.sin(t * 1.1 + v.rang * 2.0) * 0.12;
        h.position.copy(o.position);
        m.uniforms.uPulse.value = 0.5 + 0.5 * Math.sin(t * 2.0 + v.rang);
      });
    } else if (v.type === "cristal_roche") {
      const m = matCristal(couleur(0x7dd3fc));
      o.material = m;
      animes.push((t) => { m.uniforms.uPulse.value = 0.5 + 0.5 * Math.sin(t * 0.8); });
    } else if (v.type === "eau") {
      o.material = matEau(v.donnees.ecoulement ? 1 : 0, v.donnees.bassin ? 1 : 0);
      o.renderOrder = 2;
    } else if (v.type === "cascade") {
      const chute = v.donnees.chute || 40;
      o.material = new THREE.ShaderMaterial({
        transparent: true, depthWrite: false, side: THREE.DoubleSide,
        uniforms: { ...U_BRUME, ...U_CIEL, uTemps: U_TEMPS, uChute: { value: chute } },
        vertexShader: /* glsl */`
          varying vec2 vUv; varying vec3 vMonde;
          void main() {
            vUv = uv;
            vec4 m = modelMatrix * vec4(position, 1.0);
            vMonde = m.xyz;
            gl_Position = projectionMatrix * viewMatrix * m;
          }`,
        fragmentShader: /* glsl */`
          uniform float uTemps, uChute;
          varying vec2 vUv; varying vec3 vMonde;
          ${GLSL_BRUIT}
          ${GLSL_CIEL}
          ${GLSL_BRUME}
          void main() {
            float x = vUv.x, y = 1.0 - vUv.y;   // mètres de chute (le glTF retourne V)
            float n = fbm(vec2(x * 7.0, y * 0.35 - uTemps * 2.4));
            float n2 = fbm(vec2(x * 17.0 + 3.0, y * 0.9 - uTemps * 3.6));
            float stries = smoothstep(0.32, 0.82, n * 0.6 + n2 * 0.5);
            float bord = smoothstep(0.0, 0.2, x) * smoothstep(1.0, 0.8, x);
            float bas = 1.0 - smoothstep(uChute * 0.45, uChute, y);
            vec3 c = mix(vec3(0.62, 0.66, 0.8), vec3(1.0, 0.97, 0.95), stries);
            c *= mix(vec3(1.0), uSoleilCouleur * 1.25, 0.35);
            float a = (0.3 + 0.62 * stries) * bord * bas * mix(0.75, 1.0, smoothstep(0.0, 1.5, y));
            gl_FragColor = vec4(brume(c * 1.1, vMonde), a);
          }`,
      });
      o.renderOrder = 3;
    }
  }

  /* ----- halos : lanternes, lustres, lampe du phare, cristaux sous l'île ----- */
  for (const [nom, o] of parNom) {
    if (/^(lanterne|lustre)_/.test(nom)) {
      const lustre = nom.startsWith("lustre");
      const taille = lustre ? 1.1 : /chemin|porte/.test(nom) ? 1.6 : /atelier|taverne/.test(nom) ? 0.9 : 1.3;
      const s = halo(o.getWorldPosition(new THREE.Vector3()), lustre ? 0xffb860 : 0xffa94d, taille, lustre ? 0.35 : 0.8);
      const ph = Math.random() * 10, base = s.material.opacity;
      animes.push((t) => { s.material.opacity = base * (0.85 + 0.17 * Math.sin(t * 7.0 + ph) * Math.sin(t * 2.3 + ph)); });
    } else if (/^cristal_roche_/.test(nom)) {
      halo(o.getWorldPosition(new THREE.Vector3()), 0x93c5fd, 6, 0.4);
    }
  }

  /* ----- feux : braseros de la cour, cheminée de la grande salle, foyer de la forge ----- */
  {
    const c = document.createElement("canvas");
    c.width = 64; c.height = 128;
    const g = c.getContext("2d");
    const d = g.createRadialGradient(32, 92, 2, 32, 80, 60);
    d.addColorStop(0, "rgba(255,255,255,1)");
    d.addColorStop(0.25, "rgba(255,255,255,0.6)");
    d.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = d;
    g.beginPath();
    g.ellipse(32, 80, 22, 46, 0, 0, Math.PI * 2);
    g.fill();
    const texFlamme = new THREE.CanvasTexture(c);
    texFlamme.colorSpace = THREE.SRGBColorSpace;
    for (const [nom, o] of parNom) {
      if (!/^feu_/.test(nom)) continue;
      const p = o.getWorldPosition(new THREE.Vector3());
      const e = /brasero/.test(nom) ? 0.9 : /forge/.test(nom) ? 0.8 : 1.0;
      const langues = [];
      for (let k = 0; k < 6; k++) {
        const s = new THREE.Sprite(new THREE.SpriteMaterial({
          map: texFlamme, color: couleur(k < 2 ? 0xffd58a : 0xff7a2e), transparent: true, opacity: 0,
          blending: THREE.AdditiveBlending, depthWrite: false, fog: false,
        }));
        scene.add(s);
        langues.push({ s, decalage: k / 6, cote: (k % 3 - 1) * 0.12 });
      }
      const lueur = halo(p.clone().add(new THREE.Vector3(0, 0.35 * e, 0)), 0xff8a3d, 3.4 * e, 0.45);
      const ph = Math.random() * 10;
      animes.push((t) => {
        for (const l of langues) {
          const k = (t * 1.5 + l.decalage) % 1;
          l.s.position.set(p.x + (l.cote + Math.sin(t * 5 + l.decalage * 9) * 0.04) * e, p.y + k * 0.75 * e, p.z + Math.cos(t * 4.3 + l.decalage * 7) * 0.05 * e);
          const taille = (0.65 - k * 0.45) * e;
          l.s.scale.set(taille, taille * 1.7, 1);
          l.s.material.opacity = Math.sin(Math.PI * k) * 0.85;
        }
        lueur.material.opacity = 0.4 + 0.1 * Math.sin(t * 9 + ph) * Math.sin(t * 3.7 + ph);
      });
    }
  }

  /* ----- jet de la fontaine, sur la place du marché ----- */
  const jet = position("fontaine_jet");
  if (jet) {
    const n = MODESTE ? 70 : 140;
    const graines = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { graines[i * 3] = rnd(); graines[i * 3 + 1] = rnd(); graines[i * 3 + 2] = rnd(); }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute("aGraine", new THREE.BufferAttribute(graines, 3));
    const gouttes = new THREE.Points(g, new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      uniforms: { uTemps: U_TEMPS, uJet: { value: jet }, uTaille: { value: 22 * QUALITE.ratio }, uCarte: { value: texHalo } },
      vertexShader: /* glsl */`
        uniform float uTemps, uTaille; uniform vec3 uJet; attribute vec3 aGraine; varying float vA;
        void main() {
          // Chaque goutte part du sommet, s'écarte et retombe dans le bassin (une parabole)
          float k = fract(uTemps * 0.75 + aGraine.x);
          float t = k * 1.05;
          float a = aGraine.y * 6.2832;
          float v = 0.5 + aGraine.z * 0.55;
          vec3 p = uJet + vec3(cos(a) * v * t, 1.3 * t - 4.9 * t * t, sin(a) * v * t);
          vec4 mv = viewMatrix * vec4(p, 1.0);
          vA = (1.0 - smoothstep(0.75, 1.0, k)) * 0.55;
          gl_PointSize = uTaille / -mv.z;
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: /* glsl */`
        uniform sampler2D uCarte; varying float vA;
        void main() {
          float a = texture2D(uCarte, gl_PointCoord).a * vA;
          gl_FragColor = vec4(vec3(0.85, 0.9, 1.0) * a, a);
        }`,
    }));
    gouttes.frustumCulled = false;
    scene.add(gouttes);
  }

  const lampe = position("phare_lampe");
  if (lampe) {
    halo(lampe, 0xffd59a, 9, 0.9);
    const longueur = 140;
    const cone = new THREE.CylinderGeometry(0.4, 11, longueur, 32, 1, true);
    cone.translate(0, longueur / 2, 0);
    cone.rotateZ(-Math.PI / 2);
    const matFaisceau = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
      uniforms: { uCouleur: { value: couleur(0xffd9a0) }, uLongueur: { value: longueur } },
      vertexShader: /* glsl */`
        varying float vX; varying vec3 vN; varying vec3 vV;
        void main() {
          vX = position.x;
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          vN = normalize(normalMatrix * normal);
          vV = normalize(-mv.xyz);
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: /* glsl */`
        uniform vec3 uCouleur; uniform float uLongueur;
        varying float vX; varying vec3 vN; varying vec3 vV;
        void main() {
          float l = clamp(vX / uLongueur, 0.0, 1.0);
          float bord = pow(abs(dot(normalize(vN), vV)), 1.5);
          float a = (1.0 - l) * (1.0 - l) * bord * 0.42;
          gl_FragColor = vec4(uCouleur * a, a);
        }`,
    });
    const pivot = new THREE.Group();
    pivot.position.copy(lampe);
    const f1 = new THREE.Mesh(cone, matFaisceau);
    const f2 = new THREE.Mesh(cone, matFaisceau);
    f2.rotation.y = Math.PI;
    f1.rotation.z = f2.rotation.z = -0.04;
    pivot.add(f1, f2);
    scene.add(pivot);
    animes.push((t) => { pivot.rotation.y = t * 0.55; });
  }

  /* ----- brume de la cascade ----- */
  const haut = position("cascade_haut"), bas = position("cascade_bas");
  if (haut && bas) {
    const bouffees = [];
    for (let i = 0; i < 26; i++) {
      const enBas = i >= 8;
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: texNuage, color: couleur(enBas ? 0xf3d9e4 : 0xffffff), transparent: true, opacity: 0, depthWrite: false }));
      scene.add(s);
      bouffees.push({ s, enBas, decalage: rnd(), cote: rnd() - 0.5 });
    }
    animes.push((t) => {
      for (const b of bouffees) {
        const k = (t * (b.enBas ? 0.05 : 0.12) + b.decalage) % 1;
        const ref = b.enBas ? bas : haut;
        const taille = b.enBas ? 9 + k * 16 : 1.2 + k * 3.5;
        b.s.position.set(ref.x + b.cote * (b.enBas ? 10 : 2), ref.y + (b.enBas ? k * 6 - 2 : -k * 2.5), ref.z + b.cote * (b.enBas ? 6 : 1.5));
        b.s.scale.set(taille, taille * 0.7, 1);
        b.s.material.opacity = (b.enBas ? 0.28 : 0.22) * Math.sin(Math.PI * k);
      }
    });
  }

  /* ----- fumées : cheminée de la forge, maison du gardien du phare ----- */
  for (const [nom, o] of parNom) {
    if (!/^fumee/.test(nom)) continue;
    const fumee = o.getWorldPosition(new THREE.Vector3());
    const bouffees = [];
    for (let i = 0; i < 16; i++) {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: texNuage, color: couleur(0xb9a7c9), transparent: true, opacity: 0, depthWrite: false }));
      scene.add(s);
      bouffees.push({ s, decalage: i / 16 });
    }
    animes.push((t) => {
      for (const b of bouffees) {
        const k = (t * 0.07 + b.decalage) % 1;
        b.s.position.set(fumee.x + k * 3.2 + Math.sin(k * 9 + b.decalage * 20) * 0.3, fumee.y + k * 9, fumee.z - k * 1.4);
        const taille = 0.8 + k * 4.5;
        b.s.scale.set(taille, taille * 0.7, 1);
        b.s.material.opacity = 0.32 * Math.sin(Math.PI * Math.min(1, k * 1.2)) * (1 - k);
      }
    });
  }

  /* ----- herbe : des touffes posées sur les sols (ville, campagne), colorées par l'atlas cuit (ombres comprises) ----- */
  const semis = [];
  const va = new THREE.Vector3(), vb = new THREE.Vector3(), vc = new THREE.Vector3(), ab = new THREE.Vector3(), ac = new THREE.Vector3();
  for (const terrain of terrains) {
    const pixelsTerrain = pixelsTerrains.get(terrain.userData.atlas);
    if (!pixelsTerrain) continue;
    const geo = terrain.geometry;
    const P = geo.getAttribute("position"), UV = geo.getAttribute("uv"), I = geo.index;
    const nbTri = I ? I.count / 3 : P.count / 3;
    const cumul = new Float64Array(nbTri);
    const sommet = (k) => (I ? I.getX(k) : k);
    let total = 0;
    for (let t = 0; t < nbTri; t++) {
      va.fromBufferAttribute(P, sommet(3 * t)).applyMatrix4(terrain.matrixWorld);
      vb.fromBufferAttribute(P, sommet(3 * t + 1)).applyMatrix4(terrain.matrixWorld);
      vc.fromBufferAttribute(P, sommet(3 * t + 2)).applyMatrix4(terrain.matrixWorld);
      ab.subVectors(vb, va); ac.subVectors(vc, va);
      const n = ab.cross(ac);
      const aire = n.length() * 0.5;
      let poids = 0;
      if (aire > 0 && Math.abs(n.y) / (2 * aire) > 0.82) {
        const cx = (va.x + vb.x + vc.x) / 3, cz = (va.z + vb.z + vc.z) / 3;
        let d = 1e9;
        for (const l of lieux) d = Math.min(d, Math.hypot(cx - l.x, cz - l.z));
        poids = aire * (0.22 + Math.exp(-(d * d) / (26 * 26)));
      }
      total += poids;
      cumul[t] = total;
    }
    semis.push({ terrain, pixelsTerrain, P, UV, nbTri, cumul, total, sommet });
  }
  const totalSemis = semis.reduce((s, x) => s + x.total, 0);
  for (const { terrain, pixelsTerrain, P, UV, nbTri, cumul, total, sommet } of semis) {
    const N = Math.round(QUALITE.herbe * total / Math.max(1e-9, totalSemis));
    if (N < 1) continue;
    const iPos = new Float32Array(N * 3), iUv = new Float32Array(N * 2), iParam = new Float32Array(N * 4);
    const { width: W, height: H, data: px } = pixelsTerrain;
    const r2 = hasard(31 + semis.findIndex((s) => s.terrain === terrain));
    let n = 0;
    for (let essai = 0; essai < N * 4 && n < N; essai++) {
      const cible = r2() * total;
      let lo = 0, hi = nbTri - 1;
      while (lo < hi) { const m = (lo + hi) >> 1; if (cumul[m] < cible) lo = m + 1; else hi = m; }
      const t = lo;
      let s1 = Math.sqrt(r2()), s2 = r2();
      const ka = 1 - s1, kb = s1 * (1 - s2), kc = s1 * s2;
      const ia = sommet(3 * t), ib = sommet(3 * t + 1), ic = sommet(3 * t + 2);
      const u = UV.getX(ia) * ka + UV.getX(ib) * kb + UV.getX(ic) * kc;
      const v = UV.getY(ia) * ka + UV.getY(ib) * kb + UV.getY(ic) * kc;
      const p = (Math.min(H - 1, Math.max(0, Math.floor(v * H))) * W + Math.min(W - 1, Math.max(0, Math.floor(u * W)))) * 4;
      const r = px[p] / 255, g = px[p + 1] / 255, b = px[p + 2] / 255;
      // L'herbe pousse là où le sol cuit est vert : pas sur le chemin, ni sous les bâtiments, ni dans la boue
      if (g < r * 0.92 || g < b * 1.1 || g < 0.05) continue;
      va.fromBufferAttribute(P, ia).applyMatrix4(terrain.matrixWorld);
      vb.fromBufferAttribute(P, ib).applyMatrix4(terrain.matrixWorld);
      vc.fromBufferAttribute(P, ic).applyMatrix4(terrain.matrixWorld);
      iPos[n * 3] = va.x * ka + vb.x * kb + vc.x * kc;
      iPos[n * 3 + 1] = va.y * ka + vb.y * kb + vc.y * kc;
      iPos[n * 3 + 2] = va.z * ka + vb.z * kb + vc.z * kc;
      iUv[n * 2] = u;
      iUv[n * 2 + 1] = v;
      iParam[n * 4] = r2() * Math.PI * 2;
      iParam[n * 4 + 1] = 0.7 + r2() * 0.6;
      iParam[n * 4 + 2] = r2();
      iParam[n * 4 + 3] = r2() < 0.05 ? 1 + Math.floor(r2() * 4) : 0;
      n++;
    }
    // Une touffe : trois brins de deux segments, en éventail
    const brins = [];
    for (let k = 0; k < 3; k++) {
      const a = (k / 3) * Math.PI * 2 + 0.4;
      const ox = Math.cos(a) * 0.04, oz = Math.sin(a) * 0.04;
      const lx = -Math.sin(a), lz = Math.cos(a);
      const pench = 0.25 + 0.15 * k;
      const pts = [
        [-0.022, 0.0], [0.022, 0.0], [-0.016, 0.5], [0.016, 0.5],
      ];
      const base = brins.length / 3;
      for (const [w, y] of pts) brins.push(ox + lx * w + Math.cos(a) * pench * y * 0.5, y, oz + lz * w + Math.sin(a) * pench * y * 0.5);
      brins.push(ox + Math.cos(a) * pench * 0.5, 1.0, oz + Math.sin(a) * pench * 0.5);
    }
    const indices = [];
    for (let k = 0; k < 3; k++) {
      const b = k * 5;
      indices.push(b, b + 1, b + 3, b, b + 3, b + 2, b + 2, b + 3, b + 4);
    }
    const geoHerbe = new THREE.InstancedBufferGeometry();
    geoHerbe.setAttribute("position", new THREE.Float32BufferAttribute(brins, 3));
    geoHerbe.setIndex(indices);
    geoHerbe.setAttribute("iPos", new THREE.InstancedBufferAttribute(iPos, 3));
    geoHerbe.setAttribute("iUv", new THREE.InstancedBufferAttribute(iUv, 2));
    geoHerbe.setAttribute("iParam", new THREE.InstancedBufferAttribute(iParam, 4));
    geoHerbe.instanceCount = n;
    geoHerbe.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 80);
    const aTerrain = atlas.get(terrain.userData.atlas);
    const matHerbe = new THREE.ShaderMaterial({
      side: THREE.DoubleSide,
      uniforms: { ...U_BRUME, uTemps: U_TEMPS, uAtlas: { value: aTerrain.texture }, uDistMax: { value: MODESTE ? 30 : 46 } },
      vertexShader: /* glsl */`
        uniform sampler2D uAtlas; uniform float uTemps, uDistMax;
        attribute vec3 iPos; attribute vec2 iUv; attribute vec4 iParam;
        varying vec3 vCouleur; varying float vH; varying vec3 vMonde; varying float vType; varying float vVar;
        void main() {
          float ang = iParam.x, ech = iParam.y, ph = iParam.z;
          float h = mix(0.3, 0.55, fract(ph * 7.13)) * ech;
          vec3 loc = vec3(position.x * ech, position.y * h, position.z * ech);
          float c = cos(ang), s = sin(ang);
          loc = vec3(c * loc.x - s * loc.z, loc.y, s * loc.x + c * loc.z);
          float d = distance(iPos.xz, cameraPosition.xz);
          float fondu = 1.0 - smoothstep(uDistMax * 0.7, uDistMax, d);
          loc *= fondu;
          float vent = sin(uTemps * 1.7 + ph * 6.28 + iPos.x * 0.35 + iPos.z * 0.2) * 0.5 + 0.5;
          float rafale = sin(uTemps * 0.45 + iPos.x * 0.06 - iPos.z * 0.03) * 0.5 + 0.5;
          float y = position.y;
          loc.xz += vec2(0.94, 0.34) * (0.04 + 0.16 * vent * rafale) * y * y * h * fondu;
          vec3 monde = iPos + loc;
          vCouleur = textureLod(uAtlas, iUv, 0.0).rgb;
          vH = y;
          vType = iParam.w;
          vVar = fract(ph * 13.7);
          vMonde = monde;
          gl_Position = projectionMatrix * viewMatrix * vec4(monde, 1.0);
        }`,
      fragmentShader: /* glsl */`
        varying vec3 vCouleur; varying float vH; varying vec3 vMonde; varying float vType; varying float vVar;
        ${GLSL_BRUME}
        void main() {
          vec3 c = vCouleur * mix(0.5, 1.4, vH) * mix(0.9, 1.12, vVar);
          if (vType > 0.5 && vH > 0.8) {
            vec3 fleur = vType < 1.5 ? vec3(1.0, 0.55, 0.75) : vType < 2.5 ? vec3(1.0, 0.95, 0.9) : vType < 3.5 ? vec3(0.75, 0.55, 1.0) : vec3(1.0, 0.8, 0.35);
            c = fleur * (0.35 + 2.4 * dot(vCouleur, vec3(0.3, 0.59, 0.11)));
          }
          gl_FragColor = vec4(brume(c, vMonde), 1.0);
        }`,
    });
    const herbe = new THREE.Mesh(geoHerbe, matHerbe);
    herbe.frustumCulled = false;
    scene.add(herbe);
    aTerrain.abonnes.push((tex) => { matHerbe.uniforms.uAtlas.value = tex; });
  }

  /* ----- lucioles autour des lieux de chaque chapitre ----- */
  {
    const n = QUALITE.lucioles;
    const pos = new Float32Array(n * 3);
    const phase = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const l = lieux[i % Math.max(1, lieux.length)] || new THREE.Vector3();
      const x = l.x + (rnd() - 0.5) * 30, z = l.z + (rnd() - 0.5) * 30;
      pos[i * 3] = x;
      pos[i * 3 + 1] = (carte ? carte.hauteur(x, z, l.y - 1.4) : l.y - 1.4) + 0.4 + rnd() * 2.8;
      pos[i * 3 + 2] = z;
      phase[i] = rnd() * 100;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("aPhase", new THREE.BufferAttribute(phase, 1));
    const m = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      uniforms: { uTemps: U_TEMPS, uTaille: { value: 90 * QUALITE.ratio }, uCarte: { value: texHalo } },
      vertexShader: /* glsl */`
        uniform float uTemps, uTaille; attribute float aPhase; varying float vA;
        void main() {
          vec3 p = position;
          p.x += sin(uTemps * 0.4 + aPhase) * 0.9;
          p.y += sin(uTemps * 0.6 + aPhase * 1.7) * 0.5;
          p.z += cos(uTemps * 0.35 + aPhase * 0.8) * 0.9;
          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          vA = pow(0.5 + 0.5 * sin(uTemps * 1.8 + aPhase * 3.0), 3.0);
          gl_PointSize = uTaille / -mv.z;
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: /* glsl */`
        uniform sampler2D uCarte; varying float vA;
        void main() {
          float a = texture2D(uCarte, gl_PointCoord).a * vA;
          gl_FragColor = vec4(vec3(1.0, 0.82, 0.45) * 2.0 * a, a);
        }`,
    });
    const points = new THREE.Points(g, m);
    points.frustumCulled = false;
    scene.add(points);
  }

  /* ----- oiseaux : deux petites volées qui tournent autour de l'île ----- */
  {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, 0.3, 0, 0, -0.25, -0.75, 0.05, -0.1, 0.75, 0.05, -0.1], 3));
    g.setAttribute("aAile", new THREE.Float32BufferAttribute([0, 0, 1, 1], 1));
    g.setIndex([0, 1, 2, 0, 3, 1]);
    const m = new THREE.MeshBasicMaterial({ color: 0x2b2238, side: THREE.DoubleSide });
    m.onBeforeCompile = (sh) => {
      sh.uniforms.uTemps = U_TEMPS;
      sh.vertexShader = sh.vertexShader
        .replace("#include <common>", "#include <common>\nattribute float aAile;\nuniform float uTemps;")
        .replace("#include <begin_vertex>", "#include <begin_vertex>\ntransformed.y += aAile * sin(uTemps * 9.0 + float(gl_InstanceID) * 1.9) * 0.42;");
    };
    const nb = MODESTE ? 10 : 18;
    const oiseaux = new THREE.InstancedMesh(g, m, nb);
    oiseaux.frustumCulled = false;
    const params = [];
    for (let i = 0; i < nb; i++) {
      const volee = i % 2;
      params.push({
        r: (volee ? 168 : 128) + rnd() * 14, h: (volee ? 46 : 32) + rnd() * 6, v: (volee ? 0.03 : -0.04) * (0.92 + rnd() * 0.16),
        a: (volee ? 2.0 : 4.5) + rnd() * 0.6, d: rnd() * 6, e: 1.3 + rnd() * 0.6,
      });
    }
    const mat4 = new THREE.Matrix4(), q = new THREE.Quaternion(), ech = new THREE.Vector3(), p = new THREE.Vector3(), dir = new THREE.Vector3();
    scene.add(oiseaux);
    animes.push((t) => {
      params.forEach((b, i) => {
        const a = b.a + t * b.v;
        p.set(Math.cos(a) * b.r, b.h + Math.sin(t * 0.5 + b.d) * 1.5, Math.sin(a) * b.r);
        dir.set(-Math.sin(a) * Math.sign(b.v), 0, Math.cos(a) * Math.sign(b.v));
        q.setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
        ech.setScalar(b.e);
        mat4.compose(p, q, ech);
        oiseaux.setMatrixAt(i, mat4);
      });
      oiseaux.instanceMatrix.needsUpdate = true;
    });
  }

  /* ----- habitants : le peuple, Ernest, les dialogues, le mode libre, les autres visiteurs ----- */
  // Les personnages ne sont pas cuits : une lumière de ciel et le soleil couchant les éclairent.
  // Quand la caméra entre dans un bâtiment, le soleil s'efface et la lumière devient celle des lanternes.
  const lumiereCiel = new THREE.HemisphereLight(0xd6c0e6, 0x5e4a3a, 1.25);
  const lumiereSoleil = new THREE.DirectionalLight(0xffc48e, 2.1);
  lumiereSoleil.position.copy(soleil).multiplyScalar(200);
  scene.add(lumiereCiel, lumiereSoleil);
  const CIEL_DEHORS = couleur(0xd6c0e6), CIEL_DEDANS = couleur(0xffc58f);
  const SOL_DEHORS = couleur(0x5e4a3a), SOL_DEDANS = couleur(0x4a3020);
  let dedansLisse = 0;

  let peuple = null, royaume = null, dialogue = null, exploration = null, multijoueur = null, ernest = -1;
  const guideDuChapitre = (c) => guides[GUIDE_CHAPITRE[Math.max(0, Math.min(c, GUIDE_CHAPITRE.length - 1))]] || guides.guide_porte || null;
  if (carte && chemins && Object.keys(geometriesPieces).length) {
    try {
      peuple = new Peuple(scene, geometriesPieces, { uniforms: U_BRUME, glsl: GLSL_BRUME }, QUALITE.habitants);
      royaume = new Royaume(peuple, carte, chemins, reperesPnj, MODESTE);
      const g = guideDuChapitre(1);
      const depart = g ? g.pos.clone() : new THREE.Vector3();
      if (g) depart.y = carte.hauteur(depart.x, depart.z, depart.y);
      ernest = peuple.ajouterHumain({ ...ERNEST }, { pos: depart, cap: g ? g.regard : 0, anim: "repos" });
      dialogue = new Dialogue(langue);
      exploration = new Exploration({ camera, carte, peuple, ernest, dialogue, royaume, langue, canvas });
      // Pendant la visite, les autres visiteurs se rassemblent autour d'Ernest, au lieu de leur chapitre
      const rassemblements = {};
      GUIDE_CHAPITRE.forEach((nom, c) => {
        const r = guides[nom];
        if (r) rassemblements[c] = new THREE.Vector3(r.pos.x, carte.hauteur(r.pos.x, r.pos.z, r.pos.y), r.pos.z);
      });
      multijoueur = new Multijoueur({ config: MULTIJOUEUR, peuple, langue, camera, guides: rassemblements });
      multijoueur.demarrer().catch((e) => console.warn("[ile3d] temps réel indisponible :", e && e.message));
      surLangue.push((l) => { dialogue.langue = l; exploration.langue = l; multijoueur.langue = l; });
      racine.classList.add("avec-habitants");
    } catch (e) {
      console.warn("[ile3d] habitants indisponibles :", e);
      peuple = royaume = dialogue = exploration = multijoueur = null;
    }
  }

  /* ----- rendu : bloom léger, rayons de soleil, vignette et grain ----- */
  const cible = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: QUALITE.msaa });
  const composer = new EffectComposer(renderer, cible);
  composer.setPixelRatio(QUALITE.ratio);
  composer.addPass(new RenderPass(scene, camera));
  composer.addPass(new UnrealBloomPass(new THREE.Vector2(256, 256), 0.55, 0.6, 0.86));
  let rayons = null;
  if (QUALITE.rayons) {
    rayons = new ShaderPass({
      uniforms: { tDiffuse: { value: null }, uSoleilEcran: { value: new THREE.Vector2(0.5, 0.5) }, uForce: { value: 0 } },
      vertexShader: /* glsl */`varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
      fragmentShader: /* glsl */`
        uniform sampler2D tDiffuse; uniform vec2 uSoleilEcran; uniform float uForce; varying vec2 vUv;
        void main() {
          vec4 c = texture2D(tDiffuse, vUv);
          if (uForce > 0.001) {
            vec2 pas = (vUv - uSoleilEcran) / 28.0 * 0.85;
            vec2 p = vUv;
            float decroit = 1.0;
            vec3 somme = vec3(0.0);
            for (int i = 0; i < 28; i++) {
              p -= pas;
              vec3 s = texture2D(tDiffuse, clamp(p, 0.0, 1.0)).rgb;
              float l = max(dot(s, vec3(0.3, 0.5, 0.2)) - 0.8, 0.0);
              somme += s * l * decroit;
              decroit *= 0.93;
            }
            c.rgb += somme / 28.0 * uForce * vec3(1.0, 0.82, 0.62);
          }
          gl_FragColor = c;
        }`,
    });
    composer.addPass(rayons);
  }
  const etalonnage = new ShaderPass({
    uniforms: { tDiffuse: { value: null }, uTemps: { value: 0 }, uVignette: { value: 0.38 }, uGrain: { value: 0.035 } },
    vertexShader: /* glsl */`varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: /* glsl */`
      uniform sampler2D tDiffuse; uniform float uTemps, uVignette, uGrain; varying vec2 vUv;
      float h(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
      void main() {
        vec4 c = texture2D(tDiffuse, vUv);
        vec2 d = vUv - 0.5;
        c.rgb *= 1.0 - uVignette * dot(d, d) * 1.9;
        c.rgb += (h(vUv * 1371.0 + fract(uTemps) * 91.0) - 0.5) * uGrain * (0.25 + c.rgb);
        gl_FragColor = c;
      }`,
  });
  composer.addPass(etalonnage);
  composer.addPass(new OutputPass());

  /* ----- taille de l'écran, objectif de la caméra ----- */
  let largeur = 1, hauteur = 1, elargir = 1;
  function redimensionner() {
    largeur = window.innerWidth;
    hauteur = window.innerHeight;
    renderer.setSize(largeur, hauteur, false);
    composer.setSize(largeur, hauteur);
    const aspect = largeur / hauteur;
    // Écran étroit : on élargit le champ pour garder les bâtiments en entier
    const hfov = 2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(22)) * 16 / 9);
    const vfovEtroit = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(hfov / 2) / aspect));
    elargir = THREE.MathUtils.clamp(1 + (vfovEtroit / 44 - 1) * 0.6, 1, 1.65);
    mesurer();
  }
  redimensionner();
  window.addEventListener("resize", redimensionner);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(mesurer);

  /* ----- pointeur : léger effet de parallaxe ----- */
  const pointeur = new THREE.Vector2(), pointeurLisse = new THREE.Vector2();
  if (!reduceMotion && !tactile) {
    window.addEventListener("pointermove", (e) => {
      pointeur.set((e.clientX / largeur) * 2 - 1, (e.clientY / hauteur) * 2 - 1);
    }, { passive: true });
  }

  /* ----- modes : visite guidée (défilement) ou mode libre (on marche avec Ernest) ----- */
  let mode = "visite";
  // Passage d'un mode à l'autre : la caméra glisse de son ancienne pose vers la nouvelle
  const fondu = { k: 1, duree: 1, pos: new THREE.Vector3(), quat: new THREE.Quaternion(), fov: 44 };
  const hud = document.querySelector(".hud-libre");
  const boutonsLibre = [...document.querySelectorAll("[data-libre]")];
  function changerMode(m) {
    if (m === mode || (m === "libre" && !exploration)) return;
    fondu.k = 0;
    fondu.duree = m === "libre" ? 1.8 : 1.4;
    fondu.pos.copy(camera.position);
    fondu.quat.copy(camera.quaternion);
    fondu.fov = camera.fov;
    mode = m;
    racine.classList.toggle("mode-libre", m === "libre");
    if (hud) hud.hidden = m !== "libre";
    if (m === "libre") {
      // On part du lieu du chapitre en cours, là où Ernest attendait
      // Ernest se tourne vers ce que regardait la visite (l'intérieur de la pièce, le cœur du royaume)
      const g = guideDuChapitre(chapitreActuel);
      const h = peuple.humains[ernest];
      const depart = g ? g.pos : h.pos;
      const cap = Math.hypot(vise.x - depart.x, vise.z - depart.z) > 1 ? Math.atan2(vise.x - depart.x, vise.z - depart.z) : h.cap;
      exploration.activer(depart, cap);
      dialogue.montrerBulle(null, 0, 0, 0);
      pointeur.set(0, 0);
    } else {
      exploration.desactiver();
      guideActuel = -1;
      salueAuChapitre = -1;
    }
    boutonsLibre.forEach((b) => b.setAttribute("aria-pressed", String(m === "libre")));
  }
  boutonsLibre.forEach((b) => b.addEventListener("click", (e) => {
    e.preventDefault();
    changerMode(mode === "libre" ? "visite" : "libre");
  }));
  document.querySelector(".hud-retour")?.addEventListener("click", () => changerMode("visite"));
  // Échap revient à la visite (sauf s'il ferme d'abord un dialogue) : écouté avant le mode libre
  window.addEventListener("keydown", (e) => {
    if (e.code !== "Escape" || mode !== "libre" || (dialogue && dialogue.ouvert)) return;
    if (e.target && /INPUT|TEXTAREA/.test(e.target.tagName)) return;
    changerMode("visite");
  }, true);
  if (/[?&]libre\b/.test(location.search) && exploration) requestAnimationFrame(() => changerMode("libre"));

  /* ----- Ernest pendant la visite : il attend au lieu de chaque chapitre, salue, puis présente ----- */
  let guideActuel = -1, salueAuChapitre = -1, debutSalut = -10;
  function majErnestVisite(e, t, dt) {
    const h = peuple && peuple.humains[ernest];
    if (!h) return;
    const c = e.t > 0.5 ? e.vers : e.de;
    const g = guideDuChapitre(c);
    if (!g) return;
    if (c !== guideActuel) {
      guideActuel = c;
      h.pos.set(g.pos.x, carte.hauteur(g.pos.x, g.pos.z, g.pos.y), g.pos.z);
      h.cap = g.regard;
    }
    const arrete = e.de === e.vers;
    if (arrete && salueAuChapitre !== c) { salueAuChapitre = c; debutSalut = t; }
    // Il se tourne vers le visiteur (la caméra)
    const vers = Math.atan2(camera.position.x - h.pos.x, camera.position.z - h.pos.z);
    const ecart = ((vers - h.cap + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
    h.cap += ecart * Math.min(1, dt * 2.5);
    h.anim = t - debutSalut < 2.4 ? "salut" : arrete ? "parle" : "repos";
  }

  /* ----- bulle du personnage du chapitre (visite guidée) ----- */
  const ecranBulle = new THREE.Vector3();
  function majBulle(y) {
    if (!dialogue) return;
    const cle = mode === "visite" ? BULLE_CHAPITRE[chapitreActuel] : null;
    const n = cle && royaume && royaume.nommes[cle];
    const h = n && peuple.humains[n.id];
    if (!h) { dialogue.montrerBulle(null, 0, 0, 0); return; }
    ecranBulle.set(h.pos.x, h.pos.y + 2.05, h.pos.z).project(camera);
    const visible = ecranBulle.z < 1 && Math.abs(ecranBulle.x) < 0.9 && ecranBulle.y < 0.85 && ecranBulle.y > -0.6
      && h.pos.distanceTo(camera.position) < 40;
    const o = visible ? lisse(0.45, 0.95, opacitePanneau(chapitreActuel, y)) : 0;
    let x = (ecranBulle.x + 1) / 2 * largeur;
    const yb = (1 - ecranBulle.y) / 2 * hauteur;
    // La bulle ne doit pas couvrir le texte du chapitre : on la pousse à côté du panneau
    const panneau = panneaux[chapitreActuel];
    if (o > 0 && panneau && !petitEcran()) {
      const r = panneau.getBoundingClientRect(), demi = 140;
      if (x + demi > r.left - 20 && x - demi < r.right + 20 && yb > r.top - 30 && yb - 100 < r.bottom) {
        x = panneau.classList.contains("cote-droite") ? r.left - 20 - demi : r.right + 20 + demi;
      }
    }
    dialogue.montrerBulle(cle, x, yb, o);
  }

  /* ----- boucle ----- */
  const horloge = new THREE.Clock();
  let yLisse = window.scrollY;
  let decalage = 0;
  // Introduction : à l'arrivée en haut de page, la caméra descend des nuages jusqu'à la vue d'ensemble
  let intro = !reduceMotion && window.scrollY < 10 ? 0 : 1;
  const pos = new THREE.Vector3(), vise = new THREE.Vector3(), droite = new THREE.Vector3(), haut2 = new THREE.Vector3();
  const versSoleil = new THREE.Vector3(), ecran = new THREE.Vector3(), regard = new THREE.Vector3();
  const moi = { mode: "visite", chapitre: 0, pos: new THREE.Vector3(), cap: 0 };

  /* La caméra de la visite : un point du trajet choisi par le défilement */
  function poseVisite(dt, t) {
    const e = etape(yLisse);
    const k = doux(Math.min(1, Math.max(0, e.t)));
    const u = THREE.MathUtils.lerp(uChapitre(e.de), uChapitre(e.vers), k);
    courbeCam.getPoint(u, pos);
    courbeCible.getPoint(u, vise);
    // Écran en hauteur : les vues d'ensemble reculent pour garder tout le royaume dans le cadre
    const aspect = largeur / hauteur;
    if (aspect < 1.2) {
      const poids = (CHAPITRES_LARGES.has(e.de) ? 1 - k : 0) + (CHAPITRES_LARGES.has(e.vers) && e.vers !== e.de ? k : 0);
      const recul = 1 + (Math.min(2.1, 1.35 / aspect) - 1) * Math.min(1, poids);
      pos.sub(vise).multiplyScalar(recul).add(vise);
    }
    if (intro < 1) {
      const ki = doux(intro);
      const depart = regard.subVectors(pos, vise).multiplyScalar(1.6).add(vise).add(new THREE.Vector3(0, 60, 0));
      pos.lerpVectors(depart, pos, ki);
    }

    // Parallaxe et respiration, plus marquées sur les vues d'ensemble
    pointeurLisse.lerp(pointeur, 1 - Math.exp(-dt * 2.5));
    const distance = pos.distanceTo(vise);
    const ampleur = THREE.MathUtils.clamp(distance * 0.05, 0.12, 6.0);
    droite.subVectors(vise, pos).cross(camera.up).normalize();
    haut2.copy(camera.up);
    pos.addScaledVector(droite, pointeurLisse.x * ampleur);
    pos.addScaledVector(haut2, -pointeurLisse.y * ampleur * 0.5 + (reduceMotion ? 0 : Math.sin(t * 0.5) * 0.04 * ampleur));
    camera.position.copy(pos);
    camera.lookAt(vise);

    // Décalage optique : le sujet s'écarte du panneau de texte
    const panneau = panneaux[chapitreActuel] || panneaux[0];
    let cibleDecalage = 0;
    if (!petitEcran()) cibleDecalage = panneau.classList.contains("cote-droite") ? -1 : 1;
    if (CHAPITRES_LARGES.has(chapitreActuel) && !petitEcran()) cibleDecalage *= 0.6;
    decalage += (cibleDecalage - decalage) * (1 - Math.exp(-dt * 2.0));
    const dx = Math.abs(decalage) * largeur * 0.2;
    const dy = petitEcran() ? hauteur * 0.32 : 0;
    camera.fov = fovA(u) * elargir * (petitEcran() ? 1.12 : 1);
    camera.aspect = (largeur + dx) / (hauteur + dy);
    camera.setViewOffset(largeur + dx, hauteur + dy, decalage > 0 ? 0 : dx, dy, largeur, hauteur);
    if (peuple) majErnestVisite(e, t, dt);
  }

  function image() {
    const dt = Math.min(horloge.getDelta(), 0.1);
    const t = horloge.elapsedTime;
    U_TEMPS.value = t;
    const yCible = window.scrollY;
    yLisse = reduceMotion ? yCible : yLisse + (yCible - yLisse) * (1 - Math.exp(-dt * 4.5));
    if (Math.abs(yCible - yLisse) < 0.05) yLisse = yCible;
    if (yCible > 10) intro = Math.max(intro, 0.999);
    if (intro < 1) intro = Math.min(1, intro + dt / 4.2);

    if (mode === "libre") {
      exploration.maj(dt);
      camera.clearViewOffset();
      camera.aspect = largeur / hauteur;
      camera.fov = THREE.MathUtils.clamp(58 * Math.max(1, 0.8 / (largeur / hauteur)), 58, 78);
    } else {
      poseVisite(dt, t);
    }
    if (fondu.k < 1) {
      fondu.k = Math.min(1, fondu.k + dt / fondu.duree);
      const k = doux(fondu.k);
      camera.position.lerpVectors(fondu.pos, camera.position, k);
      camera.quaternion.slerpQuaternions(fondu.quat, camera.quaternion, k);
      camera.fov = THREE.MathUtils.lerp(fondu.fov, camera.fov, k);
    }
    camera.updateProjectionMatrix();
    camera.updateMatrixWorld();

    // Les habitants, Ernest et les autres visiteurs
    if (peuple) {
      royaume.maj(dt, t);
      const h = peuple.humains[ernest];
      moi.mode = mode;
      moi.chapitre = chapitreActuel;
      moi.pos.copy(h.pos);
      moi.cap = h.cap;
      multijoueur.maj(dt, moi);
      peuple.maj(t, camera);
      majBulle(yLisse);
      const dedans = carte.interieur(camera.position.x, camera.position.z) > 0 ? 1 : 0;
      dedansLisse += (dedans - dedansLisse) * Math.min(1, dt * 3);
      lumiereSoleil.intensity = THREE.MathUtils.lerp(2.1, 0.3, dedansLisse);
      lumiereCiel.intensity = THREE.MathUtils.lerp(1.25, 1.55, dedansLisse);
      lumiereCiel.color.lerpColors(CIEL_DEHORS, CIEL_DEDANS, dedansLisse);
      lumiereCiel.groundColor.lerpColors(SOL_DEHORS, SOL_DEDANS, dedansLisse);
    }

    ciel.position.copy(camera.position);
    for (const n of nuages) n.material.uniforms.uCamera.value.copy(camera.position);
    for (const s of nuagesProches) s.position.x += Math.sin(t * 0.05 + s.userData.vitesse * 10) * 0.004 * s.userData.vitesse;
    for (const f of flottants) f.objet.position.y = f.base.y + Math.sin(t * 0.45 + f.phase) * f.ampl * 1.6;
    for (const a of animes) a(t);
    etalonnage.uniforms.uTemps.value = t;
    if (rayons) {
      camera.getWorldDirection(regard);
      const face = regard.dot(soleil);
      ecran.copy(versSoleil.copy(soleil).multiplyScalar(1000).add(camera.position)).project(camera);
      const dansCadre = 1 - lisse(1.0, 1.6, Math.max(Math.abs(ecran.x), Math.abs(ecran.y)));
      rayons.uniforms.uForce.value = lisse(0.25, 0.7, face) * dansCadre * (1 - 0.8 * dedansLisse);
      rayons.uniforms.uSoleilEcran.value.set(ecran.x * 0.5 + 0.5, ecran.y * 0.5 + 0.5);
    }

    majInterface(yLisse, lisse(0.35, 0.8, intro));
    composer.render(dt);
  }

  // Compilation des matières avant d'afficher, pour éviter un à-coup à la première image
  renderer.compile(scene, camera);
  renderer.setAnimationLoop(image);
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  afficherProgression(1);
  racine.classList.add("pret");

  /* ----- atlas en haute définition, chargés en arrière-plan ----- */
  for (const [nom, a] of atlas) {
    for (const taille of [QUALITE.atlas, QUALITE.atlas / 2]) {
      if (taille <= a.taille || taille > a.tailleMax) continue;
      try {
        const tex = preparer(await chargerBitmap(`assets/${nom}_${taille}.webp`));
        const ancienne = a.texture;
        a.texture = tex;
        a.taille = taille;
        appliquerAtlas(a, tex);
        if (ancienne) {
          if (ancienne.image && ancienne.image.close) ancienne.image.close();
          ancienne.dispose();
        }
        break;
      } catch (e) {
        /* cette taille n'existe pas pour cet atlas : on essaie la suivante */
      }
    }
  }
}

demarrer().catch((e) => sans3D(e && e.message));
