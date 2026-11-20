"""Outils communs : chemins du dépôt, options de la ligne de commande, journal, bruit et géométrie 2D."""

import math
import os
import sys

from mathutils import Vector, noise

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # tools/blender
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




def angle_de(x, y):
    return math.atan2(y, x)


def polaire(r, a):
    return (r * math.cos(a), r * math.sin(a))


def ecart_angle(a, b):
    """Écart signé le plus court entre deux angles (radians)."""
    return (a - b + math.pi) % (2 * math.pi) - math.pi
