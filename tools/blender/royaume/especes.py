"""Espèces d'arbres et de buissons, faits de cartes de feuilles autour de vrais troncs."""

import math

from mathutils import Matrix, Vector

from .outils import TUILE_AIGUILLES, TUILE_BUISSON, TUILE_CYPRES, TUILE_FEUILLU, lerp


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


