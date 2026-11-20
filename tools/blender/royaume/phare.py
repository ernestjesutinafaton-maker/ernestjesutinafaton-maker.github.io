"""Le phare, sur son promontoire au nord-est, hors des remparts : le dernier chapitre (contact)."""

import math

from mathutils import Matrix, Vector

from . import plan
from .construction import Construction, ancre, lierre
from .outils import lerp, log, polaire


def T(x, y, z):
    return Matrix.Translation((x, y, z))


def construire_phare(M, coll, reperes, feuillage, rnd):
    px, py = plan.PHARE
    z0 = plan.HAUTEUR_SITE["phare"] - 0.2
    # La porte regarde vers le royaume (vers le chemin qui arrive de la porte nord-est)
    a = math.atan2(-py, -px)
    L = T(px, py, z0) @ Matrix.Rotation(a + math.pi / 2, 4, "Z")
    c = Construction("phare", coll, M)
    plan.OBSTACLES.append((px, py, 3.2))
    c.cylindre("pierre", L @ T(0, 0, 0.1), 3.4, 3.3, 1.4, 36)
    hauteur_tour, tranches = 16.0, 8
    for k in range(tranches):
        z1, z2 = 0.8 + hauteur_tour * k / tranches, 0.8 + hauteur_tour * (k + 1) / tranches
        c.cylindre("rouge" if k % 2 else "enduit", L @ T(0, 0, (z1 + z2) / 2), lerp(2.5, 1.7, k / tranches),
                   lerp(2.5, 1.7, (k + 1) / tranches), z2 - z1 + 0.002, 36)
    zt = 0.8 + hauteur_tour
    c.cylindre("pierre", L @ T(0, 0, zt + 0.15), 2.6, 2.6, 0.3, 36)
    for k in range(24):
        b = 2 * math.pi * k / 24
        c.cylindre("metal", L @ T(2.4 * math.cos(b), 2.4 * math.sin(b), zt + 0.85), 0.03, 0.03, 1.1, 6)
    c.cylindre("metal", L @ T(0, 0, zt + 1.4), 2.45, 2.45, 0.06, 36)
    c.cylindre("metal", L @ T(0, 0, zt + 0.35), 1.45, 1.45, 0.12, 24)
    c.cylindre("lumiere_phare", L @ T(0, 0, zt + 1.3), 1.3, 1.3, 1.9, 16)
    for k in range(8):
        b = 2 * math.pi * k / 8
        c.boite("metal", L @ T(1.32 * math.cos(b), 1.32 * math.sin(b), zt + 1.3) @ Matrix.Rotation(b, 4, "Z"), (0.08, 0.1, 1.95))
    c.cylindre("metal", L @ T(0, 0, zt + 2.35), 1.45, 1.45, 0.12, 24)
    c.demi_sphere("rouge", L @ T(0, 0, zt + 2.4), 1.5)
    c.cylindre("metal", L @ T(0, 0, zt + 4.2), 0.08, 0.02, 0.8, 8)
    ancre(reperes, "phare_lampe", L @ Vector((0, 0, zt + 1.3)))
    c.boite("bois_sombre", L @ T(0, -2.45, 1.9), (1.1, 0.3, 2.2), 0.02)
    c.boite("pierre", L @ T(0, -2.55, 3.1), (1.5, 0.35, 0.22), 0.02)
    for k, hz in enumerate((6.0, 10.0, 13.6)):
        b = -math.pi / 2 + (0.5 if k % 2 else -0.4)
        rr = lerp(2.5, 1.7, (hz - 0.8) / hauteur_tour)
        c.avec(donnee=(0, 1.0 if k == 1 else 0.0, 0))
        c.boite("fenetre", L @ T(rr * math.cos(b), rr * math.sin(b), hz) @ Matrix.Rotation(b + math.pi / 2, 4, "Z"), (0.5, 0.14, 0.8))
        c.avec(donnee=(0, 0, 0))
    # Maison du gardien, accolée
    G = L @ T(4.8, 0.5, 0) @ Matrix.Rotation(0.1, 4, "Z")
    c.boite("pierre", G @ T(0, 0, 1.4), (4.4, 3.6, 3.4), 0.05, (0.95, 0.93, 0.88))
    c.toit("ardoises", "pierre", G @ T(0, 0, 0), 4.4, 3.6, 3.1, 1.6, 0.35, 0.15, (0.9, 0.9, 1.0), (0.95, 0.93, 0.88))
    c.avec(donnee=(0, 1.0, 0))
    c.boite("fenetre", G @ T(0.8, -1.82, 1.6), (0.8, 0.06, 0.9))
    c.avec(donnee=(0, 0, 0))
    c.boite("bois_sombre", G @ T(-0.9, -1.82, 1.05), (0.9, 0.08, 1.9))
    c.boite("pierre", G @ T(1.3, 0.6, 3.8), (0.5, 0.5, 1.6))
    ancre(reperes, "fumee_phare", G @ Vector((1.3, 0.6, 4.8)))
    plan.OBSTACLES.append(((G @ Vector((0, 0, 0))).x, (G @ Vector((0, 0, 0))).y, 3.0))
    # Muret de pierres sèches et banc face au couchant
    for k in range(34):
        b = math.radians(70) + 2 * math.pi * k / 44
        rr = 6.0 + rnd.uniform(-0.1, 0.1)
        p = L @ Vector((rr * math.cos(b), rr * math.sin(b), 0))
        t = 0.75 + 0.2 * rnd.random()
        c.boite("pierre", T(p.x, p.y, plan.hauteur(p.x, p.y) + 0.22) @ Matrix.Rotation(a + b + rnd.uniform(-0.2, 0.2), 4, "Z"),
                (0.6, 0.85, 0.55), 0.06, (t, t, t))
        plan.OBSTACLES.append((p.x, p.y, 0.5))
        if k % 5 == 0:
            lierre(feuillage, Vector((p.x, p.y, plan.hauteur(p.x, p.y) + 0.55)), Vector((0, 0, 1)), rnd, 3, 0.3, 0.45)
    bx, by = polaire(math.hypot(px, py) - 7.5, math.atan2(py, px) - 0.04)
    B = T(bx, by, plan.hauteur(bx, by)) @ Matrix.Rotation(math.atan2(by, bx) + math.pi / 2, 4, "Z")
    c.boite("bois", B @ T(0, 0, 0.45), (1.7, 0.42, 0.07), 0.015)
    c.boite("bois", B @ T(0, 0.2, 0.78) @ Matrix.Rotation(-0.15, 4, "X"), (1.7, 0.06, 0.34), 0.015)
    for s in (-1, 1):
        c.boite("bois_sombre", B @ T(s * 0.7, 0, 0.22), (0.08, 0.38, 0.45))
    plan.OBSTACLES.append((bx, by, 1.0))
    # Lanternes le long du chemin du phare
    for k, (x, y) in enumerate(plan.CHEMIN_PHARE[1:-1:2]):
        nx, ny = -math.sin(plan.ANGLE_PHARE), math.cos(plan.ANGLE_PHARE)
        lx, ly = x + nx * 1.6 * (1 if k % 2 else -1), y + ny * 1.6 * (1 if k % 2 else -1)
        z = plan.hauteur(lx, ly)
        c.boite("bois_sombre", T(lx, ly, z + 0.75), (0.1, 0.1, 1.5), 0.015)
        c.sphere("lanterne", T(lx, ly, z + 1.6), 0.09, 1)
        c.boite("metal", T(lx, ly, z + 1.72), (0.22, 0.22, 0.04))
        ancre(reperes, f"lanterne_chemin_phare_{k + 1}", Vector((lx, ly, z + 1.6)))
        plan.OBSTACLES.append((lx, ly, 0.4))
    c.objet(groupe="monuments_ext")
    e = ancre(reperes, "pnj_gardien", L @ Vector((1.8, -3.6, 0)))
    e["regard"] = a
    e["role"] = "gardien"
    ancre(reperes, "guide_phare", L @ Vector((-1.6, -4.4, 0)))["regard"] = a
    ancre(reperes, "porte_phare", L @ Vector((0, -6.0, 1.6)))
    log("phare, maison du gardien, chemin et ses lanternes")
