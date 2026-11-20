/*
  MODE LIBRE · se promener dans le royaume avec Ernest

  Ordinateur : ZQSD, WASD ou les flèches pour marcher, Maj pour courir, glisser pour tourner la caméra,
  molette pour l'éloigner, E (ou Entrée) pour parler, Échap pour fermer un dialogue.
  Téléphone : un joystick à gauche, glisser à droite pour regarder, un bouton « Parler ».

  Les collisions viennent de la carte de marche (royaume_carte.png) : on glisse le long des murs, on passe
  les portes, et la caméra se rapproche quand on entre dans un bâtiment.
*/
import * as THREE from "../../lib/three/three.module.js";

const AVANT = ["KeyW", "KeyZ", "ArrowUp"], ARRIERE = ["KeyS", "ArrowDown"];
const GAUCHE = ["KeyA", "KeyQ", "ArrowLeft"], DROITE = ["KeyD", "ArrowRight"];

export class Exploration {
  constructor({ camera, carte, peuple, ernest, dialogue, royaume, langue, canvas }) {
    this.camera = camera;
    this.carte = carte;
    this.peuple = peuple;
    this.ernest = ernest;               // index de l'humain qui représente Ernest
    this.dialogue = dialogue;
    this.royaume = royaume;
    this.langue = langue;
    this.canvas = canvas;
    this.actif = false;
    this.touches = new Set();
    this.yaw = 0;
    this.pitch = 0.32;
    this.distance = 5.5;
    this.distanceVoulue = 5.5;
    this.joystick = new THREE.Vector2();
    this.cible = new THREE.Vector3();
    this.camPos = new THREE.Vector3();
    this.interlocuteur = null;
    this.invite = document.querySelector(".invite");
    this.boutonParler = document.querySelector(".bouton-parler");
    this._brancher();
  }

  _brancher() {
    window.addEventListener("keydown", (e) => {
      if (!this.actif) return;
      if (e.target && /INPUT|TEXTAREA/.test(e.target.tagName)) return;
      if (e.code === "Escape") {
        if (this.dialogue.ouvert) this.dialogue.clore();
        return;
      }
      if ((e.code === "KeyE" || e.code === "Enter") && !this.dialogue.ouvert) {
        this.parler();
        e.preventDefault();
        return;
      }
      this.touches.add(e.code);
      if (e.code.startsWith("Arrow") || e.code === "Space") e.preventDefault();
    });
    window.addEventListener("keyup", (e) => this.touches.delete(e.code));
    window.addEventListener("blur", () => this.touches.clear());
    // Caméra : glisser pour tourner autour d'Ernest
    let glisse = null;
    this.canvas.addEventListener("pointerdown", (e) => {
      if (!this.actif) return;
      if (e.pointerType === "touch" && e.clientX < window.innerWidth * 0.45) return;   // moitié gauche : joystick
      glisse = { x: e.clientX, y: e.clientY, id: e.pointerId };
      this.canvas.setPointerCapture(e.pointerId);
    });
    this.canvas.addEventListener("pointermove", (e) => {
      if (!glisse || e.pointerId !== glisse.id) return;
      this.yaw -= (e.clientX - glisse.x) * 0.006;
      this.pitch = THREE.MathUtils.clamp(this.pitch + (e.clientY - glisse.y) * 0.004, -0.15, 1.15);
      glisse.x = e.clientX;
      glisse.y = e.clientY;
    });
    const fin = (e) => { if (glisse && e.pointerId === glisse.id) glisse = null; };
    this.canvas.addEventListener("pointerup", fin);
    this.canvas.addEventListener("pointercancel", fin);
    this.canvas.addEventListener("wheel", (e) => {
      if (!this.actif) return;
      this.distanceVoulue = THREE.MathUtils.clamp(this.distanceVoulue + e.deltaY * 0.004, 2.2, 14);
      e.preventDefault();
    }, { passive: false });
    // Joystick tactile
    const zone = document.querySelector(".joystick");
    const bouton = zone && zone.querySelector("span");
    if (zone) {
      let id = null, centre = null;
      zone.addEventListener("pointerdown", (e) => { id = e.pointerId; centre = { x: e.clientX, y: e.clientY }; zone.setPointerCapture(id); });
      zone.addEventListener("pointermove", (e) => {
        if (e.pointerId !== id) return;
        const dx = e.clientX - centre.x, dy = e.clientY - centre.y;
        const l = Math.min(1, Math.hypot(dx, dy) / 50);
        const a = Math.atan2(dy, dx);
        this.joystick.set(Math.cos(a) * l, -Math.sin(a) * l);
        bouton.style.transform = `translate(${Math.cos(a) * l * 34}px, ${Math.sin(a) * l * 34}px)`;
      });
      const relache = () => { id = null; this.joystick.set(0, 0); bouton.style.transform = ""; };
      zone.addEventListener("pointerup", relache);
      zone.addEventListener("pointercancel", relache);
    }
    this.boutonParler?.addEventListener("click", () => this.parler());
    this.invite?.addEventListener("click", () => this.parler());
  }

  activer(depart, cap) {
    const h = this.peuple.humains[this.ernest];
    h.pos.copy(depart);
    h.pos.y = this.carte.hauteur(depart.x, depart.z, depart.y);
    h.cap = cap;
    this.yaw = cap + Math.PI;
    this.actif = true;
    this.premier = true;
    this.distance = this.distanceVoulue = 5.5;
  }

  desactiver() {
    this.actif = false;
    this.touches.clear();
    this.dialogue.clore();
    this._invite(null);
  }

  parler() {
    if (!this.interlocuteur || this.dialogue.ouvert) return;
    const it = this.interlocuteur;
    const h = this.peuple.humains[it.id];
    const e = this.peuple.humains[this.ernest];
    if (h) {
      it.capAvant = h.cap;
      it.animAvant = h.anim;
      h.cap = Math.atan2(e.pos.x - h.pos.x, e.pos.z - h.pos.z);
      h.anim = "parle";
      if (it.marcheur) it.marcheur.arret = 8;
    }
    this.dialogue.ouvrir(it.cle, it.phrase);
    this._parleAvec = it;
  }

  _invite(it) {
    if (!this.invite) return;
    if (!it) {
      this.invite.hidden = true;
      if (this.boutonParler) this.boutonParler.hidden = true;
      return;
    }
    this.invite.hidden = false;
    this.invite.querySelector(".invite-nom").textContent = it.nom;
    if (this.boutonParler) this.boutonParler.hidden = false;
  }

  maj(dt) {
    if (!this.actif) return;
    const h = this.peuple.humains[this.ernest];
    // Fin d'un dialogue : l'interlocuteur reprend ce qu'il faisait
    if (this._parleAvec && !this.dialogue.ouvert) {
      const it = this._parleAvec;
      const p = this.peuple.humains[it.id];
      if (p && it.capAvant !== undefined && !it.marcheur) { p.cap = it.capAvant; p.anim = it.animAvant; }
      this._parleAvec = null;
    }
    // Déplacement relatif à la caméra
    let ax = 0, ay = 0;
    if (!this.dialogue.ouvert) {
      if (AVANT.some((k) => this.touches.has(k))) ay += 1;
      if (ARRIERE.some((k) => this.touches.has(k))) ay -= 1;
      if (GAUCHE.some((k) => this.touches.has(k))) ax -= 1;
      if (DROITE.some((k) => this.touches.has(k))) ax += 1;
      ax += this.joystick.x;
      ay += this.joystick.y;
    }
    const l = Math.hypot(ax, ay);
    const court = this.touches.has("ShiftLeft") || this.touches.has("ShiftRight");
    if (l > 0.05) {
      ax /= Math.max(1, l);
      ay /= Math.max(1, l);
      const vitesse = (court ? 6.2 : 3.1) * Math.min(1, l);
      // Avant de la caméra (projeté au sol)
      const fx = -Math.sin(this.yaw), fz = -Math.cos(this.yaw);
      const dx = (fx * ay - fz * ax) * vitesse * dt;
      const dz = (fz * ay + fx * ax) * vitesse * dt;
      const x = h.pos.x, z = h.pos.z;
      if (this.carte.praticable(x + dx, z + dz)) { h.pos.x += dx; h.pos.z += dz; }
      else if (this.carte.praticable(x + dx, z)) h.pos.x += dx;
      else if (this.carte.praticable(x, z + dz)) h.pos.z += dz;
      const cap = Math.atan2(dx, dz);
      let ecart = ((cap - h.cap + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
      h.cap += ecart * Math.min(1, dt * 10);
      h.anim = "marche";
      h.phase += vitesse * dt * 3.2;
    } else {
      h.anim = "repos";
    }
    h.pos.y += (this.carte.hauteur(h.pos.x, h.pos.z, h.pos.y) - h.pos.y) * Math.min(1, dt * 12);
    // Caméra : derrière Ernest, plus près à l'intérieur
    const dedans = this.carte.interieur(h.pos.x, h.pos.z) > 0;
    const voulue = dedans ? Math.min(2.6, this.distanceVoulue) : this.distanceVoulue;
    this.distance += (voulue - this.distance) * Math.min(1, dt * 4);
    this.cible.set(h.pos.x, h.pos.y + 1.55, h.pos.z);
    const cp = Math.cos(this.pitch), sp = Math.sin(this.pitch);
    let d = this.distance;
    if (dedans) {
      // On rapproche la caméra tant qu'elle traverserait un mur
      for (let k = 1; k <= 12; k++) {
        const t = (k / 12) * d;
        const x = this.cible.x + Math.sin(this.yaw) * cp * t, z = this.cible.z + Math.cos(this.yaw) * cp * t;
        if (!this.carte.praticable(x, z)) { d = Math.max(0.6, t - 0.4); break; }
      }
    }
    this.camPos.set(this.cible.x + Math.sin(this.yaw) * cp * d, this.cible.y + sp * d, this.cible.z + Math.cos(this.yaw) * cp * d);
    const sol = this.carte.hauteur(this.camPos.x, this.camPos.z, -1e9) + 0.4;
    if (this.camPos.y < sol) this.camPos.y = sol;
    // Lissage propre au mode libre (le moteur fait lui-même le fondu depuis la caméra de la visite)
    if (this.premier || !this.camLisse) { this.camLisse = this.camPos.clone(); this.premier = false; }
    else this.camLisse.lerp(this.camPos, Math.min(1, dt * 10));
    this.camera.position.copy(this.camLisse);
    this.camera.lookAt(this.cible);
    // Quelqu'un à qui parler ?
    const it = this.royaume.plusProche(h.pos, 3.6, this.ernest, this.langue);
    if ((it && it.id) !== (this.interlocuteur && this.interlocuteur.id)) this._invite(it);
    this.interlocuteur = it;
  }
}
