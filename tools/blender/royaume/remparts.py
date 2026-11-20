"""
Les trois remparts concentriques, leurs tours et leurs porteries.

Chaque rempart est un profil extrudé tout autour du centre : un fruit (le mur s'élargit vers le bas),
un parapet crénelé côté extérieur, un chemin de ronde, un petit garde-corps côté ville.
Les portes coupent l'anneau ; une porterie (deux tours, un passage voûté, une herse levée) bouche le trou.
Là où la rivière passe sous le rempart extérieur, le mur repose sur une arche.
"""

import math

from mathutils import Matrix, Vector

from . import plan
from .construction import Construction, ancre, lierre
from .outils import log, polaire

# Profil du mur : (décalage radial depuis le milieu du mur, hauteur) ; les valeurs « T » et « H » sont remplacées
PARAPET, MERLON_H = 1.4, 1.1


def _profil(T, H, bas):
    return [
        (T / 2 + 0.9, bas), (T / 2, H), (T / 2, H + PARAPET), (T / 2 - 0.7, H + PARAPET), (T / 2 - 0.7, H),
        (-T / 2 + 0.5, H), (-T / 2 + 0.5, H + 0.9), (-T / 2, H + 0.9), (-T / 2, bas),
    ]


def _angles_tours(nom, m):
    portes = plan.PORTES[nom]
    R = m["rayon"]
    ecart_porte = (plan.LARGEUR_PORTE / 2 + 9.0) / R
    tours = []
    for k in range(m["tours"]):
        a = plan.SUD + math.pi / m["tours"] + 2 * math.pi * k / m["tours"]
        if any(abs((a - p + math.pi) % (2 * math.pi) - math.pi) < ecart_porte for p in portes):
            continue
        if nom == "exterieur" and abs((a - plan.ANGLE_EAU + math.pi) % (2 * math.pi) - math.pi) < 12.0 / R:
            continue
        tours.append(a)
    return tours


def anneau_de_mur(c, nom, m, rnd, niveau_eau=None):
    """Extrude le profil du mur tout autour du centre, en laissant les portes ouvertes."""
    R, T, H = m["rayon"], m["epaisseur"], m["hauteur"]
    pas = 1.4
    n = int(2 * math.pi * R / pas)
    demi_porte = (plan.LARGEUR_PORTE / 2 - 1.5) / R
    portes = plan.PORTES[nom]

    def ouvert(a):
        return any(abs((a - p + math.pi) % (2 * math.pi) - math.pi) < demi_porte for p in portes)

    c.avec(cylindrique=True)
    troncons = []
    courant = []
    for k in range(n):
        a = plan.SUD + 2 * math.pi * k / n
        if ouvert(a):
            if courant:
                troncons.append(courant)
                courant = []
        else:
            courant.append(a)
    if courant:
        # le dernier tronçon rejoint le premier si l'anneau n'est pas coupé à cet endroit
        if troncons and not ouvert(plan.SUD) and troncons[0][0] == plan.SUD:
            troncons[0] = courant + troncons[0]
        else:
            troncons.append(courant)
    sous_eau = 9.0 / R
    for angles in troncons:
        anneaux = []
        for a in angles:
            z0 = plan.niveau_mur(nom, a)
            bas = -4.0
            if niveau_eau is not None and abs((a - plan.ANGLE_EAU + math.pi) % (2 * math.pi) - math.pi) < sous_eau:
                bas = niveau_eau - z0 + 3.6          # le mur passe au-dessus de la rivière
            radial = Vector((math.cos(a), math.sin(a), 0))
            anneau = [c.bm.verts.new(radial * (R + d) + Vector((0, 0, z0 + h))) for d, h in _profil(T, H, bas)]
            anneaux.append(anneau)
        verts = [v for a in anneaux for v in a]
        np_ = len(anneaux[0])
        for i in range(len(anneaux) - 1):
            A, B = anneaux[i], anneaux[i + 1]
            for j in range(np_):
                j2 = (j + 1) % np_
                c.bm.faces.new((A[j], B[j], B[j2], A[j2]))
        # bouts du tronçon (à côté des porteries)
        c.bm.faces.new(list(reversed(anneaux[0])))
        c.bm.faces.new(anneaux[-1])
        c._finir(verts, "remparts", (0.95 + 0.05 * rnd.random(),) * 3)
    c.avec(cylindrique=False)
    # Merlons du parapet extérieur
    nb = int(2 * math.pi * R / 2.5)
    for k in range(nb):
        a = plan.SUD + 2 * math.pi * (k + 0.5) / nb
        if ouvert(a):
            continue
        z0 = plan.niveau_mur(nom, a)
        L = Matrix.Translation(Vector((math.cos(a), math.sin(a), 0)) * (R + T / 2 - 0.35)) @ Matrix.Rotation(a + math.pi / 2, 4, "Z")
        c.boite("remparts", L @ Matrix.Translation((0, 0, z0 + H + PARAPET + MERLON_H / 2)), (1.3, 0.7, MERLON_H), 0.03,
                (0.92 + 0.08 * rnd.random(),) * 3)
    return troncons


def tour_ronde(c, nom, m, a, rnd, toit=True, feuillage=None):
    R, T, H = m["rayon"], m["epaisseur"], m["hauteur"]
    rt = {"exterieur": 5.6, "milieu": 4.4, "interieur": 3.6}[nom]
    centre_r = R + T / 2 - rt * 0.35
    x, y = polaire(centre_r, a)
    z0 = plan.niveau_mur(nom, a)
    ht = H + 6.0
    seg = 28
    M0 = Matrix.Translation((x, y, z0))
    c.cylindre("remparts", M0 @ Matrix.Translation((0, 0, -2 + 1.5)), rt + 0.9, rt + 0.3, 3.0, seg)
    c.cylindre("remparts", M0 @ Matrix.Translation((0, 0, 1.0 + (ht - 1.0) / 2)), rt + 0.3, rt, ht - 1.0, seg)
    # Mâchicoulis : un anneau de corbeaux sous le couronnement
    c.cylindre("remparts", M0 @ Matrix.Translation((0, 0, ht + 0.35)), rt + 0.55, rt + 0.55, 0.7, seg)
    for k in range(18):
        b = 2 * math.pi * k / 18
        c.boite("remparts", M0 @ Matrix.Translation((math.cos(b) * (rt + 0.15), math.sin(b) * (rt + 0.15), ht - 0.45))
                @ Matrix.Rotation(b, 4, "Z"), (0.5, 0.35, 0.7), 0.02)
    # Archères
    for k in range(6):
        b = a + math.pi / 2 + (k - 2.5) * 0.55
        for hz in (ht * 0.35, ht * 0.68):
            c.boite("bois_sombre", M0 @ Matrix.Translation((math.cos(b) * (rt - 0.02), math.sin(b) * (rt - 0.02), hz))
                    @ Matrix.Rotation(b, 4, "Z"), (0.2, 0.18, 1.1))
    if toit:
        c.cylindre("ardoises", M0 @ Matrix.Translation((0, 0, ht + 0.7 + rt * 0.85)), rt + 0.9, 0.08, rt * 1.7, seg,
                   (0.95, 0.95, 1.0))
        c.cylindre("metal", M0 @ Matrix.Translation((0, 0, ht + 0.7 + rt * 1.7 + 0.6)), 0.05, 0.02, 1.4, 6)
    else:
        nb = 12
        for k in range(nb):
            b = 2 * math.pi * k / nb
            c.boite("remparts", M0 @ Matrix.Translation((math.cos(b) * (rt + 0.2), math.sin(b) * (rt + 0.2), ht + 1.25))
                    @ Matrix.Rotation(b + math.pi / 2, 4, "Z"), (1.0, 0.6, 1.0), 0.03)
        c.cylindre("remparts", M0 @ Matrix.Translation((0, 0, ht + 0.75)), rt + 0.3, rt + 0.3, 0.1, seg)
    if feuillage is not None and rnd.random() < 0.6:
        dirc = Vector((math.cos(a), math.sin(a), 0))
        lierre(feuillage, Vector((x, y, z0 + 2.5)) + dirc * (rt + 0.4), dirc, rnd, 10, 1.6, 0.8)
    plan.OBSTACLES.append((x, y, rt + 1.0))
    return (x, y, z0 + ht)


def porterie(c, nom, m, a, rnd, reperes, feuillage=None):
    """Deux tours carrées, un passage voûté qui traverse le mur, une herse levée, des vantaux ouverts."""
    R, T, H = m["rayon"], m["epaisseur"], m["hauteur"]
    z0 = min(plan.niveau_mur(nom, a), plan.hauteur(*polaire(R - T, a)), plan.hauteur(*polaire(R + T, a)))
    x, y = polaire(R, a)
    # Repère local : X le long du mur, Y vers l'extérieur
    L = Matrix.Translation((x, y, z0)) @ Matrix.Rotation(a - math.pi / 2, 4, "Z")
    larg = plan.LARGEUR_PORTE
    cote_tour = 6.4 if nom != "interieur" else 5.0
    ht = H + 7.0
    prof = T + 3.0
    for s in (-1, 1):
        tx = s * (larg / 2 - cote_tour / 2)
        c.boite("remparts", L @ Matrix.Translation((tx, 0.4, ht / 2 - 2)), (cote_tour, prof + 0.8, ht + 4), 0.06)
        # couronnement crénelé et toit en pyramide
        for k in range(4):
            for j in (-1, 1):
                c.boite("remparts", L @ Matrix.Translation((tx + (k - 1.5) * cote_tour / 4, 0.4 + j * (prof / 2 + 0.2), ht + 0.55)),
                        (cote_tour / 4 - 0.5, 0.6, 1.1), 0.03)
        c.cylindre("ardoises", L @ Matrix.Translation((tx, 0.4, ht + 3.2)) @ Matrix.Rotation(math.pi / 4, 4, "Z"),
                   cote_tour * 0.78, 0.06, 5.2, 4)
        for hz in (6.0, 11.0):
            c.boite("bois_sombre", L @ Matrix.Translation((tx, 0.4 + prof / 2 + 0.42, hz)), (0.3, 0.12, 1.3))
        # Bannière du royaume (braise et or)
        c.boite("tissu", L @ Matrix.Translation((tx, 0.4 + prof / 2 + 0.47, ht - 5.5)), (2.2, 0.05, 6.0), 0.0, (0.55, 0.12, 0.06))
        c.boite("or", L @ Matrix.Translation((tx, 0.4 + prof / 2 + 0.51, ht - 4.4)), (0.9, 0.04, 0.9))
        c.boite("bois_sombre", L @ Matrix.Translation((tx, 0.4 + prof / 2 + 0.5, ht - 2.4)), (2.6, 0.12, 0.12))
    # Corps central percé d'un passage
    ouverture = 5.6 if nom != "interieur" else 4.6
    hauteur_passage = 6.4 if nom != "interieur" else 5.4
    corps = larg - 2 * cote_tour
    for s in (-1, 1):
        c.boite("remparts", L @ Matrix.Translation((s * (ouverture / 2 + (corps - ouverture) / 4), 0, (H + 2) / 2 - 2)),
                ((corps - ouverture) / 2, prof, H + 6), 0.04)
    voute = ouverture / 2
    c.boite("remparts", L @ Matrix.Translation((0, 0, (hauteur_passage + voute + H + 2) / 2 + 0.2)),
            (ouverture + 0.05, prof, H + 2 - hauteur_passage - voute + 0.4), 0.0)
    for face in (-1, 1):
        Lf = L @ Matrix.Translation((0, face * prof / 2, 0))
        c.arche("remparts", Lf, voute + 0.35, 0.7, 0.9, hauteur_passage, 11)
    # Voûte du passage (demi-cylindre en planches de pierre)
    for k in range(9):
        b = math.pi * (k + 0.5) / 9
        c.boite("remparts", L @ Matrix.Translation((voute * math.cos(b), 0, hauteur_passage + voute * math.sin(b) + 0.2))
                @ Matrix.Rotation(b - math.pi / 2, 4, "Y"), (0.4, prof - 0.2, voute * math.pi / 9 + 0.05))
    # Herse levée, vantaux ouverts contre les murs du passage
    for k in range(7):
        c.boite("metal", L @ Matrix.Translation((-ouverture / 2 + 0.4 + k * (ouverture - 0.8) / 6, prof / 2 - 0.5, hauteur_passage + 1.2)),
                (0.1, 0.1, 3.0))
    for k in range(5):
        c.boite("metal", L @ Matrix.Translation((0, prof / 2 - 0.5, hauteur_passage - 0.1 + k * 0.6)), (ouverture - 0.6, 0.08, 0.08))
    for s in (-1, 1):
        c.boite("bois_sombre", L @ Matrix.Translation((s * (ouverture / 2 - 0.15), -prof / 2 + 1.6, hauteur_passage / 2)),
                (0.14, 2.4, hauteur_passage - 0.4), 0.02, (0.9, 0.85, 0.8))
    # Torches de part et d'autre (côté extérieur et côté intérieur)
    for face in (-1, 1):
        for s in (-1, 1):
            p = L @ Vector((s * (ouverture / 2 + 0.9), face * (prof / 2 + 0.35), 4.2))
            c.boite("metal", Matrix.Translation(p), (0.12, 0.3, 0.12))
            c.sphere("lanterne", Matrix.Translation(p + Vector((0, 0, 0.32))), 0.16, 1)
            ancre(reperes, f"lanterne_porte_{nom}_{len([o for o in reperes.objects if o.name.startswith('lanterne_porte')])}", p + Vector((0, 0, 0.32)))
    # Escalier qui monte au chemin de ronde, côté ville
    cote = -1
    for k in range(int(H / 0.32) if H <= 15 else 0):
        c.boite("remparts", L @ Matrix.Translation((larg / 2 + 1.5 + k * 0.32, cote * (T / 2 + 0.9), 0.16 + k * 0.32 - 0.5)),
                (0.34, 1.6, 1.0 + k * 0.0), 0.02)
    if feuillage is not None:
        n = (L.to_3x3() @ Vector((0, 1, 0))).normalized()
        for s in (-1, 1):
            lierre(feuillage, L @ Vector((s * (larg / 2 - 1.0), prof / 2 + 0.9, 2.0)), n, rnd, 8, 1.4, 0.7)
    plan.EMPRISES.append((x, y, a - math.pi / 2, larg / 2, prof / 2 + 0.6))
    return L, z0, prof


def construire_remparts(M, coll_ext, coll_int, coll_portes, reperes, feuillage, rnd, niveau_eau):
    """Les trois enceintes. Renvoie les chemins de ronde (pour les gardes) et les porteries (pour la caméra)."""
    chemins = {}
    portes = {}
    for nom, m in plan.REMPARTS.items():
        c = Construction(f"rempart_{nom}", coll_ext if nom == "exterieur" else coll_int, M)
        anneau_de_mur(c, nom, m, rnd, niveau_eau if nom == "exterieur" else None)
        tours = _angles_tours(nom, m)
        for a in tours:
            tour_ronde(c, nom, m, a, rnd, toit=(nom != "milieu"), feuillage=feuillage)
        cp = Construction(f"portes_{nom}", coll_portes, M)
        for a in plan.PORTES[nom]:
            portes[(nom, a)] = porterie(cp, nom, m, a, rnd, reperes, feuillage)
        cp.objet(groupe="portes")
        if nom == "exterieur":
            arche_de_l_eau(c, m, niveau_eau)
        # Lierre au pied des murs, côté ville
        for k in range(int(m["rayon"] / 3)):
            a = rnd.random() * 2 * math.pi
            if any(abs((a - p + math.pi) % (2 * math.pi) - math.pi) < 0.25 for p in plan.PORTES[nom]):
                continue
            n = -Vector((math.cos(a), math.sin(a), 0))
            p = Vector((math.cos(a), math.sin(a), 0)) * (m["rayon"] - m["epaisseur"] / 2 - 0.1)
            p.z = plan.niveau_mur(nom, a) + rnd.uniform(0.8, 4.0)
            lierre(feuillage, p, n, rnd, 9, 1.8, 0.75)
        c.objet(groupe=f"rempart_{nom}")
        # Chemin de ronde : un cercle au milieu du mur, à la hauteur du chemin
        pts = []
        for k in range(180):
            a = 2 * math.pi * k / 180
            x, y = polaire(m["rayon"] - 0.3, a)
            pts.append((x, y, plan.niveau_mur(nom, a) + m["hauteur"]))
        chemins[nom] = pts
        log(f"rempart {nom} : {len(tours)} tours, {len(plan.PORTES[nom])} porte(s)")
    return chemins, portes


def arche_de_l_eau(c, m, niveau_eau):
    """Arche et grille là où la rivière passe sous le rempart extérieur."""
    R, T = m["rayon"], m["epaisseur"]
    a = plan.ANGLE_EAU
    x, y = polaire(R, a)
    L = Matrix.Translation((x, y, niveau_eau)) @ Matrix.Rotation(a - math.pi / 2, 4, "Z")
    for face in (-1, 1):
        c.arche("remparts", L @ Matrix.Translation((0, face * (T / 2 + 0.6), 0)), 3.6, 0.8, 1.0, 0.0, 11)
    for k in range(9):
        c.boite("metal", L @ Matrix.Translation((-3.0 + k * 0.75, T / 2 + 0.3, 1.2)), (0.08, 0.08, 3.6 if abs(k - 4) < 3 else 2.4))
