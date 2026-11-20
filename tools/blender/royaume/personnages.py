"""
Les pièces des personnages et des animaux.

Chaque pièce est un petit maillage lisse, sans texture, dont l'origine est l'articulation : la tête tourne
autour du cou, le bras autour de l'épaule, la cuisse autour de la hanche... Le site les recopie en
centaines d'exemplaires (une couleur par exemplaire) et les anime : marche, salut, coups de marteau,
garde, broutage. Rien n'est cuit : ces pièces sont éclairées en temps réel.

Unités : un adulte mesure environ 1,75 m. Hanches à 0,95 m, épaules à 1,42 m, tête jusqu'à 1,75 m.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from .outils import fbm3, log

PIECES = {}


def _piece(nom, coll, construire, lisse=True):
    bm = bmesh.new()
    construire(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = lisse
    me = bpy.data.meshes.new("piece_" + nom)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("piece_" + nom, me)
    coll.objects.link(ob)
    ob["vivant"] = "piece"
    ob["piece"] = nom
    PIECES[nom] = ob
    return ob


def _sphere(bm, centre, rayons, subdiv=3):
    r = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0,
                                   matrix=Matrix.Translation(centre) @ Matrix.Diagonal((*rayons, 1.0)))
    return r["verts"]


def _cylindre(bm, bas, haut, r_bas, r_haut, segments=10):
    axe = haut - bas
    m = Matrix.Translation((bas + haut) / 2) @ axe.to_track_quat("Z", "Y").to_matrix().to_4x4()
    r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=r_bas, radius2=r_haut,
                              depth=axe.length, matrix=m)
    return r["verts"]


def _capsule(bm, bas, haut, rayon, segments=10):
    _cylindre(bm, bas, haut, rayon, rayon * 0.92, segments)
    _sphere(bm, bas, (rayon, rayon, rayon), 2)
    _sphere(bm, haut, (rayon * 0.92,) * 3, 2)


def tete(bm):
    v = _sphere(bm, Vector((0, 0, 0.13)), (0.098, 0.108, 0.122), 3)
    for p in v:
        z = p.co.z - 0.13
        # mâchoire plus étroite vers le bas, front un peu plus large
        if z < 0:
            k = 1.0 + z * 1.6
            p.co.x *= k
            p.co.y = p.co.y * (0.95 + 0.05 * k)
    _sphere(bm, Vector((0, -0.1, 0.12)), (0.018, 0.022, 0.03), 2)                 # nez
    for s in (-1, 1):
        _sphere(bm, Vector((s * 0.098, 0.0, 0.125)), (0.016, 0.026, 0.034), 2)     # oreilles
    _cylindre(bm, Vector((0, 0.005, -0.06)), Vector((0, 0.005, 0.05)), 0.048, 0.044, 10)   # cou


def yeux(bm):
    for s in (-1, 1):
        _sphere(bm, Vector((s * 0.036, -0.094, 0.145)), (0.014, 0.008, 0.01), 2)


def cheveux_courts(bm):
    """Cheveux courts et frisés, un peu plus hauts sur le dessus."""
    v = _sphere(bm, Vector((0, 0.008, 0.155)), (0.106, 0.116, 0.112), 3)
    garde = []
    for p in v:
        d = p.co - Vector((0, 0.008, 0.155))
        if d.z < -0.035 or (d.y < -0.07 and d.z < 0.05):
            p.co -= d * 0.5
        else:
            p.co += d.normalized() * 0.012 * (1 + fbm3(p.co * 60.0, 2))
            if d.z > 0.04:
                p.co.z += 0.012
        garde.append(p)


def cheveux_longs(bm):
    v = _sphere(bm, Vector((0, 0.015, 0.15)), (0.108, 0.118, 0.118), 3)
    for p in v:
        d = p.co - Vector((0, 0.015, 0.15))
        if d.y < -0.06 and d.z < 0.04:
            p.co -= d * 0.45
        elif d.z < 0 and d.y > -0.03:
            p.co.z -= 0.16 * (-d.z / 0.118)
            p.co.y += 0.02


def capuche(bm):
    v = _sphere(bm, Vector((0, 0.02, 0.15)), (0.125, 0.135, 0.14), 3)
    for p in v:
        d = p.co - Vector((0, 0.02, 0.15))
        if d.y < -0.07:
            p.co.y = 0.02 - 0.07 + (d.y + 0.07) * 0.2
        if d.z < -0.05:
            p.co.z -= 0.06
            p.co.x *= 1.25


def chapeau(bm):
    _cylindre(bm, Vector((0, 0, 0.2)), Vector((0, 0, 0.215)), 0.22, 0.22, 20)
    _cylindre(bm, Vector((0, 0, 0.2)), Vector((0, 0, 0.3)), 0.11, 0.08, 16)


def casque(bm):
    v = _sphere(bm, Vector((0, 0, 0.15)), (0.118, 0.128, 0.13), 3)
    for p in v:
        if p.co.z < 0.12:
            p.co.z = 0.12 - (0.12 - p.co.z) * 0.15
    _cylindre(bm, Vector((0, -0.12, 0.08)), Vector((0, -0.125, 0.18)), 0.012, 0.012, 6)
    _cylindre(bm, Vector((0, 0, 0.27)), Vector((0, 0, 0.32)), 0.015, 0.004, 6)


def torse(bm, carrure=1.0, epaisseur=1.0):
    """Du bassin (origine) aux épaules : tunique ou pull, un peu évasé aux hanches."""
    bm_v = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, 0.25)) @ Matrix.Diagonal((0.36 * carrure, 0.21 * epaisseur, 0.5, 1)))["verts"]
    bmesh.ops.subdivide_edges(bm, edges=list({e for v in bm_v for e in v.link_edges}), cuts=3, use_grid_fill=True)
    for v in list(bm.verts):
        z = v.co.z
        if -0.01 <= z <= 0.51:
            t = z / 0.5
            # taille plus fine au milieu, épaules arrondies
            k = 1.0 - 0.1 * math.sin(math.pi * t) + (0.06 if t < 0.15 else 0.0)
            v.co.x *= k
            if t > 0.85:
                v.co.x *= 1.0 - (t - 0.85) * 1.6 * (abs(v.co.x) > 0.12)
                v.co.z -= (t - 0.85) * 0.12 * (abs(v.co.x) / 0.18)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.025, segments=2, affect="EDGES", clamp_overlap=True)
    _cylindre(bm, Vector((0, 0.005, 0.47)), Vector((0, 0.005, 0.52)), 0.075, 0.07, 14)       # col


def jupe(bm):
    _cylindre(bm, Vector((0, 0, 0.05)), Vector((0, 0, -0.85)), 0.17, 0.3, 18)


def tablier(bm):
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, -0.12, -0.25)) @ Matrix.Diagonal((0.3, 0.02, 0.62, 1)))


def ceinture(bm):
    r = bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=0.185, radius2=0.185, depth=0.05,
                              matrix=Matrix.Translation((0, 0, 0.02)) @ Matrix.Diagonal((1.0, 0.62, 1.0, 1)))
    return r


def bras_haut(bm):
    _capsule(bm, Vector((0, 0, -0.28)), Vector((0, 0, -0.02)), 0.056, 10)


def avant_bras(bm):
    _capsule(bm, Vector((0, 0, -0.25)), Vector((0, 0, -0.02)), 0.047, 10)


def main(bm):
    v = _sphere(bm, Vector((0, 0, -0.05)), (0.035, 0.045, 0.06), 2)


def cuisse(bm):
    _capsule(bm, Vector((0, 0, -0.45)), Vector((0, 0, -0.04)), 0.078, 12)


def mollet(bm):
    _capsule(bm, Vector((0, 0, -0.4)), Vector((0, 0, -0.02)), 0.06, 12)


def botte(bm):
    v = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, -0.045, -0.035)) @ Matrix.Diagonal((0.105, 0.26, 0.09, 1)))["verts"]
    bmesh.ops.bevel(bm, geom=list({e for p in v for e in p.link_edges}), offset=0.03, segments=2, affect="EDGES", clamp_overlap=True)
    _cylindre(bm, Vector((0, 0.0, -0.04)), Vector((0, 0.0, 0.12)), 0.065, 0.068, 12)


def cape(bm):
    """Cape qui tombe des épaules (origine : la nuque), légèrement creusée."""
    n_l, n_h = 8, 10
    verts = []
    for j in range(n_h + 1):
        t = j / n_h
        rang = []
        largeur = 0.36 + 0.3 * t
        for i in range(n_l + 1):
            u = i / n_l - 0.5
            x = u * largeur * 2
            y = 0.12 + 0.05 * t + 0.08 * (1 - (2 * u) ** 2) * (0.3 + t)
            z = -1.05 * t
            rang.append(bm.verts.new((x, y, z)))
        verts.append(rang)
    for j in range(n_h):
        for i in range(n_l):
            bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.02)


def lance(bm):
    _cylindre(bm, Vector((0, 0, -0.7)), Vector((0, 0, 1.6)), 0.018, 0.016, 8)
    _cylindre(bm, Vector((0, 0, 1.6)), Vector((0, 0, 1.85)), 0.035, 0.002, 4)


def marteau(bm):
    _cylindre(bm, Vector((0, 0, -0.05)), Vector((0, 0, 0.42)), 0.018, 0.018, 8)
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, 0.45)) @ Matrix.Diagonal((0.08, 0.17, 0.08, 1)))


def livre(bm):
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, -0.04, -0.02)) @ Matrix.Diagonal((0.16, 0.04, 0.22, 1)))


def sacoche(bm):
    v = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0.17, 0.0, -0.05)) @ Matrix.Diagonal((0.08, 0.22, 0.18, 1)))["verts"]
    bmesh.ops.bevel(bm, geom=list({e for p in v for e in p.link_edges}), offset=0.02, segments=2, affect="EDGES", clamp_overlap=True)


# --- Animaux
def mouton_corps(bm):
    v = _sphere(bm, Vector((0, 0, 0)), (0.32, 0.5, 0.3), 3)
    for p in v:
        p.co += p.co.normalized() * 0.035 * (1 + fbm3(p.co * 18.0, 2))


def mouton_tete(bm):
    _sphere(bm, Vector((0, -0.08, 0)), (0.1, 0.17, 0.11), 2)
    for s in (-1, 1):
        _sphere(bm, Vector((s * 0.11, -0.02, 0.04)), (0.06, 0.025, 0.02), 2)


def patte_fine(bm):
    _cylindre(bm, Vector((0, 0, -0.42)), Vector((0, 0, 0.0)), 0.03, 0.035, 8)


def cheval_corps(bm):
    _capsule(bm, Vector((0, -0.55, 0)), Vector((0, 0.55, 0)), 0.32, 14)
    for v in bm.verts:
        v.co.z *= 1.15


def cheval_cou(bm):
    _cylindre(bm, Vector((0, 0, 0)), Vector((0, -0.25, 0.6)), 0.19, 0.13, 12)
    _sphere(bm, Vector((0, -0.42, 0.62)), (0.11, 0.28, 0.13), 2)
    for s in (-1, 1):
        _cylindre(bm, Vector((s * 0.05, -0.22, 0.72)), Vector((s * 0.06, -0.2, 0.84)), 0.03, 0.005, 6)
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0.02, 0.36)) @ Matrix.Rotation(-0.4, 4, "X") @ Matrix.Diagonal((0.04, 0.08, 0.6, 1)))


def cheval_patte(bm):
    _cylindre(bm, Vector((0, 0, -1.0)), Vector((0, 0, 0.0)), 0.055, 0.085, 10)
    _cylindre(bm, Vector((0, 0, -1.08)), Vector((0, 0, -0.98)), 0.07, 0.065, 10)


def queue(bm):
    _cylindre(bm, Vector((0, 0, 0)), Vector((0, 0.12, -0.55)), 0.06, 0.02, 8)


def chien_corps(bm):
    _capsule(bm, Vector((0, -0.25, 0)), Vector((0, 0.22, 0)), 0.13, 12)


def chien_tete(bm):
    _sphere(bm, Vector((0, -0.05, 0.05)), (0.1, 0.11, 0.1), 2)
    _sphere(bm, Vector((0, -0.17, 0.02)), (0.055, 0.08, 0.05), 2)
    for s in (-1, 1):
        _sphere(bm, Vector((s * 0.08, 0.0, 0.12)), (0.03, 0.02, 0.06), 2)


def charrette(bm):
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, 0.75)) @ Matrix.Diagonal((1.3, 2.2, 0.1, 1)))
    for s in (-1, 1):
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((s * 0.63, 0, 1.0)) @ Matrix.Diagonal((0.06, 2.2, 0.4, 1)))
        _cylindre(bm, Vector((s * 0.25, -1.1, 0.75)), Vector((s * 0.25, -2.4, 0.8)), 0.035, 0.03, 6)
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 1.08, 1.0)) @ Matrix.Diagonal((1.3, 0.06, 0.4, 1)))


def roue(bm):
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.5, radius2=0.5, depth=0.08,
                              matrix=Matrix.Rotation(math.pi / 2, 4, "Y"))


def construire_pieces(coll):
    for nom, fn in (("tete", tete), ("yeux", yeux), ("cheveux_courts", cheveux_courts), ("cheveux_longs", cheveux_longs),
                    ("capuche", capuche), ("chapeau", chapeau), ("casque", casque), ("torse", torse), ("jupe", jupe),
                    ("tablier", tablier), ("ceinture", ceinture), ("bras_haut", bras_haut), ("avant_bras", avant_bras),
                    ("main", main), ("cuisse", cuisse), ("mollet", mollet), ("botte", botte), ("cape", cape),
                    ("lance", lance), ("marteau", marteau), ("livre", livre), ("sacoche", sacoche),
                    ("mouton_corps", mouton_corps), ("mouton_tete", mouton_tete), ("patte_fine", patte_fine),
                    ("cheval_corps", cheval_corps), ("cheval_cou", cheval_cou), ("cheval_patte", cheval_patte),
                    ("queue", queue), ("chien_corps", chien_corps), ("chien_tete", chien_tete),
                    ("charrette", charrette), ("roue", roue)):
        _piece(nom, coll, fn, lisse=nom not in ("charrette",))
    # Les pièces sont rangées loin sous l'île : le site les recopie, il ne les affiche jamais telles quelles
    for k, ob in enumerate(PIECES.values()):
        ob.location = (k * 3.0, 0.0, -400.0)
        ob["origine_x"], ob["origine_y"], ob["origine_z"] = k * 3.0, 0.0, -400.0
    log(f"personnages : {len(PIECES)} pièces")
