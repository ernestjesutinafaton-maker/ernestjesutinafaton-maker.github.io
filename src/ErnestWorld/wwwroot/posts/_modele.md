---
title: Titre de l'article
date: 2026-12-01
summary: Une ou deux phrases qui donnent envie de lire.
tags: [projet, csharp]
draft: true
---

<!--
  MODÈLE D'ARTICLE (ce fichier commence par « _ » : il n'est jamais publié)

  1. Copie ce fichier dans le même dossier et renomme-le, par exemple « mon-article.md ».
     Le nom du fichier devient l'adresse : /journal/mon-article
     (minuscules, chiffres et tirets uniquement).
  2. Remplis l'en-tête ci-dessus. « title » et « date » (AAAA-MM-JJ) sont obligatoires.
  3. Écris en Markdown sous l'en-tête.
  4. Passe « draft » à false (ou supprime la ligne) pour publier.
  5. Lance le générateur depuis la racine du dépôt :
       dotnet run --project tools/ErnestWorld.Generator
     Il vérifie l'article et met à jour la liste, le flux RSS et le plan du site.
-->

## Un intertitre

Du texte, du **gras**, de l'*italique*, des [liens](https://example.com).

- une liste
- à puces

```csharp
Console.WriteLine("Du code, avec coloration");
```
