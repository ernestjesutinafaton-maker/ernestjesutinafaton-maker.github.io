"""
Le sol et la roche de l'île.

Le dessus est fait de deux maillages en grille polaire, chacun avec son atlas de lumière :
  sol_ville      du centre jusqu'au rempart du milieu (pavés, place, cour du château), maillage fin ;
  sol_campagne   du rempart du milieu jusqu'au bord (champs, chemins, rivière, lisière), maillage plus lâche.
Les attributs de couleur portent ce que la matière « sol » doit peindre : pave, chemin, eau, champ.

Dessous : une falaise puis un énorme rocher qui s'effile vers une pointe, des racines, des cristaux.
"""

import math
import time

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from . import plan
from .construction import Construction, ancre
from .outils import crete, fbm3, lerp, log, n3, smoothstep

SECTEURS = 576
R_JONCTION = 59.5      # les deux sols se rejoignent sous le rempart du milieu


def _attributs(x, y):
    pave = plan.masque_pave(x, y)
    chemin = plan.masque_chemin(x, y)
    eau = plan.masque_eau(x, y) if math.hypot(x, y) > 59 else 0.0
    c = plan.champ(x, y)
    if c is not None:
        # Les bords des champs restent en herbe (haies, talus)
        a = math.atan2(y, x)
        r = math.hypot(x, y)
        secteur_f = ((a + math.pi) / (2 * math.pi)) * 26
        bord_secteur = abs(secteur_f - round(secteur_f)) * (2 * math.pi * r / 26)
        bord_anneau = min(abs(r - 71.0), abs(r - 61.5), abs(r - 80.5))
        if bord_secteur < 0.9 or bord_anneau < 0.9 or chemin > 0.05 or eau > 0.1:
            c = None
    champ = (0.0, 0.0, 0.0) if c is None else ((c[0] + 1) / 8.0, c[1] / math.pi, c[2])
    return pave, chemin, eau, champ


def _maillage_polaire(nom, anneaux, bords, M, coll, centre=True, levre=False):
    """anneaux : liste de fonctions i -> rayon (une par anneau) ; levre : ajoute la lèvre d'herbe qui retombe."""
    t0 = time.time()
    verts, faces = [], []
    pave, chemin, eau, champ = [], [], [], []

    def ajouter(x, y, z):
        p, c, e, ch = _attributs(x, y)
        verts.append((x, y, z))
        pave.append(p)
        chemin.append(c)
        eau.append(e)
        champ.append(ch)

    if centre:
        ajouter(0.0, 0.0, plan.hauteur(0.0, 0.0))
    for j, rayon_de in enumerate(anneaux):
        for i in range(SECTEURS):
            th = 2 * math.pi * i / SECTEURS
            rr = rayon_de(i)
            x, y = rr * math.cos(th), rr * math.sin(th)
            ajouter(x, y, plan.hauteur(x, y))
    if levre:
        for i in range(SECTEURS):
            th = 2 * math.pi * i / SECTEURS
            rb = bords[i]
            x, y = (rb + 0.5) * math.cos(th), (rb + 0.5) * math.sin(th)
            ajouter(x, y, plan.hauteur(rb * math.cos(th), rb * math.sin(th)) - 0.8)
    n_anneaux = len(anneaux) + (1 if levre else 0)
    base = 1 if centre else 0

    def idx(j, i):
        return base + j * SECTEURS + (i % SECTEURS)
    if centre:
        for i in range(SECTEURS):
            faces.append((0, idx(0, i), idx(0, i + 1)))
    for j in range(n_anneaux - 1):
        for i in range(SECTEURS):
            faces.append((idx(j, i), idx(j + 1, i), idx(j + 1, i + 1), idx(j, i + 1)))
    me = bpy.data.meshes.new(nom)
    me.from_pydata(verts, [], faces)
    me.materials.append(M["sol"])
    for n, valeurs in (("pave", pave), ("chemin", chemin), ("eau", eau)):
        a = me.color_attributes.new(n, "FLOAT_COLOR", "POINT")
        a.data.foreach_set("color", [c for v in valeurs for c in (v, v, v, 1.0)])
    a = me.color_attributes.new("champ", "FLOAT_COLOR", "POINT")
    a.data.foreach_set("color", [c for v in champ for c in (*v, 1.0)])
    a = me.color_attributes.new("teinte", "FLOAT_COLOR", "POINT")
    a.data.foreach_set("color", [1.0] * (4 * len(verts)))
    me.shade_smooth()
    ob = bpy.data.objects.new(nom, me)
    ob["terrain"] = 1
    coll.objects.link(ob)
    log(f"{nom} : {len(verts)} sommets ({time.time() - t0:.1f} s)")
    return ob


def construire_sols(M, c_ville, c_campagne):
    bords = [plan.rayon_bord(2 * math.pi * i / SECTEURS) for i in range(SECTEURS)]
    # Ville : anneaux serrés (55 cm), un peu plus serrés encore au centre
    n = 100
    anneaux = [(lambda i, j=j: R_JONCTION * ((j + 1) / n) ** 0.95) for j in range(n)]
    _maillage_polaire("sol_ville", anneaux, bords, M, c_ville, centre=True)
    # Campagne : du rempart du milieu jusqu'au bord de l'île
    n = 62
    anneaux = [(lambda i, j=j: lerp(R_JONCTION - 1.0, bords[i], j / (n - 1))) for j in range(n)]
    _maillage_polaire("sol_campagne", anneaux, bords, M, c_campagne, centre=False, levre=True)
    return bords


NB_ETAGES = 76


def construire_roche(M, c_roche, bords):
    """La falaise sous la lèvre d'herbe, puis le rocher en blocs, en colonnes et en arêtes, jusqu'à la pointe."""
    t0 = time.time()
    verts, faces = [], []
    pointe = Vector((8.0, -6.0, -80.0))
    for k in range(NB_ETAGES):
        t = k / NB_ETAGES
        for i in range(SECTEURS):
            th = 2 * math.pi * i / SECTEURS
            rb = bords[i]
            z_bord = plan.hauteur(rb * math.cos(th), rb * math.sin(th)) - 0.7
            if t < 0.08:
                f = 0.995 - 0.2 * t
                z = z_bord - 0.2 - t / 0.08 * 6.0
            else:
                u = (t - 0.08) / 0.92
                f = 0.98 * (1.0 - u) ** 0.66
                z = z_bord - 6.2 - u ** 0.9 * (abs(pointe.z) + z_bord - 6.2 + 9 * n3(math.cos(th), math.sin(th), 3.0))
            cx, cy = lerp(0, pointe.x, t * t), lerp(0, pointe.y, t * t)
            x, y = cx + rb * f * math.cos(th), cy + rb * f * math.sin(th)
            p = Vector((x, y, z))
            radial = Vector((math.cos(th), math.sin(th), 0.0))
            fort = smoothstep(0.0, 0.45, t) * (1.0 - smoothstep(0.88, 1.0, t))
            depl = (0.4 + 6.5 * fort) * fbm3(p * Vector((0.03, 0.03, 0.05)), 5)
            depl += 4.0 * fort * (crete(p * Vector((0.04, 0.04, 0.022))) - 0.45)
            depl += 1.6 * n3(math.cos(th) * 16.0, math.sin(th) * 16.0, z * 0.02) * smoothstep(0.02, 0.2, t)
            depl += 1.0 * abs(n3(x * 0.15, y * 0.15, z * 0.2)) * smoothstep(0.0, 0.1, t)
            p += radial * depl
            verts.append(tuple(p))
    verts.append(tuple(pointe))
    for k in range(NB_ETAGES - 1):
        for i in range(SECTEURS):
            a = k * SECTEURS + i
            b = k * SECTEURS + (i + 1) % SECTEURS
            faces.append((a, a + SECTEURS, b + SECTEURS, b))
    dernier = (NB_ETAGES - 1) * SECTEURS
    for i in range(SECTEURS):
        faces.append((dernier + (i + 1) % SECTEURS, dernier + i, len(verts) - 1))
    me = bpy.data.meshes.new("ile_roche")
    me.from_pydata(verts, [], faces)
    me.materials.append(M["roche"])
    a = me.color_attributes.new("teinte", "FLOAT_COLOR", "POINT")
    a.data.foreach_set("color", [1.0] * (4 * len(verts)))
    me.shade_smooth()
    ob = bpy.data.objects.new("ile_roche", me)
    ob["groupe"] = "roche"
    c_roche.objects.link(ob)
    log(f"dessous de l'île : {len(verts)} sommets ({time.time() - t0:.1f} s)")
    return BVHTree.FromPolygons([Vector(v) for v in verts], faces)


def racines_et_cristaux(M, c_roche, vivant, reperes, arbre_roche, bords, rnd):
    """Racines qui pendent sous la lèvre d'herbe, et grappes de cristaux lumineux dans la roche."""
    c = Construction("racines", c_roche, M)
    for k in range(170):
        i = rnd.randrange(len(bords))
        th = 2 * math.pi * i / len(bords)
        rb = bords[i]
        x0, y0 = rb * math.cos(th), rb * math.sin(th)
        if plan.dist_riviere(x0, y0) < 6.0:
            continue
        radial = Vector((math.cos(th), math.sin(th), 0))
        depart = Vector((x0, y0, plan.hauteur(x0, y0) - 0.8)) - radial * 0.3
        longueur = rnd.uniform(2.0, 9.0)
        pts, rayons = [], []
        n = 10
        for s in range(n):
            u = s / (n - 1)
            p = depart + radial * (0.6 * math.sin(math.pi * u * 0.8) + 0.25 * u) + Vector((0, 0, -longueur * u))
            p += Vector((n3(k, u * 3, 1.0), n3(k, u * 3, 5.0), 0)) * 0.4 * u
            pts.append(p)
            rayons.append(lerp(rnd.uniform(0.06, 0.13), 0.01, u))
        c.tube("ecorce", pts, rayons, 5, (0.8, 0.75, 0.7))
        if rnd.random() < 0.45:
            a = pts[3]
            b = a + radial * 0.5 + Vector((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), -longueur * 0.4))
            c.tube("ecorce", [a, a.lerp(b, 0.5) + radial * 0.15, b], [rayons[3] * 0.7, rayons[3] * 0.4, 0.008], 4)
    c.objet(groupe="roche")

    g = Construction("vivant_cristaux_roche", vivant, M)
    nb = 0
    for k in range(16):
        th = 2 * math.pi * (k + rnd.uniform(0.2, 0.8)) / 16
        z = rnd.uniform(-45.0, -12.0)
        origine = Vector((220 * math.cos(th), 220 * math.sin(th), z))
        cible = Vector((6.0, -4.0, z - 4.0))
        hit, nrm, _, _ = arbre_roche.ray_cast(origine, (cible - origine).normalized(), 400.0)
        if hit is None:
            continue
        axe0 = (nrm + Vector((0, 0, -0.5))).normalized()
        for s in range(rnd.randint(5, 9)):
            axe = (axe0 + Vector((rnd.gauss(0, 0.35), rnd.gauss(0, 0.35), rnd.gauss(0, 0.3)))).normalized()
            longueur = rnd.uniform(1.2, 4.0) * (1.4 if s == 0 else 1.0)
            rayon = longueur * rnd.uniform(0.11, 0.16)
            base = hit - nrm * 0.3 + Vector((rnd.gauss(0, 0.6), rnd.gauss(0, 0.6), rnd.gauss(0, 0.5)))
            q = axe.to_track_quat("Z", "Y").to_matrix().to_4x4()
            centre = base + axe * longueur * 0.5
            v = g.cylindre("cristal_roche", Matrix.Translation(centre) @ q, rayon, rayon * 0.85, longueur, 6, lisse=False)
            haut = [vv for vv in v if (vv.co - centre).dot(axe) > 0]
            centre_haut = sum((vv.co for vv in haut), Vector()) / max(1, len(haut))
            for vv in haut:
                vv.co = centre_haut.lerp(vv.co, 0.35) + axe * rayon * 1.2
        ancre(reperes, f"cristal_roche_{nb + 1}", hit + nrm * 1.2)
        nb += 1
    g.objet(vivant="cristal_roche")
    log(f"cristaux sous l'île : {nb} grappes")


def rochers_flottants(M, c_roche, rnd):
    places = [(-150, -60, 10, 7.0), (-120, 95, -12, 5.0), (25, 150, 4, 8.0), (140, -80, -6, 6.0),
              (-60, -150, -22, 4.5), (160, 40, 18, 3.5), (-170, 20, 26, 3.0), (95, -135, 12, 4.0),
              (70, 125, -28, 5.5), (-135, -115, 30, 2.8)]
    for n, (x, y, z, r) in enumerate(places):
        c = Construction(f"rocher_flottant_{n + 1}", c_roche, M)
        centre = Vector((x, y, z))
        v = c.sphere("roche", Matrix.Translation(centre) @ Matrix.Diagonal((1.0, 1.0, 0.75, 1.0)), r, 3)
        for vv in v:
            d = vv.co - centre
            vv.co.z = centre.z + d.z * (0.3 if d.z > 0 else 1.6 + 0.6 * rnd.random())
        c.bosseler(v, centre, r * 0.22, 0.9 / r, rnd.random() * 50)
        if r > 4.0:
            dessus = max(vv.co.z for vv in v)
            vh = c.cylindre("herbe", Matrix.Translation(centre + Vector((0, 0, dessus - centre.z - 0.08))), r * 0.92, r * 0.8, 0.3, 28)
            c.bosseler(vh, centre + Vector((0, 0, dessus - centre.z)), 0.15, 0.6)
        c.objet(mobile=1, flotte=round(0.3 + rnd.random() * 0.5, 2))
