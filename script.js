/*
  PORTFOLIO D'ERNEST AFATON - script.js

  Deux petites fonctions, sans librairie :
  1. mettre l'année courante dans le pied de page ;
  2. surligner dans le menu la section visible à l'écran.

  Références :
  - DOM : https://developer.mozilla.org/fr/docs/Web/API/Document_Object_Model
  - IntersectionObserver : https://developer.mozilla.org/fr/docs/Web/API/Intersection_Observer_API
*/

// "use strict" : signale les erreurs courantes
// https://developer.mozilla.org/fr/docs/Web/JavaScript/Reference/Strict_mode
"use strict";

// ---------- 1. Année du pied de page ----------
// getElementById : https://developer.mozilla.org/fr/docs/Web/API/Document/getElementById
// getFullYear    : https://developer.mozilla.org/fr/docs/Web/JavaScript/Reference/Global_Objects/Date/getFullYear
const annee = document.getElementById("annee");
if (annee) {
  annee.textContent = new Date().getFullYear();
}

// ---------- 2. Lien du menu actif ----------
// querySelectorAll renvoie tous les éléments correspondant au sélecteur CSS :
// https://developer.mozilla.org/fr/docs/Web/API/Document/querySelectorAll
const liensMenu = document.querySelectorAll(".site-header nav a");
const sections = document.querySelectorAll("main section[id]");

/**
 * Applique la classe "actif" au lien du menu dont l'ancre correspond à la section donnée.
 * classList.toggle(nom, condition) : https://developer.mozilla.org/fr/docs/Web/API/Element/classList
 */
function marquerActif(idSection) {
  liensMenu.forEach((lien) => {
    lien.classList.toggle("actif", lien.getAttribute("href") === "#" + idSection);
  });
}

// IntersectionObserver prévient quand un élément entre ou sort de la zone visible.
// On ne le lance que si le navigateur le gère (très répandu aujourd'hui).
if ("IntersectionObserver" in window) {
  const observateur = new IntersectionObserver(
    (entrees) => {
      entrees.forEach((entree) => {
        if (entree.isIntersecting) {
          marquerActif(entree.target.id);
        }
      });
    },
    {
      // La section est "visible" quand elle traverse la bande centrale de l'écran
      // (rootMargin : https://developer.mozilla.org/fr/docs/Web/API/IntersectionObserver/rootMargin)
      rootMargin: "-40% 0px -55% 0px",
    }
  );

  sections.forEach((section) => observateur.observe(section));
}
