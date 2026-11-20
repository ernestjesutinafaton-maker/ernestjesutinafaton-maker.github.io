/*
  Ce que disent les habitants du royaume, en français et en anglais, et la boîte de dialogue.

  Règle : les personnages inventés (le forgeron du C#, la bibliothécaire, l'intendante, le gardien du
  phare...) parlent librement des vrais projets d'Ernest. Le coach de l'atelier représente une vraie
  personne : il ne dit que des faits vérifiables, jamais un avis inventé. Pour lui faire dire ses propres
  mots, il faut les lui demander (évaluation de stage, recommandation) et les recopier ici avec son accord.

  Chaque personnage : nom, role (petite étiquette), bulle (une phrase courte, pendant la visite guidée),
  lignes (le dialogue complet, en mode libre).
*/

export const DIALOGUES = {
  capitaine: {
    fr: {
      nom: "Le capitaine de la garde", role: "Porte du royaume",
      bulle: "Bienvenue au royaume d'Ernest, voyageur !",
      lignes: [
        "Halte, voyageur ! Bienvenue au royaume d'Ernest.",
        "Chaque bâtiment garde un morceau de son parcours : l'atelier, la bibliothèque des guildes, la grande salle du château… et le phare, tout au bout.",
        "Ernest ? Étudiant en 2e année de Bachelor Informatique à l'EPSI Lyon, parcours Conception et Développement. Il prépare aussi le BTS SIO, option SLAM.",
        "Allez, entrez. Et parlez aux habitants : ils le connaissent bien.",
      ],
    },
    en: {
      nom: "The captain of the guard", role: "Kingdom gate",
      bulle: "Welcome to Ernest's kingdom, traveller!",
      lignes: [
        "Halt, traveller! Welcome to Ernest's kingdom.",
        "Every building keeps a piece of his journey: the workshop, the guild library, the castle's great hall… and the lighthouse, at the very end.",
        "Ernest? A second-year Computer Science Bachelor's student at EPSI Lyon, in the software design and development track. He's also preparing the BTS SIO, SLAM option.",
        "Go on in. And talk to the townsfolk: they know him well.",
      ],
    },
  },
  coach: {
    fr: {
      nom: "Le coach de l'atelier", role: "MyDil · Digital Innovation Lab",
      bulle: "InfraHub, livrée en deux semaines.",
      lignes: [
        "Ici, c'est l'atelier de MyDil, le Digital Innovation Lab.",
        "Ernest y a été développeur stagiaire et assistant Fablab, d'avril à juin 2026.",
        "En deux semaines, il a livré InfraHub : la gestion des tickets étudiants, avec des droits par rôle et l'escalade automatique des incidents.",
        "Cette baie, là-bas : c'est le NAS qu'il a conçu, déployé et administré seul. 99,9 % de disponibilité mesurée.",
        "Il a aussi été Scrum Master sur 4 projets collectifs. Le tableau au mur en garde la trace.",
      ],
    },
    en: {
      nom: "The workshop coach", role: "MyDil · Digital Innovation Lab",
      bulle: "InfraHub, delivered in two weeks.",
      lignes: [
        "This is MyDil's workshop, the Digital Innovation Lab.",
        "Ernest was a developer intern and Fablab assistant here, from April to June 2026.",
        "In two weeks he delivered InfraHub: student ticket management, with role-based access and automatic incident escalation.",
        "That rack over there is the NAS he designed, deployed and ran on his own. 99.9% measured uptime.",
        "He was also Scrum Master on 4 team projects. The board on the wall keeps track of it.",
      ],
    },
  },
  forgeron: {
    fr: {
      nom: "Le forgeron du C#", role: "La forge",
      bulle: "Avec Ernest, on a forgé tout un jeu en C#.",
      lignes: [
        "Le C#, c'est mon métal. Avec Ernest, on en a forgé tout un jeu : le Monde d'Ernest.",
        "Du C# qui tourne dans le navigateur, grâce à Blazor WebAssembly. Pas une ligne de serveur.",
        "Le moteur de combat, les 5 boss, les 49 questions… et des tests xUnit, pour que rien ne casse à la trempe.",
        "À chaque envoi, GitHub Actions teste et remet tout en ligne. Va donc y jouer : c'est la « Version jeu », en haut de la page.",
      ],
    },
    en: {
      nom: "The C# blacksmith", role: "The forge",
      bulle: "Ernest and I forged a whole game in C#.",
      lignes: [
        "C# is my metal. Ernest and I forged a whole game out of it: Ernest's World.",
        "C# running in the browser, thanks to Blazor WebAssembly. Not a single line of server code.",
        "The battle engine, the 5 bosses, the 49 questions… and xUnit tests, so nothing cracks when it's quenched.",
        "Every push, GitHub Actions tests it and puts it back online. Go and play: it's the \"Game version\", at the top of the page.",
      ],
    },
  },
  bibliothecaire: {
    fr: {
      nom: "La bibliothécaire des guildes", role: "Bibliothèque des guildes",
      bulle: "Sept bannières, sept familles de compétences.",
      lignes: [
        "Sept bannières, sept familles de compétences. Laisse-moi te les présenter.",
        "Développement web : Next.js, React, Symfony, Laravel, Three.js. Et le C# avec .NET : Blazor WebAssembly, xUnit.",
        "Le mobile : React Native, Expo, Tauri, avec la synchronisation hors connexion. Le back-end : PostgreSQL, Supabase, Node.js, FastAPI.",
        "Systèmes et réseaux : Linux, Active Directory, Docker, la haute disponibilité HSRP et VRRP.",
        "L'IoT : Raspberry Pi, Arduino, NFC. Et la méthode : Scrum, Git, GitHub Actions, les tests unitaires.",
      ],
    },
    en: {
      nom: "The guild librarian", role: "Guild library",
      bulle: "Seven banners, seven skill families.",
      lignes: [
        "Seven banners, seven skill families. Let me introduce them.",
        "Web development: Next.js, React, Symfony, Laravel, Three.js. And C# with .NET: Blazor WebAssembly, xUnit.",
        "Mobile: React Native, Expo, Tauri, with offline sync. Back end: PostgreSQL, Supabase, Node.js, FastAPI.",
        "Systems and networks: Linux, Active Directory, Docker, HSRP and VRRP high availability.",
        "IoT: Raspberry Pi, Arduino, NFC. And the method: Scrum, Git, GitHub Actions, unit tests.",
      ],
    },
  },
  intendante: {
    fr: {
      nom: "L'intendante du château", role: "La grande salle",
      bulle: "Trois cristaux, trois projets dont il est fier.",
      lignes: [
        "Ces trois cristaux, ce sont les projets dont Ernest est le plus fier.",
        "Le vert, c'est ÉcoPay : l'encaissement des frais de scolarité pour les écoles privées d'Afrique de l'Ouest, avec Mobile Money. En test avec 5 testeurs.",
        "Le violet, c'est Boutik : caisse, stock et ventes à crédit pour les commerces, même sans connexion. En test dans 4 commerces.",
        "Le rose, c'est le Monde d'Ernest, la version jeu de ce portfolio. Les seize projets sont dans le portfolio classique.",
      ],
    },
    en: {
      nom: "The castle steward", role: "The great hall",
      bulle: "Three crystals, three projects he's proud of.",
      lignes: [
        "These three crystals are the projects Ernest is proudest of.",
        "The green one is ÉcoPay: school-fee collection for private schools in West Africa, with Mobile Money. In testing with 5 testers.",
        "The purple one is Boutik: checkout, stock and credit sales for small shops, even offline. In testing in 4 shops.",
        "The pink one is Ernest's World, the game version of this portfolio. All sixteen projects are in the classic portfolio.",
      ],
    },
  },
  gardien: {
    fr: {
      nom: "Le gardien du phare", role: "Le phare",
      bulle: "Un stage à proposer ? C'est ici.",
      lignes: [
        "D'ici, on voit tout le royaume. Et le phare veille toute la nuit.",
        "Ernest cherche un stage de 4 à 5 semaines, en développement ou en systèmes et réseaux.",
        "Le plus simple pour le joindre : l'email ou LinkedIn. Les liens sont juste là, dans le panneau.",
      ],
    },
    en: {
      nom: "The lighthouse keeper", role: "The lighthouse",
      bulle: "An internship to offer? This is the place.",
      lignes: [
        "From up here you can see the whole kingdom. And the lighthouse keeps watch all night.",
        "Ernest is looking for a 4 to 5 week internship, in software development or systems and networks.",
        "The easiest way to reach him: email or LinkedIn. The links are right there, in the panel.",
      ],
    },
  },
  meunier: {
    fr: {
      nom: "Le meunier", role: "Le moulin",
      bulle: "Mon moulin tourne au vent, Ernest fait tourner des Raspberry Pi.",
      lignes: [
        "Mon moulin tourne au vent. Ernest, lui, fait tourner des Raspberry Pi.",
        "Au Workshop National IoT de l'EPSI, son équipe a fini deuxième avec une boîte à lecture NFC.",
        "Des tags lus par un Raspberry Pi, des servomoteurs pilotés par Arduino, une interface Tkinter au démarrage. Du beau travail.",
      ],
    },
    en: {
      nom: "The miller", role: "The windmill",
      bulle: "My mill turns in the wind; Ernest makes Raspberry Pis turn.",
      lignes: [
        "My mill turns in the wind. Ernest makes Raspberry Pis turn.",
        "At EPSI's National IoT Workshop, his team came second with an NFC reading box.",
        "Tags read by a Raspberry Pi, servo motors driven by an Arduino, a Tkinter interface at startup. Fine work.",
      ],
    },
  },
  aubergiste: {
    fr: {
      nom: "L'aubergiste", role: "L'auberge",
      bulle: "Ici on raconte des histoires ; Ernest, lui, les écrit.",
      lignes: [
        "Ici, on raconte des histoires au coin du feu. Ernest, lui, les écrit.",
        "Dans son Journal, il explique comment ses projets marchent et ce qu'il en a appris.",
        "Tu le trouveras sur son site, à la rubrique Journal. Il y a même un flux RSS.",
      ],
    },
    en: {
      nom: "The innkeeper", role: "The inn",
      bulle: "We tell stories here; Ernest writes his down.",
      lignes: [
        "Here we tell stories by the fire. Ernest writes his down.",
        "In his Journal he explains how his projects work and what he learned from them.",
        "You'll find it on his site, under Journal. There's even an RSS feed.",
      ],
    },
  },
};

// Petites phrases des passants et des gardes (mode libre)
export const PASSANTS = {
  fr: ["Belle soirée pour une promenade !", "Le marché ferme bientôt.", "Tu as vu le phare ? Il tourne toute la nuit.",
       "On dit qu'Ernest a forgé un jeu entier en C#.", "La cascade, au sud-ouest… il faut la voir au couchant.",
       "Bonsoir, voyageur.", "Les cristaux de la grande salle brillent plus fort ce soir."],
  en: ["Lovely evening for a walk!", "The market closes soon.", "Have you seen the lighthouse? It turns all night.",
       "They say Ernest forged a whole game in C#.", "The waterfall, to the south-west… you must see it at sunset.",
       "Good evening, traveller.", "The crystals in the great hall shine brighter tonight."],
};
export const GARDES = {
  fr: ["Rien à signaler sur les remparts.", "Circulez, circulez.", "Belle vue d'ici, n'est-ce pas ?"],
  en: ["All quiet on the walls.", "Move along, move along.", "Fine view from up here, isn't it?"],
};

/* =========================================================================
   Boîte de dialogue (mode libre) et bulles (visite guidée)
   ========================================================================= */

export class Dialogue {
  constructor(langue) {
    this.langue = langue;
    this.boite = document.querySelector(".dialogue");
    this.nom = this.boite.querySelector(".dialogue-nom");
    this.role = this.boite.querySelector(".dialogue-role");
    this.texte = this.boite.querySelector(".dialogue-texte");
    this.compteur = this.boite.querySelector(".dialogue-compteur");
    this.suivant = this.boite.querySelector(".dialogue-suivant");
    this.fermer = this.boite.querySelector(".dialogue-fermer");
    this.bulle = document.querySelector(".bulle");
    this.lignes = [];
    this.indice = 0;
    this.ouvert = false;
    this.suivant.addEventListener("click", () => this.avancer());
    this.fermer.addEventListener("click", () => this.clore());
  }

  ouvrir(cle, phrase) {
    const d = DIALOGUES[cle]?.[this.langue];
    if (d) {
      this.nom.textContent = d.nom;
      this.role.textContent = d.role;
      this.lignes = d.lignes;
    } else {
      this.nom.textContent = this.langue === "en" ? "A townsperson" : "Un habitant";
      this.role.textContent = this.langue === "en" ? "Ernest's kingdom" : "Royaume d'Ernest";
      this.lignes = [phrase];
    }
    this.indice = 0;
    this.ouvert = true;
    this.boite.hidden = false;
    this.afficher();
    this.suivant.focus({ preventScroll: true });
  }

  afficher() {
    this.texte.textContent = this.lignes[this.indice];
    this.compteur.textContent = `${this.indice + 1} / ${this.lignes.length}`;
    const fin = this.indice >= this.lignes.length - 1;
    this.suivant.textContent = fin ? (this.langue === "en" ? "Close" : "Fermer") : (this.langue === "en" ? "Next" : "Suivant");
  }

  avancer() {
    if (this.indice < this.lignes.length - 1) {
      this.indice++;
      this.afficher();
    } else {
      this.clore();
    }
  }

  clore() {
    this.ouvert = false;
    this.boite.hidden = true;
  }

  /* Bulle accrochée au-dessus d'un personnage pendant la visite guidée (x, y : pixels à l'écran) */
  montrerBulle(cle, x, y, opacite) {
    const d = DIALOGUES[cle]?.[this.langue];
    if (!d || opacite < 0.02) {
      this.bulle.style.opacity = "0";
      return;
    }
    if (this.bulle.dataset.cle !== cle + this.langue) {
      this.bulle.dataset.cle = cle + this.langue;
      this.bulle.querySelector(".bulle-nom").textContent = d.nom;
      this.bulle.querySelector(".bulle-texte").textContent = d.bulle;
    }
    this.bulle.style.opacity = opacite.toFixed(3);
    this.bulle.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px) translate(-50%, -100%)`;
  }
}
