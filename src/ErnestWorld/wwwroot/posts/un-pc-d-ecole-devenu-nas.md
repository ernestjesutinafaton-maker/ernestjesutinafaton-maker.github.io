---
title: Un PC d'école devenu serveur NAS
date: 2026-11-05
summary: Stockage, cloud privé et accès à distance sécurisé sur un simple ordinateur, avec OpenMediaVault, Docker, Nextcloud et Tailscale.
tags: [infrastructure, docker, réseau]
---

Le point de départ était simple : un ordinateur de l'école inutilisé. L'objectif l'était un peu moins. Il fallait en faire un **serveur NAS** pour stocker et partager des fichiers, avec un cloud privé et un accès à distance sécurisé.

## La pile choisie

| Rôle | Outil |
|---|---|
| Système du NAS | OpenMediaVault |
| Isolation des services | Docker et Docker Compose |
| Cloud privé (type Google Drive) | Nextcloud |
| Accès à distance chiffré | Tailscale (WireGuard) |

## Étape 1 : un vrai système de NAS

J'ai installé **OpenMediaVault**, une distribution Linux pensée pour le stockage en réseau. Elle gère les disques, les partages de fichiers et les utilisateurs depuis une interface web.

## Étape 2 : un conteneur par service

Plutôt que d'installer chaque logiciel directement sur le système, je les ai placés dans des **conteneurs Docker**, décrits dans un fichier Docker Compose.

L'avantage : chaque service est isolé. On peut en mettre un à jour, le redémarrer ou le redéployer sans toucher aux autres. En cas d'incident, on reconstruit vite.

## Étape 3 : un cloud privé

**Nextcloud** apporte ce qu'on attend d'un Google Drive : accès aux fichiers depuis un navigateur ou un téléphone, partage de dossiers et synchronisation. La différence, c'est que les données restent sur notre propre machine.

## Étape 4 : l'accès à distance sans ouvrir de port

C'est la partie la plus intéressante côté sécurité. Pour accéder au NAS depuis l'extérieur, la solution classique consiste à ouvrir un port sur le routeur, et donc à exposer le serveur à tout internet.

Avec **Tailscale**, qui repose sur le protocole WireGuard, les appareils autorisés rejoignent un réseau privé chiffré. Le NAS reste invisible depuis internet, et aucun port n'est ouvert.

## Le résultat

- des fichiers centralisés au même endroit ;
- un accès distant chiffré ;
- des services isolés, faciles à mettre à jour.

Le serveur est actuellement en pause. Son redéploiement sera le sujet d'un prochain article : abonne-toi au Pigeonnier pour ne pas le rater.
