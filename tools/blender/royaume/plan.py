"""
Plan du royaume : tout ce qui décide où vont les choses.

Le royaume est bâti sur une île volante d'environ 110 m de rayon, au-dessus des nuages. Trois remparts
concentriques le divisent en anneaux (coordonnées de Blender, Z vers le haut, le sud vers -Y) :

  r < 27        le château, sur une butte, avec sa cour et ses jardins ;
  27 < r < 58   la ville : une rue circulaire, des rues rayonnantes, la grand-place au sud ;
  58 < r < 84   la campagne : champs, fermes, moulin, verger, pâturage, la rivière ;
  r > 84        la lisière : forêt, falaises, le phare sur son promontoire, la cascade.

La grande avenue part du bord sud de l'île, passe les trois portes et monte jusqu'au château.
"""

import math

from .outils import (dist_polyligne, dist_segment, fbm2, lerp, n3, polaire, reechantillonner, smoothstep)

# --- Remparts : (nom, rayon du milieu du mur, épaisseur, hauteur au-dessus du sol, nombre de tours)
REMPARTS = {
    "exterieur": dict(rayon=84.0, epaisseur=7.0, hauteur=21.0, tours=14, couronne=True),
    "milieu": dict(rayon=58.0, epaisseur=5.5, hauteur=15.0, tours=10, couronne=True),
    "interieur": dict(rayon=27.0, epaisseur=4.0, hauteur=11.0, tours=6, couronne=True),
}
SUD = -math.pi / 2
ANGLE_PHARE = math.radians(42)
# Portes de chaque rempart (angles). Le rempart extérieur a une seconde porte vers le phare.
PORTES = {"exterieur": [SUD, ANGLE_PHARE], "milieu": [SUD], "interieur": [SUD]}
LARGEUR_PORTE = 21.0         # largeur totale d'une porterie (tours comprises), en mètres

# --- Ville
R_RUE = 40.5                 # rue circulaire, au milieu de l'anneau de la ville
DEMI_RUE = 2.8
RADIALES = [math.radians(a) for a in range(-90, 270, 45)]      # rues rayonnantes, dont l'avenue (-90°)
DEMI_RADIALE = 2.0
PLACE = (0.0, -R_RUE, 10.5)  # grand-place : centre x, y, rayon
COUR = (0.0, -14.0, 9.0)     # cour du château

# Bâtiments remarquables de la ville (angle, côté : +1 extérieur de la rue, -1 intérieur)
BATIMENTS_VILLE = {
    "atelier": dict(angle=math.radians(-66), cote=1, largeur=11.0, profondeur=9.6),
    "guilde": dict(angle=math.radians(-115), cote=1, largeur=13.0, profondeur=9.8),
    "chapelle": dict(angle=math.radians(22), cote=1, largeur=9.0, profondeur=10.0),
    "taverne": dict(angle=math.radians(196), cote=-1, largeur=11.0, profondeur=6.8),
    "forge": dict(angle=math.radians(-62), cote=-1, largeur=9.0, profondeur=6.6),
}

# --- Château
GRANDE_SALLE = dict(x=-3.0, y=3.0, largeur=14.0, profondeur=18.0)   # porte au sud, en y = y - profondeur / 2
DONJON = dict(x=12.0, y=9.0, cote=10.0, hauteur=30.0)
TOUR_BIBLIOTHEQUE = dict(x=-15.0, y=13.0, rayon=3.2, hauteur=24.0)
JARDINS = dict(x=-17.0, y=-6.0, largeur=10.0, profondeur=16.0)

# --- Campagne
R_PISTE = 64.5               # chemin de terre circulaire au pied du rempart du milieu
RIVIERE = [polaire(70.0, math.radians(84)), polaire(70.6, math.radians(92))] + \
          [polaire(70.5, math.radians(a)) for a in (104, 118, 132, 146, 160, 174, 186, 194)] + \
          [polaire(76.0, math.radians(199)), polaire(84.0, math.radians(203)), polaire(95.0, math.radians(206)),
           polaire(130.0, math.radians(210))]
LARGEUR_RIVIERE = 1.9
ETANG = (polaire(70.0, math.radians(84)), 5.5)     # source de la rivière
ANGLE_EAU = math.radians(203)                        # passage de la rivière sous le rempart extérieur
MOULIN = polaire(69.0, math.radians(-54))
FERMES = [(math.radians(a), r) for a, r in ((-20, 72.0), (58, 72.0), (146, 77.0), (238, 72.0))]
VERGER = (math.radians(10), math.radians(34), 63.0, 79.0)
PATURAGE = (math.radians(118), math.radians(160), 74.0, 81.0)

# --- Lisière
PHARE = polaire(119.0, ANGLE_PHARE)

OBSTACLES = []               # (x, y, rayon) : rien ne pousse ni ne se pose dessus
INTERIEURS = []              # bâtiments où l'on entre : dict(nom, L, largeur, profondeur, sol, porte, zone)
PONTS = []                   # (x, y, angle, demi_longueur, demi_largeur, hauteur du tablier)
EMPRISES = []                # rectangles (cx, cy, angle, demi_largeur, demi_profondeur) des bâtiments
HAUTEUR_SITE = {}


def rayon_bord(theta):
    c, s = math.cos(theta), math.sin(theta)
    r = 108.0 + 7.0 * n3(c * 1.25 + 5.2, s * 1.25 + 1.7, 0.3) + 3.0 * n3(c * 3.1 + 2.0, s * 3.1 + 7.0, 1.1)
    r += 1.0 * n3(c * 7.0, s * 7.0, 4.4)
    r += 18.0 * max(0.0, math.cos(theta - ANGLE_PHARE)) ** 40      # promontoire du phare
    r += 6.0 * max(0.0, math.cos(theta - SUD)) ** 30               # belvédère de l'arrivée, au sud
    return r


def sur_ile(x, y, marge=0.0):
    return math.hypot(x, y) < rayon_bord(math.atan2(y, x)) - marge


def hauteur_brute(x, y):
    """Relief général : une butte pour le château, une ville en pente douce, une campagne vallonnée."""
    r = math.hypot(x, y)
    t = r / rayon_bord(math.atan2(y, x))
    h = 3.0
    h += 6.0 * (1.0 - smoothstep(18.0, 31.0, r))          # butte du château
    h += 2.2 * (1.0 - smoothstep(30.0, 62.0, r))          # la ville monte vers le château
    h += 1.8 * fbm2(x * 0.018, y * 0.018, 4, 0.5) * smoothstep(59.0, 66.0, r)
    h += 3.0 * fbm2(x * 0.03 + 5.0, y * 0.03, 4, 2.0) * smoothstep(86.0, 96.0, r)
    px, py = PHARE
    h += 6.0 * math.exp(-((x - px) ** 2 + (y - py) ** 2) / 220.0)
    h += 0.15 * n3(x * 0.4, y * 0.4, 9.0)
    h -= 4.0 * smoothstep(0.93, 1.0, t)
    return h


def niveau_mur(nom, angle):
    """Hauteur du pied d'un rempart, lissée le long du mur (le chemin de ronde reste presque horizontal)."""
    R = REMPARTS[nom]["rayon"]
    s = 0.0
    for k in range(-3, 4):
        a = angle + k * 0.05
        s += hauteur_brute(R * math.cos(a), R * math.sin(a))
    return s / 7.0


def dist_riviere(x, y):
    return dist_polyligne(x, y, RIVIERE)


def dist_etang(x, y):
    (cx, cy), r = ETANG
    return math.hypot(x - cx, y - cy) - r - 0.6 * n3(x * 0.3, y * 0.3, 3.3)


def dist_avenue(x, y):
    return dist_segment(x, y, 0.0, -rayon_bord(SUD) + 2.0, 0.0, COUR[1])


def dist_rues(x, y):
    """Distance au réseau des rues pavées de la ville (rue circulaire, rues rayonnantes, avenue)."""
    r = math.hypot(x, y)
    d = abs(r - R_RUE) - DEMI_RUE
    if 27.0 < r < 58.0:
        a = math.atan2(y, x)
        for ar in RADIALES:
            ecart = abs((a - ar + math.pi) % (2 * math.pi) - math.pi)
            d = min(d, r * math.sin(min(ecart, math.pi / 2)) - DEMI_RADIALE)
    return min(d, dist_avenue(x, y) - 3.0)


def dist_place(x, y):
    return math.hypot(x - PLACE[0], y - PLACE[1]) - PLACE[2]


def dist_cour(x, y):
    return math.hypot(x - COUR[0], y - COUR[1]) - COUR[2]


def masque_pave(x, y):
    """1 sur les rues, la place et la cour (pavés), 0 ailleurs."""
    r = math.hypot(x, y)
    if r > 60.0:
        return 0.0
    d = min(dist_rues(x, y), dist_place(x, y), dist_cour(x, y))
    return 1.0 - smoothstep(-0.2, 0.35, d)


def masque_chemin(x, y):
    """Chemins de terre de la campagne et de la lisière."""
    r = math.hypot(x, y)
    if r < 58.0:
        return 0.0
    d = dist_avenue(x, y) - 2.6
    d = min(d, abs(r - R_PISTE) - 1.3)
    d = min(d, dist_polyligne(x, y, CHEMIN_PHARE) - 1.2)
    for a, rf in FERMES:
        fx, fy = polaire(rf - 4.0, a)
        d = min(d, dist_segment(x, y, *polaire(R_PISTE, a), fx, fy) - 1.0)
    largeur = 0.25 * n3(x * 0.3, y * 0.3, 2.0)
    return 1.0 - smoothstep(largeur - 0.3, largeur + 0.5, d)


def masque_eau(x, y):
    a = 1.0 - smoothstep(LARGEUR_RIVIERE * 0.6, LARGEUR_RIVIERE + 2.0, dist_riviere(x, y))
    b = 1.0 - smoothstep(-0.8, 1.8, dist_etang(x, y))
    return max(a, b)


# Chemin du phare : de la porte nord-est jusqu'au promontoire
CHEMIN_PHARE = [polaire(r, ANGLE_PHARE + 0.02 * math.sin(r * 0.2)) for r in range(84, 118, 3)]


# --- Champs : secteurs de la campagne, chacun avec sa culture
CULTURES = ["prairie", "ble", "lavande", "labour", "potager", "colza", "vigne"]


def champ(x, y):
    """(indice de culture, angle des sillons, variation) du champ sous le point, ou None hors des champs."""
    r = math.hypot(x, y)
    if not (61.5 < r < 80.5):
        return None
    a = math.atan2(y, x)
    if PATURAGE[0] < a < PATURAGE[1] and r > PATURAGE[2] - 2:
        return (0, 0.0, 0.5)
    secteur = int(((a + math.pi) / (2 * math.pi)) * 26)
    anneau = 0 if r < 71.0 else 1
    graine = (secteur * 7 + anneau * 13) % 29
    culture = [1, 2, 3, 1, 4, 5, 1, 2, 6, 0, 3, 1, 5, 2][graine % 14]
    angle = (secteur * 0.61 + anneau * 1.3) % math.pi
    return (culture, angle, (graine % 7) / 7.0)


def sous_un_mur(x, y, marge=1.0):
    r = math.hypot(x, y)
    for nom, m in REMPARTS.items():
        if abs(r - m["rayon"]) < m["epaisseur"] / 2 + marge:
            return True
    return False


def hauteur_sans_eau(x, y):
    h = hauteur_brute(x, y)
    # Replats : la grand-place, la cour, les seuils des bâtiments, la base des fermes et du moulin
    for nom, (cx, cy, rr) in HAUTEUR_REPLATS.items():
        d = math.hypot(x - cx, y - cy)
        w = smoothstep(rr + 5.0, rr, d)
        if w > 0:
            h = lerp(h, HAUTEUR_SITE[nom], w)
    # Les rues et l'avenue sont légèrement creusées dans le sol
    h -= 0.06 * masque_pave(x, y) + 0.05 * masque_chemin(x, y)
    return h


HAUTEUR_REPLATS = {}


def hauteur(x, y):
    """Hauteur du sol, avec le lit de la rivière et le bassin de l'étang creusés."""
    h = hauteur_sans_eau(x, y)
    if math.hypot(x, y) > 60.0:
        d = dist_riviere(x, y)
        h -= 1.1 * (1.0 - smoothstep(LARGEUR_RIVIERE * 0.45, LARGEUR_RIVIERE + 1.2, d))
        h -= 1.3 * (1.0 - smoothstep(-2.0, 1.0, dist_etang(x, y)))
    return h


def ajouter_replat(nom, x, y, rayon):
    HAUTEUR_REPLATS[nom] = (x, y, rayon)
    HAUTEUR_SITE[nom] = hauteur_brute(x, y)


def preparer_plan():
    HAUTEUR_REPLATS.clear()
    HAUTEUR_SITE.clear()
    OBSTACLES.clear()
    EMPRISES.clear()
    INTERIEURS.clear()
    PONTS.clear()
    ajouter_replat("place", PLACE[0], PLACE[1], PLACE[2])
    ajouter_replat("cour", COUR[0], COUR[1], COUR[2] + 6)
    ajouter_replat("grande_salle", GRANDE_SALLE["x"], GRANDE_SALLE["y"], 11.0)
    ajouter_replat("donjon", DONJON["x"], DONJON["y"], 8.0)
    ajouter_replat("jardins", JARDINS["x"], JARDINS["y"], 9.0)
    for nom, b in BATIMENTS_VILLE.items():
        x, y = position_batiment(b)
        ajouter_replat(nom, x, y, max(b["largeur"], b["profondeur"]) * 0.55)
    ajouter_replat("moulin", *MOULIN, 6.0)
    for k, (a, rf) in enumerate(FERMES):
        ajouter_replat(f"ferme_{k}", *polaire(rf, a), 8.0)
    ajouter_replat("phare", *PHARE, 6.0)
    (ex, ey), er = ETANG
    ajouter_replat("etang", ex, ey, er + 2.0)
    ajouter_replat("arrivee", 0.0, -rayon_bord(SUD) + 8.0, 9.0)


def position_batiment(b):
    """Centre d'un bâtiment de la ville bâti le long de la rue circulaire, côté intérieur ou extérieur."""
    r = R_RUE + b["cote"] * (DEMI_RUE + 0.5 + b["profondeur"] / 2)
    return polaire(r, b["angle"])


def dans_emprise(x, y, marge=0.0):
    for cx, cy, ang, dl, dp in EMPRISES:
        dx, dy = x - cx, y - cy
        u = dx * math.cos(ang) + dy * math.sin(ang)
        v = -dx * math.sin(ang) + dy * math.cos(ang)
        if abs(u) < dl + marge and abs(v) < dp + marge:
            return True
    return False


def libre(x, y, marge=0.5):
    """Vrai si l'on peut planter ou poser quelque chose ici (ni rue, ni mur, ni bâtiment, ni eau)."""
    if not sur_ile(x, y, 3.0):
        return False
    if sous_un_mur(x, y, 1.5 + marge):
        return False
    if masque_pave(x, y) > 0.05 or masque_chemin(x, y) > 0.1:
        return False
    if math.hypot(x, y) > 60.0 and (dist_riviere(x, y) < LARGEUR_RIVIERE + 1.5 or dist_etang(x, y) < 1.5):
        return False
    if dans_emprise(x, y, marge):
        return False
    return not any(math.hypot(x - ox, y - oy) < orr + marge for ox, oy, orr in OBSTACLES)
