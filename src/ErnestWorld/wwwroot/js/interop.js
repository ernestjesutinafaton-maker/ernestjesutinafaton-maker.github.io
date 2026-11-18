/*
  Petites fonctions du navigateur appelées depuis C# (BrowserService).
  Tout ce qui peut échouer (stockage bloqué, presse-papiers refusé) est protégé.
*/

export function storageGet(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

export function storageSet(key, value) {
  try { localStorage.setItem(key, value); return true; } catch { return false; }
}

export async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch { return false; }
}

export function openUrl(url) {
  window.location.href = url;
}

export function submitForm(form) {
  form?.submit();
}

export function scrollToTop(el) {
  if (el) el.scrollTop = 0;
}

export function isSmallScreen() {
  return window.matchMedia("(max-width: 736px)").matches;
}

export function prefersFrench() {
  const langs = navigator.languages?.length ? navigator.languages : [navigator.language || "fr"];
  return langs.some((l) => String(l).toLowerCase().startsWith("fr"));
}

export function setDocumentLang(code) {
  document.documentElement.lang = code;
}

export function printPage() {
  window.print();
}

/*
  Suit la lecture d'un article : met à jour la barre de progression et prévient
  le C# une seule fois quand l'article est lu (fin atteinte, ou texte court
  affiché assez longtemps).
*/
export function watchReading(scroller, bar, dotnet) {
  let done = false, timer = 0;
  const finish = () => {
    if (done) return;
    done = true;
    dotnet.invokeMethodAsync("OnReadComplete");
  };
  const isShort = () => scroller.scrollHeight - scroller.clientHeight < 80;
  const update = () => {
    if (isShort()) return;
    const max = scroller.scrollHeight - scroller.clientHeight;
    const progress = Math.min(1, scroller.scrollTop / max);
    if (bar) bar.style.transform = `scaleX(${progress})`;
    if (progress >= 0.92) finish();
  };
  scroller.addEventListener("scroll", update, { passive: true });
  // Article court : pas besoin de défiler, il est lu au bout de quelques secondes
  if (isShort()) {
    if (bar) bar.style.transform = "scaleX(1)";
    timer = setTimeout(finish, 8000);
  }
  update();
  return {
    dispose() {
      scroller.removeEventListener("scroll", update);
      clearTimeout(timer);
    },
  };
}
