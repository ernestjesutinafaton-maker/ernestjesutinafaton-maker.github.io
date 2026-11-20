"""
La campagne, entre le rempart du milieu et le rempart extérieur : des fermes (maison, grange, cour,
meules de foin), un moulin à vent dont les ailes tournent (sur le site), un pont sur la rivière, un
épouvantail, des clôtures autour du pâturage. Les champs eux-mêmes sont peints dans le sol (terrain.py).
"""

import math

from mathutils import Matrix, Vector

from . import plan
from .construction import Construction, ancre
from .outils import TUILE_BUISSON, log, polaire
from .ville import maison, sol_sous


def T(x, y, z):
    return Matrix.Translation((x, y, z))


def repere_vers_centre(x, y, z=None):
    """Repère local en (x, y) dont la façade (-Y) regarde vers le centre du royaume."""
    a = math.atan2(y, x)
    z = plan.hauteur(x, y) if z is None else z
    return T(x, y, z) @ Matrix.Rotation(a - math.pi / 2, 4, "Z")


def grange(c, L, w, d, rnd):
    z0 = sol_sous(L, w, d)
    L = T(0, 0, z0) @ L
    c.boite("pierre", L @ T(0, d / 2, -0.2), (w, d, 1.0), 0.0, (0.85, 0.82, 0.78))
    n = int(w / 0.32)
    for k in range(n):
        t = 0.7 + 0.35 * rnd.random()
        for y in (0.0, d):
            c.boite("bois", L @ T(-w / 2 + (k + 0.5) * w / n, y, 0.3 + 2.3), (w / n - 0.02, 0.1, 4.6), 0.0, (t * 0.95, t * 0.8, t * 0.7))
    for s in (-1, 1):
        c.boite("bois", L @ T(s * w / 2, d / 2, 2.6), (0.12, d, 4.6), 0.0, (0.8, 0.68, 0.58))
    c.boite("bois_sombre", L @ T(0, -0.08, 1.9), (2.8, 0.08, 3.2), 0.02)
    for k in range(4):
        c.boite("bois", L @ T(0, -0.12, 0.6 + k * 0.85), (2.9, 0.06, 0.12))
    faitage = d / 2 * math.tan(math.radians(50))
    c.toit("paille", "bois", L @ T(0, d / 2, 0), w, d, 4.9, faitage, 0.7, 0.35, (1, 1, 1), (0.8, 0.68, 0.58))
    c.boite("bois_sombre", L @ T(0, -0.15, 5.6), (1.2, 0.1, 1.0))
    plan.EMPRISES.append(((L @ Vector((0, d / 2, 0))).x, (L @ Vector((0, d / 2, 0))).y,
                          math.atan2((L.to_3x3() @ Vector((1, 0, 0))).y, (L.to_3x3() @ Vector((1, 0, 0))).x), w / 2, d / 2))


def meule(c, x, y, rnd, r=None):
    r = r or rnd.uniform(1.1, 1.6)
    z = plan.hauteur(x, y)
    v = c.sphere("paille", T(x, y, z + r * 0.45) @ Matrix.Diagonal((1, 1, 1.15, 1)), r, 2)
    c.bosseler(v, Vector((x, y, z + r * 0.45)), r * 0.08, 2.0, rnd.random() * 9)
    plan.OBSTACLES.append((x, y, r + 0.3))


def cloture(c, pts, rnd, hauteur=1.1, pas=2.2):
    """Piquets et deux lisses le long d'une polyligne."""
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        l = math.hypot(bx - ax, by - ay)
        n = max(1, int(l / pas))
        ang = math.atan2(by - ay, bx - ax)
        for k in range(n + 1):
            x, y = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
            z = plan.hauteur(x, y)
            c.boite("bois", T(x, y, z + hauteur / 2 - 0.1) @ Matrix.Rotation(rnd.uniform(-0.15, 0.15), 4, "Z"), (0.12, 0.12, hauteur), 0.01,
                    (0.75, 0.7, 0.62))
            if k < n:
                x2, y2 = ax + (bx - ax) * (k + 1) / n, ay + (by - ay) * (k + 1) / n
                z2 = plan.hauteur(x2, y2)
                mx, my, mz = (x + x2) / 2, (y + y2) / 2, (z + z2) / 2
                pente = math.atan2(z2 - z, l / n)
                for hz in (0.45, 0.85):
                    c.boite("bois", T(mx, my, mz + hz) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(-pente, 4, "Y"),
                            (l / n + 0.1, 0.06, 0.09), 0.0, (0.8, 0.74, 0.65))


def ferme(c, feuillage, reperes, k, a, rf, rnd):
    x, y = polaire(rf, a)
    L = repere_vers_centre(x, y, 0.0)
    maison(c, feuillage, L @ T(-4.5, 0, 0), 7.5, 7.0, rnd, etages=2, reperes=reperes,
           style=dict(rdc_pierre=True, pignon=rnd.random() < 0.5, boutique=False, tuile=(0.38, 0.14, 0.08)))
    plan.EMPRISES.append(((L @ Vector((-4.5, 3.5, 0))).x, (L @ Vector((-4.5, 3.5, 0))).y, a + math.pi / 2, 3.9, 3.6))
    grange(c, L @ T(5.0, 1.0, 0) @ Matrix.Rotation(rnd.uniform(-0.15, 0.15), 4, "Z"), 7.0, 9.0, rnd)
    for j in range(rnd.randint(2, 4)):
        p = L @ Vector((rnd.uniform(-4, 6), rnd.uniform(-7.5, -4.0), 0))
        meule(c, p.x, p.y, rnd)
    # Charrette dans la cour
    p = L @ Vector((0.5, -3.0, 0))
    z = plan.hauteur(p.x, p.y)
    R = T(p.x, p.y, z) @ Matrix.Rotation(a + rnd.uniform(-1, 1), 4, "Z")
    c.boite("bois", R @ T(0, 0, 0.75), (1.4, 2.4, 0.12), 0.01, (0.85, 0.75, 0.6))
    for s in (-1, 1):
        c.boite("bois", R @ T(s * 0.68, 0, 1.0), (0.06, 2.4, 0.4), 0.0, (0.85, 0.75, 0.6))
        c.cylindre("bois_sombre", R @ T(s * 0.78, -0.3, 0.55) @ Matrix.Rotation(math.pi / 2, 4, "Y"), 0.55, 0.55, 0.1, 14)
    c.boite("bois", R @ T(0, 1.8, 0.75), (0.08, 1.4, 0.08))
    plan.OBSTACLES.append((p.x, p.y, 1.6))
    # Clôture de la cour, côté champs
    coins = [L @ Vector((-9.5, -9.0, 0)), L @ Vector((9.5, -9.0, 0)), L @ Vector((9.5, 10.0, 0))]
    cloture(c, [(v.x, v.y) for v in coins], rnd)
    ancre(reperes, f"ferme_{k}", L @ Vector((0, -5.0, 1.0)))


def moulin(c, vivant, M, reperes, rnd):
    x, y = plan.MOULIN
    z0 = plan.HAUTEUR_SITE["moulin"] - 0.3
    a = math.atan2(y, x)
    B = T(x, y, z0)
    h = 10.5
    c.cylindre("enduit", B @ T(0, 0, h / 2), 3.3, 2.4, h, 24, (0.95, 0.93, 0.88))
    c.cylindre("pierre", B @ T(0, 0, 0.5), 3.5, 3.4, 1.2, 24)
    c.cylindre("bois_sombre", B @ T(0, 0, h + 0.15), 2.7, 2.7, 0.3, 24)
    c.cylindre("tuiles", B @ T(0, 0, h + 1.7), 2.8, 0.1, 3.0, 24, (0.4, 0.14, 0.08))
    sortie = Vector((math.cos(a), math.sin(a), 0))
    c.boite("bois_sombre", Matrix.Translation(B @ Vector((0, 0, 1.5)) + sortie * 3.3) @ Matrix.Rotation(a + math.pi / 2, 4, "Z"),
            (1.2, 0.15, 2.3))
    for hz in (4.5, 7.5):
        c.avec(donnee=(0, 1.0, 0))
        c.boite("fenetre", Matrix.Translation(B @ Vector((0, 0, hz)) + sortie * (3.2 - hz * 0.08)) @ Matrix.Rotation(a + math.pi / 2, 4, "Z"),
                (0.7, 0.1, 0.9))
        c.avec(donnee=(0, 0, 0))
    # Ailes : un objet vivant qui tourne autour de l'axe (horizontal, tourné vers l'extérieur)
    moyeu = B @ Vector((0, 0, h + 0.6)) + sortie * 3.0
    c.boite("bois_sombre", Matrix.Translation(B @ Vector((0, 0, h + 0.6)) + sortie * 1.7) @ Matrix.Rotation(a, 4, "Z"), (2.8, 0.35, 0.35))
    ailes = Construction("vivant_ailes_moulin", vivant, M)
    R = Matrix.Translation(moyeu) @ (sortie.to_track_quat("Z", "Y").to_matrix().to_4x4())
    ailes.cylindre("bois_sombre", R, 0.35, 0.35, 0.6, 12)
    for k in range(4):
        b = k * math.pi / 2 + 0.3
        Rk = R @ Matrix.Rotation(b, 4, "Z")
        ailes.boite("bois_sombre", Rk @ T(0, 4.2, 0.0), (0.18, 8.4, 0.16))
        for j in range(7):
            ailes.boite("bois", Rk @ T(0.45, 1.6 + j * 1.0, 0.05), (0.85, 0.06, 0.04), 0.0, (0.8, 0.72, 0.6))
        ailes.boite("tissu", Rk @ T(0.45, 4.6, 0.08), (0.8, 6.2, 0.02), 0.0, (0.82, 0.76, 0.65))
    ob = ailes.objet(vivant="moulin")
    ob["axe_x"], ob["axe_y"], ob["axe_z"] = sortie.x, sortie.y, sortie.z
    ancre(reperes, "moulin_moyeu", moyeu)
    plan.OBSTACLES.append((x, y, 4.0))
    ancre(reperes, "pnj_meunier", B @ Vector((0, 0, 0)) + sortie * 4.4)["regard"] = a


def pont(c, profil, rnd):
    """Pont de pierre là où le chemin de la ferme du nord-ouest traverse la rivière."""
    a, rf = plan.FERMES[2]
    meilleur = min(profil, key=lambda p: abs(math.atan2(p[1], p[0]) - a) + abs(math.hypot(p[0], p[1]) - 70.5) * 0.05)
    x, y, z, _ = meilleur
    ang = math.atan2(y, x)
    L = T(x, y, z) @ Matrix.Rotation(ang, 4, "Z")
    longueur = 2 * plan.LARGEUR_RIVIERE + 4.0
    for k in range(9):
        t = (k / 8 - 0.5)
        hz = 1.3 - (2 * t) ** 2 * 0.8
        c.boite("pierre", L @ T(t * longueur, 0, hz), (longueur / 8 + 0.05, 2.6, 0.35), 0.02, (0.92, 0.9, 0.86))
        for s in (-1, 1):
            c.boite("pierre", L @ T(t * longueur, s * 1.25, hz + 0.45), (longueur / 8 + 0.05, 0.3, 0.6), 0.02)
    c.arche("pierre", L @ Matrix.Rotation(math.pi / 2, 4, "Z") @ T(0, 0, -0.6), plan.LARGEUR_RIVIERE + 0.4, 0.4, 2.5, 0.6, 7)
    plan.PONTS.append((x, y, ang, longueur / 2 + 0.5, 1.0, z + 1.48))
    return (x, y, z + 1.4)


def epouvantail(c, x, y, rnd):
    z = plan.hauteur(x, y)
    c.boite("bois", T(x, y, z + 1.0), (0.1, 0.1, 2.0))
    c.boite("bois", T(x, y, z + 1.6), (1.4, 0.08, 0.08))
    c.boite("tissu", T(x, y, z + 1.35), (0.55, 0.3, 0.7), 0.0, (0.5, 0.25, 0.15))
    c.sphere("paille", T(x, y, z + 2.05), 0.22, 2)
    c.cylindre("paille", T(x, y, z + 2.25), 0.4, 0.15, 0.2, 14)
    plan.OBSTACLES.append((x, y, 0.6))


def construire_campagne(M, coll, vivant, feuillage, reperes, profil, rnd):
    c = Construction("campagne", coll, M)
    for k, (a, rf) in enumerate(plan.FERMES):
        ferme(c, feuillage, reperes, k, a, rf, rnd)
    moulin(c, vivant, M, reperes, rnd)
    pont_pos = pont(c, profil, rnd)
    for a in (math.radians(-35), math.radians(80), math.radians(250)):
        epouvantail(c, *polaire(75.5, a), rnd)
    # Clôture du pâturage
    a0, a1, r0, r1 = plan.PATURAGE
    pts = [polaire(r0, a0)] + [polaire(r1, a0 + (a1 - a0) * k / 8) for k in range(9)] + [polaire(r0, a1)]
    cloture(c, pts, rnd)
    for k in range(rnd.randint(6, 9)):
        r = rnd.uniform(64.0, 80.0)
        a = rnd.random() * 2 * math.pi
        x, y = polaire(r, a)
        if plan.champ(x, y) is not None and plan.libre(x, y, 1.0):
            meule(c, x, y, rnd)
    c.objet(groupe="campagne")
    log("campagne : fermes, moulin, pont, meules, clôtures")
    return pont_pos
