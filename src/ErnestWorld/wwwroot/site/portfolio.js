/* =========================================================================
   Portfolio d'Ernest Afaton · page d'accueil
   Langue (français / anglais), thème, menu, filtres, copie de l'email,
   apparition au défilement et derniers articles du Journal.
   Le français est écrit dans la page ; l'anglais est dans le dictionnaire EN ci-dessous.
   ========================================================================= */
(function () {
  "use strict";

  var root = document.documentElement;
  var LANG_KEY = "ernest-lang"; // même réglage que la version jeu

  var EN = {
    "meta.title": "Ernest Afaton · Developer portfolio",
    "meta.description": "Portfolio of Ernest Afaton, second-year Computer Science Bachelor's student at EPSI Lyon (France): web and mobile apps, systems and networks, IoT. Looking for a 4 to 5 week internship. Includes a 3D game version.",

    "skip": "Skip to content",
    "logo.label": "Back to the top of the page",
    "nav.label": "Main navigation",
    "nav.about": "About",
    "nav.skills": "Skills",
    "nav.projects": "Projects",
    "nav.certs": "Certifications",
    "nav.journal": "Journal",
    "nav.contact": "Contact",
    "theme.label": "Switch theme",
    "header.play": "Play",
    "menu.label": "Open the menu",

    "hero.status": "Available for a 4 to 5 week internship",
    "hero.hello": "Hi, I'm",
    "hero.role": "Web and mobile developer · Systems and networks · IoT",
    "hero.lead": "Second-year Computer Science Bachelor's student at EPSI Lyon, France. I build complete apps, set up infrastructure and prototype connected devices. My portfolio also exists as a game: a 3D island to explore.",
    "hero.play": "Play my portfolio",
    "hero.projects": "See my projects",
    "hero.new3dBadge": "New",
    "hero.new3d": "The 3D island, modeled in Blender: explore it by scrolling",
    "stats.label": "A few numbers",
    "stats.projects": "projects",
    "stats.certs": "certificates earned",
    "stats.iotNum": "2<sup>nd</sup>",
    "stats.iot": "National IoT Workshop",
    "stats.nasNum": "99.9%",
    "stats.nas": "NAS uptime during my internship",

    "game.cardLabel": "Play my portfolio: open the 3D island",
    "game.name": "Ernest's World",
    "game.badge": "game version",
    "game.alt": "The 3D island of Ernest's portfolio, seen from above",
    "game.img": "site/ile-en.webp",
    "game.caption": "My portfolio is also a game",
    "game.places": "16 places",
    "game.bosses": "5 bosses",
    "game.questions": "49 questions",
    "game.achievements": "16 achievements",
    "toast.ach": "Achievement unlocked",
    "toast.achText": "Cartographer · +40 XP",
    "toast.boss": "Boss awakened",
    "toast.bossText": "The Technical Debt Dragon",

    "gameSec.eyebrow": "Ernest's World",
    "gameSec.title": "Rather explore than read?",
    "gameSec.sub": "Everything on this page also exists as a game, written in C# with Blazor and Three.js.",
    "step1.title": "Explore the island",
    "step1.text": "16 buildings: each place is a project, a skill or a step of my journey.",
    "step2.title": "Fight 5 bosses",
    "step2.text": "Questions about my projects and about code, with hearts, combos and critical hits.",
    "step3.title": "Unlock the final quest",
    "step3.text": "16 achievements, 8 ranks to earn, and a lighthouse where you can recruit me at the end.",
    "gameSec.cta": "Start the game",
    "gameSec.note": "No sign-up · works on desktop and mobile · progress saved in your browser",

    "about.eyebrow": "01 · About",
    "about.title": "Understand how things work, then build them.",
    "about.p1": "I'm in the second year of a Computer Science Bachelor's at EPSI Lyon, in the <strong>software design and development</strong> track, and I'm also preparing the <strong>BTS SIO, SLAM option</strong> (a French national IT diploma, 2027 exams).",
    "about.p2": "I have built several complete apps on my own (web, mobile, SaaS), and during my internship I developed a business platform and deployed a full system infrastructure by myself.",
    "about.p3": "I like going down the layers: from a PHP framework written without any library to a containerized NAS server reachable from anywhere. I'm looking for an internship to put these skills to work for a team.",
    "facts.label": "At a glance",
    "facts.title": "At a glance",
    "facts.edu": "Education",
    "facts.eduV": "CS Bachelor's, year 2 · EPSI Lyon",
    "facts.track": "Track",
    "facts.trackV": "Software design and development",
    "facts.dipl": "Diploma",
    "facts.diplV": "BTS SIO SLAM · 2027 exams",
    "facts.seek": "Looking for",
    "facts.seekV": "A 4 to 5 week internship",
    "facts.lang": "Languages",
    "facts.langV": "French (native) · English (B2)",
    "facts.city": "City",

    "skills.eyebrow": "02 · Skills",
    "skills.title": "From code to infrastructure.",
    "sk.web": "Web development",
    "sk.webT": "Complete apps, from back end to interface.",
    "sk.cs": "C# and .NET",
    "sk.csT": "The game version of this portfolio is written in C# with Blazor WebAssembly.",
    "sk.mobile": "Mobile and cross-platform",
    "sk.mobileT": "Android, iPhone and desktop, with offline mode.",
    "sk.sync": "Sync",
    "sk.back": "Back end and data",
    "sk.backT": "SQL databases, REST APIs, authentication, payments.",
    "sk.net": "Systems and networks",
    "sk.netT": "Directory services, high availability, monitoring, containers.",
    "sk.iot": "IoT and embedded",
    "sk.iotT": "Sensors, boards and physical prototyping.",
    "sk.print": "3D printing",
    "sk.tools": "Methods and tools",
    "sk.toolsT": "Teamwork, quality and continuous delivery.",
    "sk.tests": "Unit testing",

    "exp.eyebrow": "03 · Experience",
    "exp.title": "Internship.",
    "exp.role": "Developer intern / Fablab assistant",
    "exp.when": "April - June 2026",
    "exp.l1": "<strong>InfraHub</strong>, built in 2 weeks: a ticketing platform for students, with role-based access control and automatic incident escalation.",
    "exp.l2": "<strong>Self-hosted NAS</strong> designed, deployed and run on my own, with <strong>99.9%</strong> measured uptime.",
    "exp.l3": "<strong>Scrum Master</strong> on 4 team projects.",

    "proj.eyebrow": "04 · Projects",
    "proj.title": "What I've built.",
    "proj.filter": "Filter projects",
    "proj.all": "All",
    "proj.perso": "Personal",
    "proj.school": "School",
    "p.ecopayPill": "In testing · 5 testers",
    "p.ecopay": "A SaaS platform that manages and collects school fees for private schools in West Africa (7 countries), with Mobile Money payments and automatic reminders to parents.",
    "p.site": "Visit the site",
    "p.overview": "Overview",
    "p.boutikKind": "Mobile · Desktop · Web",
    "p.boutikPill": "In testing · 4 shops",
    "p.boutik": "Checkout, stock and credit sales for small shops, on Android, iPhone and desktop. Works offline and syncs automatically as soon as the network is back.",
    "p.worldKind": "3D game · C#",
    "p.worldPill": "This site",
    "p.worldName": "Ernest's World",
    "p.world": "The game version of this portfolio: a 3D island with 16 places, 5 bosses, a blog and a newsletter.",
    "p.play": "Play",
    "p.repo": "Repository",
    "p.metricsKind": "AI · Web",
    "p.metrics": "An AI tutor that helps people create content.",
    "p.cascadeKind": "Educational game",
    "p.cascade": "Learn CSS by playing: 1,050 levels, 25 lessons, visual challenges, duels against bots and an Elo leaderboard.",
    "p.readme": "Generates a complete README.md from a project's files. 12 ecosystems, zero dependencies, 100% offline.",
    "p.website": "Website",
    "p.hivePill": "In design",
    "p.hive": "A 3D world where every user has a house and AI assistants that work together to deliver tasks.",
    "p.shadow": "A web communication app.",
    "p.nasPill": "To be redeployed",
    "p.nasName": "Self-hosted NAS",
    "p.nas": "A school computer turned into a NAS server: file sharing, private cloud, services isolated in containers and encrypted remote access without opening any port.",
    "p.netKind": "Networks",
    "p.netName": "Network labs",
    "p.net": "Gateway high availability, outbound traffic filtering, asset and incident management, domain administration.",
    "p.nfcPill": "2nd place",
    "p.nfcName": "NFC reading box",
    "p.nfc": "National IoT Workshop, as a team: NFC tag reading on a Raspberry Pi, Arduino-driven servo motors, Tkinter interface at startup.",
    "p.wonkaName": "“Wonka” PHP framework",
    "p.wonka": "A website rebuilt on a framework written without any library, based on a structured architecture and configuration.",
    "p.todo": "A multi-user task management app.",
    "p.evalKind": "Year 2 assessment",
    "p.evalName": "Event calendar",
    "p.eval": "Entities, forms and security added to an existing mockup.",
    "p.part1": "Part 1",
    "p.part2": "Part 2",
    "p.budgetName": "Student Budget",
    "p.budget": "Expense tracking with unit tests.",
    "p.rpgKind": "Web game",
    "p.rpg": "A small browser RPG built around the DOM and events.",

    "edu.eyebrow": "05 · Education",
    "edu.title": "Education, diplomas and certifications.",
    "edu.t1when": "2025 - 2028 · ongoing",
    "edu.t1": "Bachelor's in Computer Science",
    "edu.t1sub": "EPSI Lyon · 2nd year, software design and development track",
    "edu.t2when": "2027 exams",
    "edu.t2": "BTS SIO, SLAM option",
    "edu.t2sub": "French national diploma in software and business applications · prepared at EPSI Lyon",
    "edu.t3when": "April - June 2026",
    "edu.t3": "Internship at MyDil",
    "edu.t3sub": "Developer / Fablab assistant",
    "edu.t4": "Scientific baccalaureate",
    "edu.t4sub": "With honors · La Prospérité, Benin",
    "edu.modules": "Second-year modules",
    "edu.m1": "Development",
    "edu.m1t": "PHP framework, Symfony, Angular, JavaScript, OOP in Python, business application",
    "edu.m2": "Design",
    "edu.m2t": "UML modeling (use cases, sequences), database design and operation",
    "edu.m3": "Systems and networks",
    "edu.m3t": "Active Directory, HSRP / VRRP high availability, Squid proxy, incident management with GLPI",
    "edu.m4": "Cross-disciplinary",
    "edu.m4t": "Management, technical English, IoT workshop",

    "certs.title": "Certifications and awards",
    "certs.sub": "10 certificates earned in November 2026, then my awards and diplomas.",
    "certs.linkedin": "See the certificates on LinkedIn",
    "cert.id": "ID",
    "cg.anth": "6 certificates earned · AI, agents and developer tools · November 2026",
    "ca.api": "Building applications with the Claude API.",
    "ca.code": "Coding with Claude Code, Anthropic's coding assistant.",
    "ca.mcp": "MCP: the protocol that connects AI models to tools and data.",
    "ca.evals": "Measuring the quality of an AI model's answers with evaluations.",
    "ca.limits": "What AI models can do, and where they fall short.",
    "ca.teams": "Making people and AI agents work well together.",
    "cg.li": "4 certificates earned · programming, project management, entrepreneurship · November 2026",
    "cl.prog": "Programming fundamentals, whatever the language (course in French).",
    "cl.progS1": "Programming",
    "cl.progS2": "Programming basics",
    "cl.capm": "Practice exam for PMI's CAPM® project management certification (in French).",
    "cl.capmS1": "Project management",
    "cl.startup": "Launching a startup with limited resources (course in French).",
    "cl.startupS1": "Entrepreneurship",
    "cl.attention": "AI and the human brain: staying in control of your attention (course in French).",
    "cl.attS1": "Prioritization",
    "cl.attS2": "Brain training",
    "cg.awards": "Awards and diplomas",
    "cg.awardsSub": "A competition, a diploma in progress and the baccalaureate",
    "c.second": "2nd place",
    "c.iotName": "National IoT Workshop",
    "c.iotOrg": "EPSI · national workshop, team project",
    "c.iot": "NFC reading box: tag reading on a Raspberry Pi, Arduino-driven servo motors, Tkinter interface.",
    "c.session": "2027 exams",
    "c.btsName": "BTS SIO, SLAM option",
    "c.btsOrg": "French national diploma · RNCP level 5 certification",
    "c.bts": "Application design and development, IT service support, cybersecurity.",
    "c.obtained": "Earned",
    "c.bacName": "Scientific baccalaureate",
    "c.bacOrg": "With honors · 2025",
    "c.bac": "La Prospérité, Benin.",

    "blog.eyebrow": "06 · Journal",
    "blog.title": "What I write.",
    "blog.sub": "Articles about my projects: how they work and what I learned.",
    "blog.loading": "Loading articles…",
    "blog.all": "All articles",

    "contact.eyebrow": "07 · Contact",
    "contact.title": "Have an internship to offer?<br><span class=\"gradient-text\">Let's talk.</span>",
    "contact.text": "I'm looking for a 4 to 5 week internship in software development or systems and networks. The easiest way to reach me is by email or on LinkedIn.",
    "contact.mail": "Send an email",
    "contact.copy": "Copy",

    "footer.play": "Game version",
    "footer.3d": "3D version",
    "footer.journal": "Journal",
    "footer.source": "Source code",
    "footer.top": "Back to top"
  };

  /* Petits textes écrits par le script lui-même */
  var UI = {
    fr: {
      copied: "Copié !", copyFail: "Copie impossible", copy: "Copier",
      menuOpen: "Ouvrir le menu", menuClose: "Fermer le menu",
      minutes: "min de lecture", noPosts: "Les premiers articles arrivent bientôt.",
      postsError: "Impossible de charger les articles pour le moment.", inFrench: ""
    },
    en: {
      copied: "Copied!", copyFail: "Can't copy", copy: "Copy",
      menuOpen: "Open the menu", menuClose: "Close the menu",
      minutes: "min read", noPosts: "The first articles are coming soon.",
      postsError: "The articles can't be loaded right now.",
      inFrench: "The articles are written in French. Your browser can translate them (right-click, then “Translate to English”)."
    }
  };

  var current = root.getAttribute("data-lang") === "en" ? "en" : "fr";
  var frHtml = new WeakMap();   // texte français d'origine de chaque élément traduit
  var frAttrs = new WeakMap();  // attributs français d'origine (aria-label, title, alt…)
  var frMeta = { title: document.title, description: "" };
  var metaDescription = document.querySelector('meta[name="description"]');
  if (metaDescription) frMeta.description = metaDescription.getAttribute("content");

  function t(key) { return UI[current][key]; }

  function applyLanguage(lang) {
    current = lang === "en" ? "en" : "fr";
    var en = current === "en";

    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      if (!frHtml.has(el)) frHtml.set(el, el.innerHTML);
      var value = en ? EN[el.getAttribute("data-i18n")] : null;
      el.innerHTML = value != null ? value : frHtml.get(el);
    });

    document.querySelectorAll("[data-i18n-attr]").forEach(function (el) {
      var saved = frAttrs.get(el);
      if (!saved) { saved = {}; frAttrs.set(el, saved); }
      el.getAttribute("data-i18n-attr").split(";").forEach(function (pair) {
        var parts = pair.split("="), attr = parts[0].trim(), key = (parts[1] || "").trim();
        if (!(attr in saved)) saved[attr] = el.getAttribute(attr) || "";
        var value = en ? EN[key] : null;
        el.setAttribute(attr, value != null ? value : saved[attr]);
      });
    });

    document.title = en ? EN["meta.title"] : frMeta.title;
    if (metaDescription) metaDescription.setAttribute("content", en ? EN["meta.description"] : frMeta.description);
    root.lang = current;
    root.setAttribute("data-lang", current);
    root.classList.remove("i18n-pending");

    document.querySelectorAll("[data-set-lang]").forEach(function (button) {
      button.setAttribute("aria-pressed", button.getAttribute("data-set-lang") === current ? "true" : "false");
    });

    var menuToggle = document.getElementById("menu-toggle");
    if (menuToggle) menuToggle.setAttribute("aria-label", menuToggle.getAttribute("aria-expanded") === "true" ? t("menuClose") : t("menuOpen"));

    renderPosts();
  }

  /* ------------------------------------------------------------ langue */

  document.querySelectorAll("[data-set-lang]").forEach(function (button) {
    button.addEventListener("click", function () {
      var lang = button.getAttribute("data-set-lang");
      try { localStorage.setItem(LANG_KEY, lang); } catch (e) { /* navigation privée */ }
      if (lang !== current) applyLanguage(lang);
    });
  });

  /* ------------------------------------------------------------- thème */

  var themeToggle = document.getElementById("theme-toggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
      root.setAttribute("data-theme", next);
      var meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute("content", next === "light" ? "#f8f6f1" : "#0b0a12");
      try { localStorage.setItem("theme", next); } catch (e) { /* navigation privée */ }
    });
  }

  /* -------------------------------------------------------------- menu */

  var menu = document.getElementById("menu");
  var menuToggle = document.getElementById("menu-toggle");

  function setMenu(open) {
    if (!menu || !menuToggle) return;
    menu.classList.toggle("is-open", open);
    menuToggle.setAttribute("aria-expanded", open ? "true" : "false");
    menuToggle.setAttribute("aria-label", open ? t("menuClose") : t("menuOpen"));
  }

  if (menuToggle) menuToggle.addEventListener("click", function () { setMenu(!menu.classList.contains("is-open")); });
  if (menu) menu.addEventListener("click", function (e) { if (e.target.closest("a")) setMenu(false); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") setMenu(false); });

  /* ----------------------------------------------- en-tête et lien actif */

  var header = document.querySelector(".site-header");
  function onScroll() { if (header) header.classList.toggle("is-scrolled", window.scrollY > 8); }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".nav a[href^='#']"));
  if ("IntersectionObserver" in window && navLinks.length) {
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var id = entry.target.id === "formation" ? "certifications" : entry.target.id;
        navLinks.forEach(function (a) { a.classList.toggle("is-current", a.getAttribute("href") === "#" + id); });
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    ["apropos", "competences", "projets", "formation", "journal", "contact"].forEach(function (id) {
      var section = document.getElementById(id);
      if (section) spy.observe(section);
    });
  }

  /* -------------------------------------------------- apparition douce */

  var revealed = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var reveal = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add("is-visible"); reveal.unobserve(entry.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    revealed.forEach(function (el) { reveal.observe(el); });
  } else {
    revealed.forEach(function (el) { el.classList.add("is-visible"); });
  }

  /* ---------------------------------------------------- filtres projets */

  var filters = document.querySelectorAll(".filter");
  filters.forEach(function (button) {
    button.addEventListener("click", function () {
      var value = button.getAttribute("data-filter");
      filters.forEach(function (b) {
        var on = b === button;
        b.classList.toggle("is-active", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      document.querySelectorAll(".project").forEach(function (card) {
        var show = value === "tous" || card.getAttribute("data-cat") === value;
        card.hidden = !show;
        if (show) card.classList.add("is-visible");
      });
    });
  });

  /* ------------------------------------------------------- copie email */

  var copyButton = document.getElementById("copy-mail");
  if (copyButton) {
    copyButton.addEventListener("click", function () {
      var label = copyButton.querySelector(".copy-label");
      var mail = copyButton.getAttribute("data-mail");
      var done = function (ok) {
        label.textContent = ok ? t("copied") : t("copyFail");
        setTimeout(function () { label.textContent = t("copy"); }, 2000);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(mail).then(function () { done(true); }, function () { done(false); });
      } else {
        done(false);
      }
    });
  }

  /* -------------------------------------------- préchargement du jeu */

  var prefetched = false;
  function prefetchGame() {
    if (prefetched) return;
    prefetched = true;
    var link = document.createElement("link");
    link.rel = "prefetch";
    link.href = "jeu/";
    document.head.appendChild(link);
  }
  document.querySelectorAll(".play-link").forEach(function (a) {
    a.addEventListener("pointerenter", prefetchGame, { once: true });
    a.addEventListener("focus", prefetchGame, { once: true });
  });

  /* --------------------------------------------- derniers articles */

  var posts = null;      // null : pas encore chargés ; [] : aucun ; false : erreur
  var postsBox = document.getElementById("posts");

  function formatDate(iso) {
    try {
      return new Intl.DateTimeFormat(current === "en" ? "en-US" : "fr-FR", { day: "numeric", month: "long", year: "numeric" })
        .format(new Date(iso + "T12:00:00"));
    } catch (e) { return iso; }
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function renderPosts() {
    if (!postsBox || posts === null) return;
    postsBox.textContent = "";
    if (posts === false || posts.length === 0) {
      postsBox.appendChild(el("p", "muted", posts === false ? t("postsError") : t("noPosts")));
      return;
    }
    if (current === "en") {
      var note = el("p", "lang-note", t("inFrench"));
      note.style.gridColumn = "1 / -1";
      postsBox.appendChild(note);
    }
    posts.slice(0, 3).forEach(function (post) {
      var card = el("a", "card post");
      card.href = "journal/" + encodeURIComponent(post.slug);
      card.setAttribute("hreflang", "fr");
      card.appendChild(el("span", "post-meta", formatDate(post.date) + " · " + post.readingMinutes + " " + t("minutes")));
      var title = el("h3", null, post.title);
      title.lang = "fr";
      card.appendChild(title);
      var summary = el("p", null, post.summary);
      summary.lang = "fr";
      card.appendChild(summary);
      var tags = el("span", "post-tags");
      (post.tags || []).forEach(function (tag) { tags.appendChild(el("span", null, "#" + tag)); });
      card.appendChild(tags);
      postsBox.appendChild(card);
    });
  }

  if (postsBox && window.fetch) {
    fetch("posts/index.json", { cache: "no-cache" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (list) {
        posts = (list || []).filter(function (p) { return !p.draft; })
          .sort(function (a, b) { return a.date < b.date ? 1 : -1; });
        renderPosts();
      })
      .catch(function () { posts = false; renderPosts(); });
  }

  /* ---------------------------------------------------------- divers */

  var year = document.getElementById("annee");
  if (year) year.textContent = String(new Date().getFullYear());

  applyLanguage(current);
})();
