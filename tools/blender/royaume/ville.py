"""
La ville : des rangées de maisons à colombages le long de la rue circulaire, la grand-place avec sa
fontaine et son marché, la chapelle et l'auberge.

Chaque maison est tirée au sort : largeur, nombre d'étages, rez-de-chaussée en pierre ou enduit, étages en
colombage qui avancent sur la rue (encorbellement), toit long ou pignon sur rue, couleurs de l'enduit, des
tuiles et des volets, fenêtres allumées ou non, boutique avec auvent et enseigne, jardinières fleuries.

Repère local d'une maison : X le long de la rue, -Y vers la rue (la façade), Z vers le haut, origine au sol
au milieu de la façade.
"""

import math

from mathutils import Matrix, Vector

from . import plan
from .construction import Construction, ancre, lierre
from .outils import TUILE_BUISSON, TUILE_FEUILLU, log, polaire

PLATRES = [(0.78, 0.7, 0.55), (0.8, 0.6, 0.42), (0.76, 0.56, 0.5), (0.6, 0.66, 0.7), (0.64, 0.69, 0.54),
           (0.83, 0.8, 0.74), (0.72, 0.52, 0.36), (0.7, 0.62, 0.68)]
TUILES = [(0.42, 0.13, 0.07), (0.3, 0.12, 0.08), (0.11, 0.11, 0.13), (0.2, 0.17, 0.15), (0.5, 0.22, 0.1), (0.36, 0.17, 0.1)]
VOLETS = [(0.12, 0.25, 0.18), (0.1, 0.18, 0.35), (0.4, 0.08, 0.06), (0.45, 0.33, 0.12), (0.2, 0.2, 0.22)]
AUVENTS = [(0.55, 0.12, 0.08), (0.12, 0.3, 0.2), (0.5, 0.38, 0.12), (0.18, 0.2, 0.42), (0.55, 0.5, 0.42)]

HR, HF, JET = 3.1, 2.9, 0.32     # hauteur du rez-de-chaussée, d'un étage, avancée de chaque étage


def repere_rue(angle, cote, recul=0.3):
    """Repère d'une maison bâtie le long de la rue circulaire, à l'angle donné, côté extérieur (+1) ou intérieur (-1)."""
    r = plan.R_RUE + cote * (plan.DEMI_RUE + recul)
    x, y = polaire(r, angle)
    phi = angle if cote > 0 else angle + math.pi
    return Matrix.Translation((x, y, 0)) @ Matrix.Rotation(phi - math.pi / 2, 4, "Z"), (x, y)


def sol_sous(L, w, d):
    coins = [L @ Vector((sx * w / 2, sy, 0)) for sx in (-1, 1) for sy in (0.0, d)]
    return min(plan.hauteur(p.x, p.y) for p in coins)


def fenetre(c, feuillage, L, x, y_face, z, rnd, volet, allumee, largeur=0.8, hauteur=1.15, jardiniere=False, face=-1):
    """Fenêtre posée sur une façade (face = -1 : façade avant, +1 : arrière), avec cadre, volets et appui."""
    y = y_face + face * 0.05
    c.avec(donnee=(0.0, 1.0 if allumee else 0.0, 0.0))
    c.boite("fenetre", L @ Matrix.Translation((x, y, z)), (largeur, 0.06, hauteur))
    c.avec(donnee=(0.0, 0.0, 0.0))
    for s in (-1, 1):
        c.boite("bois_sombre", L @ Matrix.Translation((x + s * (largeur / 2 + 0.04), y + face * 0.03, z)), (0.09, 0.1, hauteur + 0.14))
        c.boite("bois_sombre", L @ Matrix.Translation((x, y + face * 0.03, z + s * (hauteur / 2 + 0.04))), (largeur + 0.16, 0.1, 0.09))
    c.boite("bois_sombre", L @ Matrix.Translation((x, y + face * 0.02, z)), (0.05, 0.08, hauteur))
    c.boite("bois_sombre", L @ Matrix.Translation((x, y + face * 0.02, z + hauteur * 0.12)), (largeur, 0.08, 0.05))
    if volet is not None:
        for s in (-1, 1):
            ouverture = rnd.uniform(0.15, 0.9)
            pivot = L @ Matrix.Translation((x + s * (largeur / 2 + 0.08), y + face * 0.04, z))
            c.boite("bois", pivot @ Matrix.Rotation(-s * face * ouverture, 4, "Z") @ Matrix.Translation((s * largeur * 0.27, face * 0.02, 0)),
                    (largeur * 0.52, 0.05, hauteur + 0.05), 0.0, volet)
    c.boite("pierre", L @ Matrix.Translation((x, y + face * 0.1, z - hauteur / 2 - 0.08)), (largeur + 0.3, 0.24, 0.1))
    if jardiniere and feuillage is not None:
        c.boite("bois", L @ Matrix.Translation((x, y + face * 0.22, z - hauteur / 2 - 0.2)), (largeur + 0.1, 0.24, 0.2), 0.0, (0.8, 0.7, 0.6))
        normale = (L.to_3x3() @ Vector((0, face, 0))).normalized()
        for s in range(3):
            p = L @ Vector((x + (s - 1) * largeur * 0.32, y + face * 0.26, z - hauteur / 2 - 0.05))
            n = (normale + Vector((0, 0, 1.0)) + Vector((rnd.gauss(0, 0.3), rnd.gauss(0, 0.3), 0))).normalized()
            feuillage.carte(p, n, Vector((0, 0, 1)), 0.4, 0.34, TUILE_BUISSON, (1.0, 1.0, 1.0), p - normale, 0.15, rnd.random(), 0.2)


def maison(c, feuillage, L, w, d, rnd, etages=None, reperes=None, style=None):
    """Une maison de ville. Renvoie la hauteur du faîtage (repère local)."""
    s = style or {}
    etages = etages or rnd.choice((2, 2, 3, 3, 3, 4))
    platre = s.get("platre", rnd.choice(PLATRES))
    tuile = s.get("tuile", rnd.choice(TUILES))
    volet = s.get("volet", rnd.choice(VOLETS + [None]))
    rdc_pierre = s.get("rdc_pierre", rnd.random() < 0.45)
    pignon_sur_rue = s.get("pignon", rnd.random() < 0.4)
    boutique = s.get("boutique", rnd.random() < 0.3)
    variante = rnd.random()
    z0 = sol_sous(L, w, d)
    L = Matrix.Translation((0, 0, z0)) @ L
    base_colombage = z0 + 0.4 + HR
    # Soubassement et rez-de-chaussée
    c.boite("pierre", L @ Matrix.Translation((0, d / 2, -0.4)), (w, d, 1.6), 0.0, (0.9, 0.88, 0.85))
    c.boite("pierre" if rdc_pierre else "enduit_maison", L @ Matrix.Translation((0, d / 2, 0.4 + HR / 2)), (w, d, HR), 0.0,
            (0.92, 0.9, 0.86) if rdc_pierre else platre)
    # Étages en colombage, chacun un peu plus en avant sur la rue
    c.avec(donnee=(variante, 0.0, base_colombage / 20.0))
    for k in range(1, etages):
        zb = 0.4 + HR + (k - 1) * HF
        avance = JET * k
        c.boite("colombage", L @ Matrix.Translation((0, (d - avance) / 2, zb + HF / 2)), (w, d + avance, HF), 0.0, platre)
    c.avec(donnee=(0.0, 0.0, 0.0))
    for k in range(1, etages):
        zb = 0.4 + HR + (k - 1) * HF
        c.boite("bois_sombre", L @ Matrix.Translation((0, -JET * k - 0.06, zb + 0.06)), (w + 0.04, 0.2, 0.22))
        for j in range(max(2, int(w / 1.3)) + 1):
            xj = -w / 2 + 0.25 + j * (w - 0.5) / max(2, int(w / 1.3))
            c.boite("bois_sombre", L @ Matrix.Translation((xj, -JET * k + 0.12, zb - 0.12)), (0.16, 0.42, 0.22))
    # Toit
    zt = 0.4 + HR + (etages - 1) * HF
    d_haut = d + JET * (etages - 1)
    yc = (d - JET * (etages - 1)) / 2
    pente = math.radians(rnd.uniform(50, 58))
    c.avec(donnee=(variante, 0.0, base_colombage / 20.0))
    if pignon_sur_rue:
        faitage = w / 2 * math.tan(pente)
        c.toit("tuiles", "colombage", L @ Matrix.Translation((0, yc, 0)) @ Matrix.Rotation(math.pi / 2, 4, "Z"),
               d_haut, w, zt, faitage, 0.4, 0.16, tuile, platre)
    else:
        faitage = d_haut / 2 * math.tan(pente)
        c.toit("tuiles", "colombage", L @ Matrix.Translation((0, yc, 0)), w, d_haut, zt, faitage, 0.45, 0.16, tuile, platre)
    c.avec(donnee=(0.0, 0.0, 0.0))
    # Cheminée
    cx = rnd.choice((-1, 1)) * w * rnd.uniform(0.15, 0.3)
    c.boite("pierre", L @ Matrix.Translation((cx, yc + d_haut * 0.18, zt + faitage * 0.55)), (0.6, 0.6, faitage * 1.1 + 1.0), 0.03)
    c.boite("pierre", L @ Matrix.Translation((cx, yc + d_haut * 0.18, zt + faitage * 1.1 + 0.55)), (0.75, 0.75, 0.12), 0.02)
    # Fenêtres des étages (façade et arrière)
    n_fen = max(1, int(w / 1.7))
    xs = [-w / 2 + (i + 0.5) * w / n_fen for i in range(n_fen)]
    for k in range(1, etages):
        zb = 0.4 + HR + (k - 1) * HF
        for x in xs:
            fenetre(c, feuillage, L, x + rnd.uniform(-0.05, 0.05), -JET * k, zb + 1.5, rnd, volet, rnd.random() < 0.38,
                    jardiniere=(k == 1 and rnd.random() < 0.35))
        for x in xs[::2]:
            fenetre(c, None, L, x, d, zb + 1.5, rnd, None, rnd.random() < 0.2, 0.7, 1.0, face=1)
    # Rez-de-chaussée : porte, et soit une vitrine avec auvent et enseigne, soit des fenêtres
    xp = rnd.choice(xs) if n_fen > 1 else 0.0
    if boutique:
        xp = -w / 2 + 0.9
    c.boite("bois_sombre", L @ Matrix.Translation((xp, -0.06, 0.4 + 1.1)), (1.05, 0.1, 2.2), 0.01, rnd.choice(VOLETS + [(1, 1, 1)]))
    c.boite("pierre", L @ Matrix.Translation((xp, -0.1, 0.4 + 2.32)), (1.35, 0.16, 0.2), 0.02)
    for sx in (-1, 1):
        c.boite("pierre", L @ Matrix.Translation((xp + sx * 0.6, -0.1, 0.4 + 1.1)), (0.16, 0.16, 2.3))
    c.boite("pierre", L @ Matrix.Translation((xp, -0.45, 0.2)), (1.4, 0.7, 0.4), 0.03)
    if boutique:
        lx = 0.7
        larg_vitrine = w - 2.2
        c.avec(donnee=(0.0, 1.0 if rnd.random() < 0.7 else 0.0, 0.0))
        c.boite("fenetre", L @ Matrix.Translation((lx, -0.06, 0.4 + 1.45)), (larg_vitrine, 0.06, 1.7))
        c.avec(donnee=(0.0, 0.0, 0.0))
        c.boite("bois_sombre", L @ Matrix.Translation((lx, -0.12, 0.4 + 0.5)), (larg_vitrine + 0.2, 0.2, 0.25))
        c.boite("bois_sombre", L @ Matrix.Translation((lx, -0.12, 0.4 + 2.35)), (larg_vitrine + 0.2, 0.18, 0.18))
        auvent = rnd.choice(AUVENTS)
        c.boite("tissu", L @ Matrix.Translation((lx, -0.75, 0.4 + 2.6)) @ Matrix.Rotation(-0.42, 4, "X"),
                (larg_vitrine + 0.5, 1.5, 0.04), 0.0, auvent)
        # Enseigne suspendue
        c.boite("metal", L @ Matrix.Translation((w / 2 - 0.3, -0.5, 0.4 + 3.4)), (0.05, 1.0, 0.05))
        c.boite("bois", L @ Matrix.Translation((w / 2 - 0.3, -0.75, 0.4 + 2.95)), (0.06, 0.75, 0.6), 0.01, (0.9, 0.75, 0.55))
        c.boite("or", L @ Matrix.Translation((w / 2 - 0.3, -0.75, 0.4 + 2.95)), (0.08, 0.35, 0.25))
    else:
        for x in xs:
            if abs(x - xp) > 0.9:
                fenetre(c, feuillage, L, x, 0.0, 0.4 + 1.6, rnd, volet, rnd.random() < 0.25, 0.75, 1.0)
    # Lanterne murale
    if reperes is not None and rnd.random() < 0.4:
        p = L @ Vector((xp + 0.95, -0.35, 0.4 + 2.55))
        c.boite("metal", Matrix.Translation(L @ Vector((xp + 0.95, -0.15, 0.4 + 2.75))) @ (L.to_3x3().to_4x4()), (0.05, 0.4, 0.05))
        c.sphere("lanterne", Matrix.Translation(p), 0.1, 1)
        ancre(reperes, f"lanterne_rue_{len([o for o in reperes.objects if o.name.startswith('lanterne_rue')]) + 1}", p)
    return zt + faitage


def rangees_de_maisons(M, colls, feuillage, reperes, rnd):
    """Pose les maisons des deux côtés de la rue circulaire, en laissant la place aux rues, à la place et aux monuments."""
    reserve = []      # (angle, demi-largeur angulaire, côté)
    for nom, b in plan.BATIMENTS_VILLE.items():
        r = plan.R_RUE + b["cote"] * (plan.DEMI_RUE + 0.3)
        reserve.append((b["angle"], (b["largeur"] / 2 + 0.6) / r, b["cote"]))
    nb = 0
    constructions = [Construction(f"maisons_{k}", colls[k], M) for k in range(len(colls))]
    for cote in (1, -1):
        r_face = plan.R_RUE + cote * (plan.DEMI_RUE + 0.3)
        prof_max = (plan.REMPARTS["milieu"]["rayon"] - plan.REMPARTS["milieu"]["epaisseur"] / 2 - 1.2 - r_face) if cote > 0 \
            else (r_face - plan.REMPARTS["interieur"]["rayon"] - plan.REMPARTS["interieur"]["epaisseur"] / 2 - 1.4)
        a = -math.pi
        while a < math.pi:
            w = rnd.uniform(4.3, 6.8)
            da = w / r_face
            am = a + da / 2
            # rues rayonnantes, place, monuments
            bloque = any(abs((am - ar + math.pi) % (2 * math.pi) - math.pi) < (plan.DEMI_RADIALE + 0.6) / r_face + da / 2
                         for ar in plan.RADIALES)
            x, y = polaire(r_face, am)
            bloque = bloque or plan.dist_place(x, y) < 1.0
            bloque = bloque or any(cote == rc and abs((am - ra + math.pi) % (2 * math.pi) - math.pi) < rd + da / 2
                                   for ra, rd, rc in reserve)
            if bloque:
                a += 0.6 / r_face
                continue
            d = min(prof_max, rnd.uniform(6.2, 9.5))
            # Les tours du rempart intérieur avancent dans les cours : maisons moins profondes à cet endroit
            L, (x, y) = repere_rue(am, cote)
            fond = L @ Vector((0, d, 0))
            while d > 4.5 and any(math.hypot(fond.x - ox, fond.y - oy) < orr for ox, oy, orr in plan.OBSTACLES):
                d -= 0.5
                fond = L @ Vector((0, d, 0))
            c = constructions[0 if (am % (2 * math.pi)) < math.pi else len(constructions) - 1]
            maison(c, feuillage, L, w - 0.04, d, rnd, reperes=reperes)
            centre = L @ Vector((0, d / 2, 0))
            plan.EMPRISES.append((centre.x, centre.y, am + math.pi / 2, w / 2, d / 2))
            nb += 1
            a += da
    for c in constructions:
        c.objet(groupe=c.nom)
    log(f"maisons : {nb}")


def place_du_marche(M, coll, vivant, feuillage, reperes, rnd):
    """Fontaine au centre, étals tout autour (sauf dans l'axe de l'avenue), bancs et arbres en bacs."""
    px, py, pr = plan.PLACE
    z = plan.HAUTEUR_SITE["place"]
    c = Construction("place", coll, M)
    F = Matrix.Translation((px, py, z))
    # Fontaine : bassin octogonal, colonne, vasque
    c.cylindre("pierre", F @ Matrix.Translation((0, 0, 0.3)), 2.9, 2.9, 0.75, 8, (0.95, 0.93, 0.9), lisse=False)
    c.cylindre("pierre", F @ Matrix.Translation((0, 0, 0.72)), 3.05, 3.05, 0.12, 8, lisse=False)
    c.cylindre("pierre", F @ Matrix.Translation((0, 0, 1.3)), 0.35, 0.28, 1.6, 12)
    c.cylindre("pierre", F @ Matrix.Translation((0, 0, 2.15)), 0.4, 1.1, 0.35, 16)
    c.cylindre("pierre", F @ Matrix.Translation((0, 0, 2.6)), 0.15, 0.12, 0.7, 10)
    c.sphere("or", F @ Matrix.Translation((0, 0, 3.05)), 0.18, 2)
    e = Construction("eau_fontaine", vivant, M)
    e.cylindre("eau", F @ Matrix.Translation((0, 0, 0.62)), 2.75, 2.75, 0.02, 32)
    ob = e.objet(vivant="eau", ecoulement=0, garder_uv=1, bassin=1)
    ancre(reperes, "fontaine_jet", Vector((px, py, z + 3.2)))
    plan.OBSTACLES.append((px, py, 3.4))
    # Étals
    for k in range(10):
        a = math.radians(-60 + k * 36)
        if abs(math.sin(a)) > 0.88:      # garde l'axe nord-sud (l'avenue) libre
            continue
        sx, sy = px + 6.8 * math.cos(a), py + 6.8 * math.sin(a)
        L = Matrix.Translation((sx, sy, plan.hauteur(sx, sy))) @ Matrix.Rotation(a + math.pi / 2, 4, "Z")
        couleur = rnd.choice(AUVENTS)
        for ix in (-1, 1):
            for iy in (-1, 1):
                c.boite("bois", L @ Matrix.Translation((ix * 1.25, iy * 0.75, 1.15)), (0.1, 0.1, 2.3), 0.0, (0.8, 0.7, 0.6))
        c.boite("bois", L @ Matrix.Translation((0, -0.4, 0.9)), (2.6, 0.9, 0.1), 0.01)
        c.boite("bois_sombre", L @ Matrix.Translation((0, -0.4, 0.45)), (2.5, 0.85, 0.8), 0.0, (0.8, 0.75, 0.7))
        for s in (-1, 1):
            c.boite("tissu", L @ Matrix.Translation((0, s * 0.42, 2.45)) @ Matrix.Rotation(s * 0.35, 4, "X"), (2.9, 0.95, 0.04), 0.0, couleur)
        # Marchandises : caisses de fruits, jarres, tissus roulés
        for j in range(5):
            gx = -1.0 + j * 0.5
            c.boite("bois", L @ Matrix.Translation((gx, -0.45, 1.05)), (0.42, 0.42, 0.18), 0.0, (0.75, 0.65, 0.5))
            teinte = rnd.choice([(0.7, 0.1, 0.05), (0.85, 0.5, 0.05), (0.2, 0.45, 0.08), (0.6, 0.55, 0.1), (0.35, 0.05, 0.3)])
            for q in range(4):
                c.sphere("tissu", L @ Matrix.Translation((gx + (q % 2 - 0.5) * 0.18, -0.45 + (q // 2 - 0.5) * 0.18, 1.2)), 0.08, 1, teinte)
        for j in range(2):
            c.cylindre("enduit", L @ Matrix.Translation((1.6, 0.2 + j * 0.5, 0.35)), 0.2, 0.15, 0.7, 10, (0.7, 0.45, 0.3))
        plan.OBSTACLES.append((sx, sy, 1.6))
    # Bancs et arbres en bacs au bord de la place
    for k in range(6):
        a = math.radians(30 + k * 60 + 15)
        bx, by = px + (pr - 1.6) * math.cos(a), py + (pr - 1.6) * math.sin(a)
        if abs(math.sin(a)) > 0.9:
            continue
        L = Matrix.Translation((bx, by, plan.hauteur(bx, by))) @ Matrix.Rotation(a + math.pi / 2, 4, "Z")
        c.boite("pierre", L @ Matrix.Translation((0, 0, 0.6)), (1.4, 1.4, 1.2), 0.04, (0.85, 0.83, 0.8))
        plan.OBSTACLES.append((bx, by, 1.0))
    c.objet(groupe="monuments")
    log("place du marché : fontaine et étals")


def chapelle(M, coll, feuillage, reperes, rnd):
    b = plan.BATIMENTS_VILLE["chapelle"]
    L, _ = repere_rue(b["angle"], b["cote"])
    w, d = b["largeur"], b["profondeur"]
    z0 = sol_sous(L, w, d)
    L = Matrix.Translation((0, 0, z0)) @ L
    c = Construction("chapelle", coll, M)
    h = 9.0
    c.boite("pierre", L @ Matrix.Translation((0, d / 2 + 0.8, h / 2 - 0.6)), (w, d - 1.6, h + 1.2), 0.05, (1.0, 0.97, 0.92))
    pente = math.radians(58)
    c.toit("ardoises", "pierre", L @ Matrix.Translation((0, d / 2 + 0.8, 0)) @ Matrix.Rotation(math.pi / 2, 4, "Z"),
           d - 1.4, w, h, w / 2 * math.tan(pente), 0.35, 0.18, (0.9, 0.9, 1.0), (1.0, 0.97, 0.92))
    # Contreforts et vitraux en arc
    for k in range(3):
        y = 2.6 + k * 2.6
        for s in (-1, 1):
            c.boite("pierre", L @ Matrix.Translation((s * (w / 2 + 0.35), y + 1.3, h * 0.4)), (0.7, 0.6, h * 0.8), 0.04)
            c.boite("vitrail", L @ Matrix.Translation((s * (w / 2 + 0.02), y, h * 0.55)), (0.06, 1.1, 3.4))
    # Clocher sur la façade, avec sa flèche
    tour = 3.6
    ht = h + 9.0
    c.boite("pierre", L @ Matrix.Translation((0, 0.9, ht / 2 - 0.6)), (tour, tour, ht + 1.2), 0.05, (1.0, 0.97, 0.92))
    for s in range(4):
        a = s * math.pi / 2
        c.boite("bois_sombre", L @ Matrix.Translation((math.sin(a) * (tour / 2 + 0.01), 0.9 - math.cos(a) * (tour / 2 + 0.01), ht - 1.6))
                @ Matrix.Rotation(a, 4, "Z"), (1.0, 0.06, 1.8))
    c.cylindre("ardoises", L @ Matrix.Translation((0, 0.9, ht + 3.4)) @ Matrix.Rotation(math.pi / 4, 4, "Z"), tour * 0.8, 0.05, 7.0, 8,
               (0.9, 0.9, 1.0))
    c.cylindre("or", L @ Matrix.Translation((0, 0.9, ht + 7.4)), 0.04, 0.04, 1.0, 6)
    c.boite("or", L @ Matrix.Translation((0, 0.9, ht + 7.6)), (0.5, 0.04, 0.05))
    # Rosace et portail
    c.cylindre("vitrail", L @ Matrix.Translation((0, -0.92, h - 1.2)) @ Matrix.Rotation(math.pi / 2, 4, "X"), 0.85, 0.85, 0.06, 20)
    c.boite("bois_sombre", L @ Matrix.Translation((0, -0.92, 1.4)), (1.5, 0.1, 2.8), 0.02)
    c.arche("pierre", L @ Matrix.Translation((0, -1.0, 0)), 0.95, 0.3, 0.4, 2.8, 7)
    for s in (-1, 1):
        c.boite("pierre", L @ Matrix.Translation((s * 0.95, -1.0, 1.4)), (0.3, 0.4, 2.8))
    ancre(reperes, "lanterne_chapelle", L @ Vector((1.4, -1.2, 2.6)))
    c.sphere("lanterne", Matrix.Translation(L @ Vector((1.4, -1.2, 2.6))), 0.12, 1)
    centre = L @ Vector((0, d / 2, 0))
    plan.EMPRISES.append((centre.x, centre.y, b["angle"] + math.pi / 2, w / 2 + 0.6, d / 2 + 0.6))
    c.objet(groupe="monuments")


def taverne(M, coll, feuillage, reperes, rnd):
    b = plan.BATIMENTS_VILLE["taverne"]
    L, _ = repere_rue(b["angle"], b["cote"])
    c = Construction("taverne", coll, M)
    haut = maison(c, feuillage, L, b["largeur"], b["profondeur"], rnd, etages=3, reperes=reperes,
                  style=dict(platre=(0.82, 0.68, 0.45), tuile=(0.38, 0.12, 0.07), volet=(0.12, 0.25, 0.18),
                             rdc_pierre=True, pignon=False, boutique=False))
    z0 = sol_sous(L, b["largeur"], b["profondeur"])
    L = Matrix.Translation((0, 0, z0)) @ L
    # Grande enseigne, tonneaux et bancs devant
    c.boite("metal", L @ Matrix.Translation((2.6, -0.7, 3.7)), (0.06, 1.4, 0.06))
    c.boite("bois", L @ Matrix.Translation((2.6, -1.1, 3.1)), (0.08, 1.1, 0.8), 0.01, (0.9, 0.75, 0.5))
    c.cylindre("or", L @ Matrix.Translation((2.6, -1.1, 3.1)) @ Matrix.Rotation(math.pi / 2, 4, "Y"), 0.25, 0.25, 0.1, 12)
    for k in range(3):
        c.cylindre("bois", L @ Matrix.Translation((-3.5 + k * 0.7, -0.6, 0.45)), 0.3, 0.3, 0.9, 12, (0.8, 0.7, 0.55))
    c.boite("bois", L @ Matrix.Translation((0.5, -1.0, 0.45)), (2.0, 0.4, 0.07), 0.01)
    for s in (-1, 1):
        c.boite("bois_sombre", L @ Matrix.Translation((0.5 + s * 0.8, -1.0, 0.22)), (0.08, 0.34, 0.44))
    for s in (-1, 1):
        p = L @ Vector((s * 1.8, -0.4, 2.7))
        c.sphere("lanterne", Matrix.Translation(p), 0.12, 1)
        ancre(reperes, f"lanterne_taverne_{1 if s < 0 else 2}", p)
    centre = L @ Vector((0, b["profondeur"] / 2, 0))
    plan.EMPRISES.append((centre.x, centre.y, b["angle"] + math.pi / 2, b["largeur"] / 2, b["profondeur"] / 2))
    c.objet(groupe="monuments")


def construire_ville(M, coll_maisons, coll_monuments, vivant, feuillage, reperes, rnd):
    place_du_marche(M, coll_monuments, vivant, feuillage, reperes, rnd)
    chapelle(M, coll_monuments, feuillage, reperes, rnd)
    taverne(M, coll_monuments, feuillage, reperes, rnd)
    rangees_de_maisons(M, coll_maisons, feuillage, reperes, rnd)
