/*
  LES AUTRES VISITEURS · présence, avatars et chat en temps réel

  Le site est statique (GitHub Pages) : le temps réel passe par Supabase Realtime, un service hébergé.
  - « Presence » : chaque visiteur annonce qui il est (un numéro, une apparence tirée au sort à partir de ce
    numéro, son mode et son chapitre). Le nombre de visiteurs en ligne en découle.
  - « Broadcast » : les positions en mode libre (huit fois par seconde) et les messages du chat.
  Rien n'est enregistré : un message n'existe que pour les visiteurs présents à ce moment-là.

  Réglage : 3d/config-multijoueur.js (adresse du projet Supabase et clé publique « anon »). Si elle est
  vide, ce module ne charge rien et l'interface reste cachée.
*/
import * as THREE from "../../lib/three/three.module.js";
import { apparenceAuHasard } from "./personnages.js";

const LONGUEUR_MAX = 200;
const INTERVALLE_MESSAGES = 1500;   // ms entre deux messages d'un même visiteur
const FREQUENCE_POSITIONS = 125;    // ms entre deux positions envoyées (8 par seconde)

function hasard(graine) {
  return function () {
    graine |= 0; graine = (graine + 0x6d2b79f5) | 0;
    let t = Math.imul(graine ^ (graine >>> 15), 1 | graine);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export class Multijoueur {
  constructor({ config, peuple, langue, camera, guides }) {
    this.config = config;
    this.peuple = peuple;
    this.langue = langue;
    this.camera = camera;
    this.guides = guides;                 // { chapitre: Vector3 } : où se rassemblent les visiteurs de la visite
    this.numero = 1000 + Math.floor(Math.random() * 9000);
    this.id = `${this.numero}-${Math.random().toString(36).slice(2, 8)}`;
    this.autres = new Map();              // id -> { numero, index, cible, cap, mode, chapitre, etiquette, message, finMessage }
    this.masques = new Set();
    this.dernierMessage = 0;
    this.derniereEnvoi = 0;
    this.etat = { mode: "visite", chapitre: 0 };
    this.compteur = document.querySelector(".presence");
    this.panneau = document.querySelector(".chat");
    this.liste = document.querySelector(".chat-messages");
    this.saisie = document.querySelector(".chat-saisie");
    this.formulaire = document.querySelector(".chat-formulaire");
    this.calque = document.querySelector(".etiquettes");
    this._v = new THREE.Vector3();
  }

  nom(numero) {
    return (this.langue === "en" ? "Visitor " : "Visiteur ") + numero;
  }

  async demarrer() {
    if (!this.config || !this.config.url || !this.config.cleAnon) return false;
    let createClient;
    try {
      ({ createClient } = await import("https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.118.0/+esm"));
    } catch (e) {
      console.warn("[ile3d] temps réel indisponible :", e.message);
      return false;
    }
    this.client = createClient(this.config.url, this.config.cleAnon, { realtime: { params: { eventsPerSecond: 20 } } });
    this.canal = this.client.channel(this.config.canal || "royaume-ernest", {
      config: { presence: { key: this.id }, broadcast: { self: false } },
    });
    this.canal.on("presence", { event: "sync" }, () => this._synchroniser());
    this.canal.on("broadcast", { event: "pos" }, ({ payload }) => this._position(payload));
    this.canal.on("broadcast", { event: "chat" }, ({ payload }) => this._recevoir(payload));
    this.canal.subscribe(async (statut, erreur) => {
      if (statut === "SUBSCRIBED") {
        this.pret = true;
        await this._annoncer();
        document.documentElement.classList.add("multijoueur");
      } else {
        // Fermé ou coupé : la bibliothèque se reconnecte seule, et l'annonce est refaite à la réouverture
        this.pret = false;
        if (statut !== "CLOSED") console.warn("[ile3d] temps réel :", statut, erreur ? erreur.message : "");
      }
    });
    this._brancherInterface();
    return true;
  }

  _annoncer() {
    return this.canal.track({ numero: this.numero, mode: this.etat.mode, chapitre: this.etat.chapitre, t: Date.now() });
  }

  _brancherInterface() {
    this.compteur.addEventListener("click", () => {
      this.panneau.hidden = !this.panneau.hidden;
      this.compteur.setAttribute("aria-expanded", String(!this.panneau.hidden));
      if (!this.panneau.hidden) this.saisie.focus({ preventScroll: true });
    });
    this.panneau.querySelector(".chat-fermer").addEventListener("click", () => {
      this.panneau.hidden = true;
      this.compteur.setAttribute("aria-expanded", "false");
    });
    this.formulaire.addEventListener("submit", (e) => {
      e.preventDefault();
      this.envoyer(this.saisie.value);
    });
  }

  _synchroniser() {
    const etat = this.canal.presenceState();
    const presents = new Set();
    for (const [id, metas] of Object.entries(etat)) {
      if (id === this.id || !metas.length) continue;
      presents.add(id);
      const m = metas[metas.length - 1];
      let a = this.autres.get(id);
      if (!a) {
        const apparence = apparenceAuHasard(hasard(m.numero * 7919), { cape: null });
        const index = this.peuple.ajouterHumain(apparence, { anim: "repos" });
        if (index < 0) continue;
        a = { numero: m.numero, index, cible: null, cap: 0, mode: "visite", chapitre: 0, message: "", finMessage: 0 };
        a.etiquette = document.createElement("div");
        a.etiquette.className = "etiquette-avatar";
        a.etiquette.innerHTML = "<span class=\"etiquette-nom\"></span><span class=\"etiquette-message\"></span>";
        a.etiquette.querySelector(".etiquette-nom").textContent = this.nom(m.numero);
        this.calque.appendChild(a.etiquette);
        this.autres.set(id, a);
        this._placerDansLaVisite(a, true);
      }
      a.mode = m.mode;
      a.chapitre = m.chapitre;
    }
    for (const [id, a] of this.autres) {
      if (presents.has(id)) continue;
      this.peuple.retirerHumain(a.index);
      a.etiquette.remove();
      this.autres.delete(id);
    }
    const n = presents.size + 1;
    this.compteur.querySelector(".presence-nombre").textContent = String(n);
    this.compteur.querySelector(".presence-texte").textContent = this.langue === "en" ? (n > 1 ? "online" : "online (you)") : (n > 1 ? "en ligne" : "en ligne (toi)");
  }

  _placerDansLaVisite(a, immediat = false) {
    // Pendant la visite guidée, les visiteurs se rassemblent en demi-cercle près du guide de leur chapitre
    const centre = this.guides[a.chapitre] || this.guides[1];
    if (!centre) return;
    const rang = [...this.autres.values()].filter((b) => b.mode === "visite" && b.chapitre === a.chapitre).indexOf(a);
    const angle = 0.6 + (rang % 7) * 0.45, rayon = 2.6 + Math.floor(rang / 7) * 1.2;
    a.cible = new THREE.Vector3(centre.x + Math.cos(angle) * rayon, centre.y, centre.z + Math.sin(angle) * rayon);
    a.cap = Math.atan2(centre.x - a.cible.x, centre.z - a.cible.z);
    if (immediat) this.peuple.humains[a.index].pos.copy(a.cible);
  }

  _position(p) {
    const a = this.autres.get(p.id);
    if (!a) return;
    a.mode = "libre";
    a.cible = new THREE.Vector3(p.p[0], p.p[1], p.p[2]);
    a.cap = p.c;
  }

  envoyer(texte) {
    texte = (texte || "").replace(/\s+/g, " ").trim().slice(0, LONGUEUR_MAX);
    const maintenant = Date.now();
    if (!texte || !this.canal || !this.pret) return;
    if (maintenant - this.dernierMessage < INTERVALLE_MESSAGES) return;
    this.dernierMessage = maintenant;
    this.canal.send({ type: "broadcast", event: "chat", payload: { id: this.id, numero: this.numero, texte } });
    this._ajouterMessage(this.numero, texte, true);
    this.saisie.value = "";
  }

  _recevoir(p) {
    if (!p || typeof p.texte !== "string" || this.masques.has(p.id)) return;
    const texte = p.texte.replace(/\s+/g, " ").trim().slice(0, LONGUEUR_MAX);
    if (!texte) return;
    this._ajouterMessage(p.numero, texte, false, p.id);
    const a = this.autres.get(p.id);
    if (a) {
      a.etiquette.querySelector(".etiquette-message").textContent = texte;
      a.finMessage = performance.now() + 7000;
      a.etiquette.classList.add("avec-message");
    }
  }

  _ajouterMessage(numero, texte, moi, id) {
    const li = document.createElement("li");
    li.className = moi ? "moi" : "";
    const qui = document.createElement("span");
    qui.className = "chat-qui";
    qui.textContent = moi ? (this.langue === "en" ? "You" : "Toi") : this.nom(numero);
    const quoi = document.createElement("span");
    quoi.className = "chat-texte";
    quoi.textContent = texte;
    li.append(qui, quoi);
    if (!moi && id) {
      const masquer = document.createElement("button");
      masquer.type = "button";
      masquer.className = "chat-masquer";
      masquer.textContent = this.langue === "en" ? "Mute" : "Masquer";
      masquer.addEventListener("click", () => {
        this.masques.add(id);
        [...this.liste.querySelectorAll(`[data-auteur="${id}"]`)].forEach((n) => n.remove());
      });
      li.dataset.auteur = id;
      li.append(masquer);
    }
    this.liste.append(li);
    while (this.liste.children.length > 60) this.liste.firstChild.remove();
    this.liste.scrollTop = this.liste.scrollHeight;
  }

  /* Appelé à chaque image : ce que je fais, et où sont les autres */
  maj(dt, moi) {
    if (!this.canal) return;
    const maintenant = performance.now();
    // Rien n'est envoyé avant que le canal soit ouvert (SUBSCRIBED) : l'annonce est refaite à l'ouverture
    if (this.pret && (moi.mode !== this.etat.mode || moi.chapitre !== this.etat.chapitre)) {
      this.etat.mode = moi.mode;
      this.etat.chapitre = moi.chapitre;
      this._annoncer();
    }
    // Positions : seulement quand le canal est ouvert (sinon la bibliothèque passerait par des requêtes HTTP)
    if (moi.mode === "libre" && this.pret && maintenant - this.derniereEnvoi > FREQUENCE_POSITIONS) {
      this.derniereEnvoi = maintenant;
      const p = moi.pos;
      this.canal.send({ type: "broadcast", event: "pos", payload: { id: this.id, p: [+p.x.toFixed(2), +p.y.toFixed(2), +p.z.toFixed(2)], c: +moi.cap.toFixed(2) } });
    }
    const largeur = window.innerWidth, hauteur = window.innerHeight;
    for (const a of this.autres.values()) {
      const h = this.peuple.humains[a.index];
      if (!h) continue;
      if (a.mode === "visite") this._placerDansLaVisite(a);
      if (a.cible) {
        const d = h.pos.distanceTo(a.cible);
        h.pos.lerp(a.cible, Math.min(1, dt * (d > 20 ? 50 : 6)));
        if (d > 0.08) {
          h.anim = "marche";
          h.phase += dt * Math.min(8, d * 6);
          h.cap = Math.atan2(a.cible.x - h.pos.x, a.cible.z - h.pos.z) || a.cap;
        } else {
          h.anim = "repos";
          h.cap += ((a.cap - h.cap + Math.PI) % (2 * Math.PI) - Math.PI) * Math.min(1, dt * 4);
        }
      }
      // Étiquette au-dessus de la tête
      this._v.set(h.pos.x, h.pos.y + 2.15, h.pos.z).project(this.camera);
      const visible = this._v.z < 1 && Math.abs(this._v.x) < 1.1 && Math.abs(this._v.y) < 1.1 && h.pos.distanceTo(this.camera.position) < 45;
      a.etiquette.style.opacity = visible ? "1" : "0";
      if (visible) a.etiquette.style.transform = `translate(${((this._v.x + 1) / 2 * largeur).toFixed(0)}px, ${((1 - this._v.y) / 2 * hauteur).toFixed(0)}px) translate(-50%, -100%)`;
      if (a.finMessage && maintenant > a.finMessage) { a.finMessage = 0; a.etiquette.classList.remove("avec-message"); }
    }
  }
}
