# Le Monde d'Ernest

[![Déploiement](https://github.com/ernestjesutinafaton-maker/ernestjesutinafaton-maker.github.io/actions/workflows/deploy.yml/badge.svg)](https://github.com/ernestjesutinafaton-maker/ernestjesutinafaton-maker.github.io/actions/workflows/deploy.yml)

Portfolio et blog d'Ernest Afaton, sous la forme d'une île en 3D à explorer.
Chaque bâtiment est une section : projets, compétences, formation, le Journal (blog) et la newsletter.
Le visiteur gagne de l'XP, monte de rang, affronte des boss et débloque des succès en explorant et en lisant.

**Site :** https://ernestjesutinafaton-maker.github.io

![Le Château, au centre de l'île : le panneau « À propos » ouvert à droite, le niveau en cours à gauche](docs/apercu.png)

> **In English:** my portfolio and blog, as a 3D game. Explore an island where every building is a part of my journey,
> fight 5 bosses in turn-based battles where questions about my projects are your attacks, and read my blog.
> Built with **C# (Blazor WebAssembly, .NET 10)**, **Three.js**, xUnit and GitHub Actions. **[Play it](https://ernestjesutinafaton-maker.github.io)**
>
> ⭐ Si le projet te plaît, une étoile sur GitHub m'aide beaucoup. If you like it, a star really helps!

## Technologies

| Partie | Technologie |
|---|---|
| Application | **C#** avec **Blazor WebAssembly** (.NET 10) : le C# s'exécute dans le navigateur |
| Règles du jeu | Bibliothèque C# testée : moteur de combat, boss et questions |
| Île en 3D | Three.js (WebGL), pilotée depuis le C# : ombres, bloom, contours, particules, ciel jour/nuit |
| Sons | Web Audio API : tous les sons sont synthétisés, aucun fichier audio |
| Blog | Articles en Markdown, transformés en HTML par Markdig |
| Générateur | Programme console C# : liste des articles, flux RSS, plan du site |
| Tests | xUnit |
| Hébergement | GitHub Pages, déployé par GitHub Actions |

## Organisation du dépôt

```
src/ErnestWorld/              Le site (Blazor WebAssembly)
  Components/World/           L'île : interface de jeu, quêtes, succès, visite guidée
  Components/Places/          Le contenu de chaque bâtiment (un fichier par lieu)
  Components/Blog/            Cartes d'articles
  Components/Shared/          Petits composants réutilisables (newsletter, liens…)
  Pages/                      Le Journal et la page d'article
  Data/                       La carte de l'île, les icônes, les règles du jeu (XP, niveaux, succès)
  Services/                   Progression, blog, newsletter, pont vers la 3D
  wwwroot/js/world.js         Le moteur 3D (Three.js)
  wwwroot/posts/              Les articles du Journal (Markdown)
  wwwroot/classique/          Version classique du portfolio, sans 3D
src/ErnestWorld.Content/      Lecture des articles (en-tête, temps de lecture), partagée
src/ErnestWorld.Game/         Règles du jeu : moteur de combat (Battle), boss et questions (Bestiary)
tools/ErnestWorld.Generator/  Générateur du Journal
tests/                        Tests unitaires (articles, combats, questions)
```

## Le jeu

- **Campagne en 5 niveaux** (`Data/Campaign.cs`) : chaque niveau demande de découvrir des lieux
  (ou de lire des articles), puis réveille son **boss**. Les lieux restent toujours visitables.
- **Boss** (`src/ErnestWorld.Game/Bestiary.cs`) : le Bug Rampant, l'Hydre Hors-Ligne, le Golem du Réseau,
  le Kraken du Code Legacy et le Dragon de la Dette Technique (boss final en deux phases).
- **Combats au tour par tour** (`Battle.cs`) : une bonne réponse frappe le boss, une mauvaise coûte un cœur.
  Les combos augmentent les dégâts (×1,5 puis ×2 en coup critique), les indices retirent deux mauvaises réponses.
- **Rangs** : l'XP fait monter de rang, et un rang élevé donne plus de cœurs et d'indices au combat.
- **Succès**, visite guidée, mode nuit, mini-carte, sons et ambiance (coupables d'un bouton).

Liens directs : `/?lieu=forge` ouvre un lieu, `/?combat=golem` lance un combat (si le boss est réveillé).

### Ajouter une question à un boss

Dans `Bestiary.cs`, ajouter une ligne `new("Question ?", "Bonne réponse", ["Faux 1", "Faux 2", "Faux 3"], "Explication.")`.
Le paramètre `HintPlace` indique le lieu de l'île où trouver la réponse, `Code` affiche un extrait de code,
et `Phase: 2` réserve la question à la phase enragée du boss final. Les tests vérifient que chaque question est bien formée.

## Lancer le site en local

Il faut le [SDK .NET 10](https://dotnet.microsoft.com/download).

```bash
dotnet run --project tools/ErnestWorld.Generator   # met à jour la liste des articles
dotnet run --project src/ErnestWorld               # lance le site, puis ouvrir l'adresse affichée
```

Tests : `dotnet test`

## Écrire un article

1. Copier `src/ErnestWorld/wwwroot/posts/_modele.md` dans le même dossier, par exemple sous le nom `mon-article.md`.
   Le nom du fichier devient l'adresse `/journal/mon-article` (minuscules, chiffres et tirets).
2. Remplir l'en-tête (`title` et `date` sont obligatoires) et écrire en Markdown.
3. Mettre `draft: false` (ou supprimer la ligne) pour publier.
4. Lancer le générateur : il vérifie l'article et met à jour la liste, le flux RSS et le plan du site.

Les fichiers qui commencent par `_` et les brouillons (`draft: true`) ne sont jamais publiés.

## Newsletter

Réglée dans `src/ErnestWorld/wwwroot/appsettings.json` :

- **`"Provider": "mailto"`** (par défaut) : le visiteur envoie un email pré-rempli à Ernest. Aucun compte nécessaire.
- **`"Provider": "buttondown"`** : les inscriptions vont dans une vraie liste [Buttondown](https://buttondown.com)
  (gratuit jusqu'à 100 abonnés), avec email de confirmation. Créer un compte, puis renseigner `"ButtondownUsername"`.

## Ajouter un lieu sur l'île

1. Créer le contenu du panneau dans `Components/Places/` (un fichier `.razor`).
2. L'ajouter à la liste de `Data/Island.cs`, avec sa position sur la grille hexagonale.
3. Ajouter son icône dans `Data/Icons.cs`.
4. Modéliser le bâtiment dans `wwwroot/js/world.js` (objet `BUILD`) et, si besoin, une route dans `ROADS`.

## Déploiement

Chaque envoi sur `main` lance `.github/workflows/deploy.yml` : tests, génération du Journal,
publication, puis mise en ligne sur GitHub Pages.
Dans les réglages du dépôt, *Pages* doit avoir comme source **GitHub Actions**.
