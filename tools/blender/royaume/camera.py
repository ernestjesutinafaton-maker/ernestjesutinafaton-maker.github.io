"""
Le trajet de la caméra de la visite guidée, et les repères du guide et des personnages.

Les clés sont calculées à partir des repères posés par les bâtiments (porte_*, interieur_*), pour que la
caméra passe bien au milieu des portes. Chaque clé : (position, cible, chapitre ou None, champ vertical).
Chapitres : 0 vue d'ensemble · 1 la porte du royaume · 2 l'atelier · 3 la bibliothèque des guildes ·
4 la grande salle · 5 le phare · 6 vue d'ensemble depuis le couchant.
"""

import math

import bpy
from mathutils import Vector

from . import plan
from .construction import ancre
from .outils import log, polaire


def _pos(nom):
    return bpy.data.objects[nom].location.copy()


def _sol(x, y, dz):
    return Vector((x, y, plan.hauteur(x, y) + dz))


def _entree(nom, hauteur_oeil=1.7):
    """(dehors, seuil, dedans, centre) pour entrer dans un bâtiment par sa porte."""
    porte = _pos(f"porte_{nom}")
    centre = _pos(f"interieur_{nom}")
    d = Vector((centre.x - porte.x, centre.y - porte.y, 0)).normalized()
    sol = centre.z - 1.4
    seuil = Vector((porte.x, porte.y, sol)) + d * 2.2
    dehors = seuil - d * 3.2 + Vector((0, 0, hauteur_oeil + 0.2))
    dedans = seuil + d * 1.1 + Vector((0, 0, hauteur_oeil))
    return dehors, seuil + Vector((0, 0, hauteur_oeil)), dedans, centre


def cles_camera():
    zp = plan.hauteur(0.0, -100.0)
    cles = [
        (Vector((-150.0, -215.0, 165.0)), Vector((0.0, -6.0, 2.0)), 0, 36),
        (Vector((-40.0, -170.0, 34.0)), Vector((0.0, -96.0, zp + 8.0)), None, 42),
        (Vector((4.5, -114.0, zp + 2.3)), Vector((0.0, -84.0, zp + 9.0)), 1, 50),
        (_sol(0.0, -91.5, 2.6), _sol(0.0, -70.0, 3.2), None, 58),
        (_sol(0.8, -73.0, 2.8), _sol(0.0, -60.0, 4.8), None, 52),
        (_sol(0.0, -63.0, 2.5), _sol(0.0, -50.0, 2.5), None, 58),
    ]
    dehors, seuil, dedans, centre = _entree("atelier")
    cles += [
        (_sol(-1.5, -47.5, 2.6), dehors + (centre - dehors) * 0.3, None, 56),
        (dehors, centre, None, 58),
        (dedans, centre + Vector((0, 0, -0.2)), 2, 62),
        (dehors + Vector((0, 0, 0.3)), _sol(0.0, -41.0, 1.8), None, 60),
    ]
    dehors, seuil, dedans, centre = _entree("guilde")
    cles += [
        (_sol(0.0, -45.0, 2.6), dehors, None, 56),
        (dehors, centre, None, 58),
        (dedans, centre + Vector((0, 0, 0.6)), 3, 64),
        (dehors + Vector((0, 0, 0.3)), _sol(0.0, -36.0, 2.0), None, 60),
    ]
    dehors, seuil, dedans, centre = _entree("grande_salle")
    cles += [
        (_sol(0.0, -33.5, 2.6), _sol(0.0, -20.0, 3.0), None, 56),
        (_sol(0.0, -22.5, 2.6), _sol(0.0, -12.0, 4.0), None, 58),
        (dehors, centre, None, 56),
        (dedans, centre + Vector((0, 0, 0.4)), 4, 62),
        (dehors + Vector((0, 0, 1.5)), _sol(0.0, -26.0, 6.0), None, 56),
        (_sol(4.0, -18.0, 18.0), _sol(40.0, 40.0, 10.0), None, 50),
    ]
    px, py = plan.PHARE
    a = math.atan2(py, px)
    vers_phare = Vector((math.cos(a), math.sin(a), 0))
    cote = Vector((-math.sin(a), math.cos(a), 0))
    zph = plan.HAUTEUR_SITE["phare"]
    cles += [
        (Vector((48.0, 38.0, 44.0)), Vector((px, py, zph + 8.0)), None, 46),
        (_sol(*(Vector((px, py, 0)) - vers_phare * 17.0 - cote * 4.0).xy, 2.6), Vector((px, py, zph + 10.0)), 5, 50),
        (Vector((px, py, 0)) - vers_phare * 4.0 + cote * 30.0 + Vector((0, 0, zph + 26.0)), Vector((0.0, 0.0, 6.0)), None, 42),
        (Vector((225.0, 128.0, 88.0)), Vector((-2.0, 4.0, -2.0)), 6, 34),
    ]
    return cles


def construire_reperes_camera(reperes):
    cles = cles_camera()
    for k, (cam, cible, chap, fov) in enumerate(cles):
        e = ancre(reperes, f"cam_{k:02d}", Vector(cam))
        e["chapitre"] = -1 if chap is None else chap
        e["fov"] = fov
        ancre(reperes, f"cible_{k:02d}", Vector(cible))
    # Guide et personnages extérieurs
    zp = plan.hauteur(2.2, -101.0)
    e = ancre(reperes, "guide_porte", Vector((2.2, -101.0, zp)))
    e["regard"] = math.radians(-100)
    e = ancre(reperes, "pnj_capitaine", Vector((-3.4, -94.5, plan.hauteur(-3.4, -94.5))))
    e["regard"] = math.radians(-80)
    e["role"] = "capitaine"
    b = plan.BATIMENTS_VILLE["taverne"]
    tx, ty = polaire(plan.R_RUE - plan.DEMI_RUE + 0.6, b["angle"] + 0.06)
    e = ancre(reperes, "pnj_aubergiste", Vector((tx, ty, plan.hauteur(tx, ty))))
    e["regard"] = b["angle"]
    e["role"] = "aubergiste"
    from .outils import SOLEIL_DIR
    ancre(reperes, "soleil", SOLEIL_DIR * 100.0)
    log(f"caméra : {len(cles)} clés, {sum(1 for c in cles if c[2] is not None)} chapitres")
    vues = [((c[0].x, c[0].y), (c[1].x, c[1].y)) for c in cles if c[2] in (1, 5)]
    return vues
