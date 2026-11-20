"""
L'ÎLE DU PORTFOLIO · scène Blender de la version immersive (/3d/)

Ce script fabrique l'île dans Blender, « cuit » sa lumière avec Cycles dans des textures, puis
exporte le modèle et les textures pour le site, où Three.js les affiche.
Cuire la lumière veut dire : Cycles calcule une fois pour toutes l'éclairage réaliste (soleil, ciel,
ombres douces, lumière qui rebondit) et l'enregistre dans des images. Le navigateur n'a plus qu'à
afficher ces images : la scène a l'air rendue par Blender, et tourne pourtant sur un téléphone.

Utilisation, depuis la racine du dépôt :

  blender -b --factory-startup --python tools/blender/ile.py -- [options]

Étapes (--etapes, séparées par des virgules ; par défaut « construire,affiche,cuire ») :
  construire  modélise l'île et l'enregistre dans tools/blender/out/ile.blend
              (peint aussi la texture des feuilles : wwwroot/3d/assets/feuilles_*.webp)
  apercu      rend une image d'un chapitre (--chapitre N, « tous », ou « cleN » pour une clé de caméra)
  affiche     rend l'image de secours du site (sans WebGL) : wwwroot/3d/assets/affiche.webp
  cuire       cuit la lumière, enregistre les atlas puis exporte ile.glb dans wwwroot/3d/assets/
  exporter    réexporte seulement ile.glb (à lancer sur tools/blender/out/ile_cuite.blend)

Options : --echantillons N (qualité de la cuisson ou du rendu), --rapide (cuisson d'essai en 1024 px),
          --largeur / --hauteur (taille des aperçus).

Retoucher l'île à la main : ouvrir tools/blender/out/ile.blend, modifier, enregistrer, puis
  blender -b tools/blender/out/ile.blend --python tools/blender/ile.py -- --etapes cuire

Conventions de la scène (à respecter si on ajoute des objets à la main) :
  collections « atlas_<nom> »  objets cuits dans l'atlas <nom> (propriété « taille » = résolution).
                               Les objets d'un même « groupe » (propriété) sont fusionnés en un seul maillage.
  collection « vivant »        objets exportés sans cuisson : le site leur donne une matière animée
                               (eau, cascade, cristaux, glyphes, anneau)
  collection « reperes »       objets vides exportés : trajet de la caméra (cam_XX, cible_XX), ancres
  collection « studio »        soleil et réglages, jamais exportés

Organisation du fichier :
  1. réglages, bruit et outils          5. bâtiments et objets du décor
  2. plan de l'île (relief, eau)        6. végétation (arbres en cartes de feuilles)
  3. texture des feuilles               7. eau, cascade, dessous de l'île
  4. matières et constructeurs          8. caméra, studio, étapes (construire, aperçu, cuisson)
"""

import bpy
import bmesh
import math
import os
import random
import sys
import time

import numpy as np
from mathutils import Matrix, Vector, noise
from mathutils.bvhtree import BVHTree

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.normpath(os.path.join(ICI, "..", ".."))
SORTIE_BLEND = os.path.join(ICI, "out")
SORTIE_SITE = os.path.join(DEPOT, "src", "ErnestWorld", "wwwroot", "3d", "assets")

# Soleil couchant : direction vers le soleil (azimut depuis +X vers +Y, hauteur au-dessus de l'horizon)
SOLEIL_AZIMUT = math.radians(22)
SOLEIL_HAUTEUR = math.radians(13)
SOLEIL_DIR = Vector((math.cos(SOLEIL_HAUTEUR) * math.cos(SOLEIL_AZIMUT),
                     math.cos(SOLEIL_HAUTEUR) * math.sin(SOLEIL_AZIMUT),
                     math.sin(SOLEIL_HAUTEUR)))

# Les quatre tuiles de la texture des feuilles (2 × 2)
TUILE_FEUILLU, TUILE_AIGUILLES, TUILE_CYPRES, TUILE_BUISSON = 0, 1, 2, 3


def log(*a):
    print("[ile]", *a, flush=True)


def lire_options():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"etapes": "construire,affiche,cuire", "chapitre": "0", "echantillons": "", "rapide": False,
            "sortie": SORTIE_SITE, "largeur": "1280", "hauteur": "720"}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--rapide":
            opts["rapide"] = True
        elif a.startswith("--") and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1]
            i += 1
        i += 1
    opts["etapes"] = [e.strip() for e in opts["etapes"].split(",") if e.strip()]
    return opts


# =========================================================================
#  1. BRUIT ET OUTILS
# =========================================================================

def n3(x, y, z):
    return noise.noise(Vector((x, y, z)))


def fbm2(x, y, octaves=4, graine=0.0):
    v, a, f = 0.0, 0.5, 1.0
    for i in range(octaves):
        v += a * n3(x * f, y * f, graine + i * 7.31)
        a *= 0.5
        f *= 2.03
    return v * 1.9


def fbm3(p, octaves=4):
    v, a, f = 0.0, 0.5, 1.0
    for i in range(octaves):
        v += a * noise.noise(p * f + Vector((i * 3.7, i * 1.3, i * 5.1)))
        a *= 0.5
        f *= 2.07
    return v * 1.9


def crete(p):
    """Bruit « en crêtes » (arêtes vives), entre 0 et 1 environ."""
    v = noise.ridged_multi_fractal(p, 1.0, 2.0, 4, 1.0, 2.0)
    return max(0.0, min(1.0, v / 2.2))


def smoothstep(a, b, x):
    if a == b:
        return 0.0 if x < a else 1.0
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def dist_segment(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy)


def dist_polyligne(px, py, pts):
    return min(dist_segment(px, py, *pts[i], *pts[i + 1]) for i in range(len(pts) - 1))


def reechantillonner(pts, pas):
    """Points régulièrement espacés le long d'une polyligne, avec la distance parcourue."""
    sortie = [(pts[0][0], pts[0][1], 0.0)]
    s = 0.0
    reste = 0.0
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        l = math.hypot(bx - ax, by - ay)
        d = pas - reste
        while d <= l:
            t = d / l
            sortie.append((ax + (bx - ax) * t, ay + (by - ay) * t, s + d))
            d += pas
        reste = l - (d - pas)
        s += l
    return sortie


# =========================================================================
#  2. PLAN DE L'ÎLE
# =========================================================================

# Lieux (x, y, rayon du replat). La caméra visite les lieux des chapitres dans cet ordre.
SITES = {
    "arche": (0.0, -22.0, 4.0),
    "atelier": (-14.0, -6.0, 6.0),
    "cercle": (2.0, 6.0, 7.8),
    "cristaux": (15.0, -6.0, 4.2),
    "phare": (23.5, 19.5, 4.0),
    "etang": (-11.0, 7.0, 4.4),
}

CHEMIN = [(0.0, -27.0), (0.0, -22.0), (-1.5, -17.0), (-5.0, -12.0), (-9.0, -8.5), (-8.5, -3.0), (-5.0, 1.5),
          (-3.0, 5.0), (2.0, 6.0), (7.5, 3.5), (11.0, -1.5), (12.5, -5.0), (14.5, 1.0), (17.0, 8.0),
          (20.0, 14.5), (22.5, 18.0)]
CHEMIN_ATELIER = [(-9.0, -8.5), (-11.2, -7.4)]

# Le ruisseau part de l'étang et se jette dans le vide au sud-ouest (la cascade)
RUISSEAU = [(-11.0, 7.0), (-13.8, 4.6), (-16.6, 1.6), (-19.4, -1.8), (-22.2, -5.4), (-25.0, -8.8),
            (-27.8, -11.8), (-36.0, -19.0)]
LARGEUR_RUISSEAU = 0.85
RAYON_ETANG = 3.6

# Obstacles où l'herbe ne pousse pas et où l'on ne plante rien (x, y, rayon)
OBSTACLES = []


def rayon_bord(theta):
    c, s = math.cos(theta), math.sin(theta)
    r = 30.0 + 3.6 * n3(c * 1.25 + 5.2, s * 1.25 + 1.7, 0.3) + 1.6 * n3(c * 3.1 + 2.0, s * 3.1 + 7.0, 1.1)
    r += 0.5 * n3(c * 7.0, s * 7.0, 4.4)
    # Promontoire du phare (nord-est) et avancée de l'arche (sud)
    r += 6.0 * max(0.0, math.cos(theta - math.atan2(19.5, 23.5))) ** 10
    r += 2.5 * max(0.0, math.cos(theta + math.pi / 2)) ** 14
    return r


def hauteur_brute(x, y):
    r = math.hypot(x, y)
    t = r / rayon_bord(math.atan2(y, x))
    h = 2.6 * (1.0 - t * t)
    h += 1.7 * fbm2(x * 0.045, y * 0.045, 4, 0.5)
    h += 4.2 * math.exp(-((x - 23.5) ** 2 + (y - 19.5) ** 2) / 60.0)   # colline du phare
    h += 3.4 * math.exp(-((x + 15) ** 2 + (y - 15) ** 2) / 70.0)       # colline boisée
    h += 0.12 * n3(x * 0.6, y * 0.6, 9.0)
    return h


HAUTEUR_SITE = {}


def dist_ruisseau(x, y):
    return dist_polyligne(x, y, RUISSEAU)


def dist_etang(x, y):
    cx, cy, _ = SITES["etang"]
    return math.hypot(x - cx, y - cy) - 0.35 * n3(x * 0.5, y * 0.5, 3.3)


def hauteur_sans_eau(x, y, masque_chemin=0.0):
    h = hauteur_brute(x, y)
    for nom, (cx, cy, rr) in SITES.items():
        d = math.hypot(x - cx, y - cy)
        w = smoothstep(rr + 4.0, rr, d)
        if w > 0:
            h = lerp(h, HAUTEUR_SITE[nom], w)
    r = math.hypot(x, y)
    t = r / rayon_bord(math.atan2(y, x))
    h -= 1.1 * smoothstep(0.9, 1.0, t)
    h -= 0.07 * masque_chemin
    return h


def hauteur(x, y, masque_chemin=0.0):
    """Hauteur du sol, avec le lit du ruisseau et le bassin de l'étang creusés."""
    h = hauteur_sans_eau(x, y, masque_chemin)
    d = dist_ruisseau(x, y)
    h -= 0.7 * (1.0 - smoothstep(LARGEUR_RUISSEAU * 0.45, LARGEUR_RUISSEAU + 0.9, d))
    de = dist_etang(x, y)
    h -= 1.0 * (1.0 - smoothstep(RAYON_ETANG * 0.45, RAYON_ETANG + 0.9, de))
    return h


def masque_chemin(x, y):
    d = min(dist_polyligne(x, y, CHEMIN), dist_polyligne(x, y, CHEMIN_ATELIER))
    largeur = 0.85 + 0.25 * n3(x * 0.4, y * 0.4, 2.0)
    return 1.0 - smoothstep(largeur, largeur + 0.55, d)


def masque_eau(x, y):
    """Sol mouillé : bords du ruisseau et de l'étang."""
    a = 1.0 - smoothstep(LARGEUR_RUISSEAU * 0.5, LARGEUR_RUISSEAU + 1.6, dist_ruisseau(x, y))
    b = 1.0 - smoothstep(RAYON_ETANG - 0.6, RAYON_ETANG + 1.4, dist_etang(x, y))
    return max(a, b)


def sur_ile(x, y, marge=0.0):
    return math.hypot(x, y) < rayon_bord(math.atan2(y, x)) - marge


def preparer_plan():
    for nom, (cx, cy, rr) in SITES.items():
        HAUTEUR_SITE[nom] = hauteur_brute(cx, cy)


# =========================================================================
#  3. TEXTURE DES FEUILLES (peinte avec numpy)
# =========================================================================

class Peintre:
    """Peint des feuilles, des aiguilles et des fleurs dans une image RGBA (ligne 0 = haut de l'image)."""

    def __init__(self, taille):
        self.n = taille
        self.img = np.zeros((taille, taille, 4), dtype=np.float32)

    def _zone(self, x0, y0, x1, y1):
        x0, y0 = max(0, int(math.floor(x0))), max(0, int(math.floor(y0)))
        x1, y1 = min(self.n, int(math.ceil(x1)) + 1), min(self.n, int(math.ceil(y1)) + 1)
        if x1 <= x0 or y1 <= y0:
            return None
        Y, X = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        return x0, y0, X + 0.5, Y + 0.5

    def _poser(self, x0, y0, couleur, masque):
        h, w = masque.shape
        zone = self.img[y0:y0 + h, x0:x0 + w]
        m = masque[..., None]
        zone[..., :3] = zone[..., :3] * (1.0 - m) + couleur * m
        zone[..., 3:] = zone[..., 3:] * (1.0 - m) + m

    def feuille(self, cx, cy, ang, L, W, rgb, lumiere=1.0):
        ca, sa = math.cos(ang), math.sin(ang)
        mx, my = cx + ca * L * 0.5, cy + sa * L * 0.5
        r = L * 0.5 + W + 3
        z = self._zone(mx - r, my - r, mx + r, my + r)
        if z is None:
            return
        x0, y0, X, Y = z
        dx, dy = X - cx, Y - cy
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
        t = np.clip(u / L, 0.0, 1.0)
        # sin(pi) vaut un tout petit nombre négatif en float32 : on borne avant la puissance (sinon NaN)
        demi = 0.5 * W * np.power(np.clip(np.sin(np.pi * t), 0.0, 1.0), 0.68) * (1.0 - 0.22 * t)
        d = demi - np.abs(v)
        dedans = (u >= 0) & (u <= L)
        masque = np.where(dedans, np.clip(d + 0.5, 0.0, 1.0), 0.0).astype(np.float32)
        petiole = (u < 0) & (u > -L * 0.12) & (np.abs(v) < 1.0)
        masque = np.maximum(masque, petiole.astype(np.float32))
        if masque.max() <= 0:
            return
        bombe = np.clip(d / (demi + 1e-3), 0.0, 1.0) ** 0.5
        ton = (0.66 + 0.34 * bombe) * (0.9 + 0.15 * t) * lumiere
        ton = np.where((np.abs(v) < 1.1) & (t < 0.88) & (t > 0.02), ton * 1.16, ton)
        ton = np.where(d < 1.3, ton * 0.8, ton)
        coul = np.asarray(rgb, np.float32)[None, None, :] * ton[..., None]
        self._poser(x0, y0, coul, masque)

    def trait(self, xa, ya, xb, yb, ep, rgb_a, rgb_b=None):
        rgb_b = rgb_a if rgb_b is None else rgb_b
        z = self._zone(min(xa, xb) - ep, min(ya, yb) - ep, max(xa, xb) + ep, max(ya, yb) + ep)
        if z is None:
            return
        x0, y0, X, Y = z
        dx, dy = xb - xa, yb - ya
        l2 = dx * dx + dy * dy + 1e-6
        t = np.clip(((X - xa) * dx + (Y - ya) * dy) / l2, 0.0, 1.0)
        qx, qy = xa + t * dx, ya + t * dy
        d = np.hypot(X - qx, Y - qy)
        largeur = ep * (1.0 - 0.6 * t)
        masque = np.clip(largeur * 0.5 - d + 0.5, 0.0, 1.0)
        if masque.max() <= 0:
            return
        a, b = np.asarray(rgb_a, np.float32), np.asarray(rgb_b, np.float32)
        coul = a[None, None, :] * (1 - t[..., None]) + b[None, None, :] * t[..., None]
        self._poser(x0, y0, coul, masque)

    def ellipse(self, cx, cy, rx, ry, ang, rgb, relief=0.35):
        r = max(rx, ry) + 2
        z = self._zone(cx - r, cy - r, cx + r, cy + r)
        if z is None:
            return
        x0, y0, X, Y = z
        ca, sa = math.cos(ang), math.sin(ang)
        dx, dy = X - cx, Y - cy
        u = (dx * ca + dy * sa) / rx
        v = (-dx * sa + dy * ca) / ry
        q = np.sqrt(u * u + v * v)
        masque = np.clip((1.0 - q) * min(rx, ry) + 0.5, 0.0, 1.0)
        if masque.max() <= 0:
            return
        ton = 1.0 - relief * np.clip(q, 0, 1) ** 2 + 0.12 * np.clip(-v, 0, 1)
        coul = np.asarray(rgb, np.float32)[None, None, :] * ton[..., None]
        self._poser(x0, y0, coul, masque)


def varier(rgb, rnd, ampl=0.12, chaleur=0.0):
    k = 1.0 + rnd.uniform(-ampl, ampl)
    r, g, b = rgb
    return (min(1, r * k * (1 + chaleur)), min(1, g * k), min(1, b * k * (1 - chaleur * 0.5)))


def tuile_feuillu(p, ox, oy, t, rnd):
    c = (ox + t / 2, oy + t / 2)
    # Brindilles depuis le centre, puis les feuilles du fond vers le devant
    for k in range(9):
        a = rnd.uniform(0, 2 * math.pi)
        l = t * rnd.uniform(0.25, 0.42)
        p.trait(c[0], c[1] + t * 0.12, c[0] + math.cos(a) * l, c[1] + math.sin(a) * l, 5.0, (0.2, 0.14, 0.09))
    verts = [(0.2, 0.32, 0.1), (0.26, 0.38, 0.12), (0.32, 0.42, 0.13), (0.22, 0.36, 0.14), (0.36, 0.4, 0.12)]
    for k in range(190):
        a = rnd.uniform(0, 2 * math.pi)
        r = t * 0.42 * math.sqrt(rnd.uniform(0.02, 1.0))
        x, y = c[0] + math.cos(a) * r, c[1] + math.sin(a) * r
        ang = a + rnd.gauss(0, 0.7)
        L = rnd.uniform(0.075, 0.13) * t
        prof = 0.72 + 0.28 * min(1.0, r / (t * 0.42)) + (0.08 if k > 140 else 0.0)
        chaleur = 0.25 if rnd.random() < 0.12 else 0.0
        p.feuille(x, y, ang, L, L * rnd.uniform(0.4, 0.52), varier(rnd.choice(verts), rnd, 0.12, chaleur), prof)


def tuile_aiguilles(p, ox, oy, t, rnd):
    # Rameau de sapin : une tige du bas vers le haut, des rameaux, puis des aiguilles
    base = (ox + t * 0.5, oy + t * 0.97)
    haut = (ox + t * 0.5 + rnd.uniform(-0.05, 0.05) * t, oy + t * 0.06)
    tiges = [(base, haut)]
    for k in range(12):
        s = 0.12 + 0.07 * k
        px = lerp(base[0], haut[0], s)
        py = lerp(base[1], haut[1], s)
        cote = -1 if k % 2 else 1
        l = t * (0.36 - 0.022 * k) * rnd.uniform(0.85, 1.1)
        a = -math.pi / 2 + cote * rnd.uniform(0.75, 1.05)
        tiges.append(((px, py), (px + math.cos(a) * l, py + math.sin(a) * l)))
    for (xa, ya), (xb, yb) in tiges:
        p.trait(xa, ya, xb, yb, 4.0, (0.16, 0.11, 0.07))
    for (xa, ya), (xb, yb) in tiges:
        l = math.hypot(xb - xa, yb - ya)
        da = math.atan2(yb - ya, xb - xa)
        n = int(l / 2.6)
        for k in range(n):
            s = (k + 0.5) / n
            x, y = lerp(xa, xb, s), lerp(ya, yb, s)
            for cote in (-1, 1):
                a = da + cote * rnd.uniform(0.6, 1.0)
                la = t * rnd.uniform(0.045, 0.075) * (1.0 - 0.35 * s)
                ton = rnd.uniform(0.8, 1.15)
                p.trait(x, y, x + math.cos(a) * la, y + math.sin(a) * la, 2.4,
                        (0.07 * ton, 0.16 * ton, 0.09 * ton), (0.16 * ton, 0.3 * ton, 0.14 * ton))


def tuile_cypres(p, ox, oy, t, rnd):
    # Panache dense de petites écailles, plus clair vers le haut et vers la lumière
    for k in range(1300):
        u = rnd.gauss(0, 0.17)
        v = rnd.uniform(0.04, 0.96)
        lim = 0.36 * math.sin(math.pi * v) ** 0.6
        if abs(u) > lim:
            continue
        x, y = ox + t * (0.5 + u), oy + t * v
        r = t * rnd.uniform(0.012, 0.024)
        ton = (0.75 + 0.35 * (1 - v)) * rnd.uniform(0.85, 1.15) * (0.8 + 0.4 * (1 - abs(u) / (lim + 1e-3)) * 0.5)
        p.ellipse(x, y, r * 1.5, r, rnd.uniform(0, math.pi), (0.1 * ton, 0.21 * ton, 0.11 * ton), 0.5)


def tuile_buisson(p, ox, oy, t, rnd):
    c = (ox + t / 2, oy + t / 2)
    verts = [(0.2, 0.33, 0.12), (0.25, 0.37, 0.12), (0.3, 0.4, 0.14)]
    for k in range(420):
        a = rnd.uniform(0, 2 * math.pi)
        r = t * 0.43 * math.sqrt(rnd.uniform(0.0, 1.0))
        x, y = c[0] + math.cos(a) * r, c[1] + math.sin(a) * r
        L = rnd.uniform(0.045, 0.075) * t
        p.feuille(x, y, a + rnd.gauss(0, 0.9), L, L * rnd.uniform(0.55, 0.7), varier(rnd.choice(verts), rnd), 0.75 + 0.3 * r / (t * 0.43))
    couleurs = [(0.95, 0.55, 0.75), (0.98, 0.92, 0.95), (0.8, 0.55, 0.95), (1.0, 0.8, 0.45)]
    for k in range(46):
        a = rnd.uniform(0, 2 * math.pi)
        r = t * 0.4 * math.sqrt(rnd.uniform(0.05, 1.0))
        x, y = c[0] + math.cos(a) * r, c[1] + math.sin(a) * r
        coul = rnd.choice(couleurs)
        rp = t * rnd.uniform(0.012, 0.018)
        for s in range(5):
            b = 2 * math.pi * s / 5 + rnd.uniform(0, 0.3)
            p.ellipse(x + math.cos(b) * rp, y + math.sin(b) * rp, rp * 1.05, rp * 0.7, b, coul, 0.3)
        p.ellipse(x, y, rp * 0.55, rp * 0.55, 0, (1.0, 0.8, 0.3), 0.2)


def peindre_feuilles(sortie):
    """Texture 2048 × 2048 en 4 tuiles. Renvoie l'image Blender (pour la cuisson)."""
    t0 = time.time()
    N = 2048
    t = N // 2
    p = Peintre(N)
    rnd = random.Random(77)
    # Tuile k : colonne k % 2, rangée k // 2 en partant du BAS de l'image (convention des UV de Blender)
    for k, fn in ((TUILE_FEUILLU, tuile_feuillu), (TUILE_AIGUILLES, tuile_aiguilles),
                  (TUILE_CYPRES, tuile_cypres), (TUILE_BUISSON, tuile_buisson)):
        ox = (k % 2) * t
        oy = (1 - k // 2) * t
        fn(p, ox, oy, t, rnd)
    img = np.nan_to_num(p.img, nan=0.0)
    # Les pixels transparents prennent la couleur moyenne des feuilles : pas de liseré sombre à distance
    a = img[..., 3]
    moyenne = (img[..., :3] * a[..., None]).sum(axis=(0, 1)) / max(1.0, a.sum())
    vide = a < 0.02
    img[vide, :3] = moyenne
    img[..., :3] = np.clip(img[..., :3], 0, 1)

    def vers_blender(nom, tableau, taille):
        im = bpy.data.images.new(nom, taille, taille, alpha=True)
        im.pixels.foreach_set(np.flipud(tableau).ravel())
        return im

    os.makedirs(sortie, exist_ok=True)
    grande = vers_blender("feuilles", img, N)
    petite_np = img.reshape(N // 2, 2, N // 2, 2, 4).mean(axis=(1, 3))
    petite = vers_blender("feuilles_1024", petite_np, N // 2)
    for im, nom in ((grande, "feuilles_2048.webp"), (petite, "feuilles_1024.webp")):
        im.file_format = "WEBP"
        im.filepath_raw = os.path.join(sortie, nom)
        im.save(quality=90)
        log("texture :", os.path.relpath(im.filepath_raw, DEPOT), f"{os.path.getsize(im.filepath_raw) / 1024:.0f} Ko")
    bpy.data.images.remove(petite)
    grande.pack()
    log(f"feuilles peintes en {time.time() - t0:.1f} s")
    return grande


# =========================================================================
#  4. MATIÈRES (Cycles) ET CONSTRUCTEURS
# =========================================================================

class Noeuds:
    """Petit assistant pour écrire des arbres de nœuds sans répéter dix lignes à chaque fois."""

    def __init__(self, nom):
        self.mat = bpy.data.materials.new(nom)
        self.nt = self.mat.node_tree
        self.nt.nodes.clear()
        self.sortie = self.nt.nodes.new("ShaderNodeOutputMaterial")
        self.bsdf = self.nt.nodes.new("ShaderNodeBsdfPrincipled")
        self.lien(self.bsdf.outputs[0], self.sortie.inputs[0])
        coord = self.nt.nodes.new("ShaderNodeTexCoord")
        self.pos = coord.outputs["Object"]
        self.geo = self.nt.nodes.new("ShaderNodeNewGeometry")

    def lien(self, a, b):
        self.nt.links.new(a, b)

    def _entree(self, sock, v):
        if isinstance(v, (int, float)):
            sock.default_value = v
        elif isinstance(v, tuple):
            sock.default_value = v if len(v) == 4 or sock.type != "RGBA" else (*v, 1.0)
        else:
            self.lien(v, sock)

    def bruit(self, echelle, detail=4.0, rugo=0.5, vec=None, distorsion=0.0):
        n = self.nt.nodes.new("ShaderNodeTexNoise")
        self.lien(vec or self.pos, n.inputs["Vector"])
        n.inputs["Scale"].default_value = echelle
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rugo
        n.inputs["Distortion"].default_value = distorsion
        return n.outputs["Factor"]

    def voronoi(self, echelle, vec=None, sortie="Distance", trait="F1"):
        n = self.nt.nodes.new("ShaderNodeTexVoronoi")
        n.feature = trait
        self.lien(vec or self.pos, n.inputs["Vector"])
        n.inputs["Scale"].default_value = echelle
        return n.outputs[sortie]

    def vague(self, echelle, distorsion=4.0, direction="Z", vec=None, detail=3.0):
        n = self.nt.nodes.new("ShaderNodeTexWave")
        n.bands_direction = direction
        self.lien(vec or self.pos, n.inputs["Vector"])
        n.inputs["Scale"].default_value = echelle
        n.inputs["Distortion"].default_value = distorsion
        n.inputs["Detail"].default_value = detail
        return n.outputs["Factor"]

    def brique(self, echelle, vec=None, mortier=0.02, largeur=0.5, hauteur=0.25):
        n = self.nt.nodes.new("ShaderNodeTexBrick")
        self.lien(vec or self.pos, n.inputs["Vector"])
        n.inputs["Scale"].default_value = echelle
        n.inputs["Mortar Size"].default_value = mortier
        n.inputs["Brick Width"].default_value = largeur
        n.inputs["Row Height"].default_value = hauteur
        n.inputs["Color1"].default_value = (1, 1, 1, 1)
        n.inputs["Color2"].default_value = (0.6, 0.6, 0.6, 1)
        n.inputs["Mortar"].default_value = (0, 0, 0, 1)
        return n.outputs["Color"], n.outputs["Factor"]

    def rampe(self, fac, arrets):
        n = self.nt.nodes.new("ShaderNodeValToRGB")
        r = n.color_ramp
        while len(r.elements) > 1:
            r.elements.remove(r.elements[-1])
        r.elements[0].position = arrets[0][0]
        r.elements[0].color = (*arrets[0][1], 1.0)
        for p, c in arrets[1:]:
            e = r.elements.new(p)
            e.color = (*c, 1.0)
        self._entree(n.inputs[0], fac)
        return n.outputs["Color"]

    def melange(self, fac, a, b, mode="MIX"):
        n = self.nt.nodes.new("ShaderNodeMix")
        n.data_type = "RGBA"
        n.blend_type = mode
        self._entree(n.inputs[0], fac)
        self._entree(n.inputs[6], a)
        self._entree(n.inputs[7], b)
        return n.outputs[2]

    def math(self, op, a, b=0.0, borner=False):
        n = self.nt.nodes.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = borner
        self._entree(n.inputs[0], a)
        self._entree(n.inputs[1], b)
        return n.outputs[0]

    def plage(self, v, de_min, de_max, a_min=0.0, a_max=1.0):
        n = self.nt.nodes.new("ShaderNodeMapRange")
        self._entree(n.inputs[0], v)
        n.inputs[1].default_value = de_min
        n.inputs[2].default_value = de_max
        n.inputs[3].default_value = a_min
        n.inputs[4].default_value = a_max
        n.clamp = True
        return n.outputs[0]

    def attribut(self, nom, sortie="Color"):
        n = self.nt.nodes.new("ShaderNodeAttribute")
        n.attribute_name = nom
        return n.outputs[sortie]

    def echelle_vec(self, sx, sy, sz):
        n = self.nt.nodes.new("ShaderNodeVectorMath")
        n.operation = "MULTIPLY"
        self.lien(self.pos, n.inputs[0])
        n.inputs[1].default_value = (sx, sy, sz)
        return n.outputs[0]

    def normale_z(self):
        n = self.nt.nodes.new("ShaderNodeSeparateXYZ")
        self.lien(self.geo.outputs["Normal"], n.inputs[0])
        return n.outputs["Z"]

    def relief(self, hauteur, force=0.3, distance=0.05):
        n = self.nt.nodes.new("ShaderNodeBump")
        self._entree(n.inputs["Height"], hauteur)
        n.inputs["Strength"].default_value = force
        n.inputs["Distance"].default_value = distance
        self.lien(n.outputs[0], self.bsdf.inputs["Normal"])

    def couleur(self, c):
        self._entree(self.bsdf.inputs["Base Color"], c)

    def rugosite(self, r):
        self._entree(self.bsdf.inputs["Roughness"], r)

    def emission(self, couleur, force):
        self._entree(self.bsdf.inputs["Emission Color"], couleur)
        self._entree(self.bsdf.inputs["Emission Strength"], force)


def teinte(m):
    return m.attribut("teinte")


def creer_matieres(image_feuilles):
    M = {}

    # Herbe du dessus de l'île : chemin de terre (attribut « chemin »), berges mouillées (attribut « eau »)
    m = Noeuds("herbe")
    grand = m.bruit(0.07, 5, 0.55)
    moyen = m.bruit(0.55, 6, 0.6)
    fin = m.bruit(6.0, 3, 0.7)
    herbe = m.rampe(grand, [(0.25, (0.07, 0.11, 0.024)), (0.5, (0.105, 0.155, 0.034)),
                            (0.7, (0.16, 0.18, 0.045)), (0.85, (0.24, 0.21, 0.075))])
    herbe = m.melange(m.plage(moyen, 0.3, 0.75, 0.0, 0.4), herbe, (0.035, 0.065, 0.016), "MULTIPLY")
    fleurs = m.plage(m.voronoi(2.2, trait="F1"), 0.0, 0.06, 1.0, 0.0)
    fleurs = m.math("MULTIPLY", fleurs, m.plage(m.bruit(0.25, 2), 0.55, 0.7))
    herbe = m.melange(m.math("MULTIPLY", fleurs, 0.7), herbe, (0.6, 0.45, 0.2))
    terre = m.rampe(m.bruit(1.4, 6), [(0.3, (0.075, 0.05, 0.03)), (0.7, (0.16, 0.115, 0.07))])
    cailloux = m.plage(m.voronoi(9.0), 0.0, 0.18, 1.0, 0.0)
    terre = m.melange(m.math("MULTIPLY", cailloux, 0.5), terre, (0.22, 0.2, 0.17))
    bord = m.plage(m.math("ADD", m.attribut("chemin", "Factor"), m.math("MULTIPLY", fin, 0.4)), 0.55, 0.85)
    sol = m.melange(bord, herbe, terre)
    # Berges : boue sombre et galets
    eau = m.plage(m.math("ADD", m.attribut("eau", "Factor"), m.math("MULTIPLY", fin, 0.3)), 0.35, 0.75)
    galets = m.plage(m.voronoi(5.0), 0.0, 0.3, 1.0, 0.0)
    berge = m.melange(m.math("MULTIPLY", galets, 0.6), (0.035, 0.03, 0.025), (0.16, 0.15, 0.13))
    m.couleur(m.melange(eau, sol, berge))
    m.rugosite(0.95)
    m.relief(m.math("ADD", m.math("MULTIPLY", fin, 0.6), m.math("MULTIPLY", cailloux, bord)), 0.35, 0.04)
    M["herbe"] = m.mat

    # Roche de la falaise : strates, fissures par endroits, mousse sur les faces tournées vers le ciel
    m = Noeuds("roche")
    strates = m.vague(0.6, 16.0, "Z", m.echelle_vec(0.05, 0.05, 0.45), 6)
    var = m.math("ADD", m.math("MULTIPLY", m.bruit(0.35, 5, 0.6), 0.6), m.math("MULTIPLY", m.bruit(0.07, 3, 0.5), 0.4))
    roche = m.rampe(m.math("ADD", m.math("MULTIPLY", strates, 0.07), m.math("MULTIPLY", var, 0.93)),
                    [(0.2, (0.05, 0.04, 0.035)), (0.45, (0.12, 0.095, 0.075)),
                     (0.7, (0.2, 0.16, 0.12)), (0.9, (0.27, 0.22, 0.17))])
    fissures = m.plage(m.voronoi(0.6, trait="DISTANCE_TO_EDGE"), 0.0, 0.03, 0.0, 1.0)
    zones = m.plage(m.bruit(0.3, 3), 0.6, 0.72)
    roche = m.melange(m.math("MULTIPLY", m.math("SUBTRACT", 1.0, fissures), m.math("MULTIPLY", zones, 0.75)),
                      roche, (0.02, 0.018, 0.016))
    fissures = m.math("MULTIPLY", fissures, 0.35)
    mousse = m.math("MULTIPLY", m.plage(m.normale_z(), 0.55, 0.85), m.plage(m.bruit(1.2, 4), 0.4, 0.6))
    roche = m.melange(mousse, roche, m.rampe(var, [(0.3, (0.04, 0.07, 0.015)), (0.7, (0.1, 0.12, 0.03))]))
    m.couleur(m.melange(1.0, roche, teinte(m), "MULTIPLY"))
    m.rugosite(0.9)
    m.relief(m.math("ADD", m.math("MULTIPLY", m.bruit(3.0, 6), 0.5), fissures), 0.6, 0.15)
    M["roche"] = m.mat

    # Pierre taillée (arche, menhirs, socles, soubassements)
    m = Noeuds("pierre")
    var = m.bruit(1.6, 6, 0.6)
    pierre = m.rampe(var, [(0.3, (0.17, 0.15, 0.125)), (0.55, (0.26, 0.235, 0.2)), (0.8, (0.34, 0.31, 0.27))])
    taches = m.plage(m.bruit(4.0, 3), 0.55, 0.75)
    pierre = m.melange(m.math("MULTIPLY", taches, 0.5), pierre, (0.08, 0.075, 0.07))
    mousse = m.math("MULTIPLY", m.plage(m.normale_z(), 0.7, 0.95), m.plage(m.bruit(2.0, 4), 0.45, 0.62))
    pierre = m.melange(mousse, pierre, (0.05, 0.08, 0.02))
    m.couleur(m.melange(1.0, pierre, teinte(m), "MULTIPLY"))
    m.rugosite(0.85)
    m.relief(m.math("ADD", m.bruit(9.0, 5), m.math("MULTIPLY", m.bruit(1.5, 3), 0.5)), 0.35, 0.03)
    M["pierre"] = m.mat

    # Bois des planches : veines étirées verticalement
    m = Noeuds("bois")
    veine = m.bruit(1.0, 6, 0.6, m.echelle_vec(9.0, 9.0, 0.35), 2.0)
    bois = m.rampe(veine, [(0.3, (0.07, 0.035, 0.016)), (0.6, (0.15, 0.08, 0.036)), (0.85, (0.22, 0.13, 0.06))])
    m.couleur(m.melange(1.0, bois, teinte(m), "MULTIPLY"))
    m.rugosite(0.7)
    m.relief(veine, 0.25, 0.02)
    M["bois"] = m.mat

    m = Noeuds("bois_sombre")
    veine = m.bruit(1.0, 5, 0.6, m.echelle_vec(8.0, 8.0, 0.4), 2.0)
    m.couleur(m.melange(1.0, m.rampe(veine, [(0.3, (0.035, 0.02, 0.012)), (0.8, (0.08, 0.045, 0.025))]),
                        teinte(m), "MULTIPLY"))
    m.rugosite(0.6)
    M["bois_sombre"] = m.mat

    # Tuiles du toit
    m = Noeuds("toit")
    couleur, fac = m.brique(3.2, m.echelle_vec(1.0, 1.0, 1.0), 0.03, 0.42, 0.22)
    var = m.bruit(3.0, 4)
    toit = m.rampe(var, [(0.3, (0.11, 0.035, 0.022)), (0.7, (0.2, 0.065, 0.035))])
    toit = m.melange(1.0, toit, couleur, "MULTIPLY")
    mousse = m.math("MULTIPLY", m.plage(m.bruit(1.5, 4), 0.55, 0.7), 0.6)
    toit = m.melange(mousse, toit, (0.06, 0.08, 0.025))
    m.couleur(m.melange(1.0, toit, teinte(m), "MULTIPLY"))
    m.rugosite(0.75)
    m.relief(fac, 0.5, 0.03)
    M["toit"] = m.mat

    m = Noeuds("enduit")
    sale = m.plage(m.bruit(1.8, 6), 0.45, 0.8)
    m.couleur(m.melange(sale, (0.62, 0.58, 0.52), (0.36, 0.33, 0.29)))
    m.rugosite(0.8)
    m.relief(m.bruit(14.0, 3), 0.15, 0.01)
    M["enduit"] = m.mat

    m = Noeuds("rouge")
    sale = m.plage(m.bruit(1.8, 6), 0.45, 0.8)
    m.couleur(m.melange(sale, (0.42, 0.045, 0.03), (0.22, 0.03, 0.02)))
    m.rugosite(0.7)
    M["rouge"] = m.mat

    m = Noeuds("metal")
    m.couleur((0.025, 0.025, 0.03))
    m.bsdf.inputs["Metallic"].default_value = 0.6
    m.rugosite(0.45)
    M["metal"] = m.mat

    m = Noeuds("cuivre")
    m.couleur(m.rampe(m.bruit(3.0, 4), [(0.3, (0.09, 0.2, 0.15)), (0.7, (0.3, 0.17, 0.07))]))
    m.bsdf.inputs["Metallic"].default_value = 0.4
    m.rugosite(0.5)
    M["cuivre"] = m.mat

    # Fenêtres et lanternes allumées : leur lumière orangée est cuite sur ce qui les entoure
    m = Noeuds("lumiere")
    m.couleur((1.0, 0.6, 0.3))
    m.emission((1.0, 0.52, 0.2), 7.0)
    M["lumiere"] = m.mat

    m = Noeuds("lanterne")
    m.couleur((1.0, 0.65, 0.35))
    m.emission((1.0, 0.55, 0.22), 14.0)
    M["lanterne"] = m.mat

    m = Noeuds("lumiere_phare")
    m.couleur((1.0, 0.85, 0.6))
    m.emission((1.0, 0.75, 0.42), 16.0)
    M["lumiere_phare"] = m.mat

    m = Noeuds("ecorce")
    stries = m.bruit(1.0, 6, 0.6, m.echelle_vec(14.0, 14.0, 1.2), 1.5)
    m.couleur(m.melange(1.0, m.rampe(stries, [(0.3, (0.035, 0.026, 0.02)), (0.7, (0.1, 0.078, 0.058))]),
                        teinte(m), "MULTIPLY"))
    m.rugosite(0.9)
    m.relief(stries, 0.5, 0.03)
    M["ecorce"] = m.mat

    # Feuilles : cartes découpées par la texture peinte (UV « feuille »), teintées arbre par arbre
    m = Noeuds("feuilles")
    uv = m.nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "feuille"
    tex = m.nt.nodes.new("ShaderNodeTexImage")
    tex.image = image_feuilles
    tex.interpolation = "Linear"
    m.lien(uv.outputs["UV"], tex.inputs["Vector"])
    m.couleur(m.melange(1.0, tex.outputs["Color"], teinte(m), "MULTIPLY"))
    m.lien(tex.outputs["Alpha"], m.bsdf.inputs["Alpha"])
    m.rugosite(0.75)
    m.bsdf.inputs["Specular IOR Level"].default_value = 0.25
    M["feuilles"] = m.mat

    # Objets vivants : rendus par le site, leurs matières ici servent seulement à éclairer la cuisson
    for nom, c, force in (("glyphe", (0.55, 0.32, 1.0), 6.0), ("anneau", (0.85, 0.3, 0.95), 2.5),
                          ("cristal_vert", (0.25, 1.0, 0.55), 5.0), ("cristal_violet", (0.6, 0.35, 1.0), 5.0),
                          ("cristal_rose", (1.0, 0.35, 0.75), 5.0), ("cristal_roche", (0.45, 0.6, 1.0), 9.0)):
        m = Noeuds(nom)
        m.couleur(c)
        m.emission(c, force)
        M[nom] = m.mat

    m = Noeuds("eau")
    m.couleur((0.05, 0.08, 0.12))
    m.rugosite(0.05)
    M["eau"] = m.mat
    return M


def collection(nom, parent=None, taille=None):
    c = bpy.data.collections.get(nom) or bpy.data.collections.new(nom)
    if c.name not in (parent or bpy.context.scene.collection).children:
        (parent or bpy.context.scene.collection).children.link(c)
    if taille:
        c["taille"] = taille
    return c


class Construction:
    """Accumule des pièces (boîtes, cylindres, tubes, sphères bosselées) dans un seul maillage."""

    def __init__(self, nom, coll, M):
        self.nom, self.coll, self.M = nom, coll, M
        self.bm = bmesh.new()
        self.teinte = self.bm.verts.layers.float_color.new("teinte")
        self.mats = []

    def _idx(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _finir(self, verts, mat, couleur=(1, 1, 1)):
        idx = self._idx(mat)
        faces = {f for v in verts for f in v.link_faces}
        for f in faces:
            f.material_index = idx
            f.smooth = True
        for v in verts:
            v[self.teinte] = (*couleur, 1.0)
        return faces

    def boite(self, mat, m, taille, biseau=0.0, couleur=(1, 1, 1)):
        S = Matrix.Diagonal((*taille, 1.0))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m @ S)
        verts = r["verts"]
        faces = self._finir(verts, mat, couleur)
        for f in faces:
            f.smooth = False
        if biseau > 0:
            aretes = list({e for v in verts for e in v.link_edges})
            res = bmesh.ops.bevel(self.bm, geom=list(verts) + aretes, offset=biseau, offset_type="OFFSET",
                                  segments=2, profile=0.5, affect="EDGES", clamp_overlap=True)
            nv = {v for f in res["faces"] for v in f.verts}
            for v in nv:
                v[self.teinte] = (*couleur, 1.0)
            for f in res["faces"]:
                f.smooth = True
            verts = [v for v in set(verts) | nv if v.is_valid]
        return verts

    def cylindre(self, mat, m, r1, r2, h, segments=16, couleur=(1, 1, 1), lisse=True):
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segments,
                                  radius1=r1, radius2=r2, depth=h, matrix=m)
        faces = self._finir(r["verts"], mat, couleur)
        if not lisse:
            for f in faces:
                f.smooth = False
        return r["verts"]

    def sphere(self, mat, m, rayon, subdiv=2, couleur=(1, 1, 1)):
        r = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=rayon, matrix=m)
        self._finir(r["verts"], mat, couleur)
        return r["verts"]

    def tore(self, mat, m, rayon, epaisseur, segments=64, cotes=8):
        """Anneau plat (tore) dans le plan XY du repère m."""
        verts = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            for j in range(cotes):
                b = 2 * math.pi * j / cotes
                r = rayon + epaisseur * math.cos(b)
                verts.append(self.bm.verts.new(m @ Vector((r * math.cos(a), r * math.sin(a), epaisseur * math.sin(b)))))
        for i in range(segments):
            for j in range(cotes):
                a, b = i * cotes + j, i * cotes + (j + 1) % cotes
                c, d = ((i + 1) % segments) * cotes + (j + 1) % cotes, ((i + 1) % segments) * cotes + j
                self.bm.faces.new((verts[a], verts[d], verts[c], verts[b]))
        self._finir(verts, mat)
        return verts

    def tube(self, mat, points, rayons, cotes=8, couleur=(1, 1, 1), fermer=True):
        """Tube le long d'une suite de points (tronc, branche, racine), d'épaisseur variable."""
        anneaux = []
        n = len(points)
        normale = None
        for i, p in enumerate(points):
            t = (points[min(i + 1, n - 1)] - points[max(i - 1, 0)]).normalized()
            if normale is None:
                normale = t.orthogonal().normalized()
            else:
                normale = (normale - t * normale.dot(t)).normalized()
            b = t.cross(normale)
            r = rayons[i]
            anneaux.append([self.bm.verts.new(p + (normale * math.cos(2 * math.pi * k / cotes)
                                                   + b * math.sin(2 * math.pi * k / cotes)) * r) for k in range(cotes)])
        verts = [v for a in anneaux for v in a]
        for i in range(n - 1):
            for k in range(cotes):
                a, b = anneaux[i][k], anneaux[i][(k + 1) % cotes]
                c, d = anneaux[i + 1][(k + 1) % cotes], anneaux[i + 1][k]
                self.bm.faces.new((a, b, c, d))
        if fermer:
            bout = self.bm.verts.new(points[-1] + (points[-1] - points[-2]).normalized() * rayons[-1] * 0.5)
            verts.append(bout)
            for k in range(cotes):
                self.bm.faces.new((anneaux[-1][k], anneaux[-1][(k + 1) % cotes], bout))
        self._finir(verts, mat, couleur)
        return verts

    def demi_sphere(self, mat, m, rayon, couleur=(1, 1, 1)):
        r = bmesh.ops.create_uvsphere(self.bm, u_segments=20, v_segments=10, radius=rayon, matrix=m)
        centre = m.to_translation()
        haut = (m.to_3x3() @ Vector((0, 0, 1))).normalized()
        bas = [v for v in r["verts"] if (v.co - centre).dot(haut) < -1e-4]
        for v in bas:
            v.co -= haut * (v.co - centre).dot(haut)
        self._finir(r["verts"], mat, couleur)
        return r["verts"]

    def prisme(self, mat, pts, x0, x1, m, couleur=(1, 1, 1)):
        """Extrusion d'un polygone (y, z) entre x0 et x1, dans le repère m."""
        a = [self.bm.verts.new(m @ Vector((x0, y, z))) for y, z in pts]
        b = [self.bm.verts.new(m @ Vector((x1, y, z))) for y, z in pts]
        n = len(pts)
        self.bm.faces.new(list(reversed(a)))
        self.bm.faces.new(b)
        for i in range(n):
            j = (i + 1) % n
            self.bm.faces.new((a[i], a[j], b[j], b[i]))
        faces = self._finir(a + b, mat, couleur)
        for f in faces:
            f.smooth = False
        return a + b

    def bosseler(self, verts, centre, amplitude, frequence, graine=0.0):
        for v in verts:
            d = v.co - centre
            if d.length < 1e-6:
                continue
            v.co += d.normalized() * amplitude * fbm3(v.co * frequence + Vector((graine, 0, 0)), 3)

    def objet(self, recalculer=True, **props):
        if recalculer:
            bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        me = bpy.data.meshes.new(self.nom)
        self.bm.to_mesh(me)
        self.bm.free()
        for nom in self.mats:
            me.materials.append(self.M[nom])
        ob = bpy.data.objects.new(self.nom, me)
        self.coll.objects.link(ob)
        for k, v in props.items():
            ob[k] = v
        return ob


class Feuillage:
    """Cartes de feuilles : des rectangles pliés en V, découpés par la texture des feuilles.
    Les normales sont orientées depuis le centre de la couronne : l'arbre s'éclaire comme un volume."""

    def __init__(self):
        self.verts, self.faces, self.uv = [], [], []
        self.normales, self.teintes, self.balance = [], [], []
        self.nb = 0

    def carte(self, centre, normale, haut, largeur, hauteur, tuile, teinte, coeur, poids=0.5, phase=0.0, pli=0.22):
        n = normale.normalized()
        y = (haut - n * haut.dot(n))
        if y.length < 1e-4:
            y = n.orthogonal()
        y.normalize()
        x = y.cross(n).normalized()
        col, rang = tuile % 2, tuile // 2
        e = 0.004
        u0, u1 = col * 0.5 + e, col * 0.5 + 0.5 - e
        v0, v1 = rang * 0.5 + e, rang * 0.5 + 0.5 - e
        i0 = len(self.verts)
        for k, sy in enumerate((-0.5, 0.5)):
            for j, sx in enumerate((-0.5, 0.0, 0.5)):
                p = centre + x * (sx * largeur) + y * (sy * hauteur) + n * (pli * largeur * 0.5 if sx == 0.0 else 0.0)
                self.verts.append(tuple(p))
                vers_coeur = (p - coeur)
                vers_coeur = vers_coeur.normalized() if vers_coeur.length > 1e-4 else n
                self.normales.append(tuple((n * 0.3 + vers_coeur * 0.7).normalized()))
                self.teintes.append((*teinte, 1.0))
                self.balance.append((poids, phase, 0.0, 1.0))
        for a, b, c, d in ((0, 1, 4, 3), (1, 2, 5, 4)):
            self.faces.append((i0 + a, i0 + b, i0 + c, i0 + d))
        uvs = {0: (u0, v0), 1: ((u0 + u1) / 2, v0), 2: (u1, v0), 3: (u0, v1), 4: ((u0 + u1) / 2, v1), 5: (u1, v1)}
        for a, b, c, d in ((0, 1, 4, 3), (1, 2, 5, 4)):
            self.uv.extend([uvs[a], uvs[b], uvs[c], uvs[d]])
        self.nb += 1

    def objet(self, coll, M, nom="feuillage", **props):
        me = bpy.data.meshes.new(nom)
        me.from_pydata(self.verts, [], self.faces)
        couche = me.uv_layers.new(name="feuille")
        couche.data.foreach_set("uv", [c for uv in self.uv for c in uv])
        for nom_attr, donnees in (("teinte", self.teintes), ("balancement", self.balance)):
            a = me.color_attributes.new(nom_attr, "FLOAT_COLOR", "POINT")
            a.data.foreach_set("color", [c for t in donnees for c in t])
        me.materials.append(M["feuilles"])
        me.shade_smooth()
        me.normals_split_custom_set_from_vertices(self.normales)
        ob = bpy.data.objects.new(nom, me)
        coll.objects.link(ob)
        for k, v in props.items():
            ob[k] = v
        log(f"feuillage : {self.nb} cartes")
        return ob


def repere(x, y, z, rz=0.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, "Z")


def orientation(m_local, x, y, z, rx=0.0, ry=0.0, rz=0.0):
    return m_local @ Matrix.Translation((x, y, z)) @ (Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(ry, 4, "Y")
                                                      @ Matrix.Rotation(rx, 4, "X"))


def vers(dx, dy):
    """Rotation autour de Z pour que l'avant d'un bâtiment (son -Y local) regarde dans la direction (dx, dy)."""
    return math.atan2(dx, -dy)


def ancre(coll, nom, pos):
    e = bpy.data.objects.new(nom, None)
    e.empty_display_type = "SPHERE"
    e.empty_display_size = 0.3
    e.location = pos
    coll.objects.link(e)
    return e


def lierre(feuillage, centre, normale, rnd, nombre=6, etendue=0.8, taille=0.45):
    """Quelques petites cartes de feuilles plaquées contre un mur ou une pierre."""
    teinte = (lerp(0.75, 0.95, rnd.random()), lerp(0.85, 1.0, rnd.random()), lerp(0.6, 0.8, rnd.random()))
    for k in range(nombre):
        off = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * etendue
        off -= normale * off.dot(normale)
        c = centre + off + normale * 0.04
        n = (normale + Vector((rnd.gauss(0, 0.35), rnd.gauss(0, 0.35), rnd.gauss(0, 0.35)))).normalized()
        feuillage.carte(c, n, Vector((0, 0, 1)), taille, taille, TUILE_FEUILLU, teinte, c - normale, 0.1, rnd.random(), 0.15)


# =========================================================================
#  5. L'ÎLE, LES BÂTIMENTS ET LE DÉCOR
# =========================================================================

NB_ANNEAUX, NB_SECTEURS, NB_ETAGES = 120, 448, 72


def construire_ile(M, c_terrain, c_roche):
    t0 = time.time()
    # --- Dessus : grille polaire, du centre jusqu'au bord, puis une lèvre d'herbe qui retombe
    verts, masques, eaux, faces = [], [], [], []
    bords = [rayon_bord(2 * math.pi * i / NB_SECTEURS) for i in range(NB_SECTEURS)]

    def ajouter(x, y, z, mc, me):
        verts.append((x, y, z))
        masques.append(mc)
        eaux.append(me)

    mc = masque_chemin(0, 0)
    ajouter(0.0, 0.0, hauteur(0, 0, mc), mc, masque_eau(0, 0))
    for j in range(1, NB_ANNEAUX + 2):
        for i in range(NB_SECTEURS):
            th = 2 * math.pi * i / NB_SECTEURS
            if j <= NB_ANNEAUX:
                rr = bords[i] * (j / NB_ANNEAUX) ** 0.92
                x, y = rr * math.cos(th), rr * math.sin(th)
                mc = masque_chemin(x, y)
                ajouter(x, y, hauteur(x, y, mc), mc, masque_eau(x, y))
            else:
                rr = bords[i] + 0.35
                x, y = rr * math.cos(th), rr * math.sin(th)
                ajouter(x, y, hauteur(bords[i] * math.cos(th), bords[i] * math.sin(th)) - 0.55, 0.0,
                        masque_eau(bords[i] * math.cos(th), bords[i] * math.sin(th)))

    def idx(j, i):
        return 0 if j == 0 else 1 + (j - 1) * NB_SECTEURS + (i % NB_SECTEURS)
    for i in range(NB_SECTEURS):
        faces.append((0, idx(1, i), idx(1, i + 1)))
    for j in range(1, NB_ANNEAUX + 1):
        for i in range(NB_SECTEURS):
            faces.append((idx(j, i), idx(j + 1, i), idx(j + 1, i + 1), idx(j, i + 1)))
    me = bpy.data.meshes.new("ile_dessus")
    me.from_pydata(verts, [], faces)
    me.materials.append(M["herbe"])
    for nom, valeurs in (("chemin", masques), ("eau", eaux), ("teinte", [1.0] * len(verts))):
        attr = me.color_attributes.new(nom, "FLOAT_COLOR", "POINT")
        attr.data.foreach_set("color", [c for v in valeurs for c in (v, v, v, 1.0)])
    me.shade_smooth()
    ob = bpy.data.objects.new("ile_dessus", me)
    ob["terrain"] = 1
    c_terrain.objects.link(ob)
    log(f"dessus de l'île : {len(verts)} sommets ({time.time() - t0:.1f} s)")

    # --- Dessous : falaise puis rocher qui s'effile vers une pointe, en blocs, colonnes et strates
    t0 = time.time()
    verts, faces = [], []
    pointe = Vector((3.0, -2.0, -36.0))
    for k in range(NB_ETAGES):
        t = k / NB_ETAGES
        for i in range(NB_SECTEURS):
            th = 2 * math.pi * i / NB_SECTEURS
            rb = bords[i]
            z_bord = hauteur(rb * math.cos(th), rb * math.sin(th)) - 0.45
            if t < 0.09:
                f = 0.99 - 0.25 * t
                z = z_bord - 0.15 - t / 0.09 * 3.05
            else:
                u = (t - 0.09) / 0.91
                f = 0.98 * (1.0 - u) ** 0.7
                z = z_bord - 3.2 - u ** 0.92 * (abs(pointe.z) + z_bord - 3.2 + 4 * n3(math.cos(th), math.sin(th), 3.0))
            cx, cy = lerp(0, pointe.x, t * t), lerp(0, pointe.y, t * t)
            x, y = cx + rb * f * math.cos(th), cy + rb * f * math.sin(th)
            p = Vector((x, y, z))
            radial = Vector((math.cos(th), math.sin(th), 0.0))
            fort = smoothstep(0.0, 0.5, t) * (1.0 - smoothstep(0.88, 1.0, t))
            depl = (0.2 + 2.6 * fort) * fbm3(p * Vector((0.075, 0.075, 0.12)), 5)
            depl += 1.6 * fort * (crete(p * Vector((0.09, 0.09, 0.05))) - 0.45)
            depl += 0.7 * n3(math.cos(th) * 11.0, math.sin(th) * 11.0, z * 0.04) * smoothstep(0.02, 0.2, t)
            depl += 0.5 * abs(n3(x * 0.35, y * 0.35, z * 0.5)) * smoothstep(0.0, 0.1, t)
            p += radial * depl
            verts.append(tuple(p))
    verts.append(tuple(pointe))
    for k in range(NB_ETAGES - 1):
        for i in range(NB_SECTEURS):
            a = k * NB_SECTEURS + i
            b = k * NB_SECTEURS + (i + 1) % NB_SECTEURS
            faces.append((a, a + NB_SECTEURS, b + NB_SECTEURS, b))
    dernier = (NB_ETAGES - 1) * NB_SECTEURS
    for i in range(NB_SECTEURS):
        faces.append((dernier + (i + 1) % NB_SECTEURS, dernier + i, len(verts) - 1))
    me = bpy.data.meshes.new("ile_roche")
    me.from_pydata(verts, [], faces)
    me.materials.append(M["roche"])
    attr = me.color_attributes.new("teinte", "FLOAT_COLOR", "POINT")
    attr.data.foreach_set("color", [1.0] * (4 * len(verts)))
    me.shade_smooth()
    ob = bpy.data.objects.new("ile_roche", me)
    ob["groupe"] = "roche"
    c_roche.objects.link(ob)
    log(f"dessous de l'île : {len(verts)} sommets ({time.time() - t0:.1f} s)")
    return BVHTree.FromPolygons([Vector(v) for v in verts], faces), bords


def racines_et_cristaux(M, c_roche, vivant, reperes, arbre_roche, bords, rnd):
    """Racines qui pendent sous la lèvre d'herbe, et grappes de cristaux lumineux dans la roche."""
    c = Construction("racines", c_roche, M)
    for k in range(80):
        i = rnd.randrange(len(bords))
        th = 2 * math.pi * i / len(bords)
        rb = bords[i]
        if dist_ruisseau(rb * math.cos(th), rb * math.sin(th)) < 3.0:
            continue
        radial = Vector((math.cos(th), math.sin(th), 0))
        depart = Vector((rb * math.cos(th), rb * math.sin(th), hauteur(rb * math.cos(th), rb * math.sin(th)) - 0.55)) - radial * 0.2
        longueur = rnd.uniform(1.2, 5.5)
        pts, rayons = [], []
        n = 9
        for s in range(n):
            u = s / (n - 1)
            p = depart + radial * (0.35 * math.sin(math.pi * u * 0.8) + 0.15 * u) + Vector((0, 0, -longueur * u))
            p += Vector((n3(k, u * 3, 1.0), n3(k, u * 3, 5.0), 0)) * 0.25 * u
            pts.append(p)
            rayons.append(lerp(rnd.uniform(0.04, 0.08), 0.008, u))
        c.tube("ecorce", pts, rayons, 5, (0.8, 0.75, 0.7))
        if rnd.random() < 0.4:
            # petite ramification
            a = pts[3]
            b = a + radial * 0.3 + Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), -longueur * 0.4))
            c.tube("ecorce", [a, a.lerp(b, 0.5) + radial * 0.1, b], [rayons[3] * 0.7, rayons[3] * 0.4, 0.006], 4)
    c.objet(groupe="roche")

    # Cristaux : on vise la roche depuis l'extérieur pour poser chaque grappe sur sa surface
    g = Construction("vivant_cristaux_roche", vivant, M)
    nb = 0
    for k in range(9):
        th = 2 * math.pi * (k + rnd.uniform(0.2, 0.8)) / 9
        z = rnd.uniform(-20.0, -6.0)
        origine = Vector((70 * math.cos(th), 70 * math.sin(th), z))
        cible = Vector((2.0, -1.0, z - 2.0))
        hit, nrm, _, _ = arbre_roche.ray_cast(origine, (cible - origine).normalized(), 200.0)
        if hit is None:
            continue
        axe0 = (nrm + Vector((0, 0, -0.5))).normalized()
        for s in range(rnd.randint(4, 7)):
            axe = (axe0 + Vector((rnd.gauss(0, 0.35), rnd.gauss(0, 0.35), rnd.gauss(0, 0.3)))).normalized()
            longueur = rnd.uniform(0.5, 1.7) * (1.4 if s == 0 else 1.0)
            rayon = longueur * rnd.uniform(0.11, 0.16)
            base = hit - nrm * 0.15 + Vector((rnd.gauss(0, 0.25), rnd.gauss(0, 0.25), rnd.gauss(0, 0.2)))
            q = axe.to_track_quat("Z", "Y").to_matrix().to_4x4()
            m = Matrix.Translation(base + axe * longueur * 0.5) @ q
            v = g.cylindre("cristal_roche", m, rayon, rayon * 0.85, longueur, 6, lisse=False)
            # pointe
            haut = [vv for vv in v if (vv.co - (base + axe * longueur * 0.5)).dot(axe) > 0]
            centre_haut = sum((vv.co for vv in haut), Vector()) / max(1, len(haut))
            for vv in haut:
                vv.co = centre_haut.lerp(vv.co, 0.35) + axe * rayon * 1.2
        ancre(reperes, f"cristal_roche_{nb + 1}", hit + nrm * 0.6)
        nb += 1
    g.objet(vivant="cristal_roche")
    log(f"cristaux sous l'île : {nb} grappes")


def rochers_flottants(M, c_roche, rnd):
    places = [(-46, -18, 4, 3.2), (-38, 30, -6, 2.4), (8, 48, 2, 3.6), (44, -26, -3, 2.8),
              (-20, -46, -10, 2.0), (52, 14, 8, 1.6), (-54, 6, 12, 1.4), (30, -44, 6, 1.8)]
    for n, (x, y, z, r) in enumerate(places):
        c = Construction(f"rocher_flottant_{n + 1}", c_roche, M)
        centre = Vector((x, y, z))
        m = Matrix.Translation(centre) @ Matrix.Diagonal((1.0, 1.0, 0.75, 1.0))
        v = c.sphere("roche", m, r, 3)
        for vv in v:
            d = vv.co - centre
            if d.z > 0:
                vv.co.z = centre.z + d.z * 0.3
            else:
                vv.co.z = centre.z + d.z * (1.6 + 0.6 * rnd.random())
        c.bosseler(v, centre, r * 0.22, 0.9 / r, rnd.random() * 50)
        if r > 2.3:
            # Un tapis d'herbe sur le dessus des plus gros
            dessus = max(vv.co.z for vv in v)
            vh = c.cylindre("herbe", Matrix.Translation(centre + Vector((0, 0, dessus - centre.z - 0.05))),
                            r * 0.92, r * 0.8, 0.22, 24)
            c.bosseler(vh, centre + Vector((0, 0, dessus - centre.z)), 0.08, 1.2)
        c.objet(mobile=1, flotte=round(0.25 + rnd.random() * 0.35, 2))


def construire_arche(M, coll, reperes, feuillage, rnd):
    x, y, _ = SITES["arche"]
    z0 = HAUTEUR_SITE["arche"]
    L = repere(x, y, z0, 0.0)
    c = Construction("arche", coll, M)
    for cote in (-1, 1):
        px = cote * 2.05
        c.boite("pierre", orientation(L, px, 0, 0.1), (1.25, 1.2, 0.6), 0.05, (0.9, 0.88, 0.85))
        zb = 0.4
        for k in range(6):
            h = 0.5
            t = 0.86 + 0.08 * rnd.random()
            c.boite("pierre", orientation(L, px + rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), zb + h / 2,
                                          rz=rnd.uniform(-0.05, 0.05)), (0.86, 0.86, h - 0.03), 0.045, (t, t, t * 0.97))
            zb += h
        c.boite("pierre", orientation(L, px, 0, zb + 0.13), (1.05, 1.0, 0.26), 0.04)
        OBSTACLES.append(((L @ Vector((px, 0, 0))).x, (L @ Vector((px, 0, 0))).y, 0.85))
        # Lierre qui grimpe sur le pilier
        for hz in (0.8, 1.6, 2.3):
            lierre(feuillage, L @ Vector((px + cote * 0.45, -0.2, hz)), (L.to_3x3() @ Vector((cote, 0, 0))).normalized(), rnd, 5, 0.35, 0.42)
        lierre(feuillage, L @ Vector((px, -0.45, 1.0)), (L.to_3x3() @ Vector((0, -1, 0))).normalized(), rnd, 4, 0.35, 0.4)
        # Muret en ruine qui prolonge l'arche
        for k in range(4):
            lx = px + cote * (1.0 + k * 0.8)
            hauteur_muret = 1.2 - k * 0.25 + rnd.uniform(-0.1, 0.1)
            for etage in range(max(1, int(hauteur_muret / 0.4))):
                t = 0.8 + 0.15 * rnd.random()
                c.boite("pierre", orientation(L, lx + rnd.uniform(-0.05, 0.05), rnd.uniform(-0.06, 0.06),
                                              0.0 + etage * 0.4 + 0.2, rz=rnd.uniform(-0.08, 0.08)),
                        (0.76, 0.6, 0.38), 0.05, (t, t * 0.98, t * 0.95))
            OBSTACLES.append(((L @ Vector((lx, 0, 0))).x, (L @ Vector((lx, 0, 0))).y, 0.5))
        lierre(feuillage, L @ Vector((px + cote * 1.8, -0.32, 0.6)), (L.to_3x3() @ Vector((0, -1, 0))).normalized(), rnd, 6, 0.6, 0.45)
    zc = 3.66
    n = 9
    for i in range(n):
        a = math.pi * (i + 0.5) / n
        rr = 2.05
        cle = i == n // 2
        X = Vector((math.sin(a), 0, -math.cos(a)))
        Y = Vector((0, 1, 0))
        Z = Vector((math.cos(a), 0, math.sin(a)))
        R = Matrix((X, Y, Z)).transposed().to_4x4()
        m = L @ Matrix.Translation((rr * math.cos(a), 0, zc + rr * math.sin(a) + (0.05 if cle else 0))) @ R
        c.boite("pierre", m, (0.66, 0.92 if cle else 0.86, 0.72 if cle else 0.6), 0.04, (0.95, 0.93, 0.9))
    lierre(feuillage, L @ Vector((-1.6, -0.45, 5.0)), Vector((0, -1, 0.3)).normalized(), rnd, 7, 0.5, 0.45)
    # Lanternes de part et d'autre
    for cote in (-1, 1):
        lx, ly = cote * 3.3, -1.3
        c.cylindre("bois_sombre", orientation(L, lx, ly, 0.75), 0.06, 0.05, 1.5, 8)
        c.boite("metal", orientation(L, lx, ly, 1.55), (0.26, 0.26, 0.04))
        c.sphere("lanterne", orientation(L, lx, ly, 1.68), 0.1, 2)
        c.boite("metal", orientation(L, lx, ly, 1.86), (0.3, 0.3, 0.05))
        ancre(reperes, f"lanterne_arche_{1 if cote < 0 else 2}", L @ Vector((lx, ly, 1.68)))
    c.objet()


def construire_atelier(M, coll, reperes, feuillage, rnd):
    x, y, _ = SITES["atelier"]
    z0 = HAUTEUR_SITE["atelier"]
    L = repere(x, y, z0, vers(5.0, -1.8))
    c = Construction("atelier", coll, M)
    larg, prof, hmur = 6.0, 4.4, 2.6
    base = 0.45
    for k in range(-3, 4):
        OBSTACLES.append(((L @ Vector((k * 1.0, 0, 0))).x, (L @ Vector((k * 1.0, 0, 0))).y, 2.7))
    c.boite("pierre", orientation(L, 0, 0, base / 2 - 0.25), (larg + 0.5, prof + 0.5, base + 0.5), 0.06)
    # Murs en planches verticales (une teinte par planche)
    zb = base
    for cote in (-1, 1):
        n = int(larg / 0.3)
        for k in range(n):
            t = 0.75 + 0.35 * rnd.random()
            px = -larg / 2 + (k + 0.5) * larg / n
            c.boite("bois", orientation(L, px, cote * prof / 2, zb + hmur / 2), (larg / n - 0.015, 0.09, hmur),
                    0.0, (t, t * 0.95, t * 0.9))
        n = int(prof / 0.3)
        for k in range(n):
            t = 0.75 + 0.35 * rnd.random()
            py = -prof / 2 + (k + 0.5) * prof / n
            c.boite("bois", orientation(L, cote * larg / 2, py, zb + hmur / 2), (0.09, prof / n - 0.015, hmur),
                    0.0, (t, t * 0.95, t * 0.9))
    for cx in (-1, 1):
        for cy in (-1, 1):
            c.boite("bois_sombre", orientation(L, cx * larg / 2, cy * prof / 2, zb + hmur / 2), (0.24, 0.24, hmur + 0.1), 0.02)
    for cy in (-1, 1):
        c.boite("bois_sombre", orientation(L, 0, cy * prof / 2, zb + hmur - 0.1), (larg + 0.2, 0.2, 0.2), 0.02)
    # Pignons
    zt = zb + hmur
    faitage = 1.8
    for cx in (-1, 1):
        c.prisme("bois", [(-prof / 2, zt), (prof / 2, zt), (0, zt + faitage)], cx * larg / 2 - 0.05,
                 cx * larg / 2 + 0.05, L, (0.85, 0.82, 0.78))
    # Toit en deux pans
    debord = 0.45
    pente = math.atan2(faitage, prof / 2)
    long_pan = (prof / 2 + debord) / math.cos(pente)
    for cy in (-1, 1):
        cy_c = cy * (prof / 2 + debord) / 2
        cz = zt + faitage - (prof / 2 + debord) / 2 * math.tan(pente) + 0.1
        c.boite("toit", orientation(L, 0, cy_c, cz, rx=cy * pente), (larg + 0.9, long_pan + 0.05, 0.16), 0.02)
    c.boite("bois_sombre", orientation(L, 0, 0, zt + faitage + 0.16), (larg + 1.0, 0.22, 0.2), 0.03)
    # Cheminée qui fume (ancre pour la fumée)
    c.boite("pierre", orientation(L, 1.7, 0.9, zt + 1.6), (0.65, 0.65, 2.3), 0.04)
    c.boite("pierre", orientation(L, 1.7, 0.9, zt + 2.8), (0.8, 0.8, 0.14), 0.03)
    ancre(reperes, "fumee", L @ Vector((1.7, 0.9, zt + 3.0)))

    # Fenêtres allumées (avec jardinière fleurie) et porte sur la façade avant (-Y)
    def fenetre(px, py, face_y, lx=0.95, lz=1.05, cz=1.55):
        dy = face_y * 0.06
        c.boite("lumiere", orientation(L, px, py + dy, zb + cz), (lx, 0.04, lz))
        for s in (-1, 1):
            c.boite("bois_sombre", orientation(L, px + s * lx / 2, py + dy * 1.5, zb + cz), (0.1, 0.12, lz + 0.1))
            c.boite("bois_sombre", orientation(L, px, py + dy * 1.5, zb + cz + s * lz / 2), (lx + 0.1, 0.12, 0.1))
        c.boite("bois_sombre", orientation(L, px, py + dy * 1.3, zb + cz), (0.05, 0.1, lz))
        c.boite("bois_sombre", orientation(L, px, py + dy * 1.3, zb + cz), (lx, 0.1, 0.05))
        c.boite("bois", orientation(L, px, py + dy * 3.2, zb + cz - lz / 2 - 0.16), (lx + 0.2, 0.28, 0.2), 0.02)
        normale = (L.to_3x3() @ Vector((0, face_y, 0))).normalized()
        for s in range(5):
            p = L @ Vector((px + (s - 2) * lx * 0.22, py + dy * 3.4, zb + cz - lz / 2 - 0.02))
            n = (normale + Vector((0, 0, 0.9)) + Vector((rnd.gauss(0, 0.3), rnd.gauss(0, 0.3), 0))).normalized()
            feuillage.carte(p, n, Vector((0, 0, 1)), 0.38, 0.32, TUILE_BUISSON, (1.0, 1.0, 1.0), p - normale, 0.15, rnd.random(), 0.2)
    fenetre(-1.6, -prof / 2, -1)
    fenetre(1.7, -prof / 2, -1)
    fenetre(-1.2, prof / 2, 1)
    # Porte
    c.boite("bois_sombre", orientation(L, 0.05, -prof / 2 - 0.06, zb + 1.0), (1.0, 0.08, 2.0), 0.02, (0.9, 0.9, 0.9))
    for s in (-1, 1):
        c.boite("bois", orientation(L, 0.05 + s * 0.56, -prof / 2 - 0.09, zb + 1.05), (0.12, 0.1, 2.15))
    c.boite("bois", orientation(L, 0.05, -prof / 2 - 0.09, zb + 2.15), (1.25, 0.12, 0.12))
    c.sphere("metal", orientation(L, 0.4, -prof / 2 - 0.13, zb + 1.0), 0.04, 1)
    # Marche, lanterne, banc, tonneaux, caisses
    c.boite("pierre", orientation(L, 0.05, -prof / 2 - 0.45, base - 0.12), (1.6, 0.7, 0.24), 0.04)
    c.boite("metal", orientation(L, 0.85, -prof / 2 - 0.25, zb + 2.25), (0.05, 0.4, 0.05))
    c.sphere("lanterne", orientation(L, 0.85, -prof / 2 - 0.42, zb + 2.0), 0.09, 2)
    c.boite("metal", orientation(L, 0.85, -prof / 2 - 0.42, zb + 2.16), (0.22, 0.22, 0.04))
    ancre(reperes, "lanterne_atelier", L @ Vector((0.85, -prof / 2 - 0.42, zb + 2.0)))
    c.boite("bois", orientation(L, -1.6, -prof / 2 - 0.55, base + 0.0), (1.5, 0.38, 0.07), 0.015)
    for s in (-1, 1):
        c.boite("bois_sombre", orientation(L, -1.6 + s * 0.62, -prof / 2 - 0.55, base - 0.22), (0.08, 0.32, 0.42))
    for k, (bx, by) in enumerate(((larg / 2 + 0.55, -1.2), (larg / 2 + 0.6, -0.4), (larg / 2 + 0.5, 0.9))):
        v = c.cylindre("bois", orientation(L, bx, by, base - 0.25 + 0.45), 0.3, 0.3, 0.9, 14, (0.8, 0.75, 0.7))
        for vv in v:
            local = L.inverted() @ vv.co
            hz = (local.z - (base - 0.25 + 0.45)) / 0.45
            vv.co = L @ Vector((bx + (local.x - bx) * (1.0 + 0.12 * (1 - hz * hz)),
                                by + (local.y - by) * (1.0 + 0.12 * (1 - hz * hz)), local.z))
        if k < 2:
            c.cylindre("metal", orientation(L, bx, by, base - 0.25 + 0.2), 0.335, 0.335, 0.05, 14)
            c.cylindre("metal", orientation(L, bx, by, base - 0.25 + 0.7), 0.335, 0.335, 0.05, 14)
    c.boite("bois", orientation(L, -larg / 2 - 0.6, -1.0, base - 0.05, rz=0.2), (0.7, 0.7, 0.6), 0.03, (0.9, 0.8, 0.7))
    c.boite("bois", orientation(L, -larg / 2 - 0.55, -0.9, base + 0.5, rz=-0.15), (0.5, 0.5, 0.45), 0.03, (0.8, 0.75, 0.65))
    # Tas de bois contre le pignon
    for k in range(14):
        rang, col = divmod(k, 5)
        c.cylindre("bois", orientation(L, -larg / 2 - 0.35, 0.9 + (col - 2) * 0.24 + (0.12 if rang % 2 else 0), base - 0.15 + rang * 0.21,
                                       rx=math.pi / 2), 0.11, 0.11, 0.7, 8, (0.95, 0.8, 0.6))
    # Parabole et antenne sur le toit (un clin d'œil aux réseaux et à l'IoT)
    ax, ay = -1.9, 0.6
    az = zt + faitage - (0.6) * math.tan(pente)
    c.cylindre("metal", orientation(L, ax, ay, az + 0.6), 0.03, 0.03, 1.4, 8)
    c.cylindre("metal", orientation(L, ax + 0.9, -0.2, az + 0.9), 0.015, 0.01, 2.2, 6)
    disque = orientation(L, ax, ay - 0.15, az + 1.1, rx=math.radians(-60))
    c.demi_sphere("cuivre", disque @ Matrix.Diagonal((0.45, 0.45, 0.16, 1)), 1.0)
    # Clôture le long du chemin
    for k in range(7):
        px = larg / 2 + 1.6
        py = -prof / 2 - 1.2 + k * 1.15
        hv = 1.05 + rnd.uniform(-0.05, 0.05)
        c.boite("bois", orientation(L, px, py, base - 0.3 + hv / 2, rz=rnd.uniform(-0.1, 0.1)), (0.11, 0.11, hv), 0.015,
                (0.7, 0.68, 0.62))
        if k < 6:
            for hz in (0.45, 0.85):
                c.boite("bois", orientation(L, px, py + 0.575, base - 0.3 + hz, rx=rnd.uniform(-0.03, 0.03)),
                        (0.06, 1.15, 0.08), 0.01, (0.75, 0.72, 0.65))
    c.objet()


def construire_cercle(M, coll, vivant, rnd):
    cx, cy, _ = SITES["cercle"]
    z0 = HAUTEUR_SITE["cercle"]
    c = Construction("cercle", coll, M)
    OBSTACLES.append((cx, cy, 3.1))
    c.cylindre("pierre", repere(cx, cy, z0 + 0.05), 1.9, 1.85, 0.4, 40, (0.9, 0.88, 0.85))
    c.cylindre("pierre", repere(cx, cy, z0 + 0.3), 1.3, 1.25, 0.12, 40)
    for k in range(14):
        a = 2 * math.pi * k / 14
        c.boite("pierre", repere(cx + 2.6 * math.cos(a), cy + 2.6 * math.sin(a), z0 - 0.05, a),
                (0.5, 1.05, 0.14), 0.03, (0.8 + 0.15 * rnd.random(),) * 3)
    a = Construction("vivant_anneau", vivant, M)
    a.tore("anneau", repere(cx, cy, z0 + 0.38), 1.05, 0.035)
    a.tore("anneau", repere(cx, cy, z0 + 0.38), 0.62, 0.025, 48)
    a.objet(vivant="anneau")
    # Sept menhirs, un par famille de compétences, chacun avec un glyphe lumineux tourné vers le centre
    n = 7
    for k in range(n):
        ang = math.radians(150) + 2 * math.pi * (k + 0.5) / n
        rr = 5.0
        px, py = cx + rr * math.cos(ang), cy + rr * math.sin(ang)
        OBSTACLES.append((px, py, 0.75))
        h = 2.6 + 0.8 * rnd.random()
        m = repere(px, py, z0 + h / 2 - 0.3, ang + math.pi / 2) @ Matrix.Rotation(rnd.uniform(-0.06, 0.06), 4, "X") \
            @ Matrix.Rotation(rnd.uniform(-0.05, 0.05), 4, "Y")
        # Les sommets déjà construits sont marqués : seuls ceux du nouveau menhir seront déformés
        for vv in c.bm.verts:
            vv.tag = True
        v = c.boite("pierre", m, (1.0, 0.62, h), 0.0, (0.85 + 0.15 * rnd.random(),) * 3)
        faces = list({f for vv in v for f in vv.link_faces})
        bmesh.ops.subdivide_edges(c.bm, edges=list({e for f in faces for e in f.edges}), cuts=5, use_grid_fill=True)
        tous = [vv for vv in c.bm.verts if not vv.tag]
        centre = m.to_translation()
        for vv in tous:
            lz = (vv.co - centre).dot(m.to_3x3() @ Vector((0, 0, 1))) / h + 0.5
            haut = m.to_3x3() @ Vector((0, 0, 1))
            d = vv.co - centre
            horiz = d - haut * d.dot(haut)
            vv.co -= horiz * (0.28 * lz * lz)
            if lz > 0.85:
                vv.co -= haut * (lz - 0.85) * 0.9 * (horiz.length / 0.5) ** 2
            vv.co += (d.normalized() if d.length > 0 else d) * 0.07 * fbm3(vv.co * 1.3 + Vector((k * 9.0, 0, 0)), 3)
            vv[c.teinte] = (0.85 + 0.1 * math.sin(k * 3.1),) * 3 + (1.0,)
        for f in {f for vv in tous for f in vv.link_faces}:
            f.smooth = True
        c.bm.normal_update()
        arbre = BVHTree.FromBMesh(c.bm)
        origine = Vector((cx, cy, z0 + 1.55))
        cible = Vector((px, py, z0 + 1.55))
        hit, nrm, _, _ = arbre.ray_cast(origine, (cible - origine).normalized(), 10.0)
        if hit is None:
            continue
        g = Construction(f"vivant_glyphe_{k + 1}", vivant, M)
        X = Vector((0, 0, 1)).cross(nrm).normalized()
        Z = nrm.normalized()
        Y = Z.cross(X)
        G = Matrix.Translation(hit + nrm * 0.012) @ Matrix((X, Y, Z)).transposed().to_4x4()
        motif = k % 4
        if motif == 0:
            for s in range(10):
                a2 = 2 * math.pi * s / 10
                g.boite("glyphe", G @ Matrix.Translation((0.2 * math.cos(a2), 0.2 * math.sin(a2), 0)) @ Matrix.Rotation(a2, 4, "Z"),
                        (0.05, 0.13, 0.03))
            g.boite("glyphe", G, (0.05, 0.22, 0.03))
        elif motif == 1:
            for s, l in ((-0.16, 0.18), (0.0, 0.34), (0.16, 0.18)):
                g.boite("glyphe", G @ Matrix.Translation((0, s, 0)), (l, 0.05, 0.03))
            g.boite("glyphe", G @ Matrix.Translation((0, 0, 0)), (0.05, 0.4, 0.03))
        elif motif == 2:
            for s in range(3):
                a2 = 2 * math.pi * s / 3 + math.pi / 2
                g.boite("glyphe", G @ Matrix.Translation((0.11 * math.cos(a2 + math.pi / 3), 0.11 * math.sin(a2 + math.pi / 3), 0))
                        @ Matrix.Rotation(a2 + math.pi / 3 + math.pi / 2, 4, "Z"), (0.36, 0.05, 0.03))
            g.boite("glyphe", G, (0.07, 0.07, 0.03))
        else:
            g.boite("glyphe", G @ Matrix.Translation((-0.08, 0, 0)) @ Matrix.Rotation(0.5, 4, "Z"), (0.05, 0.38, 0.03))
            g.boite("glyphe", G @ Matrix.Translation((0.08, 0, 0)) @ Matrix.Rotation(-0.5, 4, "Z"), (0.05, 0.38, 0.03))
            g.boite("glyphe", G @ Matrix.Translation((0, -0.2, 0)), (0.3, 0.05, 0.03))
        g.objet(vivant="glyphe", rang=k)
    # Deux bancs de pierre face au cercle
    for a in (math.radians(-35), math.radians(205)):
        bx, by = cx + 7.0 * math.cos(a), cy + 7.0 * math.sin(a)
        L = repere(bx, by, hauteur(bx, by), a + math.pi / 2)
        c.boite("pierre", orientation(L, 0, 0, 0.42), (1.7, 0.45, 0.12), 0.03, (0.95, 0.93, 0.9))
        for s in (-1, 1):
            c.boite("pierre", orientation(L, s * 0.6, 0, 0.18), (0.22, 0.4, 0.4), 0.02)
        OBSTACLES.append((bx, by, 1.0))
    c.objet()


def construire_cristaux(M, coll, vivant, rnd):
    sx, sy, _ = SITES["cristaux"]
    z0 = HAUTEUR_SITE["cristaux"]
    c = Construction("socles", coll, M)
    face = Vector((-6.5, 7.0)).normalized()          # vers le point de vue de la caméra
    perp = Vector((face.y, -face.x))
    couleurs = (("cristal_vert", "ecopay"), ("cristal_violet", "boutik"), ("cristal_rose", "monde"))
    for k, (mat, nom) in enumerate(couleurs):
        off = (k - 1) * 2.3
        recul = 0.6 if k == 1 else 0.0
        px, py = sx + perp.x * off - face.x * recul, sy + perp.y * off - face.y * recul
        OBSTACLES.append((px, py, 0.8))
        hc = 1.05 + (0.25 if k == 1 else 0.0)
        c.cylindre("pierre", repere(px, py, z0 + 0.05), 0.62, 0.58, 0.3, 24, (0.9, 0.88, 0.85))
        c.cylindre("pierre", repere(px, py, z0 + 0.2 + hc / 2), 0.36, 0.3, hc, 16)
        c.cylindre("pierre", repere(px, py, z0 + 0.25 + hc), 0.52, 0.48, 0.14, 24)
        for s in range(3):
            a = rnd.random() * 2 * math.pi
            v = c.sphere("roche", repere(px + 0.85 * math.cos(a), py + 0.85 * math.sin(a), z0 + 0.0), 0.18 + 0.12 * rnd.random(), 2)
            c.bosseler(v, Vector((px + 0.85 * math.cos(a), py + 0.85 * math.sin(a), z0)), 0.05, 3.0, rnd.random() * 9)
        g = Construction(f"vivant_cristal_{k + 1}", vivant, M)
        cz = z0 + 0.32 + hc + 0.95
        centre = Vector((px, py, cz))
        bas = g.bm.verts.new(centre + Vector((0, 0, -0.5)))
        haut = g.bm.verts.new(centre + Vector((0, 0, 0.62)))
        anneau = [g.bm.verts.new(centre + Vector((0.24 * math.cos(2 * math.pi * s / 6), 0.24 * math.sin(2 * math.pi * s / 6), 0.06)))
                  for s in range(6)]
        for s in range(6):
            g.bm.faces.new((anneau[s], anneau[(s + 1) % 6], haut))
            g.bm.faces.new((anneau[(s + 1) % 6], anneau[s], bas))
        g._finir([bas, haut] + anneau, mat)
        for f in g.bm.faces:
            f.smooth = False
        g.objet(vivant="cristal", projet=nom, rang=k)
    c.objet()


def construire_phare(M, coll, reperes, feuillage, rnd):
    px, py, _ = SITES["phare"]
    z0 = HAUTEUR_SITE["phare"]
    L = repere(px, py, z0, vers(-1.0, -1.1))
    c = Construction("phare", coll, M)
    OBSTACLES.append((px, py, 2.5))
    c.cylindre("pierre", orientation(L, 0, 0, 0.1), 2.3, 2.2, 1.0, 32)
    hauteur_tour = 10.0
    tranches = 6
    for k in range(tranches):
        z1, z2 = 0.6 + hauteur_tour * k / tranches, 0.6 + hauteur_tour * (k + 1) / tranches
        r1 = lerp(1.7, 1.15, k / tranches)
        r2 = lerp(1.7, 1.15, (k + 1) / tranches)
        c.cylindre("rouge" if k % 2 else "enduit", orientation(L, 0, 0, (z1 + z2) / 2), r1, r2, z2 - z1 + 0.002, 32)
    zt = 0.6 + hauteur_tour
    c.cylindre("pierre", orientation(L, 0, 0, zt + 0.1), 1.75, 1.75, 0.22, 32)
    for k in range(18):
        a = 2 * math.pi * k / 18
        c.cylindre("metal", orientation(L, 1.62 * math.cos(a), 1.62 * math.sin(a), zt + 0.7), 0.025, 0.025, 1.0, 6)
    c.cylindre("metal", orientation(L, 0, 0, zt + 1.2), 1.66, 1.66, 0.05, 32)
    c.cylindre("metal", orientation(L, 0, 0, zt + 0.25), 1.0, 1.0, 0.1, 24)
    c.cylindre("lumiere_phare", orientation(L, 0, 0, zt + 1.0), 0.88, 0.88, 1.4, 16)
    for k in range(8):
        a = 2 * math.pi * k / 8
        c.boite("metal", orientation(L, 0.9 * math.cos(a), 0.9 * math.sin(a), zt + 1.0, rz=a), (0.06, 0.08, 1.45))
    c.cylindre("metal", orientation(L, 0, 0, zt + 1.75), 1.0, 1.0, 0.1, 24)
    c.demi_sphere("rouge", orientation(L, 0, 0, zt + 1.78), 1.02)
    c.cylindre("metal", orientation(L, 0, 0, zt + 3.05), 0.06, 0.02, 0.6, 8)
    c.sphere("metal", orientation(L, 0, 0, zt + 2.8), 0.1, 2)
    ancre(reperes, "phare_lampe", L @ Vector((0, 0, zt + 1.0)))
    # Porte et petites fenêtres
    c.boite("bois_sombre", orientation(L, 0, -1.66, 1.6), (0.85, 0.2, 1.8), 0.02)
    c.boite("pierre", orientation(L, 0, -1.72, 2.55), (1.1, 0.25, 0.18), 0.02)
    for k, hz in enumerate((4.2, 6.6, 8.9)):
        a = -math.pi / 2 + (0.5 if k % 2 else -0.4)
        rr = lerp(1.7, 1.15, (hz - 0.6) / hauteur_tour)
        c.boite("lumiere" if k == 1 else "metal", orientation(L, rr * math.cos(a), rr * math.sin(a), hz, rz=a + math.pi / 2),
                (0.35, 0.12, 0.55))
    # Muret de pierres sèches autour
    for k in range(26):
        a = math.radians(60) + 2 * math.pi * k / 34
        rr = 4.1 + rnd.uniform(-0.1, 0.1)
        t = 0.75 + 0.2 * rnd.random()
        p = L @ Vector((rr * math.cos(a), rr * math.sin(a), 0))
        c.boite("pierre", orientation(L, rr * math.cos(a), rr * math.sin(a), 0.2 + rnd.uniform(0, 0.05), rz=a + rnd.uniform(-0.2, 0.2)),
                (0.55, 0.8, 0.5), 0.06, (t, t, t))
        OBSTACLES.append((p.x, p.y, 0.5))
        if k % 4 == 0:
            lierre(feuillage, p + Vector((0, 0, 0.35)), Vector((0, 0, 1)), rnd, 3, 0.3, 0.4)
    # Banc face au couchant
    bx, by = px - 3.0, py - 6.5
    Lb = repere(bx, by, hauteur(bx, by), vers(-0.5, -1))
    c.boite("bois", orientation(Lb, 0, 0, 0.45), (1.6, 0.42, 0.07), 0.015)
    c.boite("bois", orientation(Lb, 0, 0.2, 0.75, rx=-0.15), (1.6, 0.06, 0.32), 0.015)
    for s in (-1, 1):
        c.boite("bois_sombre", orientation(Lb, s * 0.65, 0, 0.22), (0.08, 0.38, 0.45))
    OBSTACLES.append((bx, by, 1.0))
    c.objet()


def construire_lanternes(M, coll, reperes, rnd):
    """Lanternes le long du chemin : à la tombée du jour, elles posent des flaques de lumière chaude."""
    c = Construction("lanternes", coll, M)
    pts = reechantillonner(CHEMIN, 6.0)
    n = 0
    for k, (x, y, s) in enumerate(pts[1:-1], start=1):
        if any(math.hypot(x - sx, y - sy) < rr - 0.5 for nom, (sx, sy, rr) in SITES.items() if nom != "etang"):
            continue
        ax, ay, _ = pts[k - 1]
        bx, by, _ = pts[k + 1]
        tx, ty = bx - ax, by - ay
        l = math.hypot(tx, ty) or 1
        cote = 1 if k % 2 else -1
        lx, ly = x - ty / l * 1.45 * cote, y + tx / l * 1.45 * cote
        if not sur_ile(lx, ly, 2.0):
            continue
        z = hauteur(lx, ly) - 0.05
        L = repere(lx, ly, z, math.atan2(ty, tx))
        c.boite("bois_sombre", orientation(L, 0, 0, 0.75), (0.1, 0.1, 1.5), 0.015)
        c.boite("bois_sombre", orientation(L, 0, cote * 0.18, 1.45), (0.06, 0.42, 0.06))
        c.boite("metal", orientation(L, 0, cote * 0.33, 1.38), (0.2, 0.2, 0.03))
        c.sphere("lanterne", orientation(L, 0, cote * 0.33, 1.27), 0.075, 2)
        c.boite("metal", orientation(L, 0, cote * 0.33, 1.16), (0.17, 0.17, 0.03))
        pos = L @ Vector((0, cote * 0.33, 1.27))
        ancre(reperes, f"lanterne_chemin_{n + 1}", pos)
        OBSTACLES.append((lx, ly, 0.35))
        n += 1
    # Panneau indicateur au carrefour de l'atelier
    px, py = -7.6, -6.9
    L = repere(px, py, hauteur(px, py) - 0.05, 0)
    c.cylindre("bois_sombre", orientation(L, 0, 0, 1.1), 0.07, 0.06, 2.2, 8)
    for k, (cible, hz) in enumerate(((SITES["atelier"], 1.85), (SITES["cercle"], 1.55), (SITES["arche"], 1.25))):
        a = math.atan2(cible[1] - py, cible[0] - px)
        c.boite("bois", orientation(L, 0.35 * math.cos(a), 0.35 * math.sin(a), hz, rz=a), (0.75, 0.035, 0.18), 0.01, (1.0, 0.9, 0.8))
    OBSTACLES.append((px, py, 0.4))
    c.objet()
    log(f"lanternes du chemin : {n}")


# =========================================================================
#  6. VÉGÉTATION : des arbres en cartes de feuilles
# =========================================================================

TEINTES_FEUILLUS = [(1.0, 1.0, 1.0), (1.08, 1.02, 0.85), (0.9, 1.0, 0.95), (1.15, 1.0, 0.75), (0.95, 0.95, 1.0)]
TEINTES_AUTOMNE = [(1.7, 1.05, 0.55), (1.9, 0.85, 0.45), (1.5, 1.2, 0.5)]


def arbre_feuillu(troncs, f, x, y, z, rnd, e):
    """Chêne : tronc courbé, branches maîtresses, couronne faite de plusieurs touffes."""
    h = (2.6 + 1.0 * rnd.random()) * e
    pench = Vector((rnd.uniform(-0.18, 0.18), rnd.uniform(-0.18, 0.18), 1.0)).normalized()
    pts = []
    for s in range(6):
        u = s / 5
        p = Vector((x, y, z - 0.25)) + pench * h * u + Vector((math.sin(u * 3 + x) * 0.15, math.cos(u * 2.5 + y) * 0.15, 0)) * e
        pts.append(p)
    rayons = [lerp(0.32, 0.17, s / 5) * e * (1.25 if s == 0 else 1.0) for s in range(6)]
    troncs.tube("ecorce", pts, rayons, 9, (1, 1, 1), fermer=False)
    sommet = pts[-1]
    teinte = rnd.choice(TEINTES_AUTOMNE) if rnd.random() < 0.14 else rnd.choice(TEINTES_FEUILLUS)
    teinte = tuple(c * rnd.uniform(0.92, 1.08) for c in teinte)
    phase = rnd.random()
    nb_branches = rnd.randint(4, 6)
    rayon_couronne = (2.2 + 0.6 * rnd.random()) * e
    for b in range(nb_branches):
        a = 2 * math.pi * (b + rnd.uniform(-0.25, 0.25)) / nb_branches
        elev = rnd.uniform(0.35, 0.9)
        d = Vector((math.cos(a) * (1 - elev * 0.6), math.sin(a) * (1 - elev * 0.6), elev)).normalized()
        l = rayon_couronne * rnd.uniform(0.6, 0.95)
        depart = pts[4].lerp(sommet, rnd.random())
        bout = depart + d * l
        milieu = depart.lerp(bout, 0.5) + Vector((0, 0, 0.25 * e))
        troncs.tube("ecorce", [depart, milieu, bout], [rayons[4] * 0.7, rayons[4] * 0.45, 0.04 * e], 6)
        # Touffe de feuilles au bout de la branche
        rt = rayon_couronne * rnd.uniform(0.55, 0.75)
        coeur = bout + Vector((0, 0, rt * 0.15))
        for k in range(rnd.randint(18, 24)):
            dirc = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 0.8) + 0.25)).normalized()
            r = rt * rnd.uniform(0.35, 1.0) ** 0.6
            p = coeur + Vector((dirc.x, dirc.y, dirc.z * 0.75)) * r
            n = (dirc + Vector((rnd.gauss(0, 0.35), rnd.gauss(0, 0.35), rnd.gauss(0, 0.35)))).normalized()
            taille = rnd.uniform(1.05, 1.5) * e
            poids = min(1.0, 0.35 + 0.65 * (p - Vector((x, y, z))).length / (h + rayon_couronne))
            f.carte(p, n, Vector((0, 0, 1)) + Vector((rnd.gauss(0, 0.3), rnd.gauss(0, 0.3), 0)), taille, taille * rnd.uniform(0.85, 1.05),
                    TUILE_FEUILLU, teinte, coeur, poids, phase)
    # Cœur de la couronne pour éviter les trous
    for k in range(10):
        dirc = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 0.6) + 0.3)).normalized()
        p = sommet + dirc * rayon_couronne * 0.45
        f.carte(p, dirc, Vector((0, 0, 1)), 1.3 * e, 1.2 * e, TUILE_FEUILLU, tuple(c * 0.85 for c in teinte), sommet, 0.4, phase)
    return h + rayon_couronne


def arbre_conifere(troncs, f, x, y, z, rnd, e):
    """Sapin : tronc droit, étages de rameaux de plus en plus courts vers la pointe."""
    H = (6.5 + 3.0 * rnd.random()) * e
    troncs.tube("ecorce", [Vector((x, y, z - 0.3)), Vector((x, y, z + H * 0.5)), Vector((x, y, z + H))],
                [0.24 * e, 0.15 * e, 0.03 * e], 8)
    teinte = (rnd.uniform(0.85, 1.05), rnd.uniform(0.9, 1.05), rnd.uniform(0.85, 1.0))
    phase = rnd.random()
    etages = rnd.randint(10, 13)
    R0 = (2.3 + 0.6 * rnd.random()) * e
    for i in range(etages):
        t = i / (etages - 1)
        hz = z + H * (0.16 + 0.8 * t)
        r = R0 * (1.0 - t) ** 0.95 + 0.25 * e
        nb = max(4, int(9 * (1.0 - t * 0.5)))
        decal = rnd.random() * 2 * math.pi
        for k in range(nb):
            a = decal + 2 * math.pi * k / nb + rnd.uniform(-0.15, 0.15)
            radial = Vector((math.cos(a), math.sin(a), 0))
            centre = Vector((x, y, hz)) + radial * r * 0.5 - Vector((0, 0, r * 0.12))
            n = (radial * 0.55 + Vector((0, 0, 0.85))).normalized()
            haut = (radial - Vector((0, 0, 0.25))).normalized()
            f.carte(centre, n, haut, r * 0.75 + 0.3 * e, r * 1.05, TUILE_AIGUILLES, teinte,
                    Vector((x, y, hz - r * 0.3)), min(1.0, 0.25 + r / R0 * 0.75), phase, 0.12)
    # Pointe
    f.carte(Vector((x, y, z + H + 0.2 * e)), Vector((1, 0, 0)), Vector((0, 0, 1)), 0.7 * e, 1.2 * e, TUILE_AIGUILLES, teinte,
            Vector((x, y, z + H - 1)), 0.6, phase, 0.3)
    f.carte(Vector((x, y, z + H + 0.2 * e)), Vector((0, 1, 0)), Vector((0, 0, 1)), 0.7 * e, 1.2 * e, TUILE_AIGUILLES, teinte,
            Vector((x, y, z + H - 1)), 0.6, phase, 0.3)
    return H


def cypres(troncs, f, x, y, z, rnd, e):
    """Cyprès : une flamme sombre et dense, faite de panaches verticaux."""
    H = (6.0 + 2.8 * rnd.random()) * e
    R = (0.85 + 0.25 * rnd.random()) * e
    troncs.tube("ecorce", [Vector((x, y, z - 0.3)), Vector((x, y, z + 1.2))], [0.16 * e, 0.12 * e], 7)
    teinte = (rnd.uniform(0.85, 1.0), rnd.uniform(0.9, 1.05), rnd.uniform(0.85, 1.0))
    phase = rnd.random()
    for couche, (rr, nb) in enumerate(((0.55, 22), (0.95, 46))):
        for k in range(nb):
            t = rnd.uniform(0.04, 0.97)
            a = rnd.random() * 2 * math.pi
            r = R * rr * math.sin(math.pi * t ** 0.85) ** 0.75
            radial = Vector((math.cos(a), math.sin(a), 0))
            p = Vector((x, y, z + 0.6 + H * t)) + radial * r
            n = (radial + Vector((0, 0, 0.25))).normalized()
            f.carte(p, n, Vector((0, 0, 1)), 0.75 * e, 1.45 * e, TUILE_CYPRES, teinte,
                    Vector((x, y, z + 0.6 + H * t)), 0.15 + 0.85 * t * t, phase, 0.3)
    return H


def buisson(f, x, y, z, rnd, fleuri=None):
    fleuri = rnd.random() < 0.45 if fleuri is None else fleuri
    tuile = TUILE_BUISSON if fleuri else TUILE_FEUILLU
    teinte = (rnd.uniform(0.9, 1.1), rnd.uniform(0.92, 1.08), rnd.uniform(0.8, 1.0))
    r = rnd.uniform(0.55, 0.95)
    coeur = Vector((x, y, z + r * 0.25))
    phase = rnd.random()
    for k in range(rnd.randint(12, 18)):
        d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), abs(rnd.gauss(0, 0.8)) + 0.15)).normalized()
        p = coeur + Vector((d.x, d.y, d.z * 0.7)) * r * rnd.uniform(0.5, 1.0)
        taille = r * rnd.uniform(0.9, 1.3)
        f.carte(p, d, Vector((0, 0, 1)), taille, taille, tuile, teinte, coeur, 0.3, phase, 0.2)


def caillou(c, x, y, z, rnd, r):
    centre = Vector((x, y, z + r * 0.15))
    m = Matrix.Translation(centre) @ Matrix.Rotation(rnd.random() * 6.3, 4, "Z") @ Matrix.Diagonal((1.0, 0.8, 0.55, 1))
    v = c.sphere("roche", m, r, 2 if r < 0.6 else 3, (0.95, 0.9, 0.85))
    c.bosseler(v, centre, r * 0.3, 1.2 / r, rnd.random() * 99)


def construire_vegetation(M, coll_veg, coll_roche, feuillage, rnd, couloir, vues):
    def dans_le_champ(x, y, marge):
        """Vrai si le point est dans le cône de vision d'un chapitre (de la caméra jusqu'un peu après la cible)."""
        for (ax, ay), (bx, by) in vues:
            vx, vy = bx - ax, by - ay
            longueur = math.hypot(vx, vy) or 1.0
            vx, vy = vx / longueur, vy / longueur
            px, py = x - ax, y - ay
            avant = px * vx + py * vy
            cote = abs(-px * vy + py * vx)
            if -2.0 < avant < longueur + 1.5 and cote < 2.6 + marge + max(0.0, avant) * 0.3:
                return True
        return False

    def libre(x, y, marge):
        if dans_le_champ(x, y, marge):
            return False
        if not sur_ile(x, y, 2.8):
            return False
        if min(dist_polyligne(x, y, CHEMIN), dist_polyligne(x, y, CHEMIN_ATELIER)) < 1.6 + marge * 0.5:
            return False
        if dist_ruisseau(x, y) < 1.7 + marge * 0.4 or dist_etang(x, y) < RAYON_ETANG + 0.6 + marge * 0.5:
            return False
        for nom, (cx, cy, rr) in SITES.items():
            if nom != "etang" and math.hypot(x - cx, y - cy) < rr + marge:
                return False
        if any(math.hypot(x - ox, y - oy) < orr + 0.4 for ox, oy, orr in OBSTACLES):
            return False
        if dist_polyligne(x, y, couloir) < 3.2 + marge:
            return False
        return True

    def bosquet(x, y):
        a = math.exp(-((x + 16) ** 2 + (y - 14) ** 2) / 90.0)
        b = math.exp(-((x - 12) ** 2 + (y + 18) ** 2) / 60.0)
        c = math.exp(-((x + 20) ** 2 + (y + 14) ** 2) / 50.0)
        d = math.exp(-((x - 4) ** 2 + (y - 22) ** 2) / 50.0)
        return max(a, b, c, d)

    troncs = Construction("troncs", coll_veg, M)
    places = []
    essais = 0
    while len(places) < 100 and essais < 30000:
        essais += 1
        a = rnd.random() * 2 * math.pi
        r = math.sqrt(rnd.random()) * 34
        x, y = r * math.cos(a), r * math.sin(a)
        if rnd.random() > 0.12 + 0.88 * bosquet(x, y):
            continue
        if not libre(x, y, 1.0):
            continue
        if any(math.hypot(x - px, y - py) < 2.8 for px, py in places):
            continue
        places.append((x, y))
    especes = {"feuillu": 0, "sapin": 0, "cypres": 0}
    for x, y in places:
        z = hauteur(x, y)
        e = 0.85 + 0.35 * rnd.random()
        choix = rnd.random()
        if bosquet(x, y) > 0.5 and choix < 0.5:
            arbre_conifere(troncs, feuillage, x, y, z, rnd, e)
            especes["sapin"] += 1
        elif choix < 0.84:
            arbre_feuillu(troncs, feuillage, x, y, z, rnd, e)
            especes["feuillu"] += 1
        else:
            cypres(troncs, feuillage, x, y, z, rnd, e)
            especes["cypres"] += 1
        OBSTACLES.append((x, y, 0.45))
    # Cyprès en alignement près du cercle et du phare, saules (feuillus) au bord de l'étang
    for x, y in ((-3.5, 15.5), (-0.5, 16.8), (9.5, 13.5), (19.0, 22.5), (26.5, 15.0)):
        if libre(x, y, -1.5):
            cypres(troncs, feuillage, x, y, hauteur(x, y), rnd, 1.0)
            places.append((x, y))
            especes["cypres"] += 1
    ex, ey, _ = SITES["etang"]
    for a in (math.radians(40), math.radians(150), math.radians(260)):
        x, y = ex + (RAYON_ETANG + 2.4) * math.cos(a), ey + (RAYON_ETANG + 2.4) * math.sin(a)
        if sur_ile(x, y, 3) and dist_ruisseau(x, y) > 2.0 and dist_polyligne(x, y, CHEMIN) > 2.0 \
                and not dans_le_champ(x, y, 1.0) and dist_polyligne(x, y, couloir) > 4.0:
            arbre_feuillu(troncs, feuillage, x, y, hauteur(x, y), rnd, 1.1)
            places.append((x, y))
            especes["feuillu"] += 1
    troncs.objet(groupe="troncs")
    log(f"arbres : {len(places)} ({especes})")

    n = 0
    essais = 0
    while n < 110 and essais < 30000:
        essais += 1
        a = rnd.random() * 2 * math.pi
        r = math.sqrt(rnd.random()) * 33
        x, y = r * math.cos(a), r * math.sin(a)
        if not libre(x, y, -0.8) or any(math.hypot(x - px, y - py) < 1.2 for px, py in places):
            continue
        buisson(feuillage, x, y, hauteur(x, y), rnd)
        n += 1
    # Buissons au pied des bâtiments et au bord de l'eau
    for nom, nb in (("atelier", 6), ("arche", 5), ("phare", 5), ("cristaux", 4), ("etang", 7)):
        cx, cy, rr = SITES[nom]
        for k in range(nb):
            a = rnd.random() * 2 * math.pi
            d = rr + (0.6 if nom == "etang" else -0.3)
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            if (min(dist_polyligne(x, y, CHEMIN), dist_polyligne(x, y, CHEMIN_ATELIER)) > 1.3
                    and dist_polyligne(x, y, couloir) > 2.0 and dist_ruisseau(x, y) > 1.3
                    and not any(math.hypot(x - ox, y - oy) < orr + 0.3 for ox, oy, orr in OBSTACLES)):
                buisson(feuillage, x, y, hauteur(x, y), rnd, nom != "phare")
                n += 1
    for k in range(18):
        s = rnd.uniform(0.1, 0.9)
        pts = reechantillonner(RUISSEAU, 0.5)
        x, y, _ = pts[int(s * (len(pts) - 1))]
        a = rnd.random() * 2 * math.pi
        x, y = x + math.cos(a) * 1.9, y + math.sin(a) * 1.9
        if sur_ile(x, y, 2.5) and dist_ruisseau(x, y) > 1.4:
            buisson(feuillage, x, y, hauteur(x, y), rnd, False)
    log(f"buissons : {n}")

    cailloux = Construction("cailloux", coll_roche, M)
    for k in range(70):
        a = rnd.random() * 2 * math.pi
        r = 8 + math.sqrt(rnd.random()) * 26
        x, y = r * math.cos(a), r * math.sin(a)
        if r > rayon_bord(a) - 0.8:
            continue
        if min(dist_polyligne(x, y, CHEMIN), dist_polyligne(x, y, CHEMIN_ATELIER)) < 1.0 or dist_polyligne(x, y, couloir) < 1.5:
            continue
        grand = r > rayon_bord(a) - 5 and rnd.random() < 0.5
        caillou(cailloux, x, y, hauteur(x, y) - 0.1, rnd, (0.7 + 0.9 * rnd.random()) if grand else (0.15 + 0.3 * rnd.random()))
    # Petits cailloux le long du chemin, galets le long du ruisseau
    for i in range(len(CHEMIN) - 1):
        (ax, ay), (bx, by) = CHEMIN[i], CHEMIN[i + 1]
        for s in range(4):
            t = rnd.random()
            nx, ny = -(by - ay), bx - ax
            l = math.hypot(nx, ny) or 1
            cote = 1 if rnd.random() < 0.5 else -1
            x = lerp(ax, bx, t) + cote * nx / l * (1.25 + 0.3 * rnd.random())
            y = lerp(ay, by, t) + cote * ny / l * (1.25 + 0.3 * rnd.random())
            if sur_ile(x, y, 1) and dist_polyligne(x, y, couloir) > 1.2:
                caillou(cailloux, x, y, hauteur(x, y) - 0.05, rnd, 0.12 + 0.18 * rnd.random())
    for (x, y, s) in reechantillonner(RUISSEAU, 1.1):
        if not sur_ile(x, y, 1.5):
            continue
        for cote in (-1, 1):
            if rnd.random() < 0.6:
                a = rnd.random() * 2 * math.pi
                px, py = x + math.cos(a) * 1.0, y + math.sin(a) * 1.0
                caillou(cailloux, px, py, hauteur(px, py) + 0.05, rnd, 0.14 + 0.2 * rnd.random())
    cailloux.objet(groupe="roche")


# =========================================================================
#  7. L'EAU : étang, ruisseau et cascade
# =========================================================================

def construire_eau(M, vivant, reperes):
    cx, cy, _ = SITES["etang"]
    z_etang = HAUTEUR_SITE["etang"] - 0.3

    # Étang : disque au bord irrégulier. u vaut 0 au bord et 0,5 au centre (le site s'en sert pour fondre les rives)
    verts, faces, uvs = [], [], []
    anneaux, secteurs = 6, 56
    verts.append((cx, cy, z_etang))
    for j in range(1, anneaux + 1):
        for i in range(secteurs):
            a = 2 * math.pi * i / secteurs
            R = RAYON_ETANG + 0.35 * n3(math.cos(a) * 1.5, math.sin(a) * 1.5, 3.3) + 0.25
            r = R * j / anneaux
            verts.append((cx + r * math.cos(a), cy + r * math.sin(a), z_etang))
    for i in range(secteurs):
        faces.append((0, 1 + i, 1 + (i + 1) % secteurs))
    for j in range(1, anneaux):
        for i in range(secteurs):
            a = 1 + (j - 1) * secteurs + i
            b = 1 + (j - 1) * secteurs + (i + 1) % secteurs
            faces.append((a, a + secteurs, b + secteurs, b))
    me = bpy.data.meshes.new("eau_etang")
    me.from_pydata(verts, [], faces)
    couche = me.uv_layers.new(name="eau")
    for p in me.polygons:
        for li, vi in zip(p.loop_indices, p.vertices):
            x, y, _ = verts[vi]
            r = math.hypot(x - cx, y - cy)
            j = 0 if vi == 0 else (vi - 1) // secteurs + 1
            couche.data[li].uv = (0.5 * (1 - j / anneaux), r)
    me.materials.append(M["eau"])
    ob = bpy.data.objects.new("eau_etang", me)
    vivant.objects.link(ob)
    ob["vivant"] = "eau"
    ob["ecoulement"] = 0
    ob["garder_uv"] = 1

    # Ruisseau : bande qui suit le lit, à quelques centimètres sous les berges
    pts = reechantillonner(RUISSEAU, 0.45)
    depart = next(k for k, (x, y, s) in enumerate(pts) if dist_etang(x, y) > RAYON_ETANG - 0.4)
    fin = next((k for k, (x, y, s) in enumerate(pts) if not sur_ile(x, y, -0.2)), len(pts) - 1)
    pts = pts[depart:fin + 1]
    verts, faces, uvs = [], [], []
    z_prec = z_etang
    lit = []
    for k, (x, y, s) in enumerate(pts):
        a = pts[max(0, k - 1)]
        b = pts[min(len(pts) - 1, k + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        l = math.hypot(tx, ty) or 1
        nx, ny = -ty / l, tx / l
        if sur_ile(x, y, 0.4):
            z = min(z_prec - 0.012, hauteur_sans_eau(x, y) - 0.26)
        else:
            z = z_prec - 0.25
        z_prec = z
        w = LARGEUR_RUISSEAU * (0.95 + 0.15 * n3(x * 0.4, y * 0.4, 8.0))
        for c in (-1.0, 0.0, 1.0):
            verts.append((x + nx * w * c, y + ny * w * c, z))
            uvs.append(((c + 1) / 2, s - pts[0][2]))
        lit.append((Vector((x, y, z)), Vector((tx / l, ty / l, 0))))
    for k in range(len(pts) - 1):
        for c in range(2):
            a = k * 3 + c
            faces.append((a, a + 1, a + 4, a + 3))
    me = bpy.data.meshes.new("eau_ruisseau")
    me.from_pydata(verts, [], faces)
    couche = me.uv_layers.new(name="eau")
    for p in me.polygons:
        for li, vi in zip(p.loop_indices, p.vertices):
            couche.data[li].uv = uvs[vi]
    me.materials.append(M["eau"])
    ob = bpy.data.objects.new("eau_ruisseau", me)
    vivant.objects.link(ob)
    ob["vivant"] = "eau"
    ob["ecoulement"] = 1
    ob["garder_uv"] = 1

    # Cascade : un ruban qui tombe en s'écartant de la falaise, jusqu'à la mer de nuages
    levre, direction = lit[-1]
    direction = (direction + levre.normalized() * Vector((1, 1, 0)) * 0.6)
    direction.z = 0
    direction.normalize()
    lat = Vector((-direction.y, direction.x, 0))
    verts, faces, uvs = [], [], []
    etapes = 44
    chute = 40.0
    for j in range(etapes + 1):
        u = j / etapes
        y_chute = chute * u ** 1.25
        centre = levre + direction * (0.35 + 1.15 * math.sqrt(y_chute)) + Vector((0, 0, -y_chute))
        w = 0.95 + 0.075 * y_chute
        for c in (-1.0, -0.5, 0.0, 0.5, 1.0):
            p = centre + lat * w * c + direction * (0.18 * (1 - c * c))
            verts.append(tuple(p))
            uvs.append(((c + 1) / 2, y_chute))
    for j in range(etapes):
        for c in range(4):
            a = j * 5 + c
            faces.append((a, a + 1, a + 6, a + 5))
    me = bpy.data.meshes.new("cascade")
    me.from_pydata(verts, [], faces)
    couche = me.uv_layers.new(name="eau")
    for p in me.polygons:
        for li, vi in zip(p.loop_indices, p.vertices):
            couche.data[li].uv = uvs[vi]
    me.materials.append(M["eau"])
    ob = bpy.data.objects.new("cascade", me)
    vivant.objects.link(ob)
    ob["vivant"] = "cascade"
    ob["garder_uv"] = 1
    ob["chute"] = chute
    ancre(reperes, "cascade_haut", levre + direction * 0.6 + Vector((0, 0, -0.3)))
    ancre(reperes, "cascade_bas", levre + direction * (0.35 + 1.15 * math.sqrt(chute)) + Vector((0, 0, -chute + 1.0)))
    log(f"eau : étang, ruisseau de {pts[-1][2] - pts[0][2]:.0f} m, cascade de {chute:.0f} m")


# =========================================================================
#  8. CAMÉRA, STUDIO ET ÉTAPES
# =========================================================================

def cles_camera():
    A, B, C, D, E = (HAUTEUR_SITE[n] for n in ("arche", "atelier", "cercle", "cristaux", "phare"))

    def sol(x, y, dz):
        return (x, y, hauteur(x, y) + dz)

    # (position, cible, chapitre, champ de vision vertical en degrés)
    # Les clés sans chapitre arrondissent le trajet entre deux chapitres.
    return [
        ((-50.0, -49.0, 15.0), (1.0, 1.0, -5.0), 0, 40),
        ((-30.0, -52.0, A + 7.0), (0.0, -22.0, A + 2.0), None, 44),
        ((0.3, -33.5, A + 1.9), (0.0, -21.0, A + 2.5), 1, 46),
        ((-0.3, -19.8, A + 2.2), (-9.0, -9.0, B + 1.5), None, 50),
        (sol(-4.6, -14.3, 3.5), (-14.0, -6.0, B + 2.1), 2, 46),
        (sol(-10.5, -0.5, 4.0), (2.0, 6.0, C + 0.6), None, 48),
        ((-4.8, 11.8, C + 3.8), (2.0, 5.6, C + 0.9), 3, 46),
        ((5.0, 15.5, C + 6.5), (14.0, -3.0, D + 1.2), None, 46),
        (sol(9.6, 0.4, 1.8), (15.0, -6.0, D + 1.8), 4, 42),
        (sol(10.5, 3.5, 3.2), (22.0, 17.0, E + 5.0), None, 46),
        (sol(11.8, 7.6, 2.4), (23.5, 19.5, E + 6.2), 5, 46),
        ((30.0, 12.0, E + 13.0), (10.0, 2.0, 0.0), None, 44),
        ((66.0, 34.0, 25.0), (-1.0, 1.0, -6.0), 6, 38),
    ]


def construire_reperes(reperes):
    cles = cles_camera()
    for k, (cam, cible, chap, fov) in enumerate(cles):
        e = ancre(reperes, f"cam_{k:02d}", Vector(cam))
        e["chapitre"] = -1 if chap is None else chap
        e["fov"] = fov
        ancre(reperes, f"cible_{k:02d}", Vector(cible))
    # Direction du soleil, pour que le ciel du site place son halo au même endroit que la cuisson
    ancre(reperes, "soleil", SOLEIL_DIR * 100.0)
    couloir = [(c[0][0], c[0][1]) for c in cles if c[0][2] < 40 and math.hypot(c[0][0], c[0][1]) < 36]
    vues = [((c[0][0], c[0][1]), (c[1][0], c[1][1])) for c in cles if c[2] and math.hypot(c[0][0], c[0][1]) < 40]
    return couloir, vues


def construire_studio(studio):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        log("looks disponibles :", [i.identifier for i in sc.view_settings.bl_rna.properties["look"].enum_items])
    sc.view_settings.exposure = 0.95

    soleil = bpy.data.lights.new("soleil", "SUN")
    soleil.energy = 3.8
    soleil.color = (1.0, 0.6, 0.34)
    soleil.angle = math.radians(1.6)
    ob = bpy.data.objects.new("soleil", soleil)
    ob.rotation_euler = (-SOLEIL_DIR).to_track_quat("-Z", "Y").to_euler()
    studio.objects.link(ob)

    w = bpy.data.worlds.new("ciel")
    sc.world = w
    nt = w.node_tree
    nt.nodes.clear()
    sortie = nt.nodes.new("ShaderNodeOutputWorld")
    fond = nt.nodes.new("ShaderNodeBackground")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    plage = nt.nodes.new("ShaderNodeMapRange")
    nt.links.new(sep.outputs["Z"], plage.inputs[0])
    plage.inputs[1].default_value = -1.0
    plage.inputs[2].default_value = 1.0
    rampe = nt.nodes.new("ShaderNodeValToRGB")
    r = rampe.color_ramp
    arrets = [(0.0, (0.05, 0.03, 0.07)), (0.42, (0.32, 0.17, 0.2)), (0.49, (0.85, 0.45, 0.3)),
              (0.505, (1.0, 0.52, 0.27)), (0.54, (0.78, 0.33, 0.3)), (0.6, (0.38, 0.15, 0.34)),
              (0.72, (0.12, 0.07, 0.22)), (1.0, (0.02, 0.018, 0.06))]
    r.elements[0].position, r.elements[0].color = arrets[0][0], (*arrets[0][1], 1)
    r.elements[1].position, r.elements[1].color = arrets[-1][0], (*arrets[-1][1], 1)
    for p, c in arrets[1:-1]:
        e = r.elements.new(p)
        e.color = (*c, 1)
    nt.links.new(plage.outputs[0], rampe.inputs[0])
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(coord.outputs["Generated"], dot.inputs[0])
    dot.inputs[1].default_value = tuple(SOLEIL_DIR)
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    nt.links.new(dot.outputs["Value"], mx.inputs[0])
    mx.inputs[1].default_value = 0.0
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    nt.links.new(mx.outputs[0], pw.inputs[0])
    pw.inputs[1].default_value = 10.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "ADD"
    mix.inputs[0].default_value = 1.0
    nt.links.new(rampe.outputs[0], mix.inputs[6])
    halo = nt.nodes.new("ShaderNodeMath")
    halo.operation = "MULTIPLY"
    nt.links.new(pw.outputs[0], halo.inputs[0])
    halo.inputs[1].default_value = 1.6
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    for i, k in enumerate((1.0, 0.55, 0.25)):
        m2 = nt.nodes.new("ShaderNodeMath")
        m2.operation = "MULTIPLY"
        nt.links.new(halo.outputs[0], m2.inputs[0])
        m2.inputs[1].default_value = k
        nt.links.new(m2.outputs[0], comb.inputs[i])
    nt.links.new(comb.outputs[0], mix.inputs[7])
    nt.links.new(mix.outputs[2], fond.inputs["Color"])
    fond.inputs["Strength"].default_value = 1.15
    nt.links.new(fond.outputs[0], sortie.inputs[0])


def activer_gpu():
    sc = bpy.context.scene
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for t in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = t
        except TypeError:
            continue
        prefs.get_devices()
        if any(d.type == t for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == t
            sc.cycles.device = "GPU"
            log("Cycles sur", t)
            return
    sc.cycles.device = "CPU"
    log("Cycles sur le processeur")


def etape_construire(opts):
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    preparer_plan()
    OBSTACLES.clear()
    rnd = random.Random(1209)
    image_feuilles = peindre_feuilles(opts["sortie"])
    M = creer_matieres(image_feuilles)
    racine = bpy.context.scene.collection
    c_terrain = collection("atlas_terrain", racine, 4096)
    c_roche = collection("atlas_roche", racine, 2048)
    c_bat = collection("atlas_batiments", racine, 4096)
    c_veg = collection("atlas_vegetation", racine, 4096)
    vivant = collection("vivant", racine)
    reperes = collection("reperes", racine)
    studio = collection("studio", racine)
    feuillage = Feuillage()

    couloir, vues = construire_reperes(reperes)
    arbre_roche, bords = construire_ile(M, c_terrain, c_roche)
    racines_et_cristaux(M, c_roche, vivant, reperes, arbre_roche, bords, rnd)
    rochers_flottants(M, c_roche, rnd)
    construire_arche(M, c_bat, reperes, feuillage, rnd)
    construire_atelier(M, c_bat, reperes, feuillage, rnd)
    construire_cercle(M, c_bat, vivant, rnd)
    construire_cristaux(M, c_bat, vivant, rnd)
    construire_phare(M, c_bat, reperes, feuillage, rnd)
    construire_lanternes(M, c_bat, reperes, rnd)
    construire_eau(M, vivant, reperes)
    construire_vegetation(M, c_veg, c_roche, feuillage, rnd, couloir, vues)
    feuillage.objet(c_veg, M, "feuillage", groupe="feuillage", feuilles=1)
    construire_studio(studio)

    total = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
    log(f"scène construite : {total} faces, {time.time() - t0:.1f} s")
    os.makedirs(SORTIE_BLEND, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SORTIE_BLEND, "ile.blend"), compress=True)


def camera_chapitre(k):
    sc = bpy.context.scene
    cam = bpy.data.objects.get("camera_apercu")
    if cam is None:
        cam = bpy.data.objects.new("camera_apercu", bpy.data.cameras.new("camera_apercu"))
        bpy.data.collections["studio"].objects.link(cam)
    if isinstance(k, str) and k.startswith("cle"):
        e = bpy.data.objects[f"cam_{int(k[3:]):02d}"]
    else:
        e = next(o for o in bpy.data.objects if o.name.startswith("cam_") and o.get("chapitre") == int(k))
    cible = bpy.data.objects[e.name.replace("cam_", "cible_")]
    cam.location = e.location
    cam.rotation_euler = (cible.location - e.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "VERTICAL"
    cam.data.angle = math.radians(e.get("fov", 44))
    cam.data.clip_end = 2000
    sc.camera = cam
    return cam


def rendre(chemin, echantillons, largeur, hauteur_img, format_image="PNG"):
    sc = bpy.context.scene
    activer_gpu()
    sc.cycles.samples = echantillons
    sc.cycles.use_denoising = True
    sc.cycles.sample_clamp_indirect = 4.0
    sc.render.resolution_x = largeur
    sc.render.resolution_y = hauteur_img
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = format_image
    if format_image == "WEBP":
        sc.render.image_settings.quality = 82
    sc.render.filepath = chemin
    bpy.ops.render.render(write_still=True)
    log("image :", chemin)


def etape_apercu(opts):
    chapitres = [str(k) for k in range(7)] if opts["chapitre"] == "tous" else opts["chapitre"].split(",")
    for k in chapitres:
        camera_chapitre(k)
        rendre(os.path.join(SORTIE_BLEND, f"apercu_{k}.png"), int(opts["echantillons"] or 48),
               int(opts["largeur"]), int(opts["hauteur"]))


def etape_affiche(opts):
    camera_chapitre(0)
    os.makedirs(opts["sortie"], exist_ok=True)
    rendre(os.path.join(opts["sortie"], "affiche.webp"), int(opts["echantillons"] or 256), 1920, 1080, "WEBP")


def preparer_uv_cuisson(o):
    """La couche « cuisson » passe en premier (TEXCOORD_0 dans le glTF) ; la couche « feuille » est gardée en second."""
    me = o.data
    feuille = None
    if "feuille" in me.uv_layers:
        feuille = np.empty(len(me.loops) * 2, dtype=np.float32)
        me.uv_layers["feuille"].data.foreach_get("uv", feuille)
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    cuisson = me.uv_layers.new(name="cuisson")
    if feuille is not None:
        f = me.uv_layers.new(name="feuille")
        f.data.foreach_set("uv", feuille)
    me.uv_layers.active = me.uv_layers["cuisson"]
    me.uv_layers["cuisson"].active_render = True


def deplier_uv(objets, marge):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objets:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objets[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(62), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, rotate_method="ANY", scale=True, margin_method="FRACTION",
                            margin=marge, shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")


def etape_cuire(opts):
    t_total = time.time()
    sc = bpy.context.scene
    activer_gpu()
    rapide = opts["rapide"]
    sc.cycles.samples = int(opts["echantillons"] or (64 if rapide else 640))
    sc.cycles.sample_clamp_indirect = 4.0
    sc.cycles.max_bounces = 8
    sc.cycles.transparent_max_bounces = 16
    sc.render.bake.margin_type = "EXTEND"
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    os.makedirs(opts["sortie"], exist_ok=True)

    # L'eau et la cascade sont rendues par le site : on les retire de la cuisson (le lit reste éclairé)
    for o in [o for o in bpy.data.collections["vivant"].all_objects if o is not None]:
        if o.get("vivant") in ("eau", "cascade"):
            o.hide_render = True

    atlas = []
    for coll in bpy.data.collections:
        if not coll.name.startswith("atlas_"):
            continue
        nom = coll.name[len("atlas_"):]
        taille = int(coll.get("taille", 2048))
        if rapide:
            taille = min(taille, 1024)
        objets = [o for o in coll.all_objects if o.type == "MESH"]
        if not objets:
            continue
        # Les objets fixes d'un même groupe deviennent un seul maillage : moins d'appels de dessin
        groupes = {}
        for o in objets:
            if not o.get("mobile"):
                groupes.setdefault(o.get("groupe", nom), []).append(o)
        for g, membres in groupes.items():
            if len(membres) > 1:
                bpy.ops.object.select_all(action="DESELECT")
                for o in membres:
                    o.select_set(True)
                bpy.context.view_layer.objects.active = membres[0]
                bpy.ops.object.join()
            membres[0].name = g
            membres[0].data.name = g
        objets = [o for o in coll.all_objects if o.type == "MESH"]
        for o in objets:
            o["atlas"] = nom
            o["atlas_max"] = taille
            preparer_uv_cuisson(o)
        t0 = time.time()
        deplier_uv(objets, 6.0 / taille)
        log(f"atlas {nom} : {len(objets)} objets ({', '.join(o.name for o in objets[:6])}), UV dépliés en {time.time() - t0:.1f} s")
        atlas.append((nom, taille, objets))

    images = {}
    for nom, taille, objets in atlas:
        img = bpy.data.images.new(f"cuisson_{nom}", taille, taille, alpha=False, float_buffer=True)
        images[nom] = img
        mats = {s.material for o in objets for s in o.material_slots if s.material}
        for m in mats:
            nt = m.node_tree
            n = nt.nodes.get("cuisson") or nt.nodes.new("ShaderNodeTexImage")
            n.name = "cuisson"
            n.image = img
            nt.nodes.active = n
        bpy.ops.object.select_all(action="DESELECT")
        for o in objets:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objets[0]
        t0 = time.time()
        bpy.ops.object.bake(type="COMBINED", pass_filter={"DIRECT", "INDIRECT", "DIFFUSE", "EMIT"},
                            margin=max(4, taille // 256), margin_type="EXTEND", use_clear=True,
                            target="IMAGE_TEXTURES", save_mode="INTERNAL")
        log(f"atlas {nom} cuit en {time.time() - t0:.1f} s ({taille} px, {sc.cycles.samples} échantillons)")

    # Enregistrement : l'image est convertie par AgX, comme un rendu Blender, puis en WebP à plusieurs tailles.
    # Le site charge d'abord la 1024, puis la plus grande quand elle est arrivée.
    sc.render.image_settings.file_format = "WEBP"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.quality = 84
    for nom, taille, objets in atlas:
        img = images[nom]
        img.save_render(os.path.join(SORTIE_BLEND, f"cuisson_{nom}.png"), scene=sc)
        for t in sorted({taille, max(1024, taille // 2), 1024}, reverse=True):
            if t > taille:
                continue
            if t != img.size[0]:
                img.scale(t, t)
            chemin = os.path.join(opts["sortie"], f"{nom}_{t}.webp")
            img.save_render(chemin, scene=sc)
            log("texture :", os.path.relpath(chemin, DEPOT), f"{os.path.getsize(chemin) / 1024:.0f} Ko")

    # Matière d'aperçu : la texture cuite seule, puis nettoyage avant l'export
    for nom, taille, objets in atlas:
        m = bpy.data.materials.new(f"cuit_{nom}")
        nt = m.node_tree
        nt.nodes.clear()
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = images[nom]
        em = nt.nodes.new("ShaderNodeEmission")
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(tex.outputs[0], em.inputs[0])
        nt.links.new(em.outputs[0], out.inputs[0])
        for o in objets:
            o.data.materials.clear()
            o.data.materials.append(m)
            # Une seule matière : le maillage part en un seul morceau dans le glTF
            o.data.polygons.foreach_set("material_index", [0] * len(o.data.polygons))
            for nom_attr in [a.name for a in o.data.color_attributes if a.name != "balancement"]:
                o.data.color_attributes.remove(o.data.color_attributes[nom_attr])

    # La cuisson est faite : on l'enregistre avant l'export, pour pouvoir réexporter sans tout recuire
    for img in images.values():
        img.pack()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SORTIE_BLEND, "ile_cuite.blend"), compress=True)
    log(f"cuisson terminée en {time.time() - t_total:.0f} s")
    etape_exporter(opts)


def etape_exporter(opts):
    """Exporte ile.glb depuis une scène déjà cuite (après l'étape « cuire », ou en ouvrant ile_cuite.blend)."""
    # On fige la liste avant de modifier les maillages (sinon Blender peut renvoyer des objets vides)
    vivants = [o for o in bpy.data.collections["vivant"].all_objects if o is not None]
    for o in vivants:
        o.hide_render = False
        if o.type == "MESH" and not o.get("garder_uv"):
            while o.data.uv_layers:
                o.data.uv_layers.remove(o.data.uv_layers[0])
        if o.type == "MESH":
            for nom_attr in [a.name for a in o.data.color_attributes]:
                o.data.color_attributes.remove(o.data.color_attributes[nom_attr])
    bpy.ops.object.select_all(action="DESELECT")
    for coll in bpy.data.collections:
        if coll.name.startswith("atlas_") or coll.name in ("vivant", "reperes"):
            for o in [o for o in coll.all_objects if o is not None]:
                o.select_set(True)
    chemin_glb = os.path.join(opts["sortie"], "ile.glb")
    bpy.ops.export_scene.gltf(
        filepath=chemin_glb, export_format="GLB", use_selection=True, export_extras=True,
        export_materials="NONE", export_normals=True, export_texcoords=True, export_yup=True, export_apply=True,
        export_vertex_color="NAME", export_vertex_color_name="balancement",
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
        export_draco_position_quantization=15, export_draco_texcoord_quantization=15,
        export_draco_normal_quantization=8, export_draco_color_quantization=8,
        export_cameras=False, export_lights=False, export_animations=False)
    log("modèle :", os.path.relpath(chemin_glb, DEPOT), f"{os.path.getsize(chemin_glb) / 1024:.0f} Ko")


def principal():
    opts = lire_options()
    log("étapes :", ", ".join(opts["etapes"]))
    if "construire" not in opts["etapes"]:
        preparer_plan()
    for e in opts["etapes"]:
        {"construire": etape_construire, "apercu": etape_apercu, "affiche": etape_affiche,
         "cuire": etape_cuire, "exporter": etape_exporter}[e](opts)


if __name__ == "__main__":
    principal()
