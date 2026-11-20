"""
Où pousse quoi : la forêt de la lisière (hors des remparts), les arbres des bords de champs, le verger
en fleurs, les saules de la rivière, les cyprès des jardins du château, des buissons et des rochers.
Les espèces elles-mêmes (troncs, branches, cartes de feuilles) sont dans especes.py.
Rien ne pousse dans le cône de vision de la caméra à chaque arrêt de la visite.
"""

import math

from mathutils import Vector

from . import plan
from .construction import Construction
from .especes import arbre_conifere, arbre_feuillu, buisson, caillou, cypres
from .outils import TUILE_BUISSON, lerp, log, polaire


def dans_un_champ_de_vision(x, y, vues, marge=0.0):
    for (ax, ay), (bx, by) in vues:
        vx, vy = bx - ax, by - ay
        longueur = math.hypot(vx, vy) or 1.0
        vx, vy = vx / longueur, vy / longueur
        px, py = x - ax, y - ay
        avant = px * vx + py * vy
        cote = abs(-px * vy + py * vx)
        if -2.0 < avant < longueur + 1.5 and cote < 3.0 + marge + max(0.0, avant) * 0.32:
            return True
    return False


def arbre_fruitier(troncs, f, x, y, z, rnd):
    """Petit arbre du verger, couvert de fleurs."""
    h = rnd.uniform(1.6, 2.2)
    troncs.tube("ecorce", [Vector((x, y, z - 0.2)), Vector((x + 0.1, y, z + h * 0.6)), Vector((x, y + 0.1, z + h))],
                [0.16, 0.11, 0.07], 7)
    coeur = Vector((x, y, z + h + 0.7))
    phase = rnd.random()
    for k in range(22):
        d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 0.6) + 0.2)).normalized()
        p = coeur + Vector((d.x, d.y, d.z * 0.7)) * rnd.uniform(0.5, 1.4)
        f.carte(p, d, Vector((0, 0, 1)), 1.1, 1.1, TUILE_BUISSON, (1.05, 1.0, 1.05), coeur, 0.4, phase, 0.2)


def construire_vegetation(M, coll_veg, coll_roche, feuillage, rnd, vues):
    troncs = Construction("troncs", coll_veg, M)
    especes = {"chene": 0, "sapin": 0, "cypres": 0, "fruitier": 0}
    places = []

    def peut(x, y, marge, ecart):
        if dans_un_champ_de_vision(x, y, vues, marge):
            return False
        if not plan.libre(x, y, marge):
            return False
        return not any((x - px) ** 2 + (y - py) ** 2 < ecart * ecart for px, py in places)

    def planter(x, y, espece, e=None):
        z = plan.hauteur(x, y)
        e = e or (0.9 + 0.4 * rnd.random())
        if espece == "sapin":
            arbre_conifere(troncs, feuillage, x, y, z, rnd, e * 1.15)
        elif espece == "cypres":
            cypres(troncs, feuillage, x, y, z, rnd, e)
        elif espece == "fruitier":
            arbre_fruitier(troncs, feuillage, x, y, z, rnd)
        else:
            arbre_feuillu(troncs, feuillage, x, y, z, rnd, e * 1.15)
        especes[espece] += 1
        places.append((x, y))
        plan.OBSTACLES.append((x, y, 0.5))

    # 1. Forêt de la lisière, en bosquets
    centres = [polaire(rnd.uniform(93, 102), rnd.random() * 2 * math.pi) for _ in range(26)]
    essais = 0
    while especes["chene"] + especes["sapin"] < 190 and essais < 40000:
        essais += 1
        cx, cy = rnd.choice(centres)
        x, y = cx + rnd.gauss(0, 7.0), cy + rnd.gauss(0, 7.0)
        r = math.hypot(x, y)
        if not (89.0 < r < plan.rayon_bord(math.atan2(y, x)) - 3.5):
            continue
        if plan.dist_polyligne(x, y, plan.CHEMIN_PHARE) < 3.5 or math.hypot(x - plan.PHARE[0], y - plan.PHARE[1]) < 10.0:
            continue
        if not peut(x, y, 1.0, 3.6):
            continue
        planter(x, y, "sapin" if rnd.random() < 0.45 else "chene")
    # 2. Arbres isolés et en rangées au bord des champs, et saules le long de la rivière
    for k in range(70):
        a = rnd.random() * 2 * math.pi
        secteur = round(((a + math.pi) / (2 * math.pi)) * 26)
        a = secteur / 26 * 2 * math.pi - math.pi
        r = rnd.uniform(62.5, 80.0)
        x, y = polaire(r, a + rnd.uniform(-0.004, 0.004))
        if peut(x, y, 0.6, 5.0):
            planter(x, y, rnd.choice(("chene", "chene", "cypres")), 0.85)
    for (x, y, s) in plan.reechantillonner(plan.RIVIERE, 9.0)[1:-3]:
        for cote in (-1, 1):
            if rnd.random() < 0.5:
                continue
            a = math.atan2(y, x)
            px, py = x + math.cos(a) * cote * (plan.LARGEUR_RIVIERE + 3.2), y + math.sin(a) * cote * (plan.LARGEUR_RIVIERE + 3.2)
            if peut(px, py, 0.0, 4.0):
                planter(px, py, "chene", 1.05)
    # 3. Verger : des rangées d'arbres fruitiers en fleurs
    a0, a1, r0, r1 = plan.VERGER
    for i in range(6):
        for j in range(8):
            a = lerp(a0, a1, (j + 0.5) / 8)
            r = lerp(r0, r1, (i + 0.5) / 6)
            x, y = polaire(r, a)
            if peut(x, y, 0.0, 2.5):
                planter(x, y, "fruitier")
    # 4. Jardins du château : deux allées de cyprès, et des arbres dans les recoins de l'enceinte
    j = plan.JARDINS
    for s in (-1, 1):
        for k in range(5):
            x, y = j["x"] + s * (j["largeur"] / 2 + 1.2), j["y"] - j["profondeur"] / 2 + 1.5 + k * 3.2
            if plan.libre(x, y, 0.0):
                planter(x, y, "cypres", 0.8)
    for k in range(10):
        x, y = polaire(rnd.uniform(14.0, 21.0), rnd.random() * 2 * math.pi)
        if peut(x, y, 0.5, 4.0) and plan.masque_pave(x, y) < 0.01:
            planter(x, y, "chene", 0.85)
    troncs.objet(groupe="troncs")
    log(f"arbres : {len(places)} ({especes})")

    # Buissons fleuris : lisière, bords de champs, pied des remparts côté campagne, autour de l'étang
    n = 0
    essais = 0
    while n < 260 and essais < 40000:
        essais += 1
        r = rnd.uniform(60.0, 105.0)
        x, y = polaire(r, rnd.random() * 2 * math.pi)
        if plan.champ(x, y) is not None and rnd.random() < 0.85:
            continue
        if dans_un_champ_de_vision(x, y, vues, -1.0) or not plan.libre(x, y, 0.2):
            continue
        buisson(feuillage, x, y, plan.hauteur(x, y), rnd)
        n += 1
    log(f"buissons : {n}")

    cailloux = Construction("cailloux", coll_roche, M)
    for k in range(140):
        a = rnd.random() * 2 * math.pi
        r = rnd.uniform(88.0, plan.rayon_bord(a) - 0.6)
        x, y = polaire(r, a)
        if not plan.libre(x, y, 0.0) or dans_un_champ_de_vision(x, y, vues, -1.5):
            continue
        grand = r > plan.rayon_bord(a) - 8 and rnd.random() < 0.5
        caillou(cailloux, x, y, plan.hauteur(x, y) - 0.15, rnd, (1.0 + 1.6 * rnd.random()) if grand else (0.2 + 0.4 * rnd.random()))
    for (x, y, s) in plan.reechantillonner(plan.RIVIERE, 1.6):
        if not plan.sur_ile(x, y, 1.5):
            continue
        for cote in (-1, 1):
            if rnd.random() < 0.5:
                a = rnd.random() * 2 * math.pi
                px, py = x + math.cos(a) * (plan.LARGEUR_RIVIERE + 0.3), y + math.sin(a) * (plan.LARGEUR_RIVIERE + 0.3)
                caillou(cailloux, px, py, plan.hauteur(px, py) + 0.05, rnd, 0.18 + 0.3 * rnd.random())
    cailloux.objet(groupe="roche")
