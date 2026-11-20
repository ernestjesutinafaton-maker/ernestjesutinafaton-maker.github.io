"""
Les bâtiments où l'on entre : de vraies coques (murs percés de vraies ouvertures, charpente apparente)
et des intérieurs meublés. La lumière du couchant entre par les fenêtres ; des lanternes et des lustres
éclairent le reste. Tout est cuit dans l'atlas « interieurs ».

  atelier        la forge des idées de MyDil (chapitre Expérience) : établi, NAS, tableau Scrum, imprimante 3D
  guilde         la bibliothèque des guildes (chapitre Compétences) : sept bannières, une par famille
  grande_salle   la grande salle du château (chapitre Projets) : les trois cristaux, le trône, la cheminée
  forge          la forge du C# : ouverte sur la rue, son forgeron raconte ce qu'il a bâti avec Ernest

Chaque bâtiment pose des repères : porte_<nom> (devant la porte), interieur_<nom> (centre de la pièce),
pnj_<rôle> (où se tient un personnage, et vers où il regarde), guide_<nom> (où se tient Ernest).
"""

import math

from mathutils import Matrix, Vector

from . import plan
from .construction import Construction, ancre, lierre
from .outils import TUILE_BUISSON, TUILE_FEUILLU, log
from .ville import repere_rue, sol_sous

E = 0.45            # épaisseur des murs


def T(x, y, z):
    return Matrix.Translation((x, y, z))


def _bloquer(R, demi_x, demi_y):
    """Rectangle infranchissable (repère R : centre et orientation du meuble)."""
    centre = R.to_translation()
    axe = R.to_3x3() @ Vector((1, 0, 0))
    plan.EMPRISES.append((centre.x, centre.y, math.atan2(axe.y, axe.x), demi_x, demi_y))


def _interieur(nom, L, w, d, sol, porte, zone, ouvert=False):
    plan.INTERIEURS.append(dict(nom=nom, L=L.copy(), largeur=w, profondeur=d, sol=sol, porte=porte, zone=zone, ouvert=ouvert))


def personnage(reperes, nom, L, x, y, regard, **props):
    """Repère d'un personnage : position, et direction du regard (angle dans le repère local du bâtiment)."""
    p = L @ Vector((x, y, 0))
    e = ancre(reperes, nom, p)
    d = (L.to_3x3() @ Vector((math.cos(regard), math.sin(regard), 0))).normalized()
    e["regard"] = math.atan2(d.y, d.x)
    for k, v in props.items():
        e[k] = v
    return e


def coque(c, L, w, d, h, mat_mur, ouvertures, z_sol=0.45, couleur=(1, 1, 1), mat_sol="bois"):
    """Quatre murs percés (avant y = 0, arrière y = d, gauche x = -w/2, droite x = w/2) et un plancher."""
    c.mur_ouvertures(mat_mur, L, -w / 2, w / 2, -0.8, z_sol + h, E, ouvertures.get("avant", ()), y=E / 2, couleur=couleur)
    c.mur_ouvertures(mat_mur, L, -w / 2, w / 2, -0.8, z_sol + h, E, ouvertures.get("arriere", ()), y=d - E / 2, couleur=couleur)
    for s, cle in ((-1, "gauche"), (1, "droite")):
        Ls = L @ T(s * (w / 2 - E / 2), d / 2, 0) @ Matrix.Rotation(math.pi / 2, 4, "Z")
        ouv = [(o[0] - d / 2, o[1] - d / 2, o[2], o[3]) for o in ouvertures.get(cle, ())]
        c.mur_ouvertures(mat_mur, Ls, -(d / 2 - E), d / 2 - E, -0.8, z_sol + h, E, ouv, y=0.0, couleur=couleur)
    c.boite("pierre", L @ T(0, d / 2, z_sol / 2 - 0.45), (w - 2 * E + 0.02, d - 2 * E + 0.02, z_sol + 0.9), 0.0, (0.85, 0.82, 0.78))
    c.boite(mat_sol, L @ T(0, d / 2, z_sol - 0.02), (w - 2 * E, d - 2 * E, 0.06), 0.0, (0.95, 0.9, 0.85))


def charpente(c, L, w, d, zt, faitage, pas=1.8):
    """Fermes de bois sous un toit à deux pans (faîtage le long de X)."""
    pente = math.atan2(faitage, d / 2)
    longueur = (d / 2) / math.cos(pente)
    n = max(2, int(w / pas))
    for k in range(n + 1):
        x = -w / 2 + E + k * (w - 2 * E) / n
        c.boite("bois_sombre", L @ T(x, d / 2, zt - 0.1), (0.2, d - 2 * E, 0.26))
        c.boite("bois_sombre", L @ T(x, d / 2, zt + faitage * 0.5), (0.16, 0.16, faitage))
        for s in (-1, 1):
            c.boite("bois_sombre", L @ T(x, d / 2 + s * d / 4, zt + faitage / 2 - 0.15) @ Matrix.Rotation(-s * pente, 4, "X"),
                    (0.16, longueur, 0.2))
    c.boite("bois_sombre", L @ T(0, d / 2, zt + faitage - 0.2), (w, 0.22, 0.24))


def fenetre_ouverte(c, L, x0, x1, z0, z1, y, face=-1, croisillon=True):
    """Encadrement et meneaux dans une ouverture de mur (le verre est laissé ouvert : la lumière entre)."""
    xm, zm = (x0 + x1) / 2, (z0 + z1) / 2
    c.boite("pierre", L @ T(xm, y + face * 0.05, z0 - 0.08), (x1 - x0 + 0.3, E + 0.16, 0.14))
    if croisillon:
        c.boite("bois_sombre", L @ T(xm, y, zm), (0.08, 0.1, z1 - z0))
        c.boite("bois_sombre", L @ T(xm, y, z0 + (z1 - z0) * 0.62), (x1 - x0, 0.1, 0.08))


def lanterne_suspendue(c, reperes, nom, p, longueur=1.0):
    c.boite("metal", T(p.x, p.y, p.z + longueur / 2 + 0.15), (0.03, 0.03, longueur))
    c.boite("metal", T(p.x, p.y, p.z + 0.17), (0.22, 0.22, 0.04))
    c.sphere("lanterne", T(p.x, p.y, p.z), 0.12, 1)
    c.boite("metal", T(p.x, p.y, p.z - 0.15), (0.18, 0.18, 0.03))
    ancre(reperes, nom, p)


def lustre(c, reperes, nom, p, rayon=1.0, bougies=8):
    c.boite("metal", T(p.x, p.y, p.z + 1.2), (0.04, 0.04, 2.2))
    c.tore("metal", T(p.x, p.y, p.z), rayon, 0.05, 32, 6)
    for k in range(bougies):
        a = 2 * math.pi * k / bougies
        q = Vector((p.x + math.cos(a) * rayon, p.y + math.sin(a) * rayon, p.z))
        c.cylindre("enduit", T(q.x, q.y, q.z + 0.12), 0.04, 0.04, 0.22, 6)
        c.sphere("lanterne", T(q.x, q.y, q.z + 0.28), 0.045, 1)
    ancre(reperes, nom, p + Vector((0, 0, 0.3)))


def etagere(c, L, x, y, rot, largeur, hauteur, rangs=6, livres=True, rnd=None):
    R = L @ T(x, y, 0) @ Matrix.Rotation(rot, 4, "Z")
    prof = 0.42
    _bloquer(R, largeur / 2 + 0.1, prof / 2 + 0.2)
    for s in (-1, 1):
        c.boite("bois_sombre", R @ T(s * largeur / 2, 0, hauteur / 2), (0.06, prof, hauteur))
    c.boite("bois_sombre", R @ T(0, prof / 2 - 0.02, hauteur / 2), (largeur, 0.03, hauteur))
    for k in range(rangs + 1):
        z = 0.12 + k * (hauteur - 0.2) / rangs
        c.boite("bois_sombre", R @ T(0, 0, z), (largeur, prof, 0.04))
        if k < rangs:
            if livres:
                h = (hauteur - 0.2) / rangs * (0.7 + 0.2 * (rnd.random() if rnd else 0.5))
                c.boite("livres", R @ T(0, -0.02, z + 0.02 + h / 2), (largeur - 0.12, prof - 0.1, h))
            else:
                for j in range(int(largeur / 0.45)):
                    hb = 0.18 + 0.15 * (rnd.random() if rnd else 0.5)
                    c.boite("bois", R @ T(-largeur / 2 + 0.3 + j * 0.45, 0, z + 0.02 + hb / 2), (0.36, prof - 0.1, hb), 0.0,
                            (0.7 + 0.3 * (rnd.random() if rnd else 0.5),) * 3)


def table(c, L, x, y, rot, longueur, largeur, hauteur=0.82, mat="bois"):
    R = L @ T(x, y, 0) @ Matrix.Rotation(rot, 4, "Z")
    _bloquer(R, longueur / 2 + 0.25, largeur / 2 + 0.25)
    c.boite(mat, R @ T(0, 0, hauteur - 0.04), (longueur, largeur, 0.08), 0.01)
    for sx in (-1, 1):
        for sy in (-1, 1):
            c.boite("bois_sombre", R @ T(sx * (longueur / 2 - 0.12), sy * (largeur / 2 - 0.12), (hauteur - 0.08) / 2), (0.1, 0.1, hauteur - 0.08))
    return R @ T(0, 0, hauteur)


def tabouret(c, L, x, y):
    c.cylindre("bois", L @ T(x, y, 0.45), 0.2, 0.2, 0.06, 12)
    for k in range(3):
        a = k * 2 * math.pi / 3
        c.boite("bois_sombre", L @ T(x + math.cos(a) * 0.13, y + math.sin(a) * 0.13, 0.22), (0.04, 0.04, 0.44))


# =========================================================================
#  L'atelier (chapitre Expérience)
# =========================================================================

def atelier(M, coll, vivant, reperes, feuillage, rnd):
    b = plan.BATIMENTS_VILLE["atelier"]
    w, d = b["largeur"], b["profondeur"]
    L0, _ = repere_rue(b["angle"], b["cote"])
    z0 = sol_sous(L0, w, d)
    L = T(0, 0, z0) @ L0
    c = Construction("atelier", coll, M)
    zs, h = 0.45, 4.4
    porte = (-1.35, 1.35, zs - 0.1, zs + 3.1)
    fen_av = [(-4.3, -2.8, zs + 1.2, zs + 3.0), (2.8, 4.3, zs + 1.2, zs + 3.0)]
    fen_ar = [(-3.8, -2.4, zs + 1.3, zs + 3.1), (-0.7, 0.7, zs + 1.3, zs + 3.1), (2.4, 3.8, zs + 1.3, zs + 3.1)]
    coque(c, L, w, d, h, "enduit_maison", {"avant": [porte] + fen_av, "arriere": fen_ar}, zs, (0.84, 0.76, 0.62))
    for x0, x1, z0_, z1 in fen_av:
        fenetre_ouverte(c, L, x0, x1, z0_, z1, E / 2)
    for x0, x1, z0_, z1 in fen_ar:
        fenetre_ouverte(c, L, x0, x1, z0_, z1, d - E / 2, face=1)
    # Colombages décoratifs sur la façade et le pignon, soubassement de pierre
    for x in (-w / 2 + 0.15, -1.6, 1.6, w / 2 - 0.15, -5.0, 5.0):
        c.boite("bois_sombre", L @ T(x, -0.03, zs + h / 2), (0.22, 0.1, h + 0.8))
    c.boite("bois_sombre", L @ T(0, -0.03, zs + h - 0.1), (w, 0.12, 0.25))
    c.boite("pierre", L @ T(0, -0.04, 0.0), (w + 0.1, 0.14, 1.0))
    zt = zs + h
    faitage = (d / 2) * math.tan(math.radians(48))
    c.avec(donnee=(0.4, 0.0, (z0 + zt) / 20.0))
    c.toit("tuiles", "colombage", L @ T(0, d / 2, 0), w, d, zt, faitage, 0.5, 0.18, (0.42, 0.14, 0.08), (0.84, 0.76, 0.62))
    c.avec(donnee=(0.0, 0.0, 0.0))
    charpente(c, L, w, d, zt, faitage)
    # Enseigne : une roue dentée dorée
    c.boite("metal", L @ T(2.2, -0.6, zs + 3.6), (0.05, 1.1, 0.05))
    c.cylindre("or", L @ T(2.2, -0.95, zs + 3.1) @ Matrix.Rotation(math.pi / 2, 4, "Y"), 0.35, 0.35, 0.06, 12, lisse=False)
    for k in range(8):
        a = k * math.pi / 4
        c.boite("or", L @ T(2.2, -0.95 + math.cos(a) * 0.4, zs + 3.1 + math.sin(a) * 0.4), (0.07, 0.12, 0.12))
    # Vantaux ouverts
    for s in (-1, 1):
        c.boite("bois_sombre", L @ T(s * 1.85, 0.85, zs + 1.5) @ Matrix.Rotation(s * 0.1, 4, "Z"), (0.08, 1.25, 3.0), 0.01)
    # --- Intérieur
    plan_travail = table(c, L, 0.0, 5.3, 0.0, 3.6, 1.3, 0.95)
    for k in range(6):
        c.boite("bois", plan_travail @ T(-1.4 + k * 0.55, 0.3, 0.06), (0.35, 0.25, 0.12), 0.0, (0.8, 0.7, 0.6))
    c.boite("cuivre", plan_travail @ T(-0.5, -0.25, 0.012), (0.5, 0.35, 0.02))                  # carte électronique
    for k in range(4):
        c.boite("metal", plan_travail @ T(-0.65 + k * 0.1, -0.25, 0.04), (0.06, 0.06, 0.04))
    c.boite("metal", plan_travail @ T(0.7, -0.2, 0.08), (0.45, 0.12, 0.12))                     # fer à souder
    c.cylindre("metal", plan_travail @ T(1.3, -0.1, 0.25), 0.04, 0.04, 0.5, 8)                  # lampe d'établi
    c.sphere("lanterne", plan_travail @ T(1.3, -0.25, 0.48), 0.07, 1)
    ancre(reperes, "lanterne_atelier_etabli", plan_travail @ Vector((1.3, -0.25, 0.48)))
    # Le NAS : une baie avec ses voyants, contre le mur de droite
    baie = L @ T(w / 2 - E - 0.5, 7.4, 0)
    c.boite("metal", baie @ T(0, 0, zs + 1.05), (0.9, 0.85, 2.1), 0.02)
    for k in range(5):
        c.boite("bois_sombre", baie @ T(-0.46, 0, zs + 0.45 + k * 0.38), (0.04, 0.75, 0.3))
    leds = Construction("vivant_leds", vivant, M)
    for k in range(5):
        for j in range(4):
            leds.boite("ecran", baie @ T(-0.49, -0.28 + j * 0.06, zs + 0.5 + k * 0.38), (0.02, 0.025, 0.025))
    leds.objet(vivant="leds")
    # Bureau et écran
    poste = table(c, L, -w / 2 + E + 0.6, 3.6, math.pi / 2, 1.8, 0.8, 0.78)
    c.boite("ecran", poste @ T(0.15, 0.0, 0.32), (0.06, 0.75, 0.45))
    c.boite("metal", poste @ T(0.15, 0.0, 0.07), (0.15, 0.15, 0.14))
    c.boite("metal", poste @ T(-0.2, 0.0, 0.015), (0.18, 0.5, 0.03))
    tabouret(c, L, -w / 2 + E + 1.5, 3.6)
    # Imprimante 3D
    imp = table(c, L, -w / 2 + E + 0.55, 7.2, math.pi / 2, 1.2, 0.8, 0.8)
    for sx in (-1, 1):
        for sy in (-1, 1):
            c.boite("metal", imp @ T(sx * 0.25, sy * 0.25, 0.3), (0.04, 0.04, 0.6))
    c.boite("metal", imp @ T(0, 0, 0.6), (0.56, 0.56, 0.04))
    c.boite("metal", imp @ T(0, 0, 0.45), (0.5, 0.08, 0.05))
    c.sphere("braise", imp @ T(0, 0, 0.4), 0.03, 1)
    c.cylindre("tissu", imp @ T(0, 0, 0.08), 0.1, 0.07, 0.14, 8, (0.85, 0.5, 0.15))
    # Tableau Scrum, couvert de notes de couleur
    tab = L @ T(-1.0, d - E - 0.06, zs + 2.0)
    c.boite("bois_sombre", tab, (3.0, 0.06, 1.6))
    c.boite("enduit", tab @ T(0, -0.04, 0), (2.8, 0.03, 1.4))
    for col in range(3):
        c.boite("bois_sombre", tab @ T(-0.93 + col * 0.93 + 0.46, -0.06, 0), (0.02, 0.02, 1.35))
        for k in range(rnd.randint(2, 5)):
            teinte = rnd.choice([(0.95, 0.8, 0.2), (0.9, 0.45, 0.4), (0.45, 0.75, 0.9), (0.6, 0.85, 0.5)])
            c.boite("tissu", tab @ T(-1.3 + col * 0.93 + rnd.uniform(0.05, 0.6), -0.07, 0.5 - k * 0.27), (0.18, 0.01, 0.18), 0.0, teinte)
    # Étagères, caisses, outils
    etagere(c, L, w / 2 - E - 1.6, d - E - 0.25, 0.0, 2.2, 2.6, 4, livres=False, rnd=rnd)
    etagere(c, L, -w / 2 + E + 0.25, 5.6, math.pi / 2, 1.6, 2.4, 4, livres=False, rnd=rnd)
    for k in range(3):
        c.boite("bois", L @ T(w / 2 - E - 0.45, 1.3 + k * 0.7, 0.35 + zs), (0.6, 0.6, 0.6), 0.02, (0.8, 0.72, 0.6))
    for k in range(3):
        lanterne_suspendue(c, reperes, f"lanterne_atelier_{k + 1}", L @ Vector((-2.5 + k * 2.5, 4.8, zs + h - 0.4)), 0.9)
    plan.OBSTACLES.append(((baie @ Vector((0, 0, 0))).x, (baie @ Vector((0, 0, 0))).y, 0.75))
    c.objet(groupe="interieurs")
    _interieur("atelier", L, w, d, z0 + zs, (porte[0], porte[1]), 1)
    ancre(reperes, "porte_atelier", L @ Vector((0, -2.2, zs + 1.6)))
    ancre(reperes, "interieur_atelier", L @ Vector((0, 5.0, zs + 1.4)))
    personnage(reperes, "pnj_coach", L, 1.5, 3.4, -math.pi / 2 - 0.4, role="coach")
    personnage(reperes, "guide_atelier", L, -1.6, 3.0, -math.pi / 2 + 0.3, role="guide")
    return L


# =========================================================================
#  La bibliothèque des guildes (chapitre Compétences)
# =========================================================================

SYMBOLES = ["chevrons", "cube", "telephone", "base", "reseau", "puce", "boucle"]
COULEURS_BANNIERES = [(0.55, 0.12, 0.06), (0.1, 0.22, 0.4), (0.15, 0.32, 0.18), (0.45, 0.3, 0.08), (0.3, 0.12, 0.35),
                      (0.12, 0.3, 0.32), (0.4, 0.15, 0.1)]


def symbole(c, R, motif):
    """Petit emblème doré sur une bannière (repère R : centre de l'emblème, X horizontal, Z vertical)."""
    o = "or"
    if motif == "chevrons":
        for s in (-1, 1):
            c.boite(o, R @ T(s * 0.16, 0, 0.06) @ Matrix.Rotation(s * 0.7, 4, "Y"), (0.05, 0.03, 0.22))
            c.boite(o, R @ T(s * 0.16, 0, -0.06) @ Matrix.Rotation(-s * 0.7, 4, "Y"), (0.05, 0.03, 0.22))
    elif motif == "cube":
        for a in range(6):
            b = a * math.pi / 3
            c.boite(o, R @ T(0.18 * math.cos(b), 0, 0.18 * math.sin(b)) @ Matrix.Rotation(-b + math.pi / 2, 4, "Y"), (0.18, 0.03, 0.04))
    elif motif == "telephone":
        c.boite(o, R, (0.2, 0.03, 0.34))
        c.boite("tissu", R @ T(0, -0.01, 0.02), (0.14, 0.03, 0.24), 0.0, (0.1, 0.1, 0.1))
    elif motif == "base":
        for k in range(3):
            c.cylindre(o, R @ T(0, 0, -0.12 + k * 0.12) @ Matrix.Rotation(math.pi / 2, 4, "X"), 0.16, 0.16, 0.03, 16)
    elif motif == "reseau":
        for a in range(5):
            b = a * 2 * math.pi / 5
            c.sphere(o, R @ T(0.18 * math.cos(b), 0, 0.18 * math.sin(b)), 0.045, 1)
            c.boite(o, R @ T(0.09 * math.cos(b), 0, 0.09 * math.sin(b)) @ Matrix.Rotation(-b, 4, "Y"), (0.18, 0.02, 0.02))
    elif motif == "puce":
        c.boite(o, R, (0.24, 0.03, 0.24))
        for k in range(4):
            for s in (-1, 1):
                c.boite(o, R @ T(-0.09 + k * 0.06, 0, s * 0.16), (0.025, 0.03, 0.06))
                c.boite(o, R @ T(s * 0.16, 0, -0.09 + k * 0.06), (0.06, 0.03, 0.025))
    else:
        c.tore(o, R @ Matrix.Rotation(math.pi / 2, 4, "X"), 0.15, 0.03, 24, 6)
        c.boite(o, R @ T(0.15, 0, 0.05), (0.08, 0.03, 0.08))


def guilde(M, coll, vivant, reperes, feuillage, rnd):
    b = plan.BATIMENTS_VILLE["guilde"]
    w, d = b["largeur"], b["profondeur"]
    L0, _ = repere_rue(b["angle"], b["cote"])
    z0 = sol_sous(L0, w, d)
    L = T(0, 0, z0) @ L0
    c = Construction("guilde", coll, M)
    zs, h = 0.5, 6.2
    porte = (-1.2, 1.2, zs - 0.1, zs + 3.3)
    fen_av = [(-4.9, -3.7, zs + 1.6, zs + 4.6), (3.7, 4.9, zs + 1.6, zs + 4.6)]
    fen_ar = [(-4.2, -3.0, zs + 1.8, zs + 4.8), (-0.6, 0.6, zs + 1.8, zs + 4.8), (3.0, 4.2, zs + 1.8, zs + 4.8)]
    coque(c, L, w, d, h, "pierre", {"avant": [porte] + fen_av, "arriere": fen_ar}, zs, (0.95, 0.92, 0.88), "dalles")
    for x0, x1, z0_, z1 in fen_av:
        fenetre_ouverte(c, L, x0, x1, z0_, z1, E / 2)
        c.arche("pierre", L @ T((x0 + x1) / 2, E / 2, 0), (x1 - x0) / 2 + 0.1, 0.25, E + 0.1, z1, 5)
    for x0, x1, z0_, z1 in fen_ar:
        fenetre_ouverte(c, L, x0, x1, z0_, z1, d - E / 2, face=1)
    c.arche("pierre", L @ T(0, -0.05, 0), 1.35, 0.35, 0.5, zs + 3.3, 9)
    for s in (-1, 1):
        c.boite("pierre", L @ T(s * 1.35, -0.05, zs + 1.6), (0.3, 0.5, 3.4))
        for k in (-1, 1):
            c.boite("pierre", L @ T(s * (w / 2 + 0.3), d / 2 + k * 2.5, (zs + h) / 2), (0.6, 0.7, zs + h + 0.6), 0.05)
    zt = zs + h
    faitage = (d / 2) * math.tan(math.radians(52))
    c.toit("ardoises", "pierre", L @ T(0, d / 2, 0), w, d, zt, faitage, 0.45, 0.18, (0.9, 0.9, 1.0), (0.95, 0.92, 0.88))
    charpente(c, L, w, d, zt, faitage, 2.2)
    # Écu au-dessus de la porte
    c.boite("or", L @ T(0, -0.3, zs + 5.0), (0.8, 0.06, 0.9))
    for s in (-1, 1):
        c.boite("bois_sombre", L @ T(s * 1.75, 0.95, zs + 1.6) @ Matrix.Rotation(s * 0.1, 4, "Z"), (0.08, 1.15, 3.2), 0.01)
    # --- Intérieur : rayonnages tout autour, sept bannières, une grande table
    for k in range(4):
        etagere(c, L, -4.6 + k * 3.0, d - E - 0.25, 0.0, 2.6, 3.8, 6, True, rnd)
    for s in (-1, 1):
        for k in range(2):
            etagere(c, L, s * (w / 2 - E - 0.25), 2.6 + k * 3.4, -s * math.pi / 2, 2.6, 3.8, 6, True, rnd)
    poutre_z = zs + h - 0.8
    c.boite("bois_sombre", L @ T(0, 4.6, poutre_z + 0.35), (w - 2 * E, 0.25, 0.25))
    for k in range(7):
        x = -4.8 + k * 1.6
        R = L @ T(x, 4.6, poutre_z - 0.9)
        c.boite("metal", R @ T(0, 0, 1.1), (1.0, 0.04, 0.04))
        c.boite("tissu", R, (0.9, 0.035, 1.9), 0.0, COULEURS_BANNIERES[k])
        c.boite("tissu", R @ T(0, 0, -1.05), (0.9, 0.035, 0.25), 0.0, tuple(v * 0.6 for v in COULEURS_BANNIERES[k]))
        c.boite("or", R @ T(0, -0.025, 0.85), (0.92, 0.02, 0.05))
        symbole(c, R @ T(0, -0.04, 0.25), SYMBOLES[k])
        ancre(reperes, f"banniere_{k + 1}", R.to_translation())
    dessus = table(c, L, 0, 5.2, 0, 4.2, 1.4, 0.82)
    c.boite("enduit", dessus @ T(-0.8, 0, 0.015), (1.3, 0.9, 0.02), 0.0, (0.9, 0.8, 0.62))       # carte du royaume
    c.boite("livres", dessus @ T(0.9, 0.1, 0.05), (0.6, 0.45, 0.1))
    for k in range(3):
        c.cylindre("enduit", dessus @ T(1.6 - k * 0.25, -0.4, 0.12), 0.035, 0.035, 0.24, 6, (0.95, 0.9, 0.8))
        c.sphere("lanterne", dessus @ T(1.6 - k * 0.25, -0.4, 0.27), 0.035, 1)
    c.cylindre("bois_sombre", L @ T(-3.6, 3.2, zs + 0.5), 0.05, 0.1, 1.0, 8)
    c.sphere("cuivre", L @ T(-3.6, 3.2, zs + 1.25), 0.32, 2)                                          # globe
    for k, x in enumerate((-2.6, 2.6)):
        lustre(c, reperes, f"lustre_guilde_{k + 1}", L @ Vector((x, 4.0, zs + h - 1.6)), 0.8, 8)
    plan.OBSTACLES.append(((L @ Vector((-3.6, 3.2, 0))).x, (L @ Vector((-3.6, 3.2, 0))).y, 0.5))
    c.objet(groupe="interieurs")
    _interieur("guilde", L, w, d, z0 + zs, (porte[0], porte[1]), 2)
    ancre(reperes, "porte_guilde", L @ Vector((0, -2.2, zs + 1.6)))
    ancre(reperes, "interieur_guilde", L @ Vector((0, 4.6, zs + 2.6)))
    personnage(reperes, "pnj_bibliothecaire", L, 2.0, 3.2, -math.pi / 2 - 0.5, role="bibliothecaire")
    personnage(reperes, "guide_guilde", L, -1.8, 2.8, -math.pi / 2 + 0.3, role="guide")
    return L


# =========================================================================
#  La grande salle du château (chapitre Projets)
# =========================================================================

def grande_salle(M, coll, vivant, reperes, feuillage, rnd):
    g = plan.GRANDE_SALLE
    w, d = g["largeur"], g["profondeur"]
    z0 = plan.HAUTEUR_SITE["grande_salle"] - 0.2
    L = T(g["x"], g["y"] - d / 2, z0)
    c = Construction("grande_salle", coll, M)
    zs, h = 0.6, 8.6
    porte = (-1.7, 1.7, zs - 0.1, zs + 4.6)
    fen_av = [(-5.4, -4.2, zs + 2.8, zs + 6.8), (4.2, 5.4, zs + 2.8, zs + 6.8)]
    cotes = [(2.6 + k * 4.6, 3.8 + k * 4.6, zs + 2.8, zs + 7.0) for k in range(3)]
    coque(c, L, w, d, h, "remparts", {"avant": [porte] + fen_av, "gauche": cotes, "droite": cotes[:1] + cotes[2:]}, zs,
          (0.98, 0.95, 0.9), "dalles")
    for x0, x1, z0_, z1 in fen_av:
        fenetre_ouverte(c, L, x0, x1, z0_, z1, E / 2)
        c.arche("remparts", L @ T((x0 + x1) / 2, E / 2, 0), (x1 - x0) / 2 + 0.1, 0.3, E + 0.12, z1, 5)
    for s in (-1, 1):
        Ls = L @ T(s * (w / 2 - E / 2), d / 2, 0) @ Matrix.Rotation(math.pi / 2, 4, "Z")
        for x0, x1, z0_, z1 in (cotes if s < 0 else cotes[:1] + cotes[2:]):
            fenetre_ouverte(c, Ls, x0 - d / 2, x1 - d / 2, z0_, z1, 0.0, face=s)
            c.arche("remparts", Ls @ T((x0 + x1) / 2 - d / 2, 0, 0), (x1 - x0) / 2 + 0.1, 0.3, E + 0.12, z1, 5)
        for k in range(5):
            c.boite("remparts", L @ T(s * (w / 2 + 0.4), 1.0 + k * 4.0, (zs + h) / 2 - 0.4), (0.8, 0.9, zs + h + 0.8), 0.06)
    c.arche("remparts", L @ T(0, -0.1, 0), 1.95, 0.45, 0.6, zs + 4.6, 11)
    for s in (-1, 1):
        c.boite("remparts", L @ T(s * 1.95, -0.1, zs + 2.3), (0.45, 0.6, 4.6))
        c.boite("bois_sombre", L @ T(s * 2.3, 1.1, zs + 2.25) @ Matrix.Rotation(s * 0.2, 4, "Z"), (0.1, 1.6, 4.5), 0.01)
    # Rosace au fond
    c.cylindre("vitrail", L @ T(0, d - E / 2 - 0.05, zs + 6.3) @ Matrix.Rotation(math.pi / 2, 4, "X"), 1.4, 1.4, E + 0.2, 24)
    zt = zs + h
    faitage = (w / 2) * math.tan(math.radians(55))
    Lt = L @ T(0, d / 2, 0) @ Matrix.Rotation(math.pi / 2, 4, "Z")
    c.toit("ardoises", "remparts", Lt, d, w, zt, faitage, 0.5, 0.22, (0.9, 0.9, 1.0), (0.98, 0.95, 0.9))
    charpente(c, Lt, d, w, zt, faitage, 2.3)
    # --- Intérieur : colonnes, tapis, estrade et trône, cheminée, les trois cristaux
    for s in (-1, 1):
        for k in range(4):
            y = 3.0 + k * 3.8
            c.cylindre("remparts", L @ T(s * 3.6, y, zs + 3.2), 0.38, 0.32, 6.4, 16)
            c.boite("remparts", L @ T(s * 3.6, y, zs + 0.2), (0.95, 0.95, 0.4), 0.03)
            c.boite("remparts", L @ T(s * 3.6, y, zs + 6.45), (0.9, 0.9, 0.3), 0.03)
    c.boite("tissu", L @ T(0, d / 2 + 0.4, zs + 0.015), (2.4, d - 3.0, 0.02), 0.0, (0.45, 0.06, 0.05))
    c.boite("or", L @ T(-1.15, d / 2 + 0.4, zs + 0.02), (0.06, d - 3.0, 0.02))
    c.boite("or", L @ T(1.15, d / 2 + 0.4, zs + 0.02), (0.06, d - 3.0, 0.02))
    c.boite("pierre", L @ T(0, d - E - 1.5, zs + 0.25), (6.0, 3.0, 0.5), 0.03)
    trone = L @ T(0, d - E - 1.6, zs + 0.5)
    c.boite("bois_sombre", trone @ T(0, 0, 0.45), (1.1, 0.9, 0.9), 0.04)
    c.boite("bois_sombre", trone @ T(0, 0.38, 1.4), (1.1, 0.15, 2.0), 0.04)
    c.boite("tissu", trone @ T(0, -0.05, 0.92), (0.9, 0.75, 0.08), 0.0, (0.45, 0.06, 0.05))
    c.sphere("or", trone @ T(0, 0.38, 2.5), 0.12, 2)
    for s in (-1, 1):
        R = L @ T(s * 2.2, d - E - 0.1, zs + 5.0)
        c.boite("tissu", R, (1.3, 0.04, 3.6), 0.0, (0.5, 0.1, 0.06))
        c.boite("or", R @ T(0, -0.03, 0.6), (0.6, 0.02, 0.6))
    # Cheminée sur le mur de droite
    F = L @ T(w / 2 - E - 0.3, 9.5, zs)
    c.boite("remparts", F @ T(-0.1, 0, 1.0), (0.8, 2.6, 2.0), 0.04)
    c.boite("bois_sombre", F @ T(-0.52, 0, 0.6), (0.04, 1.5, 1.0))
    c.sphere("braise", F @ T(-0.5, 0, 0.3), 0.35, 1)
    c.boite("remparts", F @ T(-0.25, 0, 2.15), (1.2, 3.0, 0.3), 0.03)
    c.boite("remparts", F @ T(0.0, 0, 5.0), (0.6, 1.6, 5.6))
    ancre(reperes, "feu_cheminee", F @ Vector((-0.6, 0, 0.6)))
    # Les trois socles des cristaux, dans la nef
    projets = (("cristal_vert", "ecopay"), ("cristal_violet", "boutik"), ("cristal_rose", "monde"))
    for k, (mat, nom) in enumerate(projets):
        x, y = (-1.8 + k * 1.8), 8.6 + (0.8 if k == 1 else 0.0)
        S = L @ T(x, y, zs)
        c.cylindre("remparts", S @ T(0, 0, 0.12), 0.5, 0.46, 0.24, 20)
        c.cylindre("remparts", S @ T(0, 0, 0.7), 0.26, 0.22, 1.0, 14)
        c.cylindre("or", S @ T(0, 0, 1.25), 0.4, 0.36, 0.1, 20)
        g = Construction(f"vivant_cristal_{k + 1}", vivant, M)
        centre = S @ Vector((0, 0, 2.05))
        bas = g.bm.verts.new(centre + Vector((0, 0, -0.45)))
        haut = g.bm.verts.new(centre + Vector((0, 0, 0.55)))
        anneau = [g.bm.verts.new(centre + Vector((0.2 * math.cos(2 * math.pi * s / 6), 0.2 * math.sin(2 * math.pi * s / 6), 0.06)))
                  for s in range(6)]
        for s in range(6):
            g.bm.faces.new((anneau[s], anneau[(s + 1) % 6], haut))
            g.bm.faces.new((anneau[(s + 1) % 6], anneau[s], bas))
        g._finir([bas, haut] + anneau, mat)
        for f in g.bm.faces:
            f.smooth = False
        g.objet(vivant="cristal", projet=nom, rang=k)
    for k in range(3):
        lustre(c, reperes, f"lustre_salle_{k + 1}", L @ Vector((0, 3.5 + k * 4.5, zs + h - 2.2)), 1.2, 10)
    for s in (-1, 1):
        for k in range(4):
            q = L @ Vector((s * 3.6, 3.0 + k * 3.8, 0))
            plan.OBSTACLES.append((q.x, q.y, 0.55))
    for k in range(3):
        q = L @ Vector((-1.8 + k * 1.8, 8.6 + (0.8 if k == 1 else 0.0), 0))
        plan.OBSTACLES.append((q.x, q.y, 0.65))
    _bloquer(L @ T(0, d - E - 1.5, 0), 3.0, 1.6)
    _bloquer(F, 0.6, 1.4)
    c.objet(groupe="interieurs")
    _interieur("grande_salle", L, w, d, z0 + zs, (porte[0], porte[1]), 3)
    ancre(reperes, "porte_grande_salle", L @ Vector((0, -3.0, zs + 1.6)))
    ancre(reperes, "interieur_grande_salle", L @ Vector((0, 8.6, zs + 2.0)))
    personnage(reperes, "pnj_intendante", L, 2.6, 6.8, -math.pi / 2 - 0.5, role="intendante")
    personnage(reperes, "guide_grande_salle", L, -2.6, 5.8, -math.pi / 2 + 0.5, role="guide")
    return L


# =========================================================================
#  La forge du C#
# =========================================================================

def forge(M, coll, vivant, reperes, feuillage, rnd):
    b = plan.BATIMENTS_VILLE["forge"]
    w, d = b["largeur"], b["profondeur"]
    L0, _ = repere_rue(b["angle"], b["cote"])
    z0 = sol_sous(L0, w, d)
    L = T(0, 0, z0) @ L0
    c = Construction("forge", coll, M)
    zs, h = 0.25, 4.0
    # Ouverte sur la rue : seulement des poteaux à l'avant
    c.mur_ouvertures("pierre", L, -w / 2, w / 2, -0.8, zs + h, E, [(-w / 2 + 2.2, -0.6, zs + 1.3, zs + 2.8)], y=d - E / 2)
    for s in (-1, 1):
        Ls = L @ T(s * (w / 2 - E / 2), d / 2, 0) @ Matrix.Rotation(math.pi / 2, 4, "Z")
        c.mur_ouvertures("pierre", Ls, -(d / 2 - E), d / 2 - E, -0.8, zs + h, E, (), y=0.0)
    c.boite("pierre", L @ T(0, d / 2, zs / 2 - 0.4), (w - 2 * E, d - 2 * E, zs + 0.8), 0.0, (0.8, 0.78, 0.75))
    for x in (-w / 2 + 0.25, -1.5, 1.5, w / 2 - 0.25):
        c.boite("bois_sombre", L @ T(x, 0.2, zs + h / 2), (0.3, 0.3, h + 0.2), 0.02)
    c.boite("bois_sombre", L @ T(0, 0.2, zs + h), (w, 0.35, 0.35), 0.02)
    zt = zs + h
    faitage = (d / 2) * math.tan(math.radians(45))
    c.toit("tuiles", "bois", L @ T(0, d / 2, 0), w, d, zt, faitage, 0.6, 0.16, (0.3, 0.12, 0.08))
    charpente(c, L, w, d, zt, faitage)
    # Foyer, hotte et cheminée
    F = L @ T(1.8, d - E - 0.9, zs)
    c.boite("pierre", F @ T(0, 0, 0.55), (2.0, 1.6, 1.1), 0.04)
    c.boite("braise", F @ T(0, -0.25, 1.12), (1.2, 0.9, 0.06))
    c.boite("pierre", F @ T(0, 0.2, 2.6), (2.2, 1.2, 0.3), 0.03)
    c.boite("pierre", F @ T(0, 0.3, 4.5), (0.9, 0.9, 4.0))
    ancre(reperes, "feu_forge", F @ Vector((0, -0.25, 1.4)))
    ancre(reperes, "fumee_forge", F @ Vector((0, 0.3, 6.6)))
    # Enclume, baquet, râtelier d'épées, outils
    A = L @ T(-0.4, 2.8, zs)
    c.cylindre("bois", A @ T(0, 0, 0.35), 0.35, 0.4, 0.7, 12, (0.8, 0.7, 0.6))
    c.boite("metal", A @ T(0, 0, 0.82), (0.75, 0.3, 0.25), 0.02)
    c.boite("metal", A @ T(0.48, 0, 0.88), (0.3, 0.15, 0.1))
    c.boite("braise", A @ T(-0.05, 0.02, 0.98), (0.6, 0.06, 0.02))                                  # lame rougeoyante
    c.cylindre("bois", L @ T(-2.6, 3.8, zs + 0.4), 0.42, 0.42, 0.8, 14, (0.75, 0.65, 0.55))
    c.cylindre("eau", L @ T(-2.6, 3.8, zs + 0.78), 0.38, 0.38, 0.02, 14)
    R = L @ T(-w / 2 + E + 0.15, 2.4, zs)
    c.boite("bois_sombre", R @ T(0, 0, 1.6), (0.1, 2.2, 0.1))
    c.boite("bois_sombre", R @ T(0, 0, 0.5), (0.1, 2.2, 0.1))
    for k in range(4):
        c.boite("metal", R @ T(0.12, -0.8 + k * 0.5, 1.15), (0.03, 0.06, 1.3))
        c.boite("or", R @ T(0.12, -0.8 + k * 0.5, 1.75), (0.06, 0.24, 0.04))
    for q in (A @ Vector((0, 0, 0)), L @ Vector((-2.6, 3.8, 0))):
        plan.OBSTACLES.append((q.x, q.y, 0.6))
    _bloquer(F, 1.1, 0.9)
    _bloquer(R, 0.3, 1.2)
    c.objet(groupe="interieurs")
    _interieur("forge", L, w, d, z0 + zs, (-w / 2 + 0.6, w / 2 - 0.6), 4, ouvert=True)
    ancre(reperes, "porte_forge", L @ Vector((0, -2.0, zs + 1.6)))
    ancre(reperes, "interieur_forge", L @ Vector((0, 2.6, zs + 1.4)))
    personnage(reperes, "pnj_forgeron", L, 0.4, 3.4, -math.pi / 2, role="forgeron")
    return L


def construire_interieurs(M, coll, vivant, reperes, feuillage, rnd):
    reperes_batiments = {
        "atelier": atelier(M, coll, vivant, reperes, feuillage, rnd),
        "guilde": guilde(M, coll, vivant, reperes, feuillage, rnd),
        "grande_salle": grande_salle(M, coll, vivant, reperes, feuillage, rnd),
        "forge": forge(M, coll, vivant, reperes, feuillage, rnd),
    }
    log("intérieurs : atelier, bibliothèque des guildes, grande salle, forge du C#")
    return reperes_batiments
