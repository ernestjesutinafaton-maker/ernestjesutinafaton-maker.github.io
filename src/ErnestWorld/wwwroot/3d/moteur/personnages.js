/*
  LES HABITANTS · personnages et animaux du royaume

  Les pièces (tête, torse, bras, jambes, coiffures, cape, lance...) sont modélisées dans Blender
  (tools/blender/royaume/personnages.py) et rangées dans ile.glb sous le nom piece_<nom>.
  Ici, chaque type de pièce devient un InstancedMesh : quelques appels de dessin suffisent pour des
  centaines de personnages. À chaque image, on calcule le squelette de chaque personnage (hanches,
  épaules, coudes, genoux...) selon son animation, et on place ses pièces.

  Animations : marche, repos, salut, parole, marteau (forgeron), garde, travail aux champs, broutage.
  Les personnages sont éclairés en temps réel (lumière du couchant + ciel), avec une ombre ronde au sol.
*/
import * as THREE from "../../lib/three/three.module.js";
import { DIALOGUES, GARDES, PASSANTS } from "./dialogues.js";

const PIECES_HUMAIN = ["tete", "yeux", "torse", "bras_haut", "avant_bras", "main", "cuisse", "mollet", "botte",
  "cheveux_courts", "cheveux_longs", "capuche", "chapeau", "casque", "jupe", "tablier", "ceinture", "cape",
  "lance", "marteau", "livre", "sacoche"];
const PIECES_ANIMAUX = ["mouton_corps", "mouton_tete", "patte_fine", "cheval_corps", "cheval_cou", "cheval_patte",
  "queue", "chien_corps", "chien_tete", "charrette", "roue"];

// Couleurs (sRGB)
export const PEAUX = [0x5a3a28, 0x8d5a3b, 0xc28a62, 0xe0b48f, 0x6e4630, 0xa86f4c, 0xf0c8a8, 0x3f2a1e];
export const CHEVEUX = [0x141010, 0x2b1d14, 0x4a2f1c, 0x7a5233, 0xb88a52, 0x8a8a8a, 0x1c1410];
export const TISSUS = [0x7a3b2e, 0x3f5a3a, 0x334a6b, 0x8a6a3a, 0x5d4a6e, 0x9a8f78, 0x6b2f2f, 0x2f4f4f, 0xb0763c, 0x4b5d2a];
export const JAMBES = [0x2a2a33, 0x3b3226, 0x4a3b2b, 0x2e3a2e, 0x3a2f3f];

const V = () => new THREE.Vector3();
const Q = () => new THREE.Quaternion();

function hasard(graine) {
  return function () {
    graine |= 0; graine = (graine + 0x6d2b79f5) | 0;
    let t = Math.imul(graine ^ (graine >>> 15), 1 | graine);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* Apparence d'un humain tirée au sort (ou imposée) */
export function apparenceAuHasard(rnd, imposee = {}) {
  const choix = (t) => t[Math.floor(rnd() * t.length)];
  const femme = rnd() < 0.5;
  const coiffures = femme ? ["cheveux_longs", "cheveux_longs", "capuche", "chapeau", "cheveux_courts"]
    : ["cheveux_courts", "cheveux_courts", "capuche", "chapeau", null];
  return {
    peau: choix(PEAUX), cheveux: choix(CHEVEUX), haut: choix(TISSUS), bas: choix(JAMBES), bottes: 0x3a2618,
    coiffure: choix(coiffures), coiffureCouleur: null, jupe: femme && rnd() < 0.6 ? choix(TISSUS) : null,
    tablier: rnd() < 0.25 ? 0xd9cdb4 : null, cape: null, lance: false, marteau: false, livre: false, sacoche: rnd() < 0.2 ? 0x6b4428 : null,
    taille: 0.9 + rnd() * 0.16, carrure: 0.92 + rnd() * 0.2, ...imposee,
  };
}

// Ernest, d'après sa photo : peau brun foncé, cheveux noirs courts et frisés, pull en maille beige.
// La cape couleur braise le distingue quand il guide la visite.
export const ERNEST = {
  peau: 0x5b3a29, cheveux: 0x121010, haut: 0xd8ccb6, bas: 0x2a2c35, bottes: 0x2e2018, coiffure: "cheveux_courts",
  coiffureCouleur: null, jupe: null, tablier: null, cape: 0xb5532b, lance: false, marteau: false, livre: false,
  sacoche: 0x6b4428, taille: 1.0, carrure: 1.0,
};

/* =========================================================================
   Brume et lumière pour les matières des personnages
   ========================================================================= */

function matiereVivante(uniformsBrume, glslBrume) {
  const m = new THREE.MeshLambertMaterial({ color: 0xffffff });
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, uniformsBrume);
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vMonde;")
      .replace("#include <project_vertex>", `#include <project_vertex>
        vec4 mondeV = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
          mondeV = instanceMatrix * mondeV;
        #endif
        vMonde = (modelMatrix * mondeV).xyz;`);
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vMonde;\n" + glslBrume)
      .replace("#include <dithering_fragment>", "gl_FragColor.rgb = brume(gl_FragColor.rgb, vMonde);\n#include <dithering_fragment>");
  };
  m.customProgramCacheKey = () => "habitants";
  return m;
}

function textureOmbre() {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d");
  const d = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  d.addColorStop(0, "rgba(0,0,0,0.55)");
  d.addColorStop(0.6, "rgba(0,0,0,0.25)");
  d.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = d;
  g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

/* =========================================================================
   Le peuple : tous les personnages, dessinés par instances
   ========================================================================= */

export class Peuple {
  /**
   * @param scene        scène Three.js
   * @param geometries   { nomPiece: BufferGeometry } venues de ile.glb
   * @param brume        { uniforms, glsl } pour fondre les personnages dans la brume du site
   * @param capacite     nombre maximal d'humains et d'animaux
   */
  constructor(scene, geometries, brume, capacite = { humains: 160, animaux: 40 }) {
    this.scene = scene;
    this.humains = [];
    this.animaux = [];
    this.capacite = capacite;
    this.mat = matiereVivante(brume.uniforms, brume.glsl);
    this.instances = {};
    this.compte = {};
    const creer = (nom, n) => {
      const g = geometries[nom];
      if (!g) return;
      const im = new THREE.InstancedMesh(g, this.mat, n);
      im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      im.frustumCulled = false;
      im.count = n;
      const zero = new THREE.Matrix4().makeScale(0, 0, 0);
      for (let i = 0; i < n; i++) { im.setMatrixAt(i, zero); im.setColorAt(i, new THREE.Color(1, 1, 1)); }
      scene.add(im);
      this.instances[nom] = im;
    };
    for (const nom of PIECES_HUMAIN) {
      const parPersonnage = ["bras_haut", "avant_bras", "main", "cuisse", "mollet", "botte"].includes(nom) ? 2 : 1;
      creer(nom, capacite.humains * parPersonnage);
    }
    for (const nom of PIECES_ANIMAUX) {
      const parAnimal = nom === "patte_fine" || nom === "cheval_patte" ? 4 : nom === "roue" ? 2 : 1;
      creer(nom, capacite.animaux * parAnimal);
    }
    // Ombres rondes au sol
    const ombre = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
    this.ombres = new THREE.InstancedMesh(ombre, new THREE.MeshBasicMaterial({ map: textureOmbre(), transparent: true, depthWrite: false }),
      capacite.humains + capacite.animaux);
    this.ombres.frustumCulled = false;
    this.ombres.renderOrder = 1;
    const zero = new THREE.Matrix4().makeScale(0, 0, 0);
    for (let i = 0; i < this.ombres.count; i++) this.ombres.setMatrixAt(i, zero);
    scene.add(this.ombres);
    // Matrices réutilisées à chaque image
    this._m = Array.from({ length: 24 }, () => new THREE.Matrix4());
    this._t = new THREE.Matrix4();
    this._r = new THREE.Matrix4();
    this._v = V();
    this._q = Q();
    this._e = new THREE.Euler();
    this._s = new THREE.Vector3(1, 1, 1);
    this._c = new THREE.Color();
  }

  /* --- Humains ---------------------------------------------------------- */

  ajouterHumain(apparence, etat = {}) {
    const id = this.humains.findIndex((h) => !h.actif);
    const h = {
      actif: true, apparence, pos: V(), cap: 0, anim: "repos", phase: Math.random() * 10, vitesse: 0,
      regard: 0, inclinaison: 0, visible: true, ...etat,
    };
    if (etat.pos) h.pos.copy(etat.pos);
    let index;
    if (id >= 0) { this.humains[id] = h; index = id; }
    else if (this.humains.length < this.capacite.humains) { this.humains.push(h); index = this.humains.length - 1; }
    else return -1;
    h.index = index;
    this._colorer(h);
    return index;
  }

  retirerHumain(index) {
    const h = this.humains[index];
    if (!h) return;
    h.actif = false;
    this._cacherHumain(index);
  }

  _couleur(nom, i, hex) {
    const im = this.instances[nom];
    if (!im || hex == null) return;
    im.setColorAt(i, this._c.set(hex));
    im.instanceColor.needsUpdate = true;
  }

  _colorer(h) {
    const a = h.apparence, i = h.index;
    this._couleur("tete", i, a.peau);
    this._couleur("yeux", i, 0x1a1210);
    this._couleur("torse", i, a.haut);
    for (const k of [0, 1]) {
      this._couleur("bras_haut", i * 2 + k, a.haut);
      this._couleur("avant_bras", i * 2 + k, a.haut);
      this._couleur("main", i * 2 + k, a.peau);
      this._couleur("cuisse", i * 2 + k, a.bas);
      this._couleur("mollet", i * 2 + k, a.bas);
      this._couleur("botte", i * 2 + k, a.bottes);
    }
    for (const c of ["cheveux_courts", "cheveux_longs", "capuche", "chapeau", "casque"]) {
      this._couleur(c, i, a.coiffureCouleur ?? (c === "capuche" ? a.haut : c === "chapeau" ? 0xc9a85e : c === "casque" ? 0x8a8f96 : a.cheveux));
    }
    this._couleur("jupe", i, a.jupe ?? a.bas);
    this._couleur("tablier", i, a.tablier ?? 0xd9cdb4);
    this._couleur("ceinture", i, 0x3a2618);
    this._couleur("cape", i, a.cape ?? 0x6b2f2f);
    this._couleur("lance", i, 0x6b5a44);
    this._couleur("marteau", i, 0x4a4a4a);
    this._couleur("livre", i, 0x6b2f2f);
    this._couleur("sacoche", i, a.sacoche ?? 0x6b4428);
  }

  _poser(nom, i, m) {
    const im = this.instances[nom];
    if (im) im.setMatrixAt(i, m);
  }

  _cacher(nom, i) {
    const im = this.instances[nom];
    if (im) im.setMatrixAt(i, this._zero || (this._zero = new THREE.Matrix4().makeScale(0, 0, 0)));
  }

  _cacherHumain(i) {
    for (const nom of PIECES_HUMAIN) {
      const parPersonnage = ["bras_haut", "avant_bras", "main", "cuisse", "mollet", "botte"].includes(nom) ? 2 : 1;
      for (let k = 0; k < parPersonnage; k++) this._cacher(nom, i * parPersonnage + k);
    }
    this.ombres.setMatrixAt(i, this._zero || (this._zero = new THREE.Matrix4().makeScale(0, 0, 0)));
  }

  /* Matrice = parent × translation × rotation (Euler XYZ en radians) */
  _joint(cible, parent, x, y, z, rx = 0, ry = 0, rz = 0) {
    this._e.set(rx, ry, rz, "YXZ");
    this._q.setFromEuler(this._e);
    this._t.compose(this._v.set(x, y, z), this._q, this._s.set(1, 1, 1));
    return cible.multiplyMatrices(parent, this._t);
  }

  _humain(h, t) {
    const a = h.apparence, i = h.index;
    const M = this._m;
    // Paramètres de l'animation
    let jambe = 0, genou = 0.08, bras = 0, coude = -0.15, rebond = 0, penche = 0.03, tete = h.regard || 0, hocher = 0;
    let brasD = null, coudeD = null, ecartD = 0, ecartG = 0;
    const p = h.phase;
    if (h.anim === "marche") {
      const s = Math.sin(p), c = Math.cos(p);
      jambe = s * 0.5;
      genou = 0.12;
      bras = -s * 0.42;
      coude = -0.3;
      rebond = Math.abs(c) * 0.035;
      penche = 0.06;
    } else if (h.anim === "saut") {
      jambe = 0.35;
      genou = 0.75;
      bras = -0.9;
      brasD = -0.9;
      coude = coudeD = -0.7;
      ecartG = ecartD = 0.25;
      penche = 0.12;
    } else if (h.anim === "salut") {
      brasD = -2.6 + Math.sin(t * 7.0) * 0.05;
      coudeD = -0.5 + Math.sin(t * 7.0) * 0.45;
      ecartD = 0.35;
      hocher = Math.sin(t * 2.0) * 0.05;
    } else if (h.anim === "parle") {
      bras = Math.sin(t * 2.3 + p) * 0.25;
      coude = -0.9 + Math.sin(t * 3.1 + p) * 0.35;
      brasD = -0.35 + Math.sin(t * 2.7 + p * 2) * 0.35;
      coudeD = -1.1 + Math.sin(t * 3.7 + p) * 0.3;
      hocher = Math.sin(t * 3.5 + p) * 0.08;
    } else if (h.anim === "marteau") {
      const k = (t * 1.6 + p) % 1;
      const coup = k < 0.6 ? k / 0.6 : 1 - (k - 0.6) / 0.4;
      brasD = -0.6 - coup * 1.9;
      coudeD = -1.2 + coup * 0.6;
      penche = 0.2;
      hocher = -0.15;
    } else if (h.anim === "garde") {
      brasD = -0.25;
      coudeD = -1.3;
      tete += Math.sin(t * 0.3 + p) * 0.5;
    } else if (h.anim === "travail") {
      const k = Math.sin(t * 2.2 + p);
      penche = 0.55 + k * 0.1;
      bras = -1.0 + k * 0.4;
      brasD = -1.0 + k * 0.4;
      coude = coudeD = -0.6;
      genou = 0.3;
      hocher = 0.3;
    } else {
      // repos : respiration, regard qui flâne
      rebond = Math.sin(t * 1.4 + p) * 0.006;
      tete += Math.sin(t * 0.35 + p) * 0.35;
      bras = Math.sin(t * 0.7 + p) * 0.03;
    }
    if (brasD === null) { brasD = -bras; coudeD = coude; }
    const e = a.taille;
    // Racine : position au sol, cap, taille
    this._q.setFromAxisAngle(this._v.set(0, 1, 0), h.cap);
    M[0].compose(h.pos, this._q, this._s.set(e, e, e));
    // Hanches, torse
    this._joint(M[1], M[0], 0, 0.95 + rebond, 0, 0, Math.sin(p) * (h.anim === "marche" ? 0.08 : 0), 0);
    this._joint(M[2], M[1], 0, 0, 0, penche, 0, 0);
    this._t.makeScale(a.carrure, 1, 1);
    this._r.multiplyMatrices(M[2], this._t);
    this._poser("torse", i, this._r);
    this._poser("ceinture", i, M[1]);
    // Tête et coiffure
    this._joint(M[3], M[2], 0, 0.47, 0, hocher, tete, 0);
    this._poser("tete", i, M[3]);
    this._poser("yeux", i, M[3]);
    for (const c of ["cheveux_courts", "cheveux_longs", "capuche", "chapeau", "casque"]) {
      if (a.coiffure === c) this._poser(c, i, M[3]); else this._cacher(c, i);
    }
    if (a.cape != null) {
      this._joint(M[4], M[2], 0, 0.47, 0, (h.anim === "marche" ? 0.12 + Math.abs(Math.sin(p)) * 0.08 : 0.04), 0, 0);
      this._poser("cape", i, M[4]);
    } else this._cacher("cape", i);
    if (a.jupe != null) this._poser("jupe", i, M[1]); else this._cacher("jupe", i);
    if (a.tablier != null) this._poser("tablier", i, M[2]); else this._cacher("tablier", i);
    if (a.sacoche != null) this._poser("sacoche", i, M[1]); else this._cacher("sacoche", i);
    // Bras (0 = gauche, côté +X ; 1 = droit, côté -X)
    for (const k of [0, 1]) {
      const cote = k === 0 ? 1 : -1;
      const balance = k === 0 ? bras : brasD;
      const flexion = k === 0 ? coude : coudeD;
      const ecart = k === 0 ? ecartG : ecartD;
      this._joint(M[5], M[2], 0.2 * a.carrure * cote, 0.44, 0, balance, 0, cote * (0.08 + ecart));
      this._poser("bras_haut", i * 2 + k, M[5]);
      this._joint(M[6], M[5], 0, -0.3, 0, flexion, 0, 0);
      this._poser("avant_bras", i * 2 + k, M[6]);
      this._joint(M[7], M[6], 0, -0.27, 0, 0, 0, 0);
      this._poser("main", i * 2 + k, M[7]);
      if (k === 1) {
        if (a.marteau) this._poser("marteau", i, this._joint(M[8], M[7], 0, -0.06, 0, Math.PI / 2, 0, 0)); else this._cacher("marteau", i);
        if (a.lance) {
          this._v.setFromMatrixPosition(M[7]);
          this._q.setFromAxisAngle(this._s.set(0, 1, 0), h.cap);
          M[9].compose(this._v, this._q, this._s.set(e, e, e));
          this._poser("lance", i, M[9]);
        } else this._cacher("lance", i);
      } else {
        if (a.livre) this._poser("livre", i, M[7]); else this._cacher("livre", i);
      }
    }
    // Jambes
    for (const k of [0, 1]) {
      const cote = k === 0 ? 1 : -1;
      const balance = (k === 0 ? 1 : -1) * jambe;
      const plie = h.anim === "marche" ? genou + Math.max(0, Math.sin(p + (k === 0 ? 0 : Math.PI) - 0.6)) * 0.55 : genou;
      this._joint(M[10], M[1], 0.095 * cote, -0.02, 0, -balance, 0, 0);
      this._poser("cuisse", i * 2 + k, M[10]);
      this._joint(M[11], M[10], 0, -0.47, 0, plie, 0, 0);
      this._poser("mollet", i * 2 + k, M[11]);
      this._joint(M[12], M[11], 0, -0.43, 0, -plie * 0.6 + balance * 0.2, 0, 0);
      this._poser("botte", i * 2 + k, M[12]);
    }
    // Ombre
    this._q.identity();
    this._t.compose(this._v.set(h.pos.x, h.pos.y + 0.03, h.pos.z), this._q, this._s.set(0.9 * e, 1, 0.9 * e));
    this.ombres.setMatrixAt(i, this._t);
  }

  /* --- Animaux ---------------------------------------------------------- */

  ajouterAnimal(espece, couleur, etat = {}) {
    if (this.animaux.length >= this.capacite.animaux) return -1;
    const a = { espece, couleur, pos: V(), cap: 0, anim: "repos", phase: Math.random() * 10, ...etat };
    if (etat.pos) a.pos.copy(etat.pos);
    a.index = this.animaux.length;
    this.animaux.push(a);
    const i = a.index;
    if (espece === "mouton") {
      this._couleur("mouton_corps", i, couleur);
      this._couleur("mouton_tete", i, 0x2a2420);
      for (let k = 0; k < 4; k++) this._couleur("patte_fine", i * 4 + k, 0x2a2420);
    } else if (espece === "cheval") {
      this._couleur("cheval_corps", i, couleur);
      this._couleur("cheval_cou", i, couleur);
      this._couleur("queue", i, 0x1c1410);
      for (let k = 0; k < 4; k++) this._couleur("cheval_patte", i * 4 + k, couleur);
      if (a.charrette) {
        this._couleur("charrette", i, 0x7a5a3a);
        this._couleur("roue", i * 2, 0x4a3522);
        this._couleur("roue", i * 2 + 1, 0x4a3522);
      }
    } else if (espece === "chien") {
      this._couleur("chien_corps", i, couleur);
      this._couleur("chien_tete", i, couleur);
      this._couleur("queue", i, couleur);
      for (let k = 0; k < 4; k++) this._couleur("patte_fine", i * 4 + k, couleur);
    }
    return i;
  }

  _animal(a, t) {
    const i = a.index, M = this._m;
    const marche = a.anim === "marche";
    const s = Math.sin(a.phase);
    this._q.setFromAxisAngle(this._v.set(0, 1, 0), a.cap);
    M[0].compose(a.pos, this._q, this._s.set(1, 1, 1));
    const pattes = (nom, coins, hauteur, base, k0 = 0) => {
      coins.forEach(([x, z], k) => {
        const sens = (k === 0 || k === 3) ? 1 : -1;
        this._joint(M[5], M[0], x, hauteur, z, marche ? sens * s * 0.45 : 0, 0, 0);
        this._poser(nom, base + k, M[5]);
      });
    };
    if (a.espece === "mouton") {
      this._poser("mouton_corps", i, this._joint(M[1], M[0], 0, 0.62 + (marche ? Math.abs(s) * 0.02 : 0), 0));
      const broute = a.anim === "broute" ? 0.7 + Math.sin(t * 3 + a.phase) * 0.1 : 0;
      this._poser("mouton_tete", i, this._joint(M[2], M[0], 0, 0.75, 0.5, broute, 0, 0));
      pattes("patte_fine", [[0.17, 0.3], [-0.17, 0.3], [0.17, -0.3], [-0.17, -0.3]], 0.42, i * 4);
      this._cacher("cheval_corps", i);
    } else if (a.espece === "cheval") {
      this._poser("cheval_corps", i, this._joint(M[1], M[0], 0, 1.45 + (marche ? Math.abs(s) * 0.03 : 0), 0));
      const broute = a.anim === "broute" ? 0.9 : marche ? Math.sin(a.phase * 2) * 0.05 : 0;
      this._poser("cheval_cou", i, this._joint(M[2], M[0], 0, 1.55, 0.55, broute, 0, 0));
      this._poser("queue", i, this._joint(M[3], M[0], 0, 1.6, -0.75, 0.3, 0, Math.sin(t * 2 + a.phase) * 0.2));
      pattes("cheval_patte", [[0.2, 0.45], [-0.2, 0.45], [0.2, -0.45], [-0.2, -0.45]], 1.08, i * 4);
      if (a.charrette) {
        this._poser("charrette", i, this._joint(M[4], M[0], 0, 0, -2.6));
        const roule = (a.distance || 0) / 0.5;
        this._poser("roue", i * 2, this._joint(M[6], M[0], 0.8, 0.5, -2.6, roule, 0, 0));
        this._poser("roue", i * 2 + 1, this._joint(M[7], M[0], -0.8, 0.5, -2.6, roule, 0, 0));
      }
    } else if (a.espece === "chien") {
      this._poser("chien_corps", i, this._joint(M[1], M[0], 0, 0.42 + (marche ? Math.abs(s) * 0.02 : 0), 0));
      this._poser("chien_tete", i, this._joint(M[2], M[0], 0, 0.52, 0.3, 0, Math.sin(t * 0.8 + a.phase) * 0.3, 0));
      this._poser("queue", i, this._joint(M[3], M[0], 0, 0.47, -0.25, -0.6, 0, Math.sin(t * 8 + a.phase) * 0.4));
      for (let k = 0; k < 4; k++) {
        const [x, z] = [[0.08, 0.18], [-0.08, 0.18], [0.08, -0.18], [-0.08, -0.18]][k];
        const sens = (k === 0 || k === 3) ? 1 : -1;
        this._joint(M[5], M[0], x, 0.32, z, marche ? sens * s * 0.6 : 0, 0, 0);
        this._t.makeScale(0.8, 0.75, 0.8);
        this._poser("patte_fine", i * 4 + k, this._r.multiplyMatrices(M[5], this._t));
      }
    }
    const taille = a.espece === "cheval" ? (a.charrette ? 2.6 : 2.0) : a.espece === "mouton" ? 1.2 : 0.8;
    this._q.identity();
    this._t.compose(this._v.set(a.pos.x, a.pos.y + 0.03, a.pos.z), this._q, this._s.set(taille, 1, taille * 1.4));
    this.ombres.setMatrixAt(this.capacite.humains + i, this._t);
  }

  /* --- Image ------------------------------------------------------------ */

  maj(t, camera) {
    for (const h of this.humains) {
      if (!h.actif) continue;
      if (!h.visible || (camera && h.pos.distanceToSquared(camera.position) > 160 * 160)) { this._cacherHumain(h.index); continue; }
      this._humain(h, t);
    }
    for (const a of this.animaux) this._animal(a, t);
    for (const nom in this.instances) this.instances[nom].instanceMatrix.needsUpdate = true;
    this.ombres.instanceMatrix.needsUpdate = true;
  }
}

/* =========================================================================
   Carte de marche : hauteur du sol et cases praticables (royaume_carte.png)
   ========================================================================= */

export class CarteMarche {
  constructor(image, meta) {
    const c = document.createElement("canvas");
    c.width = image.width;
    c.height = image.height;
    const g = c.getContext("2d", { willReadFrequently: true });
    g.drawImage(image, 0, 0);
    this.px = g.getImageData(0, 0, c.width, c.height).data;
    this.n = meta.taille;
    this.pas = meta.pas;
    this.demi = meta.demi;
    this.hMin = meta.hauteurMin;
    this.hMax = meta.hauteurMax;
  }

  _case(x, z) {
    // Le site : X vers l'est, Z vers le sud (Z = -Y de Blender). La ligne 0 de l'image est le nord.
    const i = Math.floor((x + this.demi) / this.pas);
    const j = Math.floor((-z + this.demi) / this.pas);
    if (i < 0 || j < 0 || i >= this.n || j >= this.n) return -1;
    return ((this.n - 1 - j) * this.n + i) * 4;
  }

  /* Hauteur du sol, interpolée entre les quatre cases voisines pour un pas sans à-coups.
     Seules comptent les cases dont la hauteur est connue (praticables, ou à l'intérieur d'un bâtiment) ;
     sans aucune, on rend « defaut ». */
  hauteur(x, z, defaut = 0) {
    const fx = (x + this.demi) / this.pas - 0.5, fj = (-z + this.demi) / this.pas - 0.5;
    const i0 = Math.floor(fx), j0 = Math.floor(fj), tx = fx - i0, tj = fj - j0;
    let somme = 0, poids = 0;
    for (const [di, dj, w] of [[0, 0, (1 - tx) * (1 - tj)], [1, 0, tx * (1 - tj)], [0, 1, (1 - tx) * tj], [1, 1, tx * tj]]) {
      const i = i0 + di, j = j0 + dj;
      if (i < 0 || j < 0 || i >= this.n || j >= this.n) continue;
      const k = ((this.n - 1 - j) * this.n + i) * 4;
      if (this.px[k + 3] === 0 || !(this.px[k + 2] & 3)) continue;
      const h = this.hMin + ((this.px[k] * 256 + this.px[k + 1]) / 65535) * (this.hMax - this.hMin);
      somme += h * w;
      poids += w;
    }
    return poids > 1e-6 ? somme / poids : defaut;
  }

  praticable(x, z) {
    const k = this._case(x, z);
    return k >= 0 && (this.px[k + 2] & 1) === 1;
  }

  /* 0 dehors ; sinon le numéro du bâtiment (1 atelier, 2 guilde, 3 grande salle, 4 forge) */
  interieur(x, z) {
    const k = this._case(x, z);
    if (k < 0 || !(this.px[k + 2] & 2)) return 0;
    return this.px[k + 2] >> 2;
  }
}

/* =========================================================================
   La vie du royaume : qui marche où
   ========================================================================= */

class Trajet {
  constructor(points, boucle = true) {
    this.p = points.map((q) => new THREE.Vector3(q[0], 0, q[2]));
    if (boucle) this.p.push(this.p[0].clone());
    this.cumul = [0];
    for (let k = 1; k < this.p.length; k++) this.cumul.push(this.cumul[k - 1] + this.p[k].distanceTo(this.p[k - 1]));
    this.longueur = this.cumul[this.cumul.length - 1];
    this.boucle = boucle;
  }

  /* Point et direction à la distance s (avec un décalage latéral) */
  point(s, decalage, sortie, dir) {
    s = this.boucle ? ((s % this.longueur) + this.longueur) % this.longueur : Math.max(0, Math.min(this.longueur, s));
    let lo = 0, hi = this.cumul.length - 1;
    while (lo < hi - 1) { const m = (lo + hi) >> 1; if (this.cumul[m] <= s) lo = m; else hi = m; }
    const a = this.p[lo], b = this.p[hi];
    const t = (s - this.cumul[lo]) / Math.max(1e-6, this.cumul[hi] - this.cumul[lo]);
    sortie.lerpVectors(a, b, t);
    dir.subVectors(b, a).normalize();
    sortie.x += -dir.z * decalage;
    sortie.z += dir.x * decalage;
    return sortie;
  }
}

export class Royaume {
  /**
   * @param peuple   le Peuple qui dessine
   * @param carte    la CarteMarche
   * @param chemins  royaume.json (rues, piste, avenue, remparts, place, champs, pâturage)
   * @param reperes  { nom: { pos: Vector3, regard, role } } pour les personnages nommés (pnj_*)
   */
  constructor(peuple, carte, chemins, reperes, MODESTE) {
    this.peuple = peuple;
    this.carte = carte;
    this.marcheurs = [];
    this.nommes = {};
    this.animaux = [];
    const rnd = hasard(41);
    this.rnd = rnd;
    const tmp = V(), dir = V();
    // Personnages nommés, à leur place, avec leur animation
    const tenues = {
      capitaine: { casque: true, haut: 0x6b6f75, cape: 0x8a2f1c, lance: true, anim: "garde" },
      coach: { haut: 0x2f4f4f, tablier: 0x6b4a2c, coiffure: "cheveux_courts", cheveux: 0x2b1d14, anim: "parle" },
      forgeron: { haut: 0x5a3a2a, tablier: 0x3a2618, coiffure: null, marteau: true, carrure: 1.18, anim: "marteau" },
      bibliothecaire: { haut: 0x334a6b, jupe: 0x2a3a5a, coiffure: "cheveux_longs", cheveux: 0x9a9a9a, livre: true, anim: "parle" },
      intendante: { haut: 0x6b2f2f, jupe: 0x5a2424, coiffure: "cheveux_longs", cheveux: 0x2b1d14, anim: "parle" },
      gardien: { haut: 0x2a3550, coiffure: "capuche", anim: "repos" },
      meunier: { haut: 0xd9d2c0, tablier: 0xe8e2d4, coiffure: "chapeau", anim: "repos" },
      aubergiste: { haut: 0x7a3b2e, tablier: 0xd9cdb4, carrure: 1.15, anim: "parle" },
    };
    for (const [nom, r] of Object.entries(reperes)) {
      if (!nom.startsWith("pnj_")) continue;
      const role = r.role || nom.slice(4);
      const t = tenues[role] || {};
      const app = apparenceAuHasard(rnd, {
        ...t, coiffure: t.coiffure !== undefined ? t.coiffure : (t.casque ? "casque" : undefined),
      });
      if (t.casque) app.coiffure = "casque";
      if (app.coiffure === undefined) app.coiffure = "cheveux_courts";
      const pos = r.pos.clone();
      pos.y = carte.hauteur(pos.x, pos.z, r.pos.y);
      const id = peuple.ajouterHumain(app, { pos, cap: r.regard, anim: t.anim || "repos", role });
      this.nommes[role] = { id, pos, cap: r.regard, anim: t.anim || "repos" };
    }
    // Gardes sur les chemins de ronde
    const nbGardes = MODESTE ? 8 : 16;
    const rondes = Object.values(chemins.remparts || {}).map((pts) => ({ trajet: new Trajet(pts), hauteurs: pts }));
    for (let k = 0; k < nbGardes && rondes.length; k++) {
      const r = rondes[k % rondes.length];
      const app = apparenceAuHasard(rnd, { haut: 0x6b6f75, bas: 0x3a3a40, coiffure: "casque", cape: 0x8a2f1c, lance: true, jupe: null, tablier: null });
      const id = peuple.ajouterHumain(app, { anim: "marche" });
      this.marcheurs.push({ id, trajet: r.trajet, s: rnd() * r.trajet.longueur, v: (0.7 + rnd() * 0.2) * (rnd() < 0.5 ? 1 : -1), decalage: 0,
        ronde: r, arret: 0 });
    }
    // Habitants dans les rues, sur l'avenue, la piste et les rues rayonnantes
    const trajets = [];
    if (chemins.rue) trajets.push({ t: new Trajet(chemins.rue), n: MODESTE ? 18 : 34, lat: 1.6 });
    if (chemins.avenue) trajets.push({ t: new Trajet(chemins.avenue, false), n: MODESTE ? 4 : 8, lat: 1.2 });
    if (chemins.piste) trajets.push({ t: new Trajet(chemins.piste), n: MODESTE ? 4 : 8, lat: 0.6 });
    for (const seg of chemins.radiales || []) trajets.push({ t: new Trajet(seg, false), n: MODESTE ? 1 : 2, lat: 0.8 });
    for (const tr of trajets) {
      for (let k = 0; k < tr.n; k++) {
        const id = peuple.ajouterHumain(apparenceAuHasard(rnd), { anim: "marche" });
        this.marcheurs.push({ id, trajet: tr.t, s: rnd() * tr.t.longueur, v: (1.0 + rnd() * 0.45) * (rnd() < 0.5 ? 1 : -1),
          decalage: (rnd() - 0.5) * 2 * tr.lat, arret: 0, allerRetour: !tr.t.boucle });
      }
    }
    // Groupes qui discutent sur la place, paysans aux champs
    const place = chemins.place || [];
    for (let k = 0; k < Math.min(place.length, MODESTE ? 8 : 18); k += 2) {
      const a = new THREE.Vector3(place[k][0], 0, place[k][2]);
      for (const s of [-1, 1]) {
        const pos = a.clone().add(new THREE.Vector3(s * 0.55, 0, 0));
        pos.y = carte.hauteur(pos.x, pos.z);
        peuple.ajouterHumain(apparenceAuHasard(rnd), { pos, cap: s > 0 ? -Math.PI / 2 : Math.PI / 2, anim: rnd() < 0.6 ? "parle" : "repos" });
      }
    }
    for (const c of (chemins.champs || []).slice(0, MODESTE ? 6 : 14)) {
      const pos = new THREE.Vector3(c[0], 0, c[2]);
      pos.y = carte.hauteur(pos.x, pos.z);
      peuple.ajouterHumain(apparenceAuHasard(rnd, { coiffure: "chapeau", tablier: null }), { pos, cap: rnd() * 6.28, anim: "travail" });
    }
    // Moutons au pâturage, chevaux et charrettes sur l'avenue, chiens
    if (chemins.paturage) {
      const [a0, a1] = chemins.paturage.angles, [r0, r1] = chemins.paturage.rayons;
      for (let k = 0; k < (MODESTE ? 8 : 16); k++) {
        const a = a0 + rnd() * (a1 - a0), r = r0 + rnd() * (r1 - r0);
        const pos = new THREE.Vector3(Math.cos(a) * r, 0, -Math.sin(a) * r);
        pos.y = carte.hauteur(pos.x, pos.z);
        const id = peuple.ajouterAnimal("mouton", rnd() < 0.15 ? 0x3a3230 : 0xeae4d8, { pos, cap: rnd() * 6.28, anim: "broute" });
        this.animaux.push({ id, type: "mouton", zone: { a0, a1, r0, r1 }, but: pos.clone(), attente: rnd() * 6 });
      }
    }
    if (chemins.avenue) {
      const t = new Trajet(chemins.avenue, false);
      for (let k = 0; k < 2; k++) {
        const id = peuple.ajouterAnimal("cheval", [0x5a3a24, 0x2a2020, 0x8a6a4a][k], { charrette: true, anim: "marche" });
        this.animaux.push({ id, type: "cheval", trajet: t, s: rnd() * t.longueur, v: 1.3 * (k ? -1 : 1), decalage: k ? -1.3 : 1.3 });
      }
    }
    for (let k = 0; k < (MODESTE ? 2 : 5) && this.marcheurs.length; k++) {
      const maitre = this.marcheurs[Math.floor(rnd() * this.marcheurs.length)];
      const id = peuple.ajouterAnimal("chien", [0x8a5a2a, 0x2a2420, 0xd8c8a8, 0x5a4030][k % 4], { anim: "marche" });
      this.animaux.push({ id, type: "chien", maitre });
    }
    this._tmp = tmp;
    this._dir = dir;
  }

  maj(dt, t) {
    const p = this.peuple, tmp = this._tmp, dir = this._dir;
    for (const m of this.marcheurs) {
      const h = p.humains[m.id];
      if (!h) continue;
      if (m.arret > 0) {
        m.arret -= dt;
        h.anim = "repos";
      } else {
        m.s += m.v * dt;
        if (m.allerRetour && (m.s <= 0 || m.s >= m.trajet.longueur)) { m.v = -m.v; m.s = Math.max(0, Math.min(m.trajet.longueur, m.s)); m.arret = 1 + this.rnd() * 3; }
        if (!m.allerRetour && this.rnd() < dt * 0.01) m.arret = 2 + this.rnd() * 4;
        h.anim = "marche";
        h.phase += Math.abs(m.v) * dt * 5.2;
      }
      m.trajet.point(m.s, m.decalage, tmp, dir);
      if (m.v < 0) dir.negate();
      h.pos.x = tmp.x;
      h.pos.z = tmp.z;
      h.pos.y = m.ronde ? this._hauteurRonde(m, tmp) : this.carte.hauteur(tmp.x, tmp.z, h.pos.y);
      if (h.anim === "marche") h.cap = Math.atan2(dir.x, dir.z);
    }
    for (const a of this.animaux) {
      const b = p.animaux[a.id];
      if (!b) continue;
      if (a.type === "mouton") {
        if (a.attente > 0) { a.attente -= dt; b.anim = "broute"; continue; }
        tmp.subVectors(a.but, b.pos);
        tmp.y = 0;
        const d = tmp.length();
        if (d < 0.2) {
          a.attente = 3 + this.rnd() * 8;
          const an = a.zone.a0 + this.rnd() * (a.zone.a1 - a.zone.a0), r = a.zone.r0 + this.rnd() * (a.zone.r1 - a.zone.r0);
          a.but.set(Math.cos(an) * r, 0, -Math.sin(an) * r);
        } else {
          tmp.multiplyScalar(Math.min(d, 0.5 * dt) / d);
          b.pos.add(tmp);
          b.pos.y = this.carte.hauteur(b.pos.x, b.pos.z, b.pos.y);
          b.cap = Math.atan2(tmp.x, tmp.z);
          b.anim = "marche";
          b.phase += dt * 6;
        }
      } else if (a.type === "cheval") {
        a.s += a.v * dt;
        if (a.s <= 0 || a.s >= a.trajet.longueur) { a.v = -a.v; a.s = Math.max(0, Math.min(a.trajet.longueur, a.s)); }
        a.trajet.point(a.s, a.decalage, tmp, dir);
        if (a.v < 0) dir.negate();
        b.pos.set(tmp.x, this.carte.hauteur(tmp.x, tmp.z, b.pos.y), tmp.z);
        b.cap = Math.atan2(dir.x, dir.z);
        b.phase += dt * 5.5;
        b.distance = (b.distance || 0) + Math.abs(a.v) * dt;
      } else if (a.type === "chien") {
        const h = p.humains[a.maitre.id];
        if (!h) continue;
        tmp.set(-Math.sin(h.cap) * 1.4 + Math.cos(h.cap) * 0.6, 0, -Math.cos(h.cap) * 1.4 - Math.sin(h.cap) * 0.6).add(h.pos);
        const d = tmp.distanceTo(b.pos);
        b.anim = d > 0.3 ? "marche" : "repos";
        b.pos.lerp(tmp, Math.min(1, dt * 3));
        b.pos.y = this.carte.hauteur(b.pos.x, b.pos.z, b.pos.y);
        if (d > 0.3) { b.cap = h.cap; b.phase += dt * 9; }
      }
    }
  }

  /* Le personnage le plus proche à qui parler : un personnage nommé, un garde ou un passant */
  plusProche(pos, rayon, exclure, langue) {
    let meilleur = null, dmin = rayon * rayon;
    const essayer = (id, cle, marcheur) => {
      const h = this.peuple.humains[id];
      if (!h || id === exclure || !h.actif) return;
      const d = (h.pos.x - pos.x) ** 2 + (h.pos.z - pos.z) ** 2 + ((h.pos.y - pos.y) * 2) ** 2;
      if (d < dmin) { dmin = d; meilleur = { id, cle, marcheur }; }
    };
    for (const [role, n] of Object.entries(this.nommes)) essayer(n.id, role, null);
    for (const m of this.marcheurs) essayer(m.id, m.ronde ? "@garde" : "@passant", m);
    if (!meilleur) return null;
    if (meilleur.cle.startsWith("@")) {
      const liste = meilleur.cle === "@garde" ? GARDES[langue] : PASSANTS[langue];
      meilleur.phrase = liste[meilleur.id % liste.length];
      meilleur.nom = meilleur.cle === "@garde" ? (langue === "en" ? "A guard" : "Un garde") : (langue === "en" ? "A townsperson" : "Un habitant");
    } else {
      meilleur.nom = DIALOGUES[meilleur.cle]?.[langue]?.nom || meilleur.cle;
    }
    return meilleur;
  }

  _hauteurRonde(m, point) {
    // Le chemin de ronde est à hauteur fixe : on reprend la hauteur du point de la ronde le plus proche
    const pts = m.ronde.hauteurs;
    const k = Math.floor(((m.s % m.trajet.longueur) + m.trajet.longueur) % m.trajet.longueur / m.trajet.longueur * pts.length) % pts.length;
    return pts[k][1];
  }
}
