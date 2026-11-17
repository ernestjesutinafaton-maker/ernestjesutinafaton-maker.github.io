/*
  LE MONDE D'ERNEST - moteur 3D (Three.js)

  Ce module dessine l'île, ses bâtiments et ses boss, et joue les effets visuels et sonores.
  Toute la logique du jeu (quêtes, XP, combats, panneaux, blog, newsletter) est écrite en C# :
  le C# appelle les fonctions exportées ici, et ce module prévient le C# des clics
  (DotNetObjectReference.invokeMethodAsync).

  Rendu : ombres douces, ciel dynamique (soleil, lune, étoiles), post-traitement
  (anti-crénelage, contours lumineux, bloom, étalonnage et vignette), particules.
*/
import * as THREE from "../lib/three/three.module.js";
import { OrbitControls } from "../lib/three/OrbitControls.js";
import { EffectComposer } from "../lib/three/postprocessing/EffectComposer.js";
import { RenderPass } from "../lib/three/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "../lib/three/postprocessing/UnrealBloomPass.js";
import { OutlinePass } from "../lib/three/postprocessing/OutlinePass.js";
import { ShaderPass } from "../lib/three/postprocessing/ShaderPass.js";
import { OutputPass } from "../lib/three/postprocessing/OutputPass.js";
import * as audio from "./audio.js";

/* =========================================================================
   OUTILS
   ========================================================================= */

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const isSmall = () => window.innerWidth <= 736;
const LOW = isSmall() || (navigator.hardwareConcurrency || 8) <= 4;
const QUALITY = {
  pixelRatio: Math.min(window.devicePixelRatio, LOW ? 1.5 : 2),
  msaa: LOW ? 0 : 4,
  outline: !LOW,
  shadowMap: LOW ? 1024 : 2048,
  detail: LOW ? 0.5 : 1,
};

function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
let rand = mulberry32(20250121);

function hash2(x, y) {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return s - Math.floor(s);
}
function noise2(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y);
  const xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash2(xi, yi), b = hash2(xi + 1, yi), c = hash2(xi, yi + 1), d = hash2(xi + 1, yi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
const fbm = (x, y) => noise2(x, y) * 0.55 + noise2(x * 2.1, y * 2.1) * 0.3 + noise2(x * 4.3, y * 4.3) * 0.15;

// Hexagones (coordonnées axiales, pointe vers le haut)
const SQ3 = Math.sqrt(3);
const hexKey = (q, r) => `${q},${r}`;
const hexToWorld = (q, r) => [SQ3 * (q + r / 2), 1.5 * r];
const hexDist = (a, b) => (Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[0] + a[1] - b[0] - b[1])) / 2;
const HEX_DIRS = [[1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1]];
function hexRound(q, r) {
  const s = -q - r;
  let rq = Math.round(q), rr = Math.round(r);
  const rs = Math.round(s);
  const dq = Math.abs(rq - q), dr = Math.abs(rr - r), ds = Math.abs(rs - s);
  if (dq > dr && dq > ds) rq = -rr - rs;
  else if (dr > ds) rr = -rq - rs;
  return [rq, rr];
}
function hexLine(a, b) {
  const n = hexDist(a, b), out = [];
  for (let i = 0; i <= n; i++) {
    const t = n === 0 ? 0 : i / n;
    out.push(hexRound(a[0] + (b[0] - a[0]) * t + 1e-6, a[1] + (b[1] - a[1]) * t + 1e-6));
  }
  return out;
}

// Matériaux partagés, style low-poly à facettes
const matCache = new Map();
function M(color, extra = {}) {
  const key = color + JSON.stringify(extra);
  if (!matCache.has(key)) {
    matCache.set(key, new THREE.MeshStandardMaterial({ color, flatShading: true, roughness: 0.82, metalness: 0.02, ...extra }));
  }
  return matCache.get(key);
}
// Matériau propre à un objet (les boss changent de couleur quand ils sont touchés ou enragés)
const own = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, flatShading: true, roughness: 0.7, metalness: 0.05, ...extra });
const C = {
  stone: "#d9d0c1", stoneDark: "#a39888", wood: "#8a5a3b", woodDark: "#5e3b26",
  roofRed: "#c8574d", roofBlue: "#4f74c9", roofViolet: "#7c4dd6", roofTeal: "#2f9e8f",
  white: "#f3efe6", gold: "#f5c451", leaf: "#4f9d55", leafDark: "#3d8446", sand: "#ead9a8",
  rose: "#d946ef", violet: "#8b5cf6", honey: "#f2b134", metal: "#9aa3b5",
};
let windowMat;
const glowMat = (color, intensity = 1.4) => new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: intensity, flatShading: true });

function mesh(geo, material, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(geo, material);
  m.position.set(x, y, z);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}
const mat = (c) => (typeof c === "string" ? M(c) : c);
const box = (w, h, d, c, x = 0, y = 0, z = 0) => mesh(new THREE.BoxGeometry(w, h, d), mat(c), x, y + h / 2, z);
const cyl = (rt, rb, h, c, x = 0, y = 0, z = 0, seg = 8) => mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat(c), x, y + h / 2, z);
const cone = (r, h, c, x = 0, y = 0, z = 0, seg = 8) => mesh(new THREE.ConeGeometry(r, h, seg), mat(c), x, y + h / 2, z);
const ball = (r, c, x = 0, y = 0, z = 0, w = 8, h = 6) => mesh(new THREE.SphereGeometry(r, w, h), mat(c), x, y, z);
function pyramid(w, h, c, x = 0, y = 0, z = 0) {
  const g = new THREE.ConeGeometry(w * 0.7071, h, 4);
  g.rotateY(Math.PI / 4);
  return mesh(g, M(c), x, y + h / 2, z);
}
function gable(len, w, h, c, x = 0, y = 0, z = 0) {
  const g = new THREE.CylinderGeometry(1, 1, 1, 3);
  g.rotateZ(Math.PI / 2);
  g.rotateX(-Math.PI / 2);
  g.scale(len, h / 1.5, w / 1.732);
  g.translate(0, (0.5 * h) / 1.5, 0);
  return mesh(g, M(c), x, y, z);
}
function win(w, h, x, y, z, ry = 0) {
  const m = mesh(new THREE.BoxGeometry(w, h, 0.04), windowMat, x, y, z);
  m.rotation.y = ry;
  m.castShadow = false;
  return m;
}

/* =========================================================================
   ÉTAT DU MODULE
   ========================================================================= */

let renderer, composer, bloomPass, outlinePass, gradePass, scene, camera, controls, hemi, sun;
let sky, skyMat, starMat, moon, waterMat, waterGeo, waterBase, foam, fireflies, pollen;
let canvasEl, labelsEl, dotnet;
let tiles, tileList, tileMesh, PLACE, buildings, pickables, markers, labels, hoverRing, activeRing, pigeonnierTop;
let bosses = new Map();
let anims = [], lights = [], flights = [], ripples = [];
let started = false, paused = false, night = false, nightT = 0, battleId = null, savedView = null;
let activeId = null, hoverId = null, hoverBoss = null, tween = null, rafId = 0, downAt = null;
let disposers = [];
let mini = null, miniFrame = 0;
const wind = { value: 0 };
const shake = { amp: 0, offset: new THREE.Vector3() };
const clock = new THREE.Clock();

const WATER_Y = 0.12;
const RADIUS = 9;
const H0 = 0.45;
const HOME = { target: new THREE.Vector3(0, 0.5, 1.5), dist: 34, polar: 0.92, azimuth: 0.5 };

const DAY = {
  top: new THREE.Color("#3f8fd8"), horizon: new THREE.Color("#bfe4f7"), bottom: new THREE.Color("#7fb6d6"),
  fog: new THREE.Color("#bfe4f7"), hemiSky: new THREE.Color("#e6f4ff"), hemiGround: new THREE.Color("#6b8f4e"),
  sun: new THREE.Color("#fff0d4"), sunGlow: new THREE.Color("#ffd9a0"), water: new THREE.Color("#2a9ad6"),
};
const NIGHT = {
  top: new THREE.Color("#060616"), horizon: new THREE.Color("#1d1c47"), bottom: new THREE.Color("#0b0b24"),
  fog: new THREE.Color("#17163a"), hemiSky: new THREE.Color("#4b4f99"), hemiGround: new THREE.Color("#1c1b33"),
  sun: new THREE.Color("#a9bcff"), sunGlow: new THREE.Color("#7f8fd6"), water: new THREE.Color("#143563"),
};
const SUN_DIR = new THREE.Vector3(18, 26, 12).normalize();
const MOON_DIR = new THREE.Vector3(-14, 22, -16).normalize();

const ROADS = [
  ["chateau", "forge"], ["chateau", "qg"], ["chateau", "banque"], ["chateau", "marche"], ["chateau", "academie"], ["chateau", "camp"],
  ["forge", "observatoire"], ["banque", "ruche"], ["banque", "pigeonnier"], ["marche", "arene"], ["arene", "scriptorium"],
  ["academie", "bibliotheque"], ["bibliotheque", "scriptorium"], ["academie", "monument"], ["qg", "radio"], ["camp", "phare"],
];
const PLACE_HEIGHT = { observatoire: 0.99, phare: 0.55 };
const MILL_HEX = [-6, 0];

// Repaires des boss : sur l'île (case hexagonale) ou en mer (coordonnées)
const BOSS_LAYOUT = {
  bug: { hex: [-6, 6], ground: "corrupt", h: H0 },
  hydre: { x: 17.5, z: 3.5, sea: true },
  golem: { hex: [6, -7], ground: "rock", h: 1.25 },
  kraken: { x: -15.5, z: 10.5, sea: true },
  dragon: { hex: [1, -7], ground: "snow", h: 2.1 },
};

/* =========================================================================
   API APPELÉE DEPUIS C#
   ========================================================================= */

export function init(canvas, labelsContainer, dotnetRef, places, visited, bossList) {
  canvasEl = canvas;
  labelsEl = labelsContainer;
  dotnet = dotnetRef;
  rand = mulberry32(20250121);
  PLACE = Object.fromEntries(places.map((p) => [p.id, { ...p, hex: [p.q, p.r] }]));

  renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: "high-performance" });
  renderer.setPixelRatio(QUALITY.pixelRatio);
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.08;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  windowMat = new THREE.MeshStandardMaterial({ color: "#3a2f55", emissive: "#ffcf6b", emissiveIntensity: 0.05, flatShading: true });

  buildSceneBasics();
  buildTerrain();
  buildBuildings();
  buildBosses(bossList);
  buildLife();
  buildMarkersAndLabels(places, bossList);
  setVisited(visited);
  setupCamera();
  setupPostProcessing();
  setupInput();

  clock.start();
  loop();
}

export function enter() {
  started = true;
  controls.autoRotate = false;
  controls.enabled = true;
  flyTo(HOME.target, HOME.dist, HOME.polar, HOME.azimuth, 2.2);
  // Les navigateurs n'autorisent le son qu'après un geste du visiteur
  audio.startAmbient();
  const startSound = () => audio.startAmbient();
  window.addEventListener("pointerdown", startSound, { once: true });
  disposers.push(() => window.removeEventListener("pointerdown", startSound));
}

export function focusPlace(id) {
  const b = buildings.get(id);
  if (!b) return;
  activeId = id;
  activeRing.position.set(b.world.x, b.world.y + 0.04, b.world.z);
  activeRing.visible = true;
  hoverRing.visible = false;
  for (const [pid, el] of labels) el.classList.toggle("is-active", pid === id);
  flyTo(new THREE.Vector3(b.world.x, b.world.y + 0.6, b.world.z), id === "phare" ? 13 : 11, 0.95);
  spawnRipple(b.world, C.gold, 2.2);
}

export function clearFocus() {
  activeId = null;
  activeRing.visible = false;
  for (const el of labels.values()) el.classList.remove("is-active");
}

export function home() {
  clearFocus();
  flyTo(HOME.target, HOME.dist, HOME.polar, HOME.azimuth);
}

export function setNight(on) {
  night = !!on;
  audio.setNightAmbience(night);
  audio.play(night ? "night" : "day");
}

export function setVisited(ids) {
  const seen = new Set(ids || []);
  for (const [id, m] of markers) {
    const isNew = !seen.has(id);
    m.visible = isNew;
    labels.get(id)?.classList.toggle("is-new", isNew);
  }
}

export function setPaused(on) {
  paused = !!on;
  if (!paused) clock.getDelta();
}

export function releasePigeon() {
  if (!pigeonnierTop) return;
  const start = pigeonnierTop.clone();
  const dir = new THREE.Vector3(Math.cos(rand() * 6.28), 0, Math.sin(rand() * 6.28));
  const curve = new THREE.CatmullRomCurve3([
    start,
    start.clone().add(new THREE.Vector3(0, 1.5, 0)).add(dir.clone().multiplyScalar(2)),
    start.clone().add(new THREE.Vector3(0, 4, 0)).add(dir.clone().multiplyScalar(9)),
    start.clone().add(new THREE.Vector3(0, 9, 0)).add(dir.clone().multiplyScalar(26)),
  ]);
  const bird = makePigeon(1.8);
  scene.add(bird.group);
  flights.push({ bird, curve, t: 0 });
  burst(start, 24, ["#ffffff", "#f5c451", "#c4b5fd"], 2.2, 2, 1.2);
  audio.play("pigeon");
  if (activeId !== "pigeonnier") flyTo(new THREE.Vector3(start.x, start.y, start.z), 14, 0.95);
}

export const play = (name) => audio.play(name);
export const isSoundOn = () => audio.isOn();
export function toggleSound() {
  const on = audio.toggle();
  if (on && started) audio.startAmbient();
  return on;
}

export function dispose() {
  cancelAnimationFrame(rafId);
  disposers.forEach((f) => f());
  disposers = [];
  audio.stopAmbient();
  controls?.dispose();
  composer?.dispose?.();
  renderer?.dispose();
  if (labelsEl) labelsEl.innerHTML = "";
  anims = []; lights = []; flights = []; ripples = [];
  started = false;
}

/* =========================================================================
   SCÈNE : CIEL, LUMIÈRES, EAU
   ========================================================================= */

function buildSceneBasics() {
  scene = new THREE.Scene();
  scene.background = DAY.horizon.clone();
  scene.fog = new THREE.Fog(DAY.fog.clone(), 42, 105);

  camera = new THREE.PerspectiveCamera(38, window.innerWidth / window.innerHeight, 0.1, 400);

  // Ciel en dégradé, avec soleil (ou lune) et halo
  skyMat = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    uniforms: {
      uTop: { value: DAY.top.clone() },
      uHorizon: { value: DAY.horizon.clone() },
      uBottom: { value: DAY.bottom.clone() },
      uSunDir: { value: SUN_DIR.clone() },
      uSun: { value: DAY.sun.clone() },
      uGlow: { value: DAY.sunGlow.clone() },
      uSunSize: { value: 2600 },
    },
    vertexShader: /* glsl */ `
      varying vec3 vDir;
      void main() {
        vDir = normalize(position);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uTop; uniform vec3 uHorizon; uniform vec3 uBottom;
      uniform vec3 uSunDir; uniform vec3 uSun; uniform vec3 uGlow; uniform float uSunSize;
      varying vec3 vDir;
      void main() {
        vec3 dir = normalize(vDir);
        float h = dir.y;
        vec3 col = h > 0.0 ? mix(uHorizon, uTop, pow(clamp(h, 0.0, 1.0), 0.6)) : mix(uHorizon, uBottom, pow(clamp(-h, 0.0, 1.0), 0.35));
        float d = max(dot(dir, normalize(uSunDir)), 0.0);
        col += uSun * pow(d, uSunSize) * 8.0;
        col += uGlow * (pow(d, 28.0) * 0.45 + pow(d, 5.0) * 0.12);
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
  sky = new THREE.Mesh(new THREE.SphereGeometry(200, 32, 16), skyMat);
  sky.renderOrder = -1;
  scene.add(sky);

  hemi = new THREE.HemisphereLight(DAY.hemiSky.clone(), DAY.hemiGround.clone(), 1.05);
  scene.add(hemi);

  sun = new THREE.DirectionalLight(DAY.sun.clone(), 2.5);
  sun.position.copy(SUN_DIR).multiplyScalar(36);
  sun.castShadow = true;
  sun.shadow.mapSize.set(QUALITY.shadowMap, QUALITY.shadowMap);
  Object.assign(sun.shadow.camera, { left: -24, right: 24, top: 24, bottom: -24, near: 1, far: 90 });
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.02;
  sun.shadow.radius = 3;
  scene.add(sun);

  // Étoiles et lune (la nuit)
  const pts = [];
  for (let i = 0; i < 1200; i++) {
    const th = rand() * Math.PI * 2, ph = rand() * Math.PI * 0.46, R = 170;
    pts.push(R * Math.sin(ph) * Math.cos(th), R * Math.cos(ph) * 0.85 + 8, R * Math.sin(ph) * Math.sin(th));
  }
  const starGeo = new THREE.BufferGeometry();
  starGeo.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
  starMat = new THREE.PointsMaterial({ color: "#ffffff", size: 0.9, transparent: true, opacity: 0, fog: false, depthWrite: false });
  const stars = new THREE.Points(starGeo, starMat);
  scene.add(stars);
  anims.push((t) => { stars.rotation.y = t * 0.004; });

  moon = new THREE.Mesh(new THREE.SphereGeometry(4, 24, 16), new THREE.MeshBasicMaterial({ color: "#e8ecff", transparent: true, opacity: 0, fog: false }));
  moon.position.copy(MOON_DIR).multiplyScalar(150);
  scene.add(moon);

  // Eau animée
  waterGeo = new THREE.PlaneGeometry(170, 170, 80, 80);
  waterGeo.rotateX(-Math.PI / 2);
  waterBase = waterGeo.attributes.position.array.slice();
  waterMat = new THREE.MeshStandardMaterial({ color: DAY.water.clone(), flatShading: true, roughness: 0.14, metalness: 0.08, transparent: true, opacity: 0.86 });
  const water = new THREE.Mesh(waterGeo, waterMat);
  water.position.y = WATER_Y;
  water.receiveShadow = true;
  scene.add(water);
  const seabed = new THREE.Mesh(new THREE.PlaneGeometry(170, 170), new THREE.MeshStandardMaterial({ color: "#165a86" }));
  seabed.rotation.x = -Math.PI / 2;
  seabed.position.y = -1.2;
  scene.add(seabed);
}

function animateWater(t) {
  const p = waterGeo.attributes.position.array;
  for (let i = 0; i < p.length; i += 3) {
    const x = waterBase[i], z = waterBase[i + 2];
    p[i + 1] = Math.sin(x * 0.45 + t * 1.1) * 0.07 + Math.cos(z * 0.38 + t * 0.9) * 0.07 + Math.sin((x + z) * 0.8 + t * 1.7) * 0.025;
  }
  waterGeo.attributes.position.needsUpdate = true;
  waterGeo.computeVertexNormals();
}

/* =========================================================================
   TERRAIN HEXAGONAL, ROUTES, VÉGÉTATION
   ========================================================================= */

let roadPaths = [];
const corruptTiles = [];
const topOf = (q, r) => tiles.get(hexKey(q, r))?.h ?? H0;

function setTile(q, r, type, h) {
  const k = hexKey(q, r);
  const t = tiles.get(k) || { q, r };
  Object.assign(t, { type, h, forest: false, reserved: true });
  tiles.set(k, t);
  return t;
}

const TILE_COLORS = {
  sand: ["#ecdcaa", "#e4d29c"], grass: ["#86c96f", "#7bbf63", "#8fd174"], road: ["#dcc08a", "#d4b67e"],
  plaza: ["#e8dcc2"], rock: ["#9c97a8", "#8d889a"], snow: ["#f4f5fa", "#e9ebf3"], corrupt: ["#4b3d63", "#57466f"],
};

// Herbe et feuilles qui ondulent dans le vent (petite modification du shader de Three.js)
function windy(material, strength = 0.06, from = 0.3) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uWind = wind;
    shader.vertexShader = "uniform float uWind;\n" + shader.vertexShader.replace(
      "#include <begin_vertex>",
      `#include <begin_vertex>
       #ifdef USE_INSTANCING
         vec3 ip = vec3(instanceMatrix[3][0], instanceMatrix[3][1], instanceMatrix[3][2]);
       #else
         vec3 ip = vec3(0.0);
       #endif
       float sway = sin(uWind * 1.6 + ip.x * 0.7 + ip.z * 0.5) * ${strength.toFixed(3)} * max(position.y - ${from.toFixed(2)}, 0.0);
       transformed.x += sway;
       transformed.z += sway * 0.6;`,
    );
  };
  return material;
}

function buildTerrain() {
  tiles = new Map();
  for (let q = -RADIUS - 1; q <= RADIUS + 1; q++) {
    for (let r = -RADIUS - 1; r <= RADIUS + 1; r++) {
      const d = hexDist([0, 0], [q, r]);
      if (d > RADIUS) continue;
      const [x, z] = hexToWorld(q, r);
      const n = fbm(x * 0.13 + 3.1, z * 0.13 + 7.7);
      let e = 0.64 - Math.pow(d / RADIUS, 1.6) * 0.64 + (n - 0.5) * 0.5;
      e += Math.max(0, 1 - Math.hypot(x + 4.5, z + 10.5) / 4.8) * 0.6; // montagnes au nord
      if (e < 0.13) continue;
      let type, h;
      if (e < 0.21) { type = "sand"; h = 0.25; }
      else if (e < 0.72) { type = "grass"; h = H0 + Math.floor((e - 0.21) / 0.17) * 0.18; }
      else if (e < 0.9) { type = "rock"; h = 1.15 + (e - 0.72) * 3; }
      else { type = "snow"; h = 1.7 + (e - 0.9) * 3.5; }
      const forest = type === "grass" && fbm(x * 0.3 + 40, z * 0.3 - 12) > 0.56;
      tiles.set(hexKey(q, r), { q, r, type, h, forest });
    }
  }

  // Routes
  roadPaths = [];
  for (const [a, b] of ROADS) {
    if (!PLACE[a] || !PLACE[b]) continue;
    const line = hexLine(PLACE[a].hex, PLACE[b].hex);
    roadPaths.push(line);
    for (const [q, r] of line) {
      const t = tiles.get(hexKey(q, r));
      const h = t && t.type !== "sand" ? Math.min(Math.max(t.h, H0), 0.81) : 0.3;
      setTile(q, r, "road", h);
    }
  }

  // Places des bâtiments, avec un anneau aplani autour
  for (const p of Object.values(PLACE)) {
    const h = PLACE_HEIGHT[p.id] ?? H0;
    for (const [dq, dr] of HEX_DIRS) {
      const t = tiles.get(hexKey(p.hex[0] + dq, p.hex[1] + dr));
      if (t && t.type === "road") continue;
      if (p.id === "phare") setTile(p.hex[0] + dq, p.hex[1] + dr, "sand", 0.28);
      else setTile(p.hex[0] + dq, p.hex[1] + dr, "grass", h);
    }
    setTile(p.hex[0], p.hex[1], p.id === "phare" ? "rock" : "plaza", h);
  }
  setTile(MILL_HEX[0], MILL_HEX[1], "grass", H0);

  // Repaires des boss terrestres
  for (const [id, lay] of Object.entries(BOSS_LAYOUT)) {
    if (lay.sea) continue;
    const ring = lay.ground === "snow" ? "rock" : lay.ground;
    const ringH = lay.ground === "snow" ? lay.h - 0.3 : lay.h;
    for (const [dq, dr] of HEX_DIRS) setTile(lay.hex[0] + dq, lay.hex[1] + dr, ring, ringH);
    setTile(lay.hex[0], lay.hex[1], lay.ground, lay.h);
    lay.id = id;
  }

  tileList = [...tiles.values()];
  const tileGeo = new THREE.CylinderGeometry(0.985, 0.985, 1, 6);
  tileGeo.translate(0, 0.5, 0);
  tileMesh = new THREE.InstancedMesh(tileGeo, new THREE.MeshStandardMaterial({ flatShading: true, roughness: 0.95 }), tileList.length);
  tileMesh.castShadow = true;
  tileMesh.receiveShadow = true;
  const m = new THREE.Matrix4(), col = new THREE.Color();
  tileList.forEach((t, i) => {
    const [x, z] = hexToWorld(t.q, t.r);
    const base = -1.2;
    m.makeScale(1, t.h - base, 1);
    m.setPosition(x, base, z);
    tileMesh.setMatrixAt(i, m);
    const palette = TILE_COLORS[t.forest ? "grass" : t.type];
    col.set(palette[Math.floor(hash2(t.q * 3.1, t.r * 7.3) * palette.length)]);
    if (t.forest) col.offsetHSL(0, 0, -0.06);
    tileMesh.setColorAt(i, col);
    if (t.type === "corrupt") corruptTiles.push(i);
  });
  scene.add(tileMesh);

  // Écume le long des côtes
  const coast = tileList.filter((t) => HEX_DIRS.some(([dq, dr]) => !tiles.has(hexKey(t.q + dq, t.r + dr))));
  const foamGeo = new THREE.RingGeometry(0.98, 1.3, 6, 1);
  foamGeo.rotateX(-Math.PI / 2);
  foamGeo.rotateY(Math.PI / 6);
  const foamMat = new THREE.MeshBasicMaterial({ color: "#ffffff", transparent: true, opacity: 0.55, depthWrite: false });
  foam = new THREE.InstancedMesh(foamGeo, foamMat, coast.length);
  foam.userData.tiles = coast.map((t) => { const [x, z] = hexToWorld(t.q, t.r); return { x, z, ph: hash2(t.q, t.r) * 6.28 }; });
  scene.add(foam);
  const fm = new THREE.Matrix4(), fq = new THREE.Quaternion(), fs = new THREE.Vector3(), fp = new THREE.Vector3();
  anims.push((t) => {
    foam.userData.tiles.forEach((c, i) => {
      const k = 1 + Math.sin(t * 1.3 + c.ph) * 0.06;
      fm.compose(fp.set(c.x, WATER_Y + 0.05, c.z), fq, fs.set(k, 1, k));
      foam.setMatrixAt(i, fm);
    });
    foam.instanceMatrix.needsUpdate = true;
    foamMat.opacity = (0.42 + Math.sin(t * 0.9) * 0.1) * (1 - nightT * 0.45);
  });

  // Arbres, rochers, fleurs et touffes d'herbe (instanciés pour la performance)
  const treeSpots = [], rockSpots = [], flowerSpots = [], tuftSpots = [];
  for (const t of tileList) {
    const [x, z] = hexToWorld(t.q, t.r);
    if (t.type === "grass" || (t.type === "plaza" && rand() < 0.3)) {
      if (rand() < 0.5 * QUALITY.detail) for (let i = 0; i < 1 + Math.floor(rand() * 3); i++) flowerSpots.push([x + (rand() - 0.5) * 1.4, t.h, z + (rand() - 0.5) * 1.4]);
      if (rand() < 0.7 * QUALITY.detail) for (let i = 0; i < 2 + Math.floor(rand() * 4); i++) tuftSpots.push([x + (rand() - 0.5) * 1.5, t.h, z + (rand() - 0.5) * 1.5]);
    }
    if (t.reserved) continue;
    if (t.forest) {
      const n = 1 + Math.floor(rand() * 3);
      for (let i = 0; i < n; i++) treeSpots.push([x + (rand() - 0.5) * 1.1, t.h, z + (rand() - 0.5) * 1.1, 0.7 + rand() * 0.5]);
    } else if (t.type === "grass" && rand() < 0.12) {
      treeSpots.push([x + (rand() - 0.5) * 0.9, t.h, z + (rand() - 0.5) * 0.9, 0.6 + rand() * 0.4]);
    } else if ((t.type === "rock" || t.type === "sand" || t.type === "snow") && rand() < 0.25) {
      rockSpots.push([x + (rand() - 0.5) * 0.9, t.h, z + (rand() - 0.5) * 0.9, 0.15 + rand() * 0.2]);
    }
  }

  const q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
  const trunkGeo = new THREE.CylinderGeometry(0.07, 0.1, 0.35, 5); trunkGeo.translate(0, 0.175, 0);
  const leafGeo = new THREE.ConeGeometry(0.38, 0.95, 6); leafGeo.translate(0, 0.75, 0);
  const leaf2Geo = new THREE.ConeGeometry(0.28, 0.7, 6); leaf2Geo.translate(0, 1.15, 0);
  const trunks = new THREE.InstancedMesh(trunkGeo, M(C.woodDark), treeSpots.length);
  const leaves = new THREE.InstancedMesh(leafGeo, windy(own(C.leaf, { roughness: 0.85, metalness: 0 })), treeSpots.length);
  const leaves2 = new THREE.InstancedMesh(leaf2Geo, windy(own(C.leafDark, { roughness: 0.85, metalness: 0 })), treeSpots.length);
  treeSpots.forEach(([x, y, z, sc], i) => {
    q.setFromAxisAngle(up, rand() * Math.PI);
    m.compose(p.set(x, y, z), q, s.set(sc, sc, sc));
    trunks.setMatrixAt(i, m); leaves.setMatrixAt(i, m); leaves2.setMatrixAt(i, m);
    col.set(C.leaf).offsetHSL((rand() - 0.5) * 0.05, 0, (rand() - 0.5) * 0.1);
    leaves.setColorAt(i, col);
  });
  for (const im of [trunks, leaves, leaves2]) { im.castShadow = true; im.receiveShadow = true; scene.add(im); }

  const rocks = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(1, 0), M("#8f8a9c"), rockSpots.length);
  rockSpots.forEach(([x, y, z, sc], i) => {
    q.setFromEuler(new THREE.Euler(rand(), rand() * 3, rand()));
    m.compose(p.set(x, y + sc * 0.4, z), q, s.set(sc, sc * 0.7, sc));
    rocks.setMatrixAt(i, m);
  });
  rocks.castShadow = true;
  scene.add(rocks);

  const flowerColors = ["#ffffff", "#ffe066", "#ff8fab", "#c084fc", "#ff6b6b", "#7dd3fc"];
  const flowers = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(0.055, 0), own("#ffffff", { roughness: 0.6 }), flowerSpots.length);
  flowerSpots.forEach(([x, y, z], i) => {
    m.compose(p.set(x, y + 0.06, z), q.identity(), s.set(1, 1, 1));
    flowers.setMatrixAt(i, m);
    flowers.setColorAt(i, col.set(flowerColors[Math.floor(rand() * flowerColors.length)]));
  });
  scene.add(flowers);

  const tuftGeo = new THREE.ConeGeometry(0.045, 0.24, 3); tuftGeo.translate(0, 0.12, 0);
  const tufts = new THREE.InstancedMesh(tuftGeo, windy(own("#6fb85a", { roughness: 0.9 }), 0.35, 0.0), tuftSpots.length);
  tuftSpots.forEach(([x, y, z], i) => {
    q.setFromEuler(new THREE.Euler((rand() - 0.5) * 0.4, rand() * 3, (rand() - 0.5) * 0.4));
    const sc = 0.7 + rand() * 0.7;
    m.compose(p.set(x, y, z), q, s.set(sc, sc, sc));
    tufts.setMatrixAt(i, m);
    tufts.setColorAt(i, col.set("#6fb85a").offsetHSL((rand() - 0.5) * 0.06, 0, (rand() - 0.5) * 0.12));
  });
  scene.add(tufts);
}

/* =========================================================================
   BÂTIMENTS
   ========================================================================= */

function glowSprite(color, size, always = 0) {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d");
  const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grd.addColorStop(0, color);
  grd.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = grd;
  g.fillRect(0, 0, 64, 64);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: always }));
  sp.scale.set(size, size, 1);
  sp.userData.always = always;
  lights.push(sp);
  return sp;
}
function lantern(x, y, z) {
  const g = new THREE.Group();
  g.add(cyl(0.03, 0.03, 0.7, C.woodDark, 0, 0, 0, 5));
  g.add(box(0.12, 0.14, 0.12, glowMat("#ffcf6b", 1.6), 0, 0.7, 0));
  const s = glowSprite("rgba(255,200,110,0.9)", 1.4);
  s.position.set(0, 0.78, 0);
  g.add(s);
  g.position.set(x, y, z);
  return g;
}
function flag(color, x, y, z, h = 0.9) {
  const g = new THREE.Group();
  g.add(cyl(0.025, 0.025, h, C.metal, 0, 0, 0, 5));
  const cloth = box(0.42, 0.26, 0.02, color, 0.22, h - 0.3, 0);
  g.add(cloth);
  g.position.set(x, y, z);
  const ph = rand() * 6;
  anims.push((t) => { cloth.rotation.y = Math.sin(t * 2.4 + ph) * 0.35; });
  return g;
}
function smokeAt(group, x, y, z, color = "#d9d6e0") {
  const puffs = [];
  for (let i = 0; i < 7; i++) {
    const p = new THREE.Mesh(new THREE.IcosahedronGeometry(0.12, 0), new THREE.MeshStandardMaterial({ color, flatShading: true, transparent: true, opacity: 0.8 }));
    group.add(p);
    puffs.push({ p, off: i / 7 });
  }
  anims.push((t) => {
    for (const { p, off } of puffs) {
      const k = (t * 0.25 + off) % 1;
      p.position.set(x + Math.sin(k * 6 + off * 10) * 0.12, y + k * 1.6, z + k * 0.3);
      p.scale.setScalar(0.6 + k * 1.8);
      p.material.opacity = (1 - k) * 0.7;
    }
  });
}
function makePigeon(scale = 1) {
  const group = new THREE.Group();
  const body = ball(0.09, "#f1f1f6");
  body.scale.set(1.6, 1, 1);
  const head = ball(0.055, "#d7d9e6", 0.15, 0.05, 0);
  const beak = cone(0.02, 0.06, "#f2a33a", 0.21, 0.03, 0, 4);
  beak.rotation.z = -Math.PI / 2;
  const wingL = box(0.14, 0.01, 0.2, "#e6e7f0", 0, 0.02, 0.1), wingR = box(0.14, 0.01, 0.2, "#e6e7f0", 0, 0.02, -0.1);
  wingL.geometry.translate(0, 0, 0.1); wingR.geometry.translate(0, 0, -0.1);
  wingL.position.z = 0.02; wingR.position.z = -0.02;
  group.add(body, head, beak, wingL, wingR);
  group.scale.setScalar(scale);
  return { group, wingL, wingR };
}

const BUILD = {
  chateau() {
    const g = new THREE.Group();
    g.add(box(2.1, 0.75, 2.1, C.stone));
    for (const [x, z] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
      g.add(cyl(0.34, 0.38, 1.45, C.stone, x, 0, z));
      g.add(cone(0.46, 0.7, C.roofViolet, x, 1.45, z));
    }
    for (let i = -2; i <= 2; i++) {
      if (i === 0) continue;
      g.add(box(0.18, 0.18, 0.18, C.stone, i * 0.33, 0.75, -1.05), box(0.18, 0.18, 0.18, C.stone, i * 0.33, 0.75, 1.05));
      g.add(box(0.18, 0.18, 0.18, C.stone, -1.05, 0.75, i * 0.33), box(0.18, 0.18, 0.18, C.stone, 1.05, 0.75, i * 0.33));
    }
    g.add(box(1.0, 1.55, 1.0, C.white, 0, 0.75, 0));
    g.add(pyramid(1.25, 0.95, C.roofViolet, 0, 2.3, 0));
    g.add(box(0.5, 0.55, 0.06, C.woodDark, 0, 0, 1.06));
    g.add(win(0.18, 0.28, 0, 1.6, 0.51), win(0.18, 0.28, -0.25, 1.6, 0.51), win(0.18, 0.28, 0.25, 1.6, 0.51));
    g.add(win(0.18, 0.28, 0.51, 1.6, 0, Math.PI / 2), win(0.18, 0.28, -0.51, 1.6, 0, Math.PI / 2));
    g.add(flag(C.rose, 0, 3.2, 0, 0.8));
    g.add(lantern(-0.55, 0, 1.35), lantern(0.55, 0, 1.35));
    return g;
  },

  forge() {
    const g = new THREE.Group();
    g.add(box(1.5, 0.85, 1.1, C.stoneDark));
    g.add(gable(1.65, 1.3, 0.6, C.roofRed, 0, 0.85, 0));
    g.add(box(0.32, 1.5, 0.32, C.stoneDark, 0.45, 0.6, -0.25));
    const fire = box(0.42, 0.36, 0.06, glowMat("#ff7a2f", 1.8), -0.2, 0.1, 0.56);
    g.add(fire);
    anims.push((t) => { fire.material.emissiveIntensity = 1.6 + Math.sin(t * 9) * 0.35 + Math.sin(t * 23) * 0.2; });
    g.add(box(0.36, 0.14, 0.18, "#4a4a55", 0.55, 0.22, 0.95), box(0.16, 0.22, 0.12, "#4a4a55", 0.55, 0, 0.95));
    g.add(win(0.22, 0.22, 0.4, 0.45, 0.56));
    const s = glowSprite("rgba(255,130,60,0.9)", 1.6, 0.3);
    s.position.set(-0.2, 0.3, 0.75);
    g.add(s);
    smokeAt(g, 0.45, 2.15, -0.25);
    // étincelles de l'enclume
    anims.push((t) => { if (Math.random() < 0.025 && started) burst(g.localToWorld(new THREE.Vector3(0.55, 0.45, 0.95)), 6, ["#ffb347", "#ffd27a"], 1.2, 3, 0.5, 0.04); });
    return g;
  },

  qg() {
    const g = new THREE.Group();
    g.add(box(1.7, 0.2, 1.3, C.stoneDark));
    g.add(box(1.5, 1.25, 1.1, C.white, 0, 0.2, 0));
    g.add(box(1.52, 0.18, 1.12, C.violet, 0, 0.9, 0));
    for (let i = -1; i <= 1; i++) g.add(win(0.34, 0.3, i * 0.45, 0.55, 0.56), win(0.34, 0.3, i * 0.45, 1.25, 0.56));
    g.add(box(0.6, 0.55, 0.5, C.white, 0.35, 1.45, -0.1));
    g.add(cyl(0.02, 0.02, 0.8, C.metal, -0.5, 1.45, -0.3, 4));
    const dish = mesh(new THREE.SphereGeometry(0.22, 8, 4, 0, Math.PI * 2, 0, Math.PI / 2), M(C.metal), -0.2, 1.5, 0.25);
    dish.rotation.x = -0.9;
    g.add(dish);
    anims.push((t) => { dish.rotation.z = Math.sin(t * 0.5) * 0.8; });
    g.add(box(0.36, 0.36, 0.36, "#2d2a3a", -0.9, 0.2, 0.75));
    const head = box(0.08, 0.06, 0.08, glowMat(C.rose), -0.9, 0.42, 0.75);
    g.add(head);
    anims.push((t) => { head.position.x = -0.9 + Math.sin(t * 3) * 0.1; });
    g.add(lantern(0.95, 0, 0.8));
    return g;
  },

  banque() {
    const g = new THREE.Group();
    g.add(box(1.8, 0.14, 1.4, C.stone), box(1.6, 0.14, 1.25, C.stone, 0, 0.14, 0));
    g.add(box(1.4, 1.0, 0.8, C.white, 0, 0.28, -0.15));
    for (let i = 0; i < 5; i++) g.add(cyl(0.07, 0.08, 0.95, C.white, -0.6 + i * 0.3, 0.28, 0.45, 8));
    g.add(box(1.6, 0.14, 1.25, C.stone, 0, 1.23, 0));
    const roof = gable(1.25, 1.65, 0.45, C.stone, 0, 1.37, 0);
    roof.rotation.y = Math.PI / 2;
    g.add(roof);
    g.add(win(0.3, 0.5, 0, 0.3, 0.26));
    const coin = mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.07, 20), M(C.gold, { metalness: 0.75, roughness: 0.28, emissive: "#6b4a00", emissiveIntensity: 0.35 }), 0, 2.45, 0);
    coin.rotation.x = Math.PI / 2;
    g.add(coin);
    anims.push((t) => { coin.rotation.z = t * 1.5; coin.position.y = 2.45 + Math.sin(t * 2) * 0.08; });
    const s = glowSprite("rgba(255,214,110,0.8)", 1.4, 0.25);
    s.position.set(0, 2.45, 0);
    g.add(s);
    g.add(lantern(-0.95, 0, 0.75), lantern(0.95, 0, 0.75));
    return g;
  },

  marche() {
    const g = new THREE.Group();
    const stall = (x, z, ry, c1, c2) => {
      const s = new THREE.Group();
      s.add(box(0.75, 0.32, 0.45, C.wood));
      for (const [px, pz] of [[-0.34, -0.2], [0.34, -0.2], [-0.34, 0.2], [0.34, 0.2]]) s.add(cyl(0.025, 0.025, 0.85, C.woodDark, px, 0, pz, 4));
      for (let i = 0; i < 5; i++) {
        const strip = box(0.17, 0.05, 0.62, i % 2 ? c1 : c2, -0.34 + i * 0.17, 0.85, 0);
        strip.rotation.x = 0.25;
        s.add(strip);
      }
      s.add(box(0.14, 0.1, 0.14, "#e05a47", -0.18, 0.32, 0.05), box(0.14, 0.1, 0.14, "#f2c94c", 0.05, 0.32, 0.05), box(0.14, 0.1, 0.14, "#7ac74f", 0.25, 0.32, 0.05));
      s.position.set(x, 0, z);
      s.rotation.y = ry;
      return s;
    };
    g.add(stall(-0.55, -0.35, 0.3, C.rose, C.white), stall(0.6, -0.3, -0.3, C.roofTeal, C.white), stall(0, 0.65, Math.PI, C.violet, C.white));
    g.add(box(0.25, 0.25, 0.25, C.wood, 0.85, 0, 0.55), box(0.2, 0.2, 0.2, C.wood, 0.9, 0.25, 0.55), box(0.25, 0.25, 0.25, C.wood, -0.9, 0, 0.5));
    g.add(lantern(0, 0, 0));
    return g;
  },

  observatoire() {
    const g = new THREE.Group();
    g.add(cyl(0.75, 0.85, 0.3, C.stoneDark));
    g.add(cyl(0.55, 0.62, 1.3, C.white, 0, 0.3, 0, 12));
    const top = new THREE.Group();
    top.position.y = 1.6;
    top.add(mesh(new THREE.SphereGeometry(0.62, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), M(C.roofViolet)));
    const scope = cyl(0.09, 0.13, 1.0, C.metal, 0, 0, 0, 8);
    scope.position.set(0, 0.45, 0.3);
    scope.rotation.x = 0.8;
    top.add(scope);
    g.add(top);
    anims.push((t) => { top.rotation.y = t * 0.25; });
    g.add(win(0.18, 0.3, 0, 0.9, 0.6), win(0.18, 0.3, 0.6, 0.9, 0, Math.PI / 2));
    const s = glowSprite("rgba(190,160,255,0.8)", 2.2);
    s.position.set(0, 2.4, 0);
    g.add(s);
    return g;
  },

  arene() {
    const g = new THREE.Group();
    g.add(mesh(new THREE.CylinderGeometry(1.2, 1.3, 0.75, 20, 1, true), M(C.stone, { side: THREE.DoubleSide }), 0, 0.375, 0));
    g.add(cyl(1.15, 1.15, 0.04, C.sand, 0, 0, 0, 20));
    for (let i = 0; i < 10; i++) {
      const a = (i / 10) * Math.PI * 2;
      g.add(box(0.16, 0.18, 0.16, C.stone, Math.cos(a) * 1.25, 0.75, Math.sin(a) * 1.25));
    }
    for (let i = 0; i < 4; i++) {
      const a = (i / 4) * Math.PI * 2 + Math.PI / 4;
      g.add(flag(i % 2 ? C.violet : C.rose, Math.cos(a) * 1.3, 0.75, Math.sin(a) * 1.3, 0.7));
    }
    const f1 = box(0.22, 0.3, 0.22, C.violet, -0.3, 0.04, 0), f2 = box(0.22, 0.3, 0.22, C.rose, 0.3, 0.04, 0);
    g.add(f1, f2);
    anims.push((t) => {
      f1.position.y = 0.04 + Math.max(0, Math.sin(t * 3)) * 0.15;
      f2.position.y = 0.04 + Math.max(0, Math.sin(t * 3 + Math.PI)) * 0.15;
      f1.rotation.y = t; f2.rotation.y = -t;
    });
    return g;
  },

  bibliotheque() {
    const g = new THREE.Group();
    g.add(box(1.5, 0.95, 1.1, C.stone));
    g.add(gable(1.6, 1.25, 0.55, C.roofBlue, 0, 0.95, 0));
    g.add(box(0.36, 0.55, 0.06, C.woodDark, 0, 0, 0.56));
    g.add(win(0.22, 0.3, -0.45, 0.5, 0.56), win(0.22, 0.3, 0.45, 0.5, 0.56));
    const book = new THREE.Group();
    const pageL = box(0.45, 0.03, 0.6, C.white, -0.23, 0, 0), pageR = box(0.45, 0.03, 0.6, C.white, 0.23, 0, 0);
    pageL.rotation.z = 0.2; pageR.rotation.z = -0.2;
    book.add(pageL, pageR, box(0.06, 0.06, 0.62, C.roofBlue, 0, -0.03, 0));
    book.position.set(0, 2.2, 0);
    g.add(book);
    anims.push((t) => { book.position.y = 2.2 + Math.sin(t * 1.6) * 0.1; book.rotation.y = Math.sin(t * 0.5) * 0.4; });
    const s = glowSprite("rgba(160,190,255,0.85)", 1.8, 0.25);
    s.position.set(0, 2.25, 0);
    g.add(s);
    return g;
  },

  ruche() {
    const g = new THREE.Group();
    for (const [y, r] of [[0, 0.9], [0.35, 0.78], [0.7, 0.62]]) g.add(mesh(new THREE.CylinderGeometry(r, r, 0.33, 6), M(C.honey), 0, y + 0.165, 0));
    g.add(mesh(new THREE.CylinderGeometry(0.35, 0.62, 0.3, 6), M("#d99a22"), 0, 1.2, 0));
    for (const [x, z] of [[-0.95, -0.6], [0.95, -0.6], [-0.95, 0.6], [0.95, 0.6]]) g.add(cyl(0.025, 0.025, 1.7, C.wood, x, 0, z, 4));
    g.add(box(1.95, 0.04, 0.05, C.wood, 0, 0.9, -0.6), box(1.95, 0.04, 0.05, C.wood, 0, 0.9, 0.6), box(1.95, 0.04, 0.05, C.wood, 0, 1.65, -0.6));
    const crane = new THREE.Group();
    crane.add(box(0.12, 2.6, 0.12, "#f2b134"));
    const arm = new THREE.Group();
    arm.position.y = 2.6;
    arm.add(box(1.8, 0.1, 0.1, "#f2b134", 0.6, 0, 0), box(0.3, 0.25, 0.25, "#3a3a46", -0.35, -0.1, 0));
    arm.add(box(0.04, 0.6, 0.04, "#3a3a46", 1.35, -0.6, 0));
    crane.add(arm);
    crane.position.set(1.2, 0, -0.2);
    g.add(crane);
    anims.push((t) => { arm.rotation.y = Math.sin(t * 0.35) * 1.1; });
    for (let i = 0; i < 4; i++) {
      const bee = ball(0.07, glowMat(i % 2 ? C.rose : C.violet, 1.6));
      g.add(bee);
      const ph = (i / 4) * Math.PI * 2;
      anims.push((t) => { bee.position.set(Math.cos(t * 1.4 + ph) * 1.1, 1.6 + Math.sin(t * 3 + ph) * 0.2, Math.sin(t * 1.4 + ph) * 1.1); });
    }
    return g;
  },

  radio() {
    const g = new THREE.Group();
    g.add(box(0.6, 0.45, 0.6, C.white), box(0.62, 0.08, 0.62, C.roofTeal, 0, 0.45, 0));
    for (let i = 0; i < 6; i++) {
      const w = 0.42 - i * 0.06;
      g.add(box(w, 0.05, w, C.metal, 0, 0.55 + i * 0.4, 0));
      for (const [x, z] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) g.add(box(0.035, 0.42, 0.035, "#c33d3d", (x * w) / 2, 0.55 + i * 0.4, (z * w) / 2));
    }
    const tip = ball(0.08, glowMat("#ff3b3b"), 0, 3.0, 0);
    g.add(tip);
    anims.push((t) => { tip.material.emissiveIntensity = Math.sin(t * 4) > 0 ? 2.6 : 0.2; });
    for (let i = 0; i < 3; i++) {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.3, 0.015, 4, 32), new THREE.MeshBasicMaterial({ color: C.rose, transparent: true }));
      ring.rotation.x = Math.PI / 2;
      ring.position.y = 3.0;
      g.add(ring);
      anims.push((t) => {
        const k = (t * 0.5 + i / 3) % 1;
        ring.scale.setScalar(1 + k * 4);
        ring.material.opacity = (1 - k) * 0.8;
      });
    }
    return g;
  },

  academie() {
    const g = new THREE.Group();
    g.add(box(2.0, 1.0, 1.2, C.white));
    g.add(gable(2.15, 1.35, 0.55, C.roofBlue, 0, 1.0, 0));
    g.add(box(0.55, 1.95, 0.55, C.stone, 0, 0, 0.35));
    g.add(pyramid(0.75, 0.6, C.roofBlue, 0, 1.95, 0.35));
    const clockFace = mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.03, 16), M(C.white), 0, 1.6, 0.63);
    clockFace.rotation.x = Math.PI / 2;
    g.add(clockFace);
    const hand = box(0.02, 0.12, 0.02, "#222222", 0, 1.6, 0.66);
    g.add(hand);
    anims.push((t) => { hand.rotation.z = -t * 0.8; });
    g.add(box(0.36, 0.55, 0.06, C.woodDark, 0, 0, 0.63));
    for (const x of [-0.7, -0.45, 0.45, 0.7]) g.add(win(0.16, 0.3, x, 0.55, 0.61));
    g.add(box(0.06, 0.6, 0.02, C.violet, -0.32, 0.9, 0.63), box(0.06, 0.6, 0.02, C.violet, 0.32, 0.9, 0.63));
    g.add(lantern(-1.1, 0, 0.7));
    return g;
  },

  camp() {
    const g = new THREE.Group();
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2;
      g.add(cyl(0.035, 0.035, 0.35, C.wood, Math.cos(a) * 1.2, 0, Math.sin(a) * 1.2, 4));
    }
    const tent = cone(0.6, 0.8, C.roofTeal, -0.35, 0, -0.35, 4);
    tent.rotation.y = Math.PI / 4;
    g.add(tent);
    for (const [x, z] of [[0.45, -0.3], [0.5, 0.35]]) {
      g.add(cyl(0.04, 0.04, 0.5, C.wood, x, 0, z, 4));
      g.add(cyl(0.13, 0.13, 0.35, "#d8b07a", x, 0.4, z, 6));
      g.add(ball(0.11, "#d8b07a", x, 0.88, z, 6, 5));
    }
    const target = mesh(new THREE.CylinderGeometry(0.28, 0.28, 0.05, 16), M(C.white), -0.4, 0.45, 0.6);
    target.rotation.x = Math.PI / 2;
    const bull = mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.06, 16), M("#d64545"), -0.4, 0.45, 0.6);
    bull.rotation.x = Math.PI / 2;
    g.add(target, bull);
    g.add(box(0.3, 0.06, 0.06, C.woodDark, 0, 0, 0.1), box(0.06, 0.06, 0.3, C.woodDark, 0, 0, 0.1));
    const flame = cone(0.1, 0.25, glowMat("#ff8a3d", 2), 0, 0.05, 0.1, 5);
    g.add(flame);
    anims.push((t) => { flame.scale.y = 1 + Math.sin(t * 12) * 0.2; });
    const s = glowSprite("rgba(255,140,60,0.9)", 1.6, 0.25);
    s.position.set(0, 0.3, 0.1);
    g.add(s);
    return g;
  },

  scriptorium() {
    const g = new THREE.Group();
    g.add(box(1.7, 0.18, 1.3, C.stoneDark));
    g.add(box(1.5, 1.15, 1.1, C.stone, 0, 0.18, 0));
    g.add(gable(1.65, 1.3, 0.7, C.roofTeal, 0, 1.33, 0));
    const rose = mesh(new THREE.CylinderGeometry(0.26, 0.26, 0.05, 12), glowMat("#b89cff", 0.8), 0, 1.05, 0.56);
    rose.rotation.x = Math.PI / 2;
    g.add(rose);
    g.add(box(0.38, 0.6, 0.06, C.woodDark, 0, 0.18, 0.56));
    g.add(win(0.18, 0.32, -0.5, 0.65, 0.56), win(0.18, 0.32, 0.5, 0.65, 0.56));
    const quill = new THREE.Group();
    const feather = cone(0.16, 1.0, C.white, 0, 0, 0, 6);
    feather.scale.z = 0.25;
    quill.add(feather, cyl(0.02, 0.02, 0.3, "#3a3a46", 0, -0.3, 0, 5));
    quill.position.set(0.15, 2.45, 0);
    quill.rotation.z = -0.5;
    g.add(quill);
    anims.push((t) => { quill.position.y = 2.45 + Math.sin(t * 1.4) * 0.12; quill.rotation.y = t * 0.6; });
    for (let i = 0; i < 5; i++) {
      const page = mesh(new THREE.PlaneGeometry(0.22, 0.28), M(C.white, { side: THREE.DoubleSide }));
      page.castShadow = false;
      g.add(page);
      const ph = (i / 5) * Math.PI * 2;
      anims.push((t) => {
        page.position.set(Math.cos(t * 0.6 + ph) * 1.15, 1.9 + Math.sin(t * 1.3 + ph) * 0.35, Math.sin(t * 0.6 + ph) * 1.15);
        page.rotation.set(Math.sin(t + ph) * 0.6, t + ph, Math.cos(t * 0.8 + ph) * 0.4);
      });
    }
    const s = glowSprite("rgba(184,156,255,0.9)", 2.2, 0.3);
    s.position.set(0, 2.3, 0);
    g.add(s);
    g.add(lantern(-0.95, 0, 0.75));
    return g;
  },

  pigeonnier() {
    const g = new THREE.Group();
    g.add(cyl(0.7, 0.75, 0.2, C.stoneDark, 0, 0, 0, 10));
    g.add(cyl(0.5, 0.56, 1.7, C.white, 0, 0.2, 0, 10));
    for (let row = 0; row < 3; row++) {
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2 + row * 0.4;
        const hole = box(0.1, 0.1, 0.04, "#3a2f45", Math.cos(a) * 0.52, 0.75 + row * 0.35, Math.sin(a) * 0.52);
        hole.rotation.y = -a + Math.PI / 2;
        hole.castShadow = false;
        g.add(hole);
      }
    }
    g.add(cone(0.72, 0.75, C.roofRed, 0, 1.9, 0, 10));
    g.add(cyl(0.02, 0.02, 0.35, C.metal, 0, 2.65, 0, 4));
    for (let i = 0; i < 3; i++) {
      const p = makePigeon(1);
      g.add(p.group);
      const ph = (i / 3) * Math.PI * 2, rad = 1.3 + i * 0.25;
      anims.push((t) => {
        const a = t * (0.7 + i * 0.1) + ph;
        p.group.position.set(Math.cos(a) * rad, 2.5 + Math.sin(t * 2 + ph) * 0.2 + i * 0.2, Math.sin(a) * rad);
        p.group.rotation.y = -a - Math.PI / 2;
        const flap = Math.sin(t * 14 + ph) * 0.7;
        p.wingL.rotation.x = flap; p.wingR.rotation.x = -flap;
      });
    }
    g.add(lantern(0.85, 0, 0.5));
    return g;
  },

  monument() {
    const g = new THREE.Group();
    g.add(box(1.0, 0.25, 1.0, C.stone), box(0.75, 0.25, 0.75, C.stone, 0, 0.25, 0), box(0.5, 0.6, 0.5, C.white, 0, 0.5, 0));
    const trophy = new THREE.Group();
    const gold = M(C.gold, { metalness: 0.8, roughness: 0.25, emissive: "#6b4a00", emissiveIntensity: 0.35 });
    trophy.add(mesh(new THREE.CylinderGeometry(0.1, 0.18, 0.1, 10), gold, 0, 0.05, 0));
    trophy.add(mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.25, 8), gold, 0, 0.22, 0));
    trophy.add(mesh(new THREE.CylinderGeometry(0.28, 0.1, 0.4, 12), gold, 0, 0.55, 0));
    for (const x of [-0.3, 0.3]) trophy.add(mesh(new THREE.TorusGeometry(0.1, 0.025, 6, 12), gold, x, 0.58, 0));
    trophy.position.y = 1.1;
    g.add(trophy);
    anims.push((t) => { trophy.rotation.y = t * 0.6; });
    const king = new THREE.Group();
    king.add(cyl(0.12, 0.15, 0.08, "#2b2735"), cyl(0.06, 0.1, 0.35, "#2b2735", 0, 0.08, 0), ball(0.08, "#2b2735", 0, 0.5, 0));
    king.add(box(0.03, 0.14, 0.03, "#2b2735", 0, 0.55, 0), box(0.1, 0.03, 0.03, "#2b2735", 0, 0.62, 0));
    king.position.set(0.7, 0, 0.55);
    const pawn = new THREE.Group();
    pawn.add(cyl(0.1, 0.12, 0.06, C.white), cyl(0.04, 0.08, 0.2, C.white, 0, 0.06, 0), ball(0.07, C.white, 0, 0.32, 0));
    pawn.position.set(-0.7, 0, 0.6);
    g.add(king, pawn);
    const s = glowSprite("rgba(255,210,100,0.9)", 2.4, 0.5);
    s.position.set(0, 1.7, 0);
    g.add(s);
    return g;
  },

  phare() {
    const g = new THREE.Group();
    const H = 3.0, seg = 5;
    for (let i = 0; i < seg; i++) {
      const r0 = 0.5 - (i / seg) * 0.2, r1 = 0.5 - ((i + 1) / seg) * 0.2;
      g.add(mesh(new THREE.CylinderGeometry(r1, r0, H / seg, 12), M(i % 2 ? C.white : "#d64545"), 0, (i + 0.5) * (H / seg), 0));
    }
    g.add(cyl(0.42, 0.42, 0.08, "#333333", 0, H, 0, 12));
    g.add(cyl(0.22, 0.22, 0.4, glowMat("#fff2b0", 2.2), 0, H + 0.08, 0, 10));
    g.add(cone(0.32, 0.35, "#d64545", 0, H + 0.48, 0, 10));
    const beamGeo = new THREE.ConeGeometry(0.9, 9, 16, 1, true);
    beamGeo.translate(0, -4.5, 0);
    beamGeo.rotateZ(Math.PI / 2);
    const beamMat = new THREE.MeshBasicMaterial({ color: "#fff3c4", transparent: true, opacity: 0.08, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    const beam = new THREE.Mesh(beamGeo, beamMat);
    beam.position.y = H + 0.28;
    g.add(beam);
    anims.push((t) => { beam.rotation.y = t * 0.9; beamMat.opacity = 0.05 + nightT * 0.24; });
    const s = glowSprite("rgba(255,240,180,1)", 2.6, 0.4);
    s.position.y = H + 0.3;
    g.add(s);
    return g;
  },
};

function buildBuildings() {
  buildings = new Map();
  pickables = [];
  for (const p of Object.values(PLACE)) {
    const make = BUILD[p.id];
    if (!make) continue;
    const [x, z] = hexToWorld(p.hex[0], p.hex[1]);
    const y = topOf(p.hex[0], p.hex[1]);
    const g = make();
    g.position.set(x, y, z);
    g.rotation.y = p.id === "chateau" ? Math.PI / 6 : Math.atan2(x, z) + Math.PI; // façade vers le centre
    g.traverse((o) => { if (o.isMesh) { o.userData.placeId = p.id; pickables.push(o); } });
    scene.add(g);
    const bb = new THREE.Box3().setFromObject(g);
    // Étiquette posée juste au-dessus du bâtiment (on ignore ce qui flotte très haut)
    buildings.set(p.id, { group: g, top: Math.min(bb.max.y, y + 2.8) + 0.35, world: new THREE.Vector3(x, y, z) });
    if (p.id === "pigeonnier") pigeonnierTop = new THREE.Vector3(x, y + 2.4, z);
  }

  // Moulin
  const [mx, mz] = hexToWorld(MILL_HEX[0], MILL_HEX[1]);
  const mill = new THREE.Group();
  mill.add(cyl(0.35, 0.5, 1.5, C.white, 0, 0, 0, 8), cone(0.45, 0.5, C.roofRed, 0, 1.5, 0, 8));
  const blades = new THREE.Group();
  blades.position.set(0, 1.35, 0.5);
  for (let i = 0; i < 4; i++) {
    const b = box(0.14, 0.9, 0.03, C.wood);
    b.geometry.translate(0, 0.45, 0);
    b.position.set(0, 0, 0);
    b.rotation.z = (i * Math.PI) / 2;
    blades.add(b);
  }
  mill.add(blades);
  anims.push((t) => { blades.rotation.z = t * 1.2; });
  mill.position.set(mx, H0, mz);
  mill.rotation.y = 0.6;
  scene.add(mill);

  // Huttes de villageois
  let placed = 0;
  for (const t of tileList) {
    if (placed >= 8) break;
    if (t.reserved || t.forest || t.type !== "grass") continue;
    if (Object.values(PLACE).some((p) => hexDist(p.hex, [t.q, t.r]) < 2)) continue;
    if (hash2(t.q * 5.7, t.r * 2.3) > 0.18) continue;
    const [x, z] = hexToWorld(t.q, t.r);
    const hut = new THREE.Group();
    hut.add(box(0.55, 0.4, 0.45, C.white), gable(0.62, 0.55, 0.35, rand() < 0.5 ? C.roofRed : C.roofTeal, 0, 0.4, 0), win(0.12, 0.12, 0.15, 0.22, 0.23));
    hut.position.set(x + (rand() - 0.5) * 0.3, t.h, z + (rand() - 0.5) * 0.3);
    hut.rotation.y = rand() * Math.PI;
    t.reserved = true;
    scene.add(hut);
    placed++;
  }
}

/* =========================================================================
   BOSS
   ========================================================================= */

// Chaîne de sphères qui suit une courbe (cous, tentacules)
function chain(count, r0, r1, color) {
  const parts = [];
  for (let i = 0; i < count; i++) {
    const k = i / (count - 1);
    parts.push(ball(r0 + (r1 - r0) * k, color, 0, 0, 0, 8, 6));
  }
  return parts;
}

const BOSS_BUILD = {
  bug() {
    const g = new THREE.Group();
    const shellMat = own("#3b2a5a", { emissive: "#1a0f2e", emissiveIntensity: 0.6, roughness: 0.45, metalness: 0.2 });
    const shell = mesh(new THREE.SphereGeometry(0.6, 12, 8), shellMat, 0, 0.55, 0);
    shell.scale.set(1.35, 0.72, 1);
    g.add(shell);
    g.add(box(1.4, 0.03, 0.05, glowMat("#a78bfa", 1.5), 0, 0.97, 0));
    const head = ball(0.32, own("#2a1d40"), 0.85, 0.45, 0, 10, 8);
    g.add(head);
    const eyeMat = glowMat("#ff2e63", 2.6);
    g.add(ball(0.07, eyeMat, 1.1, 0.55, 0.14), ball(0.07, eyeMat, 1.1, 0.55, -0.14));
    for (const s of [1, -1]) {
      const mand = cone(0.05, 0.3, own("#1b1228"), 1.18, 0.3, 0.12 * s, 5);
      mand.rotation.z = -1.2;
      g.add(mand);
      const ant = cyl(0.015, 0.015, 0.7, own("#1b1228"), 1.0, 0.65, 0.12 * s, 4);
      ant.rotation.set(0.4 * s, 0, -0.7);
      g.add(ant);
    }
    const legs = [];
    for (let i = 0; i < 3; i++) {
      for (const s of [1, -1]) {
        const leg = new THREE.Group();
        const seg1 = box(0.06, 0.06, 0.55, own("#22172f"), 0, 0, 0.27 * s);
        const seg2 = box(0.05, 0.4, 0.05, own("#22172f"), 0, -0.4, 0.55 * s);
        leg.add(seg1, seg2);
        leg.position.set(-0.45 + i * 0.45, 0.55, 0.3 * s);
        g.add(leg);
        legs.push({ leg, ph: i * 2.1 + (s > 0 ? 0 : Math.PI) });
      }
    }
    const aura = glowSprite("rgba(167,139,250,0.8)", 3.2, 0.35);
    aura.position.y = 0.5;
    g.add(aura);
    g.scale.setScalar(1.25);
    return {
      group: g,
      forward: "x",
      idle(t) {
        shell.position.y = 0.55 + Math.sin(t * 4) * 0.03;
        legs.forEach(({ leg, ph }) => { leg.rotation.x = Math.sin(t * 8 + ph) * 0.25; });
        g.rotation.y = (this.baseYaw ?? 0) + Math.sin(t * 0.4) * 0.5;
      },
      mouth: new THREE.Vector3(1.2, 0.4, 0),
    };
  },

  hydre() {
    const g = new THREE.Group();
    const scale = own("#1f8f86", { roughness: 0.35, metalness: 0.15 });
    const belly = own("#8fe0c9");
    const body = mesh(new THREE.SphereGeometry(1.4, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), scale, 0, -0.2, 0);
    g.add(body);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(1.7, 0.12, 6, 28), new THREE.MeshBasicMaterial({ color: "#ffffff", transparent: true, opacity: 0.55 }));
    ring.rotation.x = Math.PI / 2;
    ring.position.y = 0.02;
    g.add(ring);
    const necks = [];
    for (let n = 0; n < 3; n++) {
      const parts = chain(8, 0.32, 0.2, n === 1 ? scale : own("#23a196", { roughness: 0.35 }));
      parts.forEach((p) => g.add(p));
      const head = new THREE.Group();
      head.add(box(0.5, 0.28, 0.32, scale, 0.15, -0.14, 0), box(0.42, 0.1, 0.28, belly, 0.18, -0.2, 0));
      const eye = glowMat("#ffe14d", 2.6);
      head.add(ball(0.05, eye, 0.12, 0.08, 0.13), ball(0.05, eye, 0.12, 0.08, -0.13));
      head.add(cone(0.05, 0.22, belly, -0.1, 0.1, 0.1, 4), cone(0.05, 0.22, belly, -0.1, 0.1, -0.1, 4));
      g.add(head);
      necks.push({ parts, head, base: new THREE.Vector3((n - 1) * 0.95, 0.2, (n === 1 ? -0.2 : 0.25)), ph: n * 1.7, alive: true, drop: 0 });
    }
    g.scale.setScalar(1.35);
    const tmp = new THREE.Vector3();
    return {
      group: g,
      forward: "x",
      idle(t) {
        ring.scale.setScalar(1 + Math.sin(t * 2) * 0.05);
        ring.material.opacity = 0.45 + Math.sin(t * 2) * 0.1;
        for (const nk of necks) {
          nk.drop = nk.alive ? Math.max(0, nk.drop - 0.02) : Math.min(1, nk.drop + 0.02);
          const height = 2.8 * (1 - nk.drop * 0.95);
          nk.parts.forEach((p, i) => {
            const k = i / (nk.parts.length - 1);
            tmp.set(
              nk.base.x + Math.sin(t * 1.3 + nk.ph + k * 2.2) * 0.35 * k + k * 0.6 * Math.sign(nk.base.x || 0.001),
              nk.base.y + k * height,
              nk.base.z + Math.cos(t * 1.1 + nk.ph + k * 2.0) * 0.3 * k,
            );
            p.position.copy(tmp);
          });
          const last = nk.parts[nk.parts.length - 1].position;
          nk.head.position.set(last.x + 0.2, last.y + 0.15, last.z);
          nk.head.rotation.z = Math.sin(t * 2 + nk.ph) * 0.25 - 0.2;
          nk.head.rotation.y = Math.sin(t * 0.8 + nk.ph) * 0.5;
        }
        g.position.y = WATER_Y + Math.sin(t * 1.2) * 0.08;
      },
      onHpRatio(r) {
        // les têtes tombent une à une : à 2/3 des PV, à 1/3, puis à la mort
        necks.forEach((nk, i) => { nk.alive = r > (2 - i) / 3 + 0.001; });
      },
      mouth: new THREE.Vector3(0, 3.2, 0),
    };
  },

  golem() {
    const g = new THREE.Group();
    const rock = own("#7d7a8c", { roughness: 0.95 });
    const dark = own("#5b586a", { roughness: 0.95 });
    const core = glowMat("#38e1ff", 2.2);
    g.add(box(0.42, 0.75, 0.45, dark, -0.32, 0, 0), box(0.42, 0.75, 0.45, dark, 0.32, 0, 0));
    const torso = box(1.35, 1.05, 0.85, rock, 0, 0.75, 0);
    g.add(torso);
    g.add(box(0.36, 0.36, 0.06, core, 0, 1.15, 0.44));
    for (const y of [0.95, 1.4]) g.add(box(1.0, 0.04, 0.03, core, 0, y, 0.43));
    const head = new THREE.Group();
    head.add(box(0.6, 0.48, 0.55, rock, 0, 0, 0), box(0.5, 0.06, 0.04, core, 0, 0.06, 0.29));
    head.position.set(0, 1.85, 0.05);
    g.add(head);
    const arms = [];
    for (const s of [1, -1]) {
      const arm = new THREE.Group();
      arm.add(box(0.5, 0.45, 0.5, dark, 0, -0.1, 0), box(0.38, 0.9, 0.38, rock, 0, -0.85, 0), box(0.5, 0.42, 0.5, dark, 0, -1.4, 0));
      arm.position.set(0.95 * s, 1.75, 0);
      g.add(arm);
      arms.push({ arm, s });
    }
    const rocks = [];
    for (let i = 0; i < 4; i++) {
      const r = mesh(new THREE.DodecahedronGeometry(0.16 + i * 0.03, 0), dark);
      g.add(r);
      rocks.push({ r, ph: (i / 4) * Math.PI * 2 });
    }
    const aura = glowSprite("rgba(56,225,255,0.7)", 3, 0.3);
    aura.position.y = 1.2;
    g.add(aura);
    g.scale.setScalar(1.15);
    return {
      group: g,
      forward: "z",
      idle(t) {
        torso.scale.y = 1 + Math.sin(t * 1.5) * 0.02;
        head.rotation.y = Math.sin(t * 0.6) * 0.4;
        arms.forEach(({ arm, s }) => { arm.rotation.x = Math.sin(t * 1.2 + (s > 0 ? 0 : 1.5)) * 0.15; });
        rocks.forEach(({ r, ph }) => r.position.set(Math.cos(t * 0.9 + ph) * 1.6, 1.4 + Math.sin(t * 1.7 + ph) * 0.3, Math.sin(t * 0.9 + ph) * 1.6));
        core.emissiveIntensity = 1.8 + Math.sin(t * 3) * 0.6;
      },
      mouth: new THREE.Vector3(0, 1.85, 0.4),
    };
  },

  kraken() {
    const g = new THREE.Group();
    const skin = own("#7a2f8f", { roughness: 0.4, metalness: 0.1 });
    const spots = own("#c86bd8");
    const head = mesh(new THREE.SphereGeometry(1.1, 14, 10), skin, 0, 1.3, 0);
    head.scale.set(0.9, 1.25, 0.9);
    g.add(head);
    for (let i = 0; i < 6; i++) g.add(ball(0.12, spots, Math.cos(i) * 0.75, 1.7 + Math.sin(i * 2) * 0.4, Math.sin(i) * 0.75));
    const eyeWhite = own("#fff6c2", { emissive: "#ffe66d", emissiveIntensity: 1.6 });
    const pupil = own("#120a18");
    for (const s of [1, -1]) {
      g.add(ball(0.22, eyeWhite, 0.45 * s, 1.15, 0.8), ball(0.1, pupil, 0.45 * s, 1.15, 0.98));
    }
    const tentacles = [];
    for (let n = 0; n < 8; n++) {
      const parts = chain(9, 0.24, 0.07, n % 2 ? skin : own("#8c3aa3", { roughness: 0.4 }));
      parts.forEach((p) => g.add(p));
      tentacles.push({ parts, a: (n / 8) * Math.PI * 2, ph: n * 0.8 });
    }
    const ring = new THREE.Mesh(new THREE.TorusGeometry(2.2, 0.1, 6, 32), new THREE.MeshBasicMaterial({ color: "#ffffff", transparent: true, opacity: 0.5 }));
    ring.rotation.x = Math.PI / 2;
    ring.position.y = 0.03;
    g.add(ring);
    g.scale.setScalar(1.3);
    return {
      group: g,
      forward: "z",
      idle(t) {
        head.position.y = 1.3 + Math.sin(t * 1.1) * 0.12;
        for (const tc of tentacles) {
          tc.parts.forEach((p, i) => {
            const k = i / (tc.parts.length - 1);
            const rad = 1.0 + k * 1.3;
            const lift = Math.sin(k * Math.PI) * (1.4 + Math.sin(t * 1.4 + tc.ph) * 0.6);
            const swirl = tc.a + Math.sin(t * 1.2 + tc.ph + k * 3) * 0.35 * k;
            p.position.set(Math.cos(swirl) * rad, 0.2 + lift, Math.sin(swirl) * rad);
          });
        }
        ring.rotation.z = t * 0.5;
        g.position.y = WATER_Y - 0.3 + Math.sin(t * 0.9) * 0.08;
      },
      mouth: new THREE.Vector3(0, 1.1, 1.0),
    };
  },

  dragon() {
    const g = new THREE.Group();
    const scales = own("#a32b2b", { roughness: 0.4, metalness: 0.2 });
    const dark = own("#5c1414", { roughness: 0.5 });
    const belly = own("#f2b46b");
    const horn = own("#f3ead7");
    const body = mesh(new THREE.SphereGeometry(0.8, 14, 10), scales, 0, 1.0, 0);
    body.scale.set(1.5, 0.95, 1);
    g.add(body);
    const bellyMesh = mesh(new THREE.SphereGeometry(0.6, 12, 8), belly, 0.2, 0.85, 0);
    bellyMesh.scale.set(1.3, 0.8, 0.9);
    g.add(bellyMesh);
    for (const [x, z] of [[0.6, 0.45], [0.6, -0.45], [-0.6, 0.45], [-0.6, -0.45]]) g.add(box(0.22, 0.6, 0.22, dark, x, 0.25, z));
    const neck = chain(5, 0.36, 0.26, scales);
    neck.forEach((p, i) => { p.position.set(1.0 + i * 0.22, 1.25 + i * 0.28, 0); g.add(p); });
    const head = new THREE.Group();
    head.add(box(0.6, 0.42, 0.5, scales, 0, 0, 0), box(0.55, 0.22, 0.4, scales, 0.45, -0.08, 0), box(0.5, 0.08, 0.36, belly, 0.48, -0.2, 0));
    const eye = glowMat("#ffb000", 3);
    head.add(ball(0.06, eye, 0.18, 0.12, 0.22), ball(0.06, eye, 0.18, 0.12, -0.22));
    for (const s of [1, -1]) {
      const h = cone(0.07, 0.45, horn, -0.15, 0.2, 0.15 * s, 5);
      h.rotation.z = 1.0;
      head.add(h);
    }
    head.position.set(2.1, 2.45, 0);
    g.add(head);
    const wings = [];
    for (const s of [1, -1]) {
      const wing = new THREE.Group();
      wing.add(box(0.1, 0.1, 1.9, dark, 0, 0, 0.95 * s));
      const shape = new THREE.BufferGeometry();
      const v = new Float32Array([0, 0, 0, 0, 0, 1.9 * s, -1.3, -0.1, 1.5 * s, 0, 0, 0, -1.3, -0.1, 1.5 * s, -1.0, -0.1, 0.3 * s]);
      shape.setAttribute("position", new THREE.BufferAttribute(v, 3));
      shape.computeVertexNormals();
      wing.add(mesh(shape, own("#7a1f2b", { side: THREE.DoubleSide, roughness: 0.6 })));
      wing.position.set(0.1, 1.55, 0.3 * s);
      g.add(wing);
      wings.push({ wing, s });
    }
    const tail = chain(7, 0.3, 0.08, scales);
    tail.forEach((p) => g.add(p));
    const spikes = [];
    for (let i = 0; i < 5; i++) {
      const sp = cone(0.08, 0.3, horn, -0.3 + i * 0.3, 1.65, 0, 4);
      g.add(sp);
      spikes.push(sp);
    }
    const aura = glowSprite("rgba(255,120,40,0.7)", 4, 0.3);
    aura.position.y = 1.3;
    g.add(aura);
    g.scale.setScalar(1.15);
    return {
      group: g,
      forward: "x",
      idle(t) {
        wings.forEach(({ wing, s }) => { wing.rotation.x = Math.sin(t * 2.2) * 0.45 * s - 0.2 * s; });
        head.position.y = 2.45 + Math.sin(t * 1.3) * 0.1;
        head.rotation.y = Math.sin(t * 0.5) * 0.35;
        body.scale.y = 0.95 + Math.sin(t * 2.2) * 0.03;
        tail.forEach((p, i) => p.position.set(-1.1 - i * 0.32, 0.8 - i * 0.08 + Math.sin(t * 1.5 + i * 0.6) * 0.06 * i, Math.sin(t * 1.2 + i * 0.5) * 0.12 * i));
        if (Math.random() < 0.02 && started) burst(head.localToWorld(new THREE.Vector3(0.75, -0.05, 0)), 3, ["#555555", "#888888"], 0.4, -0.5, 1.2, 0.07);
      },
      mouth: new THREE.Vector3(2.8, 2.35, 0),
      head,
    };
  },
};

function buildBosses(list) {
  bosses = new Map();
  for (const info of list) {
    const lay = BOSS_LAYOUT[info.id];
    const make = BOSS_BUILD[info.id];
    if (!lay || !make) continue;
    let x, y, z;
    if (lay.sea) { x = lay.x; z = lay.z; y = WATER_Y; }
    else { [x, z] = hexToWorld(lay.hex[0], lay.hex[1]); y = topOf(lay.hex[0], lay.hex[1]); }
    const model = make();
    model.group.position.set(x, y, z);
    // Le boss regarde le centre de l'île (donc la caméra pendant le combat)
    model.baseYaw = model.forward === "z" ? Math.atan2(-x, -z) : Math.atan2(z, -x);
    model.group.rotation.y = model.baseYaw;
    model.group.traverse((o) => {
      if (o.isMesh) { o.userData.bossId = info.id; o.userData.liveMat = o.material; pickables.push(o); }
    });
    scene.add(model.group);

    // Sceau magique au sol tant que le boss dort
    const sealGeo = new THREE.RingGeometry(1.1, 1.4, 6, 1);
    sealGeo.rotateX(-Math.PI / 2);
    const seal = new THREE.Mesh(sealGeo, new THREE.MeshBasicMaterial({ color: "#8b5cf6", transparent: true, opacity: 0.5, depthWrite: false, blending: THREE.AdditiveBlending }));
    seal.position.set(x, y + 0.05, z);
    seal.scale.setScalar(lay.sea ? 1.8 : 1);
    scene.add(seal);
    anims.push((t) => { seal.rotation.y = t * 0.4; seal.material.opacity = 0.3 + Math.sin(t * 2) * 0.15; });

    const bb = new THREE.Box3().setFromObject(model.group);
    const size = bb.getSize(new THREE.Vector3());
    const center = bb.getCenter(new THREE.Vector3());

    // Éclat blanc quand il est touché, halo rouge quand il enrage
    const flashSprite = glowSprite("rgba(255,255,255,1)", Math.max(size.x, size.y) * 1.6, 0);
    const rageSprite = glowSprite("rgba(255,40,40,0.9)", Math.max(size.x, size.y) * 1.8, 0);
    lights.splice(lights.indexOf(flashSprite), 1);
    lights.splice(lights.indexOf(rageSprite), 1);
    flashSprite.position.copy(center);
    rageSprite.position.copy(center);
    scene.add(flashSprite, rageSprite);

    const boss = {
      id: info.id, label: info.label, model, seal, state: "locked", enraged: false, dying: 0, spawn: 1,
      flash: 0, lunge: 0, rematch: false, baseScale: model.group.scale.x,
      world: new THREE.Vector3(x, y, z), center, top: bb.max.y + 0.4, flashSprite, rageSprite,
    };
    bosses.set(info.id, boss);
    applyBossState(boss, info.state, false);
    anims.push((t, dt) => updateBoss(boss, t, dt));
  }
}

const stoneMat = new THREE.MeshStandardMaterial({ color: "#9a97a6", roughness: 1, flatShading: true });

function applyBossState(boss, state, animate) {
  const prev = boss.state;
  boss.state = state;
  boss.seal.visible = state === "locked";
  boss.model.group.visible = state !== "locked";
  if (state === "available" && prev !== "available") {
    boss.spawn = animate ? 0 : 1;
    if (animate) burst(boss.world.clone().add(new THREE.Vector3(0, 1, 0)), 40, ["#8b5cf6", "#d946ef", "#ffffff"], 3, 1, 1.4);
  }
  if (state === "defeated") turnToStone(boss);
  if (boss.id === "bug") recolorCorruption(state === "defeated");
  const el = bossLabels.get(boss.id);
  if (el) updateBossLabel(boss, el);
}

function turnToStone(boss) {
  boss.enraged = false;
  boss.model.group.traverse((o) => {
    if (o.isMesh) o.material = stoneMat;
    if (o.isSprite) o.visible = false;
  });
  boss.rageSprite.material.opacity = 0;
}

function bringBackToLife(boss) {
  boss.model.group.traverse((o) => {
    if (o.isMesh && o.userData.liveMat) o.material = o.userData.liveMat;
    if (o.isSprite) o.visible = true;
  });
}

function resetBossLook(boss) {
  boss.enraged = false;
  boss.flash = 0;
  boss.lunge = 0;
  boss.rageSprite.material.opacity = 0;
  boss.model.group.scale.setScalar(boss.baseScale);
  boss.model.group.position.copy(boss.world);
  boss.model.group.rotation.z = 0;
  boss.model.onHpRatio?.(1);
}

function recolorCorruption(healed) {
  const col = new THREE.Color();
  for (const i of corruptTiles) {
    const palette = healed ? TILE_COLORS.grass : TILE_COLORS.corrupt;
    tileMesh.setColorAt(i, col.set(palette[i % palette.length]));
  }
  if (tileMesh.instanceColor) tileMesh.instanceColor.needsUpdate = true;
}

function updateBoss(boss, t, dt) {
  const g = boss.model.group;
  if (boss.state === "locked") return;
  boss.flashSprite.material.opacity = boss.flash;
  if (boss.flash > 0) boss.flash = Math.max(0, boss.flash - dt * 3);
  if (boss.enraged) boss.rageSprite.material.opacity = 0.35 + Math.sin(t * 6) * 0.15;
  if (boss.spawn < 1) {
    boss.spawn = Math.min(1, boss.spawn + dt / 1.6);
    const k = 1 - Math.pow(1 - boss.spawn, 3);
    g.scale.setScalar(boss.baseScale * Math.max(0.01, k));
  }
  if (boss.dying > 0) {
    boss.dying = Math.min(1, boss.dying + dt / 2.2);
    g.rotation.z = Math.sin(boss.dying * 40) * 0.06 * (1 - boss.dying);
    g.position.y = boss.world.y - boss.dying * 0.25;
    if (boss.dying >= 1) { boss.dying = 0; applyBossState(boss, "defeated", false); }
    return;
  }
  if (boss.state === "defeated") return;
  const speed = boss.enraged ? 1.7 : 1;
  boss.model.idle(t * speed);
  if (boss.lunge > 0) {
    boss.lunge = Math.max(0, boss.lunge - dt * 2.2);
    const k = Math.sin(boss.lunge * Math.PI);
    const toCam = camera.position.clone().sub(boss.world).setY(0).normalize();
    g.position.x = boss.world.x + toCam.x * k * 1.4;
    g.position.z = boss.world.z + toCam.z * k * 1.4;
  }
}

export function setBosses(list) {
  for (const info of list) {
    const boss = bosses.get(info.id);
    if (!boss || boss.state === info.state || boss.dying > 0) continue;
    applyBossState(boss, info.state, info.state === "available");
    const el = bossLabels.get(info.id);
    if (el) updateBossLabel(boss, el);
  }
}

export function battleStart(id) {
  const boss = bosses.get(id);
  if (!boss) return;
  battleId = id;
  clearFocus();
  const view = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
  savedView = { target: controls.target.clone(), dist: view.radius, polar: view.phi, azimuth: view.theta };
  const lay = BOSS_LAYOUT[id];
  const dist = lay.sea ? 16 : id === "dragon" ? 13 : 11;
  const toCenter = new THREE.Vector3(-boss.world.x, 0, -boss.world.z).normalize();
  const azimuth = Math.atan2(toCenter.x, toCenter.z);
  // On vise un peu au-dessus du boss : la carte de combat occupe le bas de l'écran
  const aim = boss.center.clone().add(new THREE.Vector3(0, (boss.top - boss.world.y) * 0.35, 0));
  flyTo(aim, dist, 1.08, azimuth, 1.6);
  if (boss.state === "defeated") {
    // revanche : la statue reprend vie le temps du combat
    boss.rematch = true;
    boss.state = "available";
    bringBackToLife(boss);
  }
  resetBossLook(boss);
  updateOutline();
  addShake(0.25);
}

export function bossHit(id, critical, hpRatio) {
  const boss = bosses.get(id);
  if (!boss) return;
  boss.flash = critical ? 1 : 0.7;
  burst(boss.center, critical ? 60 : 30, critical ? ["#fff3b0", "#f5c451", "#ffffff", "#ff8a3d"] : ["#ffffff", "#f5c451"], critical ? 5 : 3.2, 4, 0.9, 0.06);
  spawnRipple(boss.world, critical ? "#ffd166" : "#ffffff", critical ? 4 : 2.8);
  addShake(critical ? 0.5 : 0.22);
  boss.model.onHpRatio?.(hpRatio);
}

export function bossAttack(id) {
  const boss = bosses.get(id);
  if (!boss) return;
  boss.lunge = 1;
  addShake(0.8);
  gradePass.uniforms.uDanger.value = 1;
  const mouth = boss.model.group.localToWorld(boss.model.mouth.clone());
  const toCam = camera.position.clone().sub(mouth).normalize();
  const colors = id === "dragon" ? ["#ff5a1f", "#ffb000", "#ffe14d"] : id === "golem" ? ["#38e1ff", "#ffffff"] : id === "kraken" ? ["#c86bd8", "#3a0f45"] : id === "hydre" ? ["#7ef0d8", "#ffffff"] : ["#a78bfa", "#ff2e63"];
  burst(mouth, 70, colors, 6, -1, 0.9, 0.12, toCam);
}

export function bossEnrage(id) {
  const boss = bosses.get(id);
  if (!boss) return;
  boss.enraged = true;
  boss.model.group.scale.setScalar(boss.baseScale * 1.15);
  burst(boss.world.clone().add(new THREE.Vector3(0, 1.5, 0)), 80, ["#ff2a2a", "#ff8a3d", "#2a0a0a"], 5, 2, 1.4);
  addShake(1);
}

export function bossDefeated(id) {
  const boss = bosses.get(id);
  if (!boss) return;
  boss.model.onHpRatio?.(0);
  boss.dying = 0.001;
  addShake(1.2);
  // feu d'artifice et pilier de lumière
  for (let i = 0; i < 5; i++) {
    setTimeout(() => {
      const p = boss.world.clone().add(new THREE.Vector3((rand() - 0.5) * 3, 3 + rand() * 2, (rand() - 0.5) * 3));
      burst(p, 50, ["#f5c451", "#d946ef", "#8b5cf6", "#7dd3fc", "#ffffff"], 4, 2.5, 1.6);
    }, i * 260);
  }
  const pillar = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 1.4, 30, 16, 1, true), new THREE.MeshBasicMaterial({ color: "#ffe9a8", transparent: true, opacity: 0.6, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
  pillar.position.copy(boss.world).add(new THREE.Vector3(0, 15, 0));
  scene.add(pillar);
  let life = 0;
  anims.push((t, dt) => {
    if (!pillar.parent) return; // déjà retiré (on ne modifie pas la liste pendant qu'on la parcourt)
    life += dt;
    pillar.material.opacity = Math.max(0, 0.6 - life * 0.25);
    pillar.scale.x = pillar.scale.z = 1 + life * 0.4;
    if (life > 2.6) scene.remove(pillar);
  });
}

export function battleEnd() {
  const boss = bosses.get(battleId);
  if (boss) {
    if (boss.dying === 0 && boss.state === "available") resetBossLook(boss);
    // fin d'une revanche sans victoire : la statue redevient de pierre
    if (boss.rematch && boss.dying === 0 && boss.state !== "defeated") applyBossState(boss, "defeated", false);
    boss.rematch = false;
  }
  battleId = null;
  updateOutline();
  gradePass.uniforms.uDanger.value = 0;
  if (savedView) flyTo(savedView.target, Math.max(savedView.dist, 16), savedView.polar, savedView.azimuth, 1.4);
  savedView = null;
}

/* =========================================================================
   PARTICULES, ONDES DE CLIC, TREMBLEMENT
   ========================================================================= */

let particles;
const P_MAX = 900;
function setupParticles() {
  const geo = new THREE.BoxGeometry(1, 1, 1);
  const material = new THREE.MeshBasicMaterial({ color: "#ffffff", transparent: true, blending: THREE.AdditiveBlending, depthWrite: false });
  const im = new THREE.InstancedMesh(geo, material, P_MAX);
  im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  im.count = 0;
  im.frustumCulled = false;
  scene.add(im);
  particles = { im, list: [] };
}

function burst(origin, count, colors, speed = 3, gravity = 3, life = 1, size = 0.09, dir = null) {
  if (!particles) return;
  const n = Math.round(count * (LOW ? 0.5 : 1));
  for (let i = 0; i < n && particles.list.length < P_MAX; i++) {
    const v = new THREE.Vector3(rand() - 0.5, rand() * 0.9 + 0.1, rand() - 0.5).normalize().multiplyScalar(speed * (0.4 + rand() * 0.8));
    if (dir) v.addScaledVector(dir, speed * 1.4);
    particles.list.push({
      p: origin.clone(), v, life: life * (0.6 + rand() * 0.6), max: life, g: gravity,
      s: size * (0.6 + rand() * 0.9), c: new THREE.Color(colors[Math.floor(rand() * colors.length)]), r: rand() * 6,
    });
  }
}

const pm = new THREE.Matrix4(), pq = new THREE.Quaternion(), ps = new THREE.Vector3(), pe = new THREE.Euler();
function updateParticles(dt) {
  if (!particles) return;
  const { im, list } = particles;
  let n = 0;
  for (let i = list.length - 1; i >= 0; i--) {
    const q = list[i];
    q.life -= dt;
    if (q.life <= 0) { list.splice(i, 1); continue; }
    q.v.y -= q.g * dt;
    q.v.multiplyScalar(1 - dt * 0.8);
    q.p.addScaledVector(q.v, dt);
    q.r += dt * 6;
    const k = q.life / q.max;
    pm.compose(q.p, pq.setFromEuler(pe.set(q.r, q.r * 0.7, 0)), ps.setScalar(q.s * (0.4 + k * 0.6)));
    im.setMatrixAt(n, pm);
    im.setColorAt(n, q.c.clone().multiplyScalar(0.6 + k * 1.4));
    n++;
  }
  im.count = n;
  im.instanceMatrix.needsUpdate = true;
  if (im.instanceColor) im.instanceColor.needsUpdate = true;
}

function spawnRipple(at, color, size = 2) {
  const geo = new THREE.RingGeometry(0.85, 1, 6, 1);
  geo.rotateX(-Math.PI / 2);
  geo.rotateY(Math.PI / 6);
  const ring = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.9, depthWrite: false, blending: THREE.AdditiveBlending }));
  ring.position.set(at.x, at.y + 0.06, at.z);
  scene.add(ring);
  ripples.push({ ring, t: 0, size });
}
function updateRipples(dt) {
  for (let i = ripples.length - 1; i >= 0; i--) {
    const r = ripples[i];
    r.t += dt / 0.7;
    if (r.t >= 1) { scene.remove(r.ring); ripples.splice(i, 1); continue; }
    r.ring.scale.setScalar(0.3 + r.t * r.size);
    r.ring.material.opacity = 0.9 * (1 - r.t);
  }
}

function addShake(amount) { if (!reduceMotion) shake.amp = Math.min(1.5, shake.amp + amount); }

/* =========================================================================
   VIE DE L'ÎLE
   ========================================================================= */

function buildLife() {
  setupParticles();

  // Villageois sur les routes
  const colors = [C.violet, C.rose, "#3b82f6", "#f59e0b", "#10b981", "#ef4444"];
  roadPaths.forEach((path, i) => {
    if (path.length < 2) return;
    const pts = path.map(([q, r]) => { const [x, z] = hexToWorld(q, r); return new THREE.Vector3(x, topOf(q, r), z); });
    const curve = new THREE.CatmullRomCurve3(pts);
    const v = new THREE.Group();
    v.add(cyl(0.07, 0.09, 0.22, colors[i % colors.length], 0, 0, 0, 6));
    v.add(ball(0.075, "#8a5a3b", 0, 0.29, 0));
    scene.add(v);
    const speed = 0.035 + rand() * 0.03, ph = rand();
    const look = new THREE.Vector3();
    anims.push((t) => {
      const raw = (t * speed + ph) % 2;
      const k = raw < 1 ? raw : 2 - raw;
      curve.getPointAt(k, v.position);
      curve.getPointAt(Math.min(1, Math.max(0, k + (raw < 1 ? 0.01 : -0.01))), look);
      look.y = v.position.y;
      v.lookAt(look);
      v.position.y += Math.abs(Math.sin(t * 9 + i)) * 0.04;
    });
  });

  // Nuages
  const cloudMat = new THREE.MeshStandardMaterial({ color: "#ffffff", flatShading: true, transparent: true, opacity: 0.94, roughness: 1 });
  for (let i = 0; i < 11; i++) {
    const c = new THREE.Group();
    const n = 3 + Math.floor(rand() * 4);
    for (let j = 0; j < n; j++) {
      const m = new THREE.Mesh(new THREE.IcosahedronGeometry(0.6 + rand() * 0.7, 1), cloudMat);
      m.position.set(j * 0.75 - n * 0.35, rand() * 0.35, (rand() - 0.5) * 0.7);
      m.scale.y = 0.75;
      m.castShadow = true;
      c.add(m);
    }
    // Les nuages tournent en couronne autour de l'île : ils encadrent la vue sans la cacher
    const radius = 22 + rand() * 16, angle0 = rand() * Math.PI * 2, height = 8 + rand() * 6;
    const sp = (0.006 + rand() * 0.008) * (rand() < 0.5 ? 1 : -1);
    scene.add(c);
    anims.push((t) => {
      const a = angle0 + t * sp;
      c.position.set(Math.cos(a) * radius, height, Math.sin(a) * radius);
    });
  }

  // Bateau près du phare
  if (PLACE.phare) {
    const [px, pz] = hexToWorld(PLACE.phare.hex[0], PLACE.phare.hex[1]);
    const boat = new THREE.Group();
    boat.add(box(0.9, 0.2, 0.35, C.wood), cyl(0.02, 0.02, 0.9, C.woodDark, 0, 0.2, 0, 4));
    const sail = mesh(new THREE.ConeGeometry(0.35, 0.7, 3), M(C.white), 0.12, 0.65, 0);
    sail.scale.z = 0.08;
    boat.add(sail);
    scene.add(boat);
    anims.push((t) => {
      const a = t * 0.12;
      boat.position.set(px + Math.cos(a) * 3.2, WATER_Y + Math.sin(t * 2) * 0.05, pz + Math.sin(a) * 3.2);
      boat.rotation.y = -a - Math.PI / 2;
      boat.rotation.z = Math.sin(t * 1.7) * 0.06;
    });
  }

  // Volée d'oiseaux
  const flock = [];
  for (let i = 0; i < 9; i++) {
    const b = new THREE.Group();
    const wl = box(0.38, 0.015, 0.12, "#2b2f3a"), wr = box(0.38, 0.015, 0.12, "#2b2f3a");
    wl.geometry.translate(0.19, 0, 0); wr.geometry.translate(-0.19, 0, 0);
    b.add(ball(0.05, "#2b2f3a"), wl, wr);
    scene.add(b);
    flock.push({ b, wl, wr, off: new THREE.Vector3((rand() - 0.5) * 3, (rand() - 0.5) * 1.2, (rand() - 0.5) * 3), ph: rand() * 6 });
  }
  anims.push((t) => {
    const a = t * 0.12;
    const cx = Math.cos(a) * 16, cz = Math.sin(a) * 12, cy = 11 + Math.sin(t * 0.3) * 1.5;
    for (const f of flock) {
      f.b.position.set(cx + f.off.x, cy + f.off.y + Math.sin(t * 2 + f.ph) * 0.2, cz + f.off.z);
      f.b.rotation.y = -a;
      const flap = Math.sin(t * 9 + f.ph) * 0.6;
      f.wl.rotation.z = flap; f.wr.rotation.z = -flap;
      f.b.visible = nightT < 0.7;
    }
  });

  // Lucioles (nuit) et pollen doré (jour)
  const mkPoints = (n, color, size, spread) => {
    const pos = new Float32Array(n * 3), seeds = [];
    for (let i = 0; i < n; i++) {
      const t = tileList[Math.floor(rand() * tileList.length)];
      const [x, z] = hexToWorld(t.q, t.r);
      seeds.push([x, t.h + 0.3 + rand() * spread, z, rand() * 10]);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    const material = new THREE.PointsMaterial({ color, size, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    scene.add(new THREE.Points(geo, material));
    return { pos, seeds, geo, material };
  };
  const ff = mkPoints(90, "#ffe28a", 0.14, 0.9);
  fireflies = ff.material;
  const pl = mkPoints(140, "#fff6d8", 0.07, 2.4);
  pollen = pl.material;
  anims.push((t) => {
    if (ff.material.opacity > 0.01) {
      ff.seeds.forEach(([x, y, z, s], i) => {
        ff.pos[i * 3] = x + Math.sin(t * 0.7 + s) * 0.5;
        ff.pos[i * 3 + 1] = y + Math.sin(t * 1.3 + s * 2) * 0.25;
        ff.pos[i * 3 + 2] = z + Math.cos(t * 0.6 + s) * 0.5;
      });
      ff.geo.attributes.position.needsUpdate = true;
    }
    if (pl.material.opacity > 0.01) {
      pl.seeds.forEach(([x, y, z, s], i) => {
        pl.pos[i * 3] = x + Math.sin(t * 0.3 + s) * 0.8;
        pl.pos[i * 3 + 1] = y + ((t * 0.12 + s) % 2.4);
        pl.pos[i * 3 + 2] = z + Math.cos(t * 0.25 + s) * 0.8;
      });
      pl.geo.attributes.position.needsUpdate = true;
    }
  });
}

/* =========================================================================
   MARQUEURS DE QUÊTE ET ÉTIQUETTES
   ========================================================================= */

const bossLabels = new Map();
const SKULL = "M12 3a8 8 0 0 0-8 8c0 3 1.6 5.2 4 6.3V21h8v-3.7c2.4-1.1 4-3.3 4-6.3a8 8 0 0 0-8-8zM9 10.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 1 0 0-3M15 10.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 1 0 0-3";

function iconSvg(path) {
  return `<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${path}"/></svg>`;
}

function buildMarkersAndLabels(places, bossList) {
  markers = new Map();
  const geo = new THREE.OctahedronGeometry(0.22, 0);
  geo.scale(0.8, 1.4, 0.8);
  const markerMat = new THREE.MeshStandardMaterial({ color: C.gold, emissive: "#c88a10", emissiveIntensity: 1.2, flatShading: true });
  for (const p of places) {
    const b = buildings.get(p.id);
    if (!b) continue;
    const m = new THREE.Mesh(geo, markerMat);
    m.position.set(b.world.x, b.top + 0.55, b.world.z);
    m.userData.placeId = p.id;
    scene.add(m);
    pickables.push(m);
    markers.set(p.id, m);
    const ph = rand() * 6;
    anims.push((t) => { m.position.y = b.top + 0.55 + Math.sin(t * 2.5 + ph) * 0.12; m.rotation.y = t * 1.5; });
  }

  const makeRing = (color, opacity) => {
    const g = new THREE.RingGeometry(1.5, 1.72, 6, 1);
    g.rotateX(-Math.PI / 2);
    g.rotateY(Math.PI / 6);
    const r = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false }));
    r.visible = false;
    scene.add(r);
    return r;
  };
  hoverRing = makeRing(C.white, 0.55);
  activeRing = makeRing(C.gold, 0.9);
  anims.push((t) => { activeRing.scale.setScalar(1 + Math.sin(t * 3) * 0.04); });

  labels = new Map();
  labelsEl.innerHTML = "";
  for (const p of places) {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "label is-hidden";
    el.tabIndex = -1;
    el.innerHTML = `<span class="label-icon">${iconSvg(p.icon)}</span><span class="label-name"></span>`;
    el.querySelector(".label-name").textContent = p.label;
    el.addEventListener("click", () => dotnet.invokeMethodAsync("OnPlaceClicked", p.id));
    el.addEventListener("pointerenter", () => setHover(p.id));
    el.addEventListener("pointerleave", () => setHover(null));
    labelsEl.appendChild(el);
    labels.set(p.id, el);
  }

  // Étiquettes des boss (rouges quand ils sont réveillés)
  for (const info of bossList) {
    const boss = bosses.get(info.id);
    if (!boss) continue;
    const el = document.createElement("button");
    el.type = "button";
    el.className = "label is-boss is-hidden";
    el.tabIndex = -1;
    el.innerHTML = `<span class="label-icon">${iconSvg(SKULL)}</span><span class="label-name"></span>`;
    el.addEventListener("click", () => dotnet.invokeMethodAsync("OnBossClicked", info.id));
    el.addEventListener("pointerenter", () => setBossHover(info.id));
    el.addEventListener("pointerleave", () => setBossHover(null));
    labelsEl.appendChild(el);
    bossLabels.set(info.id, el);
    updateBossLabel(boss, el);
  }
}

function updateBossLabel(boss, el) {
  el.querySelector(".label-name").textContent = boss.state === "defeated" ? `${boss.label} · vaincu` : `Boss · ${boss.label}`;
  el.classList.toggle("is-defeated", boss.state === "defeated");
}

function setHover(id) {
  hoverId = id;
  for (const [pid, el] of labels) el.classList.toggle("is-hover", pid === id);
  canvasEl.classList.toggle("is-hover", !!id || !!hoverBoss);
  if (id && id !== activeId) {
    const b = buildings.get(id);
    hoverRing.position.set(b.world.x, b.world.y + 0.03, b.world.z);
    hoverRing.visible = true;
  } else {
    hoverRing.visible = false;
  }
  updateOutline();
}

function setBossHover(id) {
  hoverBoss = id;
  for (const [bid, el] of bossLabels) el.classList.toggle("is-hover", bid === id);
  canvasEl.classList.toggle("is-hover", !!id || !!hoverId);
  updateOutline();
}

function updateOutline() {
  if (!outlinePass) return;
  const sel = [];
  const placeId = hoverId || activeId;
  if (placeId && buildings.get(placeId)) sel.push(buildings.get(placeId).group);
  const bossId = battleId || hoverBoss;
  const boss = bossId && bosses.get(bossId);
  if (boss && boss.state !== "locked") sel.push(boss.model.group);
  outlinePass.selectedObjects = sel;
  outlinePass.visibleEdgeColor.set(boss && (battleId || hoverBoss) ? "#ff4d4d" : "#ffd166");
  outlinePass.enabled = sel.length > 0;
}

const v3 = new THREE.Vector3();
function placeLabel(el, x, y, z, hidden) {
  v3.set(x, y, z).project(camera);
  const visible = v3.z < 1 && Math.abs(v3.x) < 1.15 && Math.abs(v3.y) < 1.15;
  const w = window.innerWidth, h = window.innerHeight;
  el.style.transform = `translate(${((v3.x * 0.5 + 0.5) * w).toFixed(1)}px, ${((-v3.y * 0.5 + 0.5) * h).toFixed(1)}px) translate(-50%, -100%)`;
  el.classList.toggle("is-hidden", !visible || hidden);
}

function updateLabels() {
  const camDist = camera.position.distanceTo(controls.target);
  for (const [id, el] of labels) {
    const b = buildings.get(id);
    const far = camDist > 44 && id !== activeId && id !== hoverId;
    placeLabel(el, b.world.x, b.top + (markers.get(id)?.visible ? 0.95 : 0.25), b.world.z, far || !started || !!battleId);
  }
  for (const [id, el] of bossLabels) {
    const boss = bosses.get(id);
    placeLabel(el, boss.world.x, boss.top + 0.3, boss.world.z, boss.state === "locked" || !started || !!battleId);
  }
}

/* =========================================================================
   CAMÉRA ET INTERACTIONS
   ========================================================================= */

function setupCamera() {
  controls = new OrbitControls(camera, canvasEl);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 6;
  controls.maxDistance = 54;
  controls.minPolarAngle = 0.35;
  controls.maxPolarAngle = 1.25;
  controls.screenSpacePanning = false;
  controls.target.set(0, 0.5, 0);
  controls.enabled = false;
  controls.autoRotate = !reduceMotion;
  controls.autoRotateSpeed = 0.35;
  camera.position.setFromSphericalCoords(58, 0.75, 0.6).add(controls.target);
  camera.lookAt(controls.target);
  controls.addEventListener("change", () => {
    const t = controls.target;
    const r = Math.hypot(t.x, t.z);
    if (r > 20) { t.x *= 20 / r; t.z *= 20 / r; }
    t.y = THREE.MathUtils.clamp(t.y, 0, 3);
  });
}

const ease = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
function flyTo(target, dist, polar, azimuth, duration = 1.3) {
  const sph = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
  tween = {
    t0: performance.now(), dur: reduceMotion ? 1 : duration * 1000,
    fromT: controls.target.clone(), toT: target.clone(),
    fromS: sph, toS: new THREE.Spherical(dist, polar, azimuth ?? sph.theta),
  };
}
function updateTween(now) {
  if (!tween) return;
  const k = Math.min(1, (now - tween.t0) / tween.dur), e = ease(k);
  controls.target.lerpVectors(tween.fromT, tween.toT, e);
  let dTheta = tween.toS.theta - tween.fromS.theta;
  dTheta = Math.atan2(Math.sin(dTheta), Math.cos(dTheta));
  const s = new THREE.Spherical(
    THREE.MathUtils.lerp(tween.fromS.radius, tween.toS.radius, e),
    THREE.MathUtils.lerp(tween.fromS.phi, tween.toS.phi, e),
    tween.fromS.theta + dTheta * e,
  );
  camera.position.setFromSpherical(s).add(controls.target);
  if (k >= 1) tween = null;
}

// Décale la vue quand un panneau ou la carte de combat est ouvert, pour garder le sujet visible
const shift = { x: 0, y: 0 };
function updateViewOffset() {
  const w = window.innerWidth, h = window.innerHeight;
  const panel = document.getElementById("panel");
  const card = document.getElementById("battle-card");
  let tx = 0, ty = 0;
  if (panel) {
    if (isSmall()) ty = panel.offsetHeight * 0.85;
    else tx = panel.offsetWidth + 16;
  } else if (card) {
    ty = card.offsetHeight * 1.05;
  }
  shift.x += (tx - shift.x) * 0.1;
  shift.y += (ty - shift.y) * 0.1;
  if (Math.abs(shift.x) < 0.5 && Math.abs(shift.y) < 0.5 && tx === 0 && ty === 0) {
    if (camera.view && camera.view.enabled) camera.clearViewOffset();
    return;
  }
  camera.setViewOffset(w + shift.x, h + shift.y, shift.x, shift.y, w, h);
}

function setupInput() {
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  const setPointer = (e) => {
    const r = canvasEl.getBoundingClientRect();
    pointer.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
  };
  // Un objet n'est cliquable que s'il est visible, lui et tous ses parents (un boss endormi est caché)
  const shown = (o) => { for (; o; o = o.parent) if (!o.visible) return false; return true; };
  const pick = (e) => {
    setPointer(e);
    const hit = raycaster.intersectObjects(pickables, false).find((h) => shown(h.object));
    return hit ? { place: hit.object.userData.placeId, boss: hit.object.userData.bossId, point: hit.point } : null;
  };
  const onMove = (e) => {
    if (!started || paused || battleId || e.pointerType === "touch") return;
    const hit = pick(e);
    const place = hit?.place ?? null;
    const boss = hit?.boss && bosses.get(hit.boss)?.state !== "locked" ? hit.boss : null;
    if (place !== hoverId) setHover(place);
    if (boss !== hoverBoss) setBossHover(boss);
  };
  const onDown = (e) => {
    downAt = [e.clientX, e.clientY];
    if (!battleId) tween = null;
    if (started) dotnet.invokeMethodAsync("OnUserInterrupt");
  };
  const onUp = (e) => {
    if (!started || !downAt || battleId) return;
    const moved = Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]);
    downAt = null;
    if (moved > 6) return;
    const hit = pick(e);
    if (hit?.boss && bosses.get(hit.boss)?.state !== "locked") {
      dotnet.invokeMethodAsync("OnBossClicked", hit.boss);
    } else if (hit?.place) {
      dotnet.invokeMethodAsync("OnPlaceClicked", hit.place);
    } else {
      setPointer(e);
      const ground = raycaster.intersectObject(tileMesh, false)[0];
      if (ground) spawnRipple(ground.point, "#ffffff", 1.4);
    }
  };
  const onKey = (e) => {
    if (!started || paused || e.target.closest?.("input, textarea, select")) return;
    if (["Escape", "ArrowLeft", "ArrowRight", "Home"].includes(e.key)) dotnet.invokeMethodAsync("OnKey", e.key);
  };
  const onResize = () => {
    const w = window.innerWidth, h = window.innerHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
    composer.setSize(w, h);
    outlinePass?.resolution?.set(w, h);
  };
  canvasEl.addEventListener("pointermove", onMove);
  canvasEl.addEventListener("pointerdown", onDown);
  canvasEl.addEventListener("pointerup", onUp);
  window.addEventListener("keydown", onKey);
  window.addEventListener("resize", onResize);
  disposers.push(() => {
    canvasEl.removeEventListener("pointermove", onMove);
    canvasEl.removeEventListener("pointerdown", onDown);
    canvasEl.removeEventListener("pointerup", onUp);
    window.removeEventListener("keydown", onKey);
    window.removeEventListener("resize", onResize);
  });
}

/* =========================================================================
   POST-TRAITEMENT : contours, bloom, étalonnage, vignette
   ========================================================================= */

const GradeShader = {
  uniforms: {
    tDiffuse: { value: null },
    uVignette: { value: 1.0 },
    uSaturation: { value: 1.1 },
    uDanger: { value: 0 },
    uWarmth: { value: 0.03 },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse; uniform float uVignette; uniform float uSaturation; uniform float uDanger; uniform float uWarmth;
    varying vec2 vUv;
    void main() {
      vec4 c = texture2D(tDiffuse, vUv);
      float l = dot(c.rgb, vec3(0.2126, 0.7152, 0.0722));
      c.rgb = mix(vec3(l), c.rgb, uSaturation);
      c.rgb *= vec3(1.0 + uWarmth, 1.0, 1.0 - uWarmth);
      float v = smoothstep(0.95, 0.3, length(vUv - 0.5) * uVignette);
      c.rgb *= mix(0.62, 1.0, v);
      c.rgb = mix(c.rgb, c.rgb * vec3(1.15, 0.25, 0.22), uDanger * (1.0 - v) * 0.9);
      gl_FragColor = c;
    }`,
};

function setupPostProcessing() {
  const w = window.innerWidth, h = window.innerHeight;
  const target = new THREE.WebGLRenderTarget(w * QUALITY.pixelRatio, h * QUALITY.pixelRatio, { type: THREE.HalfFloatType, samples: QUALITY.msaa });
  composer = new EffectComposer(renderer, target);
  composer.setPixelRatio(QUALITY.pixelRatio);
  composer.setSize(w, h);
  composer.addPass(new RenderPass(scene, camera));
  if (QUALITY.outline) {
    outlinePass = new OutlinePass(new THREE.Vector2(w, h), scene, camera);
    Object.assign(outlinePass, { edgeStrength: 4, edgeGlow: 0.7, edgeThickness: 1.6, pulsePeriod: 2.4 });
    outlinePass.visibleEdgeColor.set("#ffd166");
    outlinePass.hiddenEdgeColor.set("#3a2a10");
    outlinePass.enabled = false;
    composer.addPass(outlinePass);
  }
  bloomPass = new UnrealBloomPass(new THREE.Vector2(w, h), 0.3, 0.55, 1.35);
  composer.addPass(bloomPass);
  gradePass = new ShaderPass(GradeShader);
  composer.addPass(gradePass);
  composer.addPass(new OutputPass());
}

/* =========================================================================
   MINI-CARTE
   ========================================================================= */

const MINI_SPAN = 48; // largeur du monde représentée
export function attachMinimap(canvas) {
  if (mini?.canvas === canvas) return;
  if (mini) mini.canvas.removeEventListener("pointerdown", mini.onClick);
  const size = canvas.width;
  const scale = size / MINI_SPAN;
  const base = document.createElement("canvas");
  base.width = base.height = size;
  const c = base.getContext("2d");
  const grd = c.createRadialGradient(size / 2, size / 2, size * 0.1, size / 2, size / 2, size * 0.5);
  grd.addColorStop(0, "#2d8fc9");
  grd.addColorStop(1, "#0f3b5c");
  c.fillStyle = grd;
  c.fillRect(0, 0, size, size);
  const hexPath = (cx, cy, r) => {
    c.beginPath();
    for (let i = 0; i < 6; i++) {
      const a = (Math.PI / 3) * i + Math.PI / 6;
      c.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
    }
    c.closePath();
  };
  for (const t of tileList) {
    const [x, z] = hexToWorld(t.q, t.r);
    const palette = TILE_COLORS[t.forest ? "grass" : t.type] || TILE_COLORS.grass;
    c.fillStyle = t.forest ? "#5c9c4f" : palette[0];
    hexPath(size / 2 + x * scale, size / 2 + z * scale, 1.02 * scale);
    c.fill();
  }
  const onClick = (e) => {
    if (!started || battleId) return;
    const r = canvas.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width * size - size / 2) / scale;
    const z = ((e.clientY - r.top) / r.height * size - size / 2) / scale;
    flyTo(new THREE.Vector3(x, 0.5, z), Math.min(camera.position.distanceTo(controls.target), 24), 0.95, undefined, 1);
    spawnRipple(new THREE.Vector3(x, H0, z), C.gold, 2);
  };
  canvas.addEventListener("pointerdown", onClick);
  mini = { canvas, ctx: canvas.getContext("2d"), base, size, scale, onClick };
}

function drawMinimap() {
  if (!mini || !mini.canvas.isConnected) return;
  const { ctx, base, size, scale } = mini;
  const toMap = (x, z) => [size / 2 + x * scale, size / 2 + z * scale];
  ctx.clearRect(0, 0, size, size);
  ctx.drawImage(base, 0, 0);
  for (const [id, b] of buildings) {
    const [x, y] = toMap(b.world.x, b.world.z);
    const isNew = markers.get(id)?.visible;
    ctx.fillStyle = id === activeId ? "#ffffff" : isNew ? "#f5c451" : "#3b2a5a";
    ctx.beginPath();
    ctx.arc(x, y, id === activeId ? 4.5 : 3, 0, Math.PI * 2);
    ctx.fill();
  }
  for (const boss of bosses.values()) {
    if (boss.state === "locked") continue;
    const [x, y] = toMap(boss.world.x, boss.world.z);
    ctx.fillStyle = boss.state === "defeated" ? "#9a97a6" : "#ff4d4d";
    ctx.beginPath();
    ctx.arc(x, y, 4.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.2;
    ctx.stroke();
  }
  // champ de vision de la caméra
  const [tx, ty] = toMap(controls.target.x, controls.target.z);
  const dir = new THREE.Vector3().subVectors(controls.target, camera.position).setY(0).normalize();
  const ang = Math.atan2(dir.z, dir.x);
  const reach = Math.min(18, camera.position.distanceTo(controls.target) * 0.55) * scale;
  ctx.fillStyle = "rgba(255, 255, 255, 0.16)";
  ctx.beginPath();
  ctx.moveTo(tx - Math.cos(ang) * reach * 0.6, ty - Math.sin(ang) * reach * 0.6);
  ctx.arc(tx - Math.cos(ang) * reach * 0.6, ty - Math.sin(ang) * reach * 0.6, reach * 1.6, ang - 0.38, ang + 0.38);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "#ffd166";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(tx, ty, 5, 0, Math.PI * 2);
  ctx.stroke();
}

/* =========================================================================
   JOUR / NUIT ET BOUCLE
   ========================================================================= */

const tmpDir = new THREE.Vector3();
function applyDayNight(dt) {
  nightT += ((night ? 1 : 0) - nightT) * Math.min(1, dt * 1.6);
  const u = skyMat.uniforms;
  u.uTop.value.copy(DAY.top).lerp(NIGHT.top, nightT);
  u.uHorizon.value.copy(DAY.horizon).lerp(NIGHT.horizon, nightT);
  u.uBottom.value.copy(DAY.bottom).lerp(NIGHT.bottom, nightT);
  u.uSun.value.copy(DAY.sun).multiplyScalar(1 - nightT); // la nuit, la lune (sphère) remplace le disque solaire
  u.uGlow.value.copy(DAY.sunGlow).lerp(NIGHT.sunGlow, nightT);
  u.uSunDir.value.copy(tmpDir.copy(SUN_DIR).lerp(MOON_DIR, nightT).normalize());
  u.uSunSize.value = THREE.MathUtils.lerp(2600, 900, nightT);
  scene.fog.color.copy(u.uHorizon.value);
  scene.background.copy(u.uHorizon.value);
  hemi.color.copy(DAY.hemiSky).lerp(NIGHT.hemiSky, nightT);
  hemi.groundColor.copy(DAY.hemiGround).lerp(NIGHT.hemiGround, nightT);
  hemi.intensity = THREE.MathUtils.lerp(1.05, 0.42, nightT);
  sun.color.copy(DAY.sun).lerp(NIGHT.sun, nightT);
  sun.intensity = THREE.MathUtils.lerp(2.5, 0.6, nightT);
  sun.position.copy(u.uSunDir.value).multiplyScalar(36);
  windowMat.emissiveIntensity = 0.05 + nightT * 2.2;
  starMat.opacity = nightT;
  moon.material.opacity = nightT;
  fireflies.opacity = nightT * 0.95;
  pollen.opacity = (1 - nightT) * 0.5;
  waterMat.color.copy(DAY.water).lerp(NIGHT.water, nightT);
  for (const s of lights) s.material.opacity = Math.max(s.userData.always || 0, nightT * 0.95);
  bloomPass.strength = THREE.MathUtils.lerp(0.32, 0.95, nightT) + (battleId ? 0.15 : 0);
  bloomPass.threshold = THREE.MathUtils.lerp(1.35, 0.55, nightT);
  gradePass.uniforms.uVignette.value = THREE.MathUtils.lerp(gradePass.uniforms.uVignette.value, battleId ? 1.35 : 1.0, dt * 2);
  gradePass.uniforms.uWarmth.value = THREE.MathUtils.lerp(0.035, -0.03, nightT);
  gradePass.uniforms.uDanger.value = Math.max(0, gradePass.uniforms.uDanger.value - dt * 1.4);
}

function updateFlights(dt) {
  for (let i = flights.length - 1; i >= 0; i--) {
    const f = flights[i];
    f.t += dt / 4.5;
    if (f.t >= 1) { scene.remove(f.bird.group); flights.splice(i, 1); continue; }
    const pos = f.curve.getPointAt(f.t), next = f.curve.getPointAt(Math.min(1, f.t + 0.01));
    f.bird.group.position.copy(pos);
    f.bird.group.lookAt(next);
    f.bird.group.rotateY(-Math.PI / 2);
    const flap = Math.sin(performance.now() / 45) * 0.8;
    f.bird.wingL.rotation.x = flap; f.bird.wingR.rotation.x = -flap;
  }
}

function loop() {
  rafId = requestAnimationFrame(loop);
  if (paused) return;
  const dt = Math.min(clock.getDelta(), 0.05);
  const t = clock.elapsedTime;

  camera.position.sub(shake.offset);
  updateTween(performance.now());
  controls.update();
  if (shake.amp > 0.001) {
    shake.offset.set((Math.random() - 0.5) * shake.amp * 0.5, (Math.random() - 0.5) * shake.amp * 0.4, (Math.random() - 0.5) * shake.amp * 0.5);
    shake.amp *= Math.pow(0.02, dt);
  } else {
    shake.offset.set(0, 0, 0);
  }
  camera.position.add(shake.offset);

  wind.value = t;
  if (!reduceMotion) {
    animateWater(t);
    for (const f of anims) f(t, dt);
  } else {
    for (const boss of bosses.values()) updateBoss(boss, 0, dt);
  }
  sky.position.copy(camera.position);
  updateParticles(dt);
  updateRipples(dt);
  updateFlights(dt);
  applyDayNight(dt);
  updateViewOffset();
  updateLabels();
  if (outlinePass?.enabled && battleId) outlinePass.edgeStrength = 4 + Math.sin(t * 6) * 1.5;
  if (++miniFrame % 3 === 0) drawMinimap();
  composer.render(dt);
}
