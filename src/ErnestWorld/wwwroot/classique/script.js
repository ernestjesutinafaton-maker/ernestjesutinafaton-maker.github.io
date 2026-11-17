/*
  PORTFOLIO D'ERNEST AFATON - script.js (version 3)
  Sans librairie :
  1. année du pied de page ;
  2. thème clair / sombre (mémorisé) ;
  3. menu mobile ;
  4. lien actif du menu et bordure de l'en-tête au défilement ;
  5. filtres des projets ;
  6. apparition des blocs au défilement ;
  7. copie de l'adresse email.
*/
"use strict";

document.documentElement.classList.add("js");

// ---------- 1. Année ----------
const annee = document.getElementById("annee");
if (annee) annee.textContent = new Date().getFullYear();

// ---------- 2. Thème ----------
const racine = document.documentElement;
const boutonTheme = document.getElementById("theme-toggle");
const prefereClair = window.matchMedia("(prefers-color-scheme: light)");

function themeActuel() {
  return racine.getAttribute("data-theme") || (prefereClair.matches ? "light" : "dark");
}

function majMetaTheme() {
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", themeActuel() === "light" ? "#faf9fe" : "#0b0a12");
}

if (boutonTheme) {
  boutonTheme.addEventListener("click", () => {
    const suivant = themeActuel() === "light" ? "dark" : "light";
    racine.setAttribute("data-theme", suivant);
    try { localStorage.setItem("theme", suivant); } catch (e) { /* stockage indisponible */ }
    majMetaTheme();
  });
}
majMetaTheme();

// ---------- 3. Menu mobile ----------
const boutonMenu = document.getElementById("menu-toggle");
const menu = document.getElementById("menu");

function fermerMenu() {
  if (!menu || !boutonMenu) return;
  menu.classList.remove("is-open");
  boutonMenu.setAttribute("aria-expanded", "false");
  boutonMenu.setAttribute("aria-label", "Ouvrir le menu");
}

if (boutonMenu && menu) {
  boutonMenu.addEventListener("click", () => {
    const ouvert = menu.classList.toggle("is-open");
    boutonMenu.setAttribute("aria-expanded", String(ouvert));
    boutonMenu.setAttribute("aria-label", ouvert ? "Fermer le menu" : "Ouvrir le menu");
  });
  menu.querySelectorAll("a").forEach((lien) => lien.addEventListener("click", fermerMenu));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") fermerMenu(); });
}

// ---------- 4. Lien actif + en-tête ----------
const entete = document.querySelector(".site-header");
const liensMenu = document.querySelectorAll(".nav a");
const sections = document.querySelectorAll("main section[id]");

function marquerActif(id) {
  liensMenu.forEach((lien) => {
    lien.classList.toggle("actif", lien.getAttribute("href") === "#" + id);
  });
}

window.addEventListener("scroll", () => {
  if (entete) entete.classList.toggle("is-scrolled", window.scrollY > 8);
}, { passive: true });

if ("IntersectionObserver" in window) {
  const obsSections = new IntersectionObserver((entrees) => {
    entrees.forEach((entree) => { if (entree.isIntersecting) marquerActif(entree.target.id); });
  }, { rootMargin: "-40% 0px -55% 0px" });
  sections.forEach((s) => obsSections.observe(s));
}

// ---------- 5. Filtres des projets ----------
const filtres = document.querySelectorAll(".filter");
const listeProjets = document.querySelector(".projects");
const projets = document.querySelectorAll(".project");

filtres.forEach((bouton) => {
  bouton.addEventListener("click", () => {
    const choix = bouton.dataset.filter;
    filtres.forEach((b) => {
      const actif = b === bouton;
      b.classList.toggle("is-active", actif);
      b.setAttribute("aria-pressed", String(actif));
    });
    projets.forEach((p) => {
      p.hidden = choix !== "tous" && p.dataset.cat !== choix;
      p.classList.add("is-visible");
    });
    if (listeProjets) listeProjets.classList.toggle("is-filtered", choix !== "tous");
  });
});

// ---------- 6. Apparition au défilement ----------
const blocs = document.querySelectorAll(".reveal");
if ("IntersectionObserver" in window) {
  const obsBlocs = new IntersectionObserver((entrees, obs) => {
    entrees.forEach((entree) => {
      if (entree.isIntersecting) {
        entree.target.classList.add("is-visible");
        obs.unobserve(entree.target);
      }
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
  blocs.forEach((b) => obsBlocs.observe(b));
} else {
  blocs.forEach((b) => b.classList.add("is-visible"));
}

// ---------- 7. Copier l'email ----------
const boutonCopie = document.getElementById("copy-mail");
if (boutonCopie) {
  const etiquette = boutonCopie.querySelector(".copy-label");
  boutonCopie.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(boutonCopie.dataset.mail);
      etiquette.textContent = "Copié !";
    } catch (e) {
      window.location.href = "mailto:" + boutonCopie.dataset.mail;
      return;
    }
    setTimeout(() => { etiquette.textContent = "Copier"; }, 2000);
  });
}
