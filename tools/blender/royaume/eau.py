"""
L'eau du royaume : l'étang où naît la rivière, la rivière qui fait le tour de la campagne, passe sous
le rempart extérieur par une arche, traverse la lisière, puis tombe du bord de l'île : la cascade.

Le niveau de l'eau descend toujours (jamais de remontée) et reste sous les berges creusées par plan.hauteur.
L'eau, la cascade et leur brume sont rendues par le site ; ici on ne fait que la géométrie.
"""

import math

import bpy
from mathutils import Vector

from . import plan
from .construction import ancre
from .outils import log, n3, reechantillonner


def _uv_par_sommet(me, nom, uvs):
    couche = me.uv_layers.new(name=nom)
    for p in me.polygons:
        for li, vi in zip(p.loop_indices, p.vertices):
            couche.data[li].uv = uvs[vi]


def _objet_eau(nom, verts, faces, uvs, M, coll, **props):
    me = bpy.data.meshes.new(nom)
    me.from_pydata(verts, [], faces)
    _uv_par_sommet(me, "eau", uvs)
    me.materials.append(M["eau"])
    ob = bpy.data.objects.new(nom, me)
    coll.objects.link(ob)
    ob["garder_uv"] = 1
    for k, v in props.items():
        ob[k] = v
    return ob


def profil_riviere():
    """Points de la rivière tous les 0,6 m : (x, y, z de l'eau, distance), de l'étang jusqu'au bord de l'île."""
    pts = reechantillonner(plan.RIVIERE, 0.6)
    (ex, ey), er = plan.ETANG
    z_prec = plan.HAUTEUR_SITE["etang"] - 0.35
    sortie = []
    for x, y, s in pts:
        if plan.dist_etang(x, y) < -0.5:
            continue
        if plan.sur_ile(x, y, 0.3):
            z = min(z_prec - 0.01, plan.hauteur_sans_eau(x, y) - 0.32)
        else:
            z = z_prec - 0.3
        sortie.append((x, y, z, s))
        z_prec = z
        if not plan.sur_ile(x, y, -0.6):
            break
    return sortie


def niveau_au_rempart(profil):
    a = plan.ANGLE_EAU
    R = plan.REMPARTS["exterieur"]["rayon"]
    meilleur = min(profil, key=lambda p: math.hypot(p[0] - R * math.cos(a), p[1] - R * math.sin(a)))
    return meilleur[2]


def construire_eau(M, vivant, reperes):
    (cx, cy), er = plan.ETANG
    z_etang = plan.HAUTEUR_SITE["etang"] - 0.35
    # Étang : disque au bord irrégulier (u = 0 au bord, 0,5 au centre : le site fond les rives)
    anneaux, secteurs = 7, 64
    verts, faces, uvs = [(cx, cy, z_etang)], [], [(0.5, 0.0)]
    for j in range(1, anneaux + 1):
        for i in range(secteurs):
            a = 2 * math.pi * i / secteurs
            R = er + 0.6 * n3(math.cos(a) * 1.5, math.sin(a) * 1.5, 3.3) + 0.5
            r = R * j / anneaux
            verts.append((cx + r * math.cos(a), cy + r * math.sin(a), z_etang))
            uvs.append((0.5 * (1 - j / anneaux), r))
    for i in range(secteurs):
        faces.append((0, 1 + i, 1 + (i + 1) % secteurs))
    for j in range(1, anneaux):
        for i in range(secteurs):
            a = 1 + (j - 1) * secteurs + i
            b = 1 + (j - 1) * secteurs + (i + 1) % secteurs
            faces.append((a, a + secteurs, b + secteurs, b))
    _objet_eau("eau_etang", verts, faces, uvs, M, vivant, vivant="eau", ecoulement=0)

    # Rivière : une bande au fil du lit
    profil = profil_riviere()
    verts, faces, uvs = [], [], []
    for k, (x, y, z, s) in enumerate(profil):
        a = profil[max(0, k - 1)]
        b = profil[min(len(profil) - 1, k + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        l = math.hypot(tx, ty) or 1
        nx, ny = -ty / l, tx / l
        w = plan.LARGEUR_RIVIERE * (0.95 + 0.15 * n3(x * 0.2, y * 0.2, 8.0))
        for c in (-1.0, 0.0, 1.0):
            verts.append((x + nx * w * c, y + ny * w * c, z))
            uvs.append(((c + 1) / 2, s - profil[0][3]))
    for k in range(len(profil) - 1):
        for c in range(2):
            a = k * 3 + c
            faces.append((a, a + 1, a + 4, a + 3))
    _objet_eau("eau_riviere", verts, faces, uvs, M, vivant, vivant="eau", ecoulement=1)

    # Cascade : un ruban qui s'écarte de la falaise et tombe jusque dans la mer de nuages
    x, y, z, _ = profil[-1]
    levre = Vector((x, y, z))
    ax, ay, _, _ = profil[-4]
    direction = Vector((x - ax, y - ay, 0)).normalized()
    direction = (direction + Vector((x, y, 0)).normalized() * 0.6).normalized()
    lat = Vector((-direction.y, direction.x, 0))
    verts, faces, uvs = [], [], []
    etapes, chute = 60, 78.0
    for j in range(etapes + 1):
        u = j / etapes
        h = chute * u ** 1.25
        centre = levre + direction * (0.5 + 1.7 * math.sqrt(h)) + Vector((0, 0, -h))
        w = 2.0 + 0.11 * h
        for c in (-1.0, -0.5, 0.0, 0.5, 1.0):
            verts.append(tuple(centre + lat * w * c + direction * (0.3 * (1 - c * c))))
            uvs.append(((c + 1) / 2, h))
    for j in range(etapes):
        for c in range(4):
            a = j * 5 + c
            faces.append((a, a + 1, a + 6, a + 5))
    _objet_eau("cascade", verts, faces, uvs, M, vivant, vivant="cascade", chute=chute)
    ancre(reperes, "cascade_haut", levre + direction * 0.9 + Vector((0, 0, -0.5)))
    ancre(reperes, "cascade_bas", levre + direction * (0.5 + 1.7 * math.sqrt(chute)) + Vector((0, 0, -chute + 2.0)))
    log(f"eau : étang, rivière de {profil[-1][3] - profil[0][3]:.0f} m, cascade de {chute:.0f} m")
    return profil
