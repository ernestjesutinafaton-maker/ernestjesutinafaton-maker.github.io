---
title: "Boutik : une caisse qui marche sans internet"
date: 2026-11-12
summary: Comment construire une application de caisse qui continue de fonctionner quand le réseau tombe, puis se resynchronise toute seule.
tags: [projet, mobile, hors-ligne]
---

Dans beaucoup de boutiques, la connexion internet n'est pas garantie. Une caisse qui se bloque dès que le réseau tombe, c'est une vente perdue.

**Boutik** part de ce constat. C'est une application de caisse, de stock et de ventes à crédit qui fonctionne **d'abord sans internet**, puis se synchronise dès que la connexion revient.

## Ce que fait l'application

- encaisser une vente et imprimer un ticket ;
- suivre le stock en temps réel ;
- gérer les ventes à crédit, c'est-à-dire ce que chaque client doit encore ;
- tourner sur **Android, iPhone et ordinateur** avec la même base de code.

Elle est aujourd'hui en test chez quatre commerces.

## L'idée clé : la base de données est sur l'appareil

Une application classique interroge un serveur à chaque action. Boutik fait l'inverse : chaque appareil garde **sa propre base de données locale** (SQLite). Toutes les opérations, comme une vente ou une entrée de stock, y sont écrites immédiatement. L'interface ne dépend donc jamais du réseau.

La synchronisation est confiée à **PowerSync**. Quand le réseau est disponible, les modifications locales partent vers le serveur (**Supabase**, basé sur PostgreSQL), et celles des autres appareils redescendent. Quand il ne l'est pas, elles attendent simplement leur tour.

## Une seule base de code, trois plateformes

- **React Native avec Expo** pour Android et iPhone ;
- **Tauri** pour la version ordinateur ;
- une version web pour le reste.

Le tout est écrit en **TypeScript** et testé avec Vitest.

## Ce que ce projet m'a appris

Penser « hors ligne d'abord » change toute la conception. On ne se demande plus *« que se passe-t-il si le serveur répond ? »* mais *« que se passe-t-il si deux appareils modifient la même donnée sans se voir ? »*.

C'est cette question qui rend le sujet passionnant.

Tu peux découvrir Boutik sur [son site](https://boutik-services.vercel.app) ou sur [sa page de présentation](https://github.com/ernestjesutinafaton-maker/Boutik-presentation).
