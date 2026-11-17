---
title: Bienvenue sur mon île
date: 2026-11-17
summary: Pourquoi mon portfolio est devenu une île en 3D à explorer, et comment elle est construite.
tags: [portfolio, csharp, 3d]
---

Un CV se lit en trente secondes. Je voulais que mon portfolio se **visite**.

Alors j'en ai fait une île. Chaque bâtiment raconte une partie de mon parcours : la Forge pour mes compétences, l'Académie pour ma formation, la Banque pour ÉcoPay, le Marché pour Boutik… Et ce Journal, rangé au Scriptorium, où j'écris sur ce que je construis et ce que j'apprends.

## Qui suis-je ?

Je m'appelle Ernest Afaton. Je suis en 2<sup>e</sup> année de Bachelor Informatique à l'EPSI Lyon, parcours Conception et Développement, et je prépare en parallèle le BTS SIO option SLAM.

J'aime comprendre comment les choses fonctionnent de l'intérieur. Ça m'a amené à écrire un framework PHP sans librairie, à construire une application de caisse qui marche sans internet, et à transformer un ordinateur de l'école en serveur NAS.

## Une île qui se joue

Le site emprunte quelques idées aux jeux de stratégie :

- **les quêtes** : chaque lieu découvert coche une quête, et la dernière t'attend au Phare ;
- **l'expérience** : découvrir un lieu, lire un article ou t'abonner à la newsletter te fait gagner de l'XP et monter de niveau ;
- **les succès** : certains se débloquent en explorant, d'autres en lisant… et un se mérite la nuit.

Ta progression reste dans ton navigateur. Rien n'est envoyé nulle part.

## Sous le capot

Le site est écrit en **C#** avec **Blazor WebAssembly** : le code C# s'exécute directement dans ton navigateur. Il gère les quêtes, l'XP, les succès, la newsletter et ce Journal, dont les articles sont de simples fichiers Markdown.

L'île elle-même est dessinée avec **Three.js**. Chaque tuile hexagonale, chaque arbre et chaque bâtiment sont générés par du code : il n'y a aucun modèle 3D téléchargé.

Un petit programme C# lit les articles avant chaque mise en ligne. Il vérifie leur en-tête, puis produit la liste des articles, le flux RSS et le plan du site.

## Et maintenant ?

Explore l'île, lis un article ou deux, et si tu veux suivre la suite, passe par le **Pigeonnier** pour t'abonner à la newsletter.

Et si tu cherches un stagiaire, le Phare est toujours allumé.
