"""
Le château, sur sa butte au cœur des trois enceintes : un donjon carré à tourelles, une tour fine (la
bibliothèque), une cour pavée avec son puits, des jardins à la française. La grande salle, où l'on entre,
est construite avec les autres intérieurs (interieurs.py).
"""

import math

from mathutils import Matrix, Vector

from . import plan
from .construction import Construction, ancre, lierre
from .outils import TUILE_BUISSON, TUILE_FEUILLU, log


def donjon(c, feuillage, reperes, rnd):
    d = plan.DONJON
    z0 = plan.HAUTEUR_SITE["donjon"] - 0.3
    L = Matrix.Translation((d["x"], d["y"], z0))
    cote, h = d["cote"], d["hauteur"]
    c.boite("remparts", L @ Matrix.Translation((0, 0, 1.0)), (cote + 1.6, cote + 1.6, 3.0), 0.08)
    c.boite("remparts", L @ Matrix.Translation((0, 0, h / 2)), (cote, cote, h), 0.06)
    # Bandeaux, mâchicoulis et créneaux
    for hz in (h * 0.36, h * 0.68):
        c.boite("remparts", L @ Matrix.Translation((0, 0, hz)), (cote + 0.3, cote + 0.3, 0.35), 0.03)
    c.boite("remparts", L @ Matrix.Translation((0, 0, h + 0.4)), (cote + 1.0, cote + 1.0, 0.8), 0.04)
    for s in range(4):
        a = s * math.pi / 2
        for k in range(5):
            off = (k - 2) * cote / 5
            p = Vector((math.cos(a) * (cote / 2 + 0.3) - math.sin(a) * off, math.sin(a) * (cote / 2 + 0.3) + math.cos(a) * off, h + 1.35))
            c.boite("remparts", L @ Matrix.Translation(p) @ Matrix.Rotation(a, 4, "Z"), (0.6, 1.1, 1.1), 0.03)
    # Toit en pyramide d'ardoises et étendard
    c.cylindre("ardoises", L @ Matrix.Translation((0, 0, h + 4.6)) @ Matrix.Rotation(math.pi / 4, 4, "Z"), cote * 0.64, 0.1, 7.6, 4,
               (0.9, 0.9, 1.0))
    c.cylindre("metal", L @ Matrix.Translation((0, 0, h + 9.6)), 0.07, 0.04, 3.0, 6)
    c.boite("tissu", L @ Matrix.Translation((0.9, 0, h + 10.4)), (1.6, 0.04, 0.9), 0.0, (0.55, 0.12, 0.06))
    # Tourelles d'angle en encorbellement, coiffées en poivrière
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = Vector((sx * cote / 2, sy * cote / 2, 0))
            c.cylindre("remparts", L @ Matrix.Translation(p + Vector((0, 0, h - 2.2))), 1.7, 1.7, 5.2, 16)
            c.cylindre("remparts", L @ Matrix.Translation(p + Vector((0, 0, h - 5.4))), 0.3, 1.7, 1.4, 16)
            c.cylindre("ardoises", L @ Matrix.Translation(p + Vector((0, 0, h + 2.4))), 2.1, 0.05, 4.2, 16, (0.9, 0.9, 1.0))
            c.boite("bois_sombre", L @ Matrix.Translation(p * 1.06 + Vector((0, 0, h - 1.6))) @ Matrix.Rotation(math.atan2(sy, sx), 4, "Z"),
                    (0.12, 0.3, 1.0))
    # Fenêtres à meneaux, allumées pour la plupart
    for s in range(4):
        a = s * math.pi / 2
        n = Vector((math.cos(a), math.sin(a), 0))
        t = Vector((-math.sin(a), math.cos(a), 0))
        for etage, hz in enumerate((8.0, 13.5, 19.0, 24.5)):
            for k in (-1, 1):
                p = n * (cote / 2 + 0.03) + t * (k * 2.2) + Vector((0, 0, hz))
                c.avec(donnee=(0, 1.0 if rnd.random() < 0.65 else 0.0, 0))
                c.boite("fenetre", L @ Matrix.Translation(p) @ Matrix.Rotation(a, 4, "Z"), (0.08, 1.0, 1.8))
                c.avec(donnee=(0, 0, 0))
                c.boite("remparts", L @ Matrix.Translation(p + n * 0.05 + Vector((0, 0, -1.0))) @ Matrix.Rotation(a, 4, "Z"), (0.25, 1.4, 0.18))
                c.boite("remparts", L @ Matrix.Translation(p + n * 0.05 + Vector((0, 0, 1.0))) @ Matrix.Rotation(a, 4, "Z"), (0.25, 1.4, 0.3))
    # Porte du donjon et son perron
    c.boite("bois_sombre", L @ Matrix.Translation((-cote / 2 - 0.05, 0, 2.0)), (0.12, 1.8, 2.8), 0.02)
    c.arche("remparts", L @ Matrix.Translation((-cote / 2 - 0.1, 0, 0)) @ Matrix.Rotation(math.pi / 2, 4, "Z"), 1.05, 0.4, 0.5, 3.4, 7)
    for k in range(4):
        c.boite("remparts", L @ Matrix.Translation((-cote / 2 - 0.6 - k * 0.4, 0, 0.6 - k * 0.2)), (0.45, 2.6, 0.24 + k * 0.2), 0.02)
    for s in (-1, 1):
        p = L @ Vector((-cote / 2 - 0.3, s * 1.5, 3.2))
        c.sphere("lanterne", Matrix.Translation(p), 0.14, 1)
        ancre(reperes, f"lanterne_donjon_{1 if s < 0 else 2}", p)
    lierre(feuillage, L @ Vector((cote / 2 + 0.05, -2.0, 3.0)), Vector((1, 0, 0)), rnd, 14, 2.2, 0.8)
    plan.EMPRISES.append((d["x"], d["y"], 0.0, cote / 2 + 1.2, cote / 2 + 1.2))
    ancre(reperes, "sommet_donjon", L @ Vector((0, 0, h + 1.0)))


def tour_bibliotheque(c, feuillage, reperes, rnd):
    t = plan.TOUR_BIBLIOTHEQUE
    z0 = plan.hauteur(t["x"], t["y"]) - 0.5
    L = Matrix.Translation((t["x"], t["y"], z0))
    r, h = t["rayon"], t["hauteur"]
    c.cylindre("remparts", L @ Matrix.Translation((0, 0, h / 2)), r + 0.4, r, h, 24)
    c.cylindre("remparts", L @ Matrix.Translation((0, 0, h + 0.3)), r + 0.5, r + 0.5, 0.6, 24)
    c.cylindre("ardoises", L @ Matrix.Translation((0, 0, h + 4.0)), r + 0.9, 0.05, 7.2, 24, (0.9, 0.9, 1.0))
    c.cylindre("or", L @ Matrix.Translation((0, 0, h + 8.0)), 0.05, 0.03, 1.6, 6)
    for k in range(5):
        a = k * 1.3 + 0.4
        hz = 4.0 + k * 4.2
        p = Vector((math.cos(a) * (r + 0.05), math.sin(a) * (r + 0.05), hz))
        c.avec(donnee=(0, 1.0, 0))
        c.boite("fenetre", L @ Matrix.Translation(p) @ Matrix.Rotation(a, 4, "Z"), (0.08, 0.7, 1.4))
        c.avec(donnee=(0, 0, 0))
    plan.OBSTACLES.append((t["x"], t["y"], r + 1.0))


def cour_et_jardins(c, feuillage, reperes, rnd):
    cx, cy, cr = plan.COUR
    z = plan.HAUTEUR_SITE["cour"]
    # Puits au milieu de la cour
    P = Matrix.Translation((cx, cy - 1.0, z))
    c.cylindre("pierre", P @ Matrix.Translation((0, 0, 0.45)), 1.0, 1.0, 0.9, 20, (0.95, 0.93, 0.9))
    for s in (-1, 1):
        c.boite("bois", P @ Matrix.Translation((s * 0.85, 0, 1.6)), (0.12, 0.12, 2.3))
    c.boite("bois", P @ Matrix.Translation((0, 0, 2.6)), (2.0, 0.14, 0.14))
    c.toit("tuiles", "bois", P @ Matrix.Translation((0, 0, 0)), 2.2, 1.6, 2.65, 0.7, 0.2, 0.08, (0.4, 0.13, 0.07))
    plan.OBSTACLES.append((cx, cy - 1.0, 1.5))
    # Braseros sur leurs trépieds, de part et d'autre de l'allée
    for s in (-1, 1):
        p = Vector((cx + s * 4.5, cy + 3.0, z))
        for k in range(3):
            a = k * 2 * math.pi / 3
            c.boite("metal", Matrix.Translation(p + Vector((math.cos(a) * 0.25, math.sin(a) * 0.25, 0.6))), (0.05, 0.05, 1.2))
        c.cylindre("metal", Matrix.Translation(p + Vector((0, 0, 1.25))), 0.42, 0.3, 0.3, 12)
        c.sphere("braise", Matrix.Translation(p + Vector((0, 0, 1.38))), 0.3, 1)
        ancre(reperes, f"feu_brasero_{1 if s < 0 else 2}", p + Vector((0, 0, 1.6)))
        plan.OBSTACLES.append((p.x, p.y, 0.7))
    # Jardins : haies taillées en compartiments, bassin, massifs fleuris
    j = plan.JARDINS
    zj = plan.HAUTEUR_SITE["jardins"]
    J = Matrix.Translation((j["x"], j["y"], zj))
    lx, ly = j["largeur"], j["profondeur"]
    for ix in (-1, 1):
        for iy in (-1, 0, 1):
            centre = Vector((ix * lx * 0.24, iy * ly * 0.3, 0))
            for (dx, dy, sx, sy) in ((0, 0.9, 3.4, 0.5), (0, -0.9, 3.4, 0.5), (1.45, 0, 0.5, 1.8), (-1.45, 0, 0.5, 1.8)):
                c.boite("haie", J @ Matrix.Translation(centre + Vector((dx * 1.0, dy * 1.4, 0.35))), (sx, sy, 0.8), 0.12)
            for k in range(5):
                p = J @ (centre + Vector((rnd.uniform(-1.0, 1.0), rnd.uniform(-0.8, 0.8), 0.25)))
                feuillage.carte(p, Vector((rnd.gauss(0, 0.4), rnd.gauss(0, 0.4), 1.0)).normalized(), Vector((0, 1, 0)), 0.8, 0.8,
                                TUILE_BUISSON, (1.0, 1.0, 1.0), p - Vector((0, 0, 0.5)), 0.2, rnd.random(), 0.2)
    c.cylindre("pierre", J @ Matrix.Translation((0, 0, 0.25)), 1.6, 1.6, 0.5, 24)
    plan.EMPRISES.append((j["x"], j["y"], 0.0, lx / 2, ly / 2))


def construire_chateau(M, coll, feuillage, reperes, rnd):
    c = Construction("chateau", coll, M)
    donjon(c, feuillage, reperes, rnd)
    tour_bibliotheque(c, feuillage, reperes, rnd)
    cour_et_jardins(c, feuillage, reperes, rnd)
    c.objet(groupe="chateau")
    log("château : donjon, tour de la bibliothèque, cour et jardins")
