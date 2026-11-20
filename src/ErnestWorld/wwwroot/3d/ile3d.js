/*
  L'ÎLE EN 3D · moteur de la version immersive (Three.js)

  L'île vient de Blender (tools/blender/ile.py) : un fichier ile.glb (la géométrie, compressée avec Draco)
  et des « atlas » de lumière cuite par Cycles. Chaque maillage cuit est affiché avec une matière sans
  calcul d'éclairage (MeshBasicMaterial) : l'image contient déjà le soleil, les ombres douces et la lumière
  qui rebondit. Le navigateur n'ajoute que ce qui bouge : ciel, mer de nuages, faisceau du phare,
  cristaux, glyphes, lucioles, fumée, rochers flottants.

  La caméra suit un trajet tracé dans Blender (objets vides cam_XX et cible_XX). Le défilement de la page
  choisit la position sur ce trajet : chaque chapitre (section HTML) correspond à un arrêt.
*/
import * as THREE from "../lib/three/three.module.js";
import { GLTFLoader } from "../lib/three/loaders/GLTFLoader.js";
import { DRACOLoader } from "../lib/three/loaders/DRACOLoader.js";
import { EffectComposer } from "../lib/three/postprocessing/EffectComposer.js";
import { RenderPass } from "../lib/three/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "../lib/three/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "../lib/three/postprocessing/ShaderPass.js";
import { OutputPass } from "../lib/three/postprocessing/OutputPass.js";

/* =========================================================================
   RÉGLAGES
   ========================================================================= */

const racine = document.documentElement;
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const tactile = window.matchMedia("(pointer: coarse)").matches;
const petitEcran = () => window.innerWidth <= 760;
const MODESTE = petitEcran() || tactile || (navigator.hardwareConcurrency || 8) <= 4 || (navigator.deviceMemory || 8) <= 4;
const QUALITE = {
  ratio: Math.min(window.devicePixelRatio || 1, MODESTE ? 1.5 : 2),
  msaa: MODESTE ? 0 : 4,
  atlas: MODESTE ? 2048 : 4096,
  couchesNuages: MODESTE ? 4 : 7,
  lucioles: MODESTE ? 60 : 140,
};

// Couleurs du coucher de soleil (sRGB), accordées au ciel utilisé par Blender pour la cuisson
const PALETTE = {
  zenith: 0x221a45,
  haut: 0x4c3a7c,
  milieu: 0xa26c9e,
  horizon: 0xf3c4a2,
  soleil: 0xffc58a,
  bas: 0xd59fa2,
  fond: 0x5c4a78,
  nuageClair: 0xffd9c4,
  nuageOmbre: 0x7e6596,
  brume: 0xcf9fae,
};

/* =========================================================================
   LANGUE (le français est écrit dans la page)
   ========================================================================= */

const EN = {
  "meta.title": "Ernest Afaton · The 3D island",
  "meta.description": "Ernest Afaton's portfolio as an immersive experience: a 3D island at sunset, modeled and lit in Blender, to explore by scrolling.",
  "skip": "Skip to content",
  "logo.label": "Back to the classic portfolio",
  "nav.label": "Other versions of the portfolio",
  "nav.classic": "Classic version",
  "nav.game": "Game version",
  "toc.label": "Chapters",
  "toc.0": "Home", "toc.1": "About", "toc.2": "Experience", "toc.3": "Skills", "toc.4": "Projects", "toc.5": "Contact",
  "hero.status": "Available for a 4 to 5 week internship",
  "hero.hello": "Hi, I'm",
  "hero.role": "Web and mobile developer · Systems and networks · IoT",
  "hero.lead": "Welcome to my island: my portfolio as an immersive experience. Scroll down, each place tells part of my journey.",
  "hero.cue": "Scroll to explore",
  "about.eyebrow": "The arch · About",
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
  "skills.eyebrow": "The stone circle · Skills",
  "skills.title": "From code to infrastructure.",
  "skills.sub": "Seven stones, seven skill families.",
  "sk.web": "Web development", "sk.cs": "C# and .NET", "sk.mobile": "Mobile", "sk.back": "Back end and data",
  "sk.net": "Systems and networks", "sk.iot": "IoT and embedded", "sk.tools": "Methods", "sk.tests": "unit testing",
  "proj.eyebrow": "The crystals · Projects",
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
  "contact.how": "How the island is made",
  "contact.credit": "Island modeled by a Python script in Blender, lighting computed by Cycles, displayed with Three.js.",
  "load.title": "The island is getting ready…",
  "load.classic": "See the classic version instead",
  "no3d": "3D couldn't start on this device: here is the island as an image, and all the content is still readable.",
};

const FR = {};
let langue = racine.getAttribute("data-lang") === "en" ? "en" : "fr";

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
   OUTILS
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

/* =========================================================================
   DÉFILEMENT : chapitres, panneaux et sommaire
   ========================================================================= */

const sections = [...document.querySelectorAll(".chapitre")];
const panneaux = sections.map((s) => s.querySelector(".panneau"));
const liensSommaire = [...document.querySelectorAll(".sommaire a")];
const voile = document.querySelector(".voile");
const barreProgression = document.querySelector(".progression span");

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
function majInterface(y) {
  let meilleur = 0, meilleure = -1;
  panneaux.forEach((p, c) => {
    const o = opacitePanneau(c, y);
    p.style.opacity = o.toFixed(3);
    p.style.transform = `translateY(${((1 - o) * 18).toFixed(1)}px)`;
    p.classList.toggle("cache", o < 0.05);
    if (o > meilleure) { meilleure = o; meilleur = c; }
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

liensSommaire.forEach((a, c) => {
  a.addEventListener("click", (e) => {
    e.preventDefault();
    window.scrollTo({ top: debuts[c] + (c === 0 ? 0 : 2), behavior: reduceMotion ? "auto" : "smooth" });
    history.replaceState(null, "", "#" + sections[c].id);
  });
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
  scene.fog = new THREE.Fog(couleur(PALETTE.brume), 110, 620);
  const camera = new THREE.PerspectiveCamera(44, window.innerWidth / window.innerHeight, 0.15, 3000);

  /* ----- chargement de l'île et des atlas (taille 1024 d'abord) ----- */
  let progGlb = 0, progTex = 0, nbTex = 4;
  const maj = () => afficherProgression(progGlb * 0.7 + (progTex / nbTex) * 0.3);
  const draco = new DRACOLoader().setDecoderPath("../lib/three/libs/draco/gltf/");
  const chargeur = new GLTFLoader().setDRACOLoader(draco);
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
  const atlas = new Map();       // nom de l'atlas -> { matiere, tailleMax }
  const vivants = [];
  const flottants = [];
  ile.traverse((o) => {
    parNom.set(o.name, o);
    if (!o.isMesh) return;
    const d = Object.keys(o.userData).length ? o.userData : (o.parent ? o.parent.userData : {});
    if (d.atlas) {
      if (!atlas.has(d.atlas)) {
        atlas.set(d.atlas, { matiere: new THREE.MeshBasicMaterial({ color: 0xffffff }), tailleMax: d.atlas_max || 4096 });
      }
      o.material = atlas.get(d.atlas).matiere;
      o.geometry.deleteAttribute("normal");
      if (d.mobile) flottants.push({ objet: o, base: o.position.clone(), ampl: d.flotte || 0.3, phase: Math.random() * 6.28 });
    } else if (d.vivant) {
      vivants.push({ objet: o, type: d.vivant, rang: d.rang || 0, projet: d.projet });
    }
  });
  nbTex = atlas.size;

  const aniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  const preparer = (tex) => {
    tex.flipY = false;
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = aniso;
    tex.needsUpdate = true;
    return tex;
  };
  try {
    await Promise.all([...atlas.entries()].map(([nom, a]) =>
      chargerBitmap(`assets/${nom}_1024.webp`).then((tex) => {
        a.matiere.map = preparer(tex);
        a.matiere.needsUpdate = true;
        a.taille = 1024;
        progTex++;
        maj();
      })));
  } catch (e) {
    sans3D(e.message);
    return;
  }

  /* ----- repères venus de Blender ----- */
  const position = (nom, defaut) => {
    const o = parNom.get(nom);
    return o ? o.getWorldPosition(new THREE.Vector3()) : defaut;
  };
  const cles = [...parNom.keys()].filter((n) => /^cam_\d+$/.test(n)).sort();
  const ptsCam = cles.map((n) => position(n));
  const ptsCible = cles.map((n) => position(n.replace("cam_", "cible_")));
  const chapitreVersIndice = [];
  cles.forEach((n, i) => {
    const c = parNom.get(n).userData.chapitre;
    if (c !== undefined && c >= 0) chapitreVersIndice[c] = i;
  });
  const courbeCam = new THREE.CatmullRomCurve3(ptsCam, false, "centripetal", 0.5);
  const courbeCible = new THREE.CatmullRomCurve3(ptsCible, false, "centripetal", 0.5);
  const uChapitre = (c) => (chapitreVersIndice[c] ?? 0) / (cles.length - 1);
  const soleil = position("soleil", new THREE.Vector3(0.9034, 0.225, -0.365)).normalize();

  /* ----- ciel ----- */
  const ciel = new THREE.Mesh(
    new THREE.SphereGeometry(1500, 48, 24),
    new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: {
        uZenith: { value: couleur(PALETTE.zenith) }, uHaut: { value: couleur(PALETTE.haut) },
        uMilieu: { value: couleur(PALETTE.milieu) }, uHorizon: { value: couleur(PALETTE.horizon) },
        uBas: { value: couleur(PALETTE.bas) }, uFond: { value: couleur(PALETTE.fond) },
        uSoleilCouleur: { value: couleur(PALETTE.soleil) }, uSoleil: { value: soleil }, uTemps: { value: 0 },
      },
      vertexShader: /* glsl */`
        varying vec3 vDir;
        void main() {
          vDir = normalize(position);
          vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          gl_Position = p.xyww;
        }`,
      fragmentShader: /* glsl */`
        uniform vec3 uZenith, uHaut, uMilieu, uHorizon, uBas, uFond, uSoleilCouleur, uSoleil;
        uniform float uTemps;
        varying vec3 vDir;
        float h21(vec2 p) { return fract(sin(dot(p, vec2(41.3, 289.1))) * 45758.5453); }
        void main() {
          vec3 d = normalize(vDir);
          float h = d.y;
          float s = max(dot(d, uSoleil), 0.0);
          vec3 c = mix(uHorizon, uMilieu, smoothstep(0.0, 0.16, h));
          c = mix(c, uHaut, smoothstep(0.1, 0.42, h));
          c = mix(c, uZenith, smoothstep(0.35, 0.95, h));
          vec3 b = mix(uHorizon, uBas, smoothstep(0.0, -0.08, h));
          b = mix(b, uFond, smoothstep(-0.08, -0.5, h));
          c = h < 0.0 ? b : c;
          // Halo du soleil, plus large le long de l'horizon
          c += uSoleilCouleur * (pow(s, 6.0) * 0.45 + pow(s, 40.0) * 0.7);
          c += uSoleilCouleur * 0.35 * exp(-abs(h) * 14.0) * pow(s, 3.0);
          c += vec3(1.0, 0.92, 0.78) * smoothstep(0.99935, 0.9997, s) * 5.0;
          // Quelques étoiles tout en haut
          vec2 g = floor(vec2(atan(d.z, d.x) * 180.0, d.y * 260.0));
          float e = step(0.9975, h21(g)) * smoothstep(0.45, 0.9, h);
          c += vec3(e) * (0.5 + 0.5 * sin(uTemps * 1.5 + h21(g + 3.0) * 30.0)) * 0.6;
          gl_FragColor = vec4(c, 1.0);
        }`,
    }));
  ciel.renderOrder = -10;
  ciel.frustumCulled = false;
  scene.add(ciel);

  /* ----- mer de nuages : couches de bruit animé, sous l'île ----- */
  const nuages = [];
  const matNuage = (k, n) => new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, fog: false,
    uniforms: {
      uTemps: { value: 0 }, uCouche: { value: k / Math.max(1, n - 1) }, uGraine: { value: k * 17.31 },
      uClair: { value: couleur(PALETTE.nuageClair) }, uOmbre: { value: couleur(PALETTE.nuageOmbre) },
      uHorizon: { value: couleur(PALETTE.horizon) }, uSoleilCouleur: { value: couleur(PALETTE.soleil) },
      uSoleil: { value: soleil }, uCamera: { value: new THREE.Vector3() },
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
      uniform vec3 uClair, uOmbre, uHorizon, uSoleilCouleur, uSoleil, uCamera;
      varying vec3 vMonde;
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
      }
      void main() {
        vec2 p = vMonde.xz * 0.0085 + vec2(uTemps * 0.006, uTemps * 0.0025) + uGraine;
        float n = fbm(p + 0.35 * vec2(fbm(p * 0.7 + 4.0), fbm(p * 0.7 - 3.0)));
        float seuil = mix(0.36, 0.5, uCouche);
        float densite = smoothstep(seuil, seuil + 0.22, n);
        float dist = length(vMonde.xz - uCamera.xz);
        densite *= 1.0 - smoothstep(1100.0, 1450.0, dist);
        vec3 vue = normalize(vMonde - uCamera);
        vec2 vs = normalize(uSoleil.xz);
        float versSoleil = pow(max(dot(normalize(vue.xz), vs), 0.0), 4.0);
        vec3 c = mix(uOmbre, uClair, clamp(uCouche * 0.75 + (n - seuil) * 1.4, 0.0, 1.0));
        c += uSoleilCouleur * versSoleil * 0.45 * uCouche;
        c = mix(c, uHorizon, smoothstep(160.0, 1100.0, dist) * 0.85);
        gl_FragColor = vec4(c, densite * mix(0.45, 0.8, uCouche));
      }`,
  });
  for (let k = 0; k < QUALITE.couchesNuages; k++) {
    const n = QUALITE.couchesNuages;
    const plan = new THREE.Mesh(new THREE.PlaneGeometry(3000, 3000), matNuage(k, n));
    plan.rotation.x = -Math.PI / 2;
    plan.position.y = -54 + (k / Math.max(1, n - 1)) * 26;
    plan.renderOrder = -5 + k;
    plan.frustumCulled = false;
    scene.add(plan);
    nuages.push(plan);
  }

  /* ----- nuages proches (sprites) : profondeur pendant la vue d'ensemble ----- */
  const rnd = hasard(7);
  const texNuage = textureNuage(rnd);
  const nuagesProches = [];
  for (let i = 0; i < 16; i++) {
    const a = rnd() * Math.PI * 2;
    const r = 55 + rnd() * 70;
    const s = new THREE.Sprite(new THREE.SpriteMaterial({
      map: texNuage, color: couleur(i % 3 ? PALETTE.nuageClair : PALETTE.milieu), transparent: true,
      opacity: 0.22 + rnd() * 0.2, depthWrite: false, fog: false,
    }));
    s.position.set(Math.cos(a) * r, -26 + rnd() * 22, Math.sin(a) * r);
    s.scale.set(40 + rnd() * 40, 16 + rnd() * 12, 1);
    s.userData.vitesse = 0.3 + rnd() * 0.5;
    scene.add(s);
    nuagesProches.push(s);
  }

  /* ----- objets vivants : glyphes, anneau, cristaux ----- */
  const texHalo = textureHalo();
  const animes = [];
  const couleursCristal = { ecopay: 0x4ade80, boutik: 0xa78bfa, monde: 0xf472b6 };
  for (const v of vivants) {
    const o = v.objet;
    // Les objets sont exportés avec leurs sommets en coordonnées du monde : on les recentre
    o.geometry.computeBoundingBox();
    const centre = o.geometry.boundingBox.getCenter(new THREE.Vector3());
    o.geometry.translate(-centre.x, -centre.y, -centre.z);
    o.position.add(centre);
    if (v.type === "glyphe") {
      const m = new THREE.MeshBasicMaterial({ color: couleur(0xb79cff), fog: false });
      o.material = m;
      animes.push((t) => m.color.setRGB(0.72, 0.6, 1.0).multiplyScalar(1.6 + 0.9 * Math.sin(t * 1.3 + v.rang * 0.9)));
    } else if (v.type === "anneau") {
      const m = new THREE.MeshBasicMaterial({ color: couleur(0xe879f9), fog: false });
      o.material = m;
      animes.push((t) => m.color.setRGB(0.9, 0.45, 1.0).multiplyScalar(1.1 + 0.5 * Math.sin(t * 0.9)));
      const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: texHalo, color: couleur(0xd946ef), transparent: true, opacity: 0.22, blending: THREE.AdditiveBlending, depthWrite: false }));
      halo.position.copy(o.position).add(new THREE.Vector3(0, 0.5, 0));
      halo.scale.set(4.2, 2.0, 1);
      scene.add(halo);
    } else if (v.type === "cristal") {
      const teinte = couleur(couleursCristal[v.projet] || 0xffffff);
      const m = new THREE.ShaderMaterial({
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
      o.material = m;
      const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: texHalo, color: teinte, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false }));
      halo.scale.set(2.6, 2.6, 1);
      scene.add(halo);
      const base = o.position.clone();
      animes.push((t) => {
        o.rotation.y = t * 0.5 + v.rang;
        o.position.y = base.y + Math.sin(t * 1.1 + v.rang * 2.0) * 0.12;
        halo.position.copy(o.position);
        m.uniforms.uPulse.value = 0.5 + 0.5 * Math.sin(t * 2.0 + v.rang);
      });
    }
  }

  /* ----- halos des lanternes et de la lampe du phare ----- */
  for (const [nom, o] of parNom) {
    if (!/^lanterne_/.test(nom)) continue;
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: texHalo, color: couleur(0xffa94d), transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthWrite: false }));
    s.position.copy(o.getWorldPosition(new THREE.Vector3()));
    s.scale.set(1.4, 1.4, 1);
    scene.add(s);
    const ph = Math.random() * 10;
    animes.push((t) => { s.material.opacity = 0.65 + 0.15 * Math.sin(t * 7.0 + ph) * Math.sin(t * 2.3 + ph); });
  }

  const lampe = position("phare_lampe");
  if (lampe) {
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: texHalo, color: couleur(0xffd59a), transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false }));
    halo.position.copy(lampe);
    halo.scale.set(7, 7, 1);
    scene.add(halo);
    // Deux faisceaux opposés qui tournent
    const longueur = 70;
    const cone = new THREE.CylinderGeometry(0.35, 7, longueur, 32, 1, true);
    cone.translate(0, longueur / 2, 0);
    cone.rotateZ(-Math.PI / 2);
    const matFaisceau = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false,
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

  /* ----- fumée de la cheminée ----- */
  const fumee = position("fumee");
  if (fumee) {
    const bouffees = [];
    for (let i = 0; i < 18; i++) {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: texNuage, color: couleur(0xb9a7c9), transparent: true, opacity: 0, depthWrite: false }));
      scene.add(s);
      bouffees.push({ s, decalage: i / 18 });
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

  /* ----- lucioles autour des lieux de chaque chapitre ----- */
  {
    const n = QUALITE.lucioles;
    const pos = new Float32Array(n * 3);
    const phase = new Float32Array(n);
    const lieux = ptsCible.filter((_, i) => parNom.get(cles[i]).userData.chapitre > 0);
    for (let i = 0; i < n; i++) {
      const l = lieux[i % lieux.length] || new THREE.Vector3();
      pos[i * 3] = l.x + (rnd() - 0.5) * 16;
      pos[i * 3 + 1] = l.y - 1.2 + rnd() * 3.2;
      pos[i * 3 + 2] = l.z + (rnd() - 0.5) * 16;
      phase[i] = rnd() * 100;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("aPhase", new THREE.BufferAttribute(phase, 1));
    const m = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      uniforms: { uTemps: { value: 0 }, uTaille: { value: 90 * QUALITE.ratio }, uCarte: { value: texHalo } },
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
    animes.push((t) => { m.uniforms.uTemps.value = t; });
  }

  /* ----- rendu : bloom léger, vignette et grain ----- */
  const cible = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: QUALITE.msaa });
  const composer = new EffectComposer(renderer, cible);
  composer.setPixelRatio(QUALITE.ratio);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.55, 0.6, 0.86);
  composer.addPass(bloom);
  const etalonnage = new ShaderPass({
    uniforms: { tDiffuse: { value: null }, uTemps: { value: 0 }, uVignette: { value: 0.38 }, uGrain: { value: 0.04 } },
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
  let largeur = 1, hauteur = 1, fovBase = 44;
  function redimensionner() {
    largeur = window.innerWidth;
    hauteur = window.innerHeight;
    renderer.setSize(largeur, hauteur, false);
    composer.setSize(largeur, hauteur);
    const aspect = largeur / hauteur;
    // Écran étroit : on élargit le champ pour garder les bâtiments en entier
    const hfov = 2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(22)) * 16 / 9);
    const vfovEtroit = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(hfov / 2) / aspect));
    fovBase = THREE.MathUtils.clamp(44 + (vfovEtroit - 44) * 0.6, 44, 72);
    camera.aspect = aspect;
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

  /* ----- boucle ----- */
  const horloge = new THREE.Clock();
  let yLisse = window.scrollY;
  let decalage = 0;
  const pos = new THREE.Vector3(), vise = new THREE.Vector3(), droite = new THREE.Vector3(), haut = new THREE.Vector3();
  let surface = 0;

  function image() {
    const dt = Math.min(horloge.getDelta(), 0.1);
    const t = horloge.elapsedTime;
    const yCible = window.scrollY;
    yLisse = reduceMotion ? yCible : yLisse + (yCible - yLisse) * (1 - Math.exp(-dt * 4.5));
    if (Math.abs(yCible - yLisse) < 0.05) yLisse = yCible;

    const e = etape(yLisse);
    const u = THREE.MathUtils.lerp(uChapitre(e.de), uChapitre(e.vers), doux(Math.min(1, Math.max(0, e.t))));
    courbeCam.getPoint(u, pos);
    courbeCible.getPoint(u, vise);
    // Écran en hauteur : la vue d'ensemble recule pour garder toute l'île dans le cadre
    const aspect = largeur / hauteur;
    if (aspect < 1.2) {
      const poids = e.de === 0 ? 1 - doux(Math.min(1, e.t * 1.6)) : 0;
      const recul = 1 + (Math.min(2.3, 1.45 / aspect) - 1) * poids;
      pos.sub(vise).multiplyScalar(recul).add(vise);
    }

    // Parallaxe et respiration, plus marquées sur la vue d'ensemble
    pointeurLisse.lerp(pointeur, 1 - Math.exp(-dt * 2.5));
    const distance = pos.distanceTo(vise);
    const ampleur = THREE.MathUtils.clamp(distance * 0.06, 0.25, 4.0);
    droite.subVectors(vise, pos).cross(camera.up).normalize();
    haut.copy(camera.up);
    pos.addScaledVector(droite, pointeurLisse.x * ampleur);
    pos.addScaledVector(haut, -pointeurLisse.y * ampleur * 0.5 + (reduceMotion ? 0 : Math.sin(t * 0.5) * 0.04 * ampleur));
    camera.position.copy(pos);
    camera.lookAt(vise);

    // Décalage optique : le sujet s'écarte du panneau de texte
    const panneau = panneaux[chapitreActuel] || panneaux[0];
    let cibleDecalage = 0;
    if (!petitEcran()) cibleDecalage = panneau.classList.contains("cote-droite") ? -1 : 1;
    if (chapitreActuel === 0 && !petitEcran()) cibleDecalage = 0.6;
    decalage += (cibleDecalage - decalage) * (1 - Math.exp(-dt * 2.0));
    const dx = Math.abs(decalage) * largeur * 0.2;
    const dy = petitEcran() ? hauteur * 0.32 : 0;
    camera.fov = fovBase * (petitEcran() ? 1.12 : 1);
    camera.aspect = (largeur + dx) / (hauteur + dy);
    camera.setViewOffset(largeur + dx, hauteur + dy, decalage > 0 ? 0 : dx, dy, largeur, hauteur);
    camera.updateProjectionMatrix();

    ciel.position.copy(camera.position);
    ciel.material.uniforms.uTemps.value = t;
    for (const n of nuages) {
      n.material.uniforms.uTemps.value = t;
      n.material.uniforms.uCamera.value.copy(camera.position);
    }
    for (const s of nuagesProches) s.position.x += Math.sin(t * 0.05 + s.userData.vitesse * 10) * 0.004 * s.userData.vitesse;
    for (const f of flottants) f.objet.position.y = f.base.y + Math.sin(t * 0.45 + f.phase) * f.ampl * 1.6;
    for (const a of animes) a(t);
    etalonnage.uniforms.uTemps.value = t;

    majInterface(yLisse);
    composer.render(dt);
    surface++;
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
        const ancienne = a.matiere.map;
        a.matiere.map = tex;
        a.taille = taille;
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
