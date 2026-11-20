"""Constructeurs de maillages : pièces assemblées (bmesh) et cartes de feuilles."""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from .outils import TUILE_FEUILLU, fbm3, lerp, log


def collection(nom, parent=None, taille=None):
    c = bpy.data.collections.get(nom) or bpy.data.collections.new(nom)
    if c.name not in (parent or bpy.context.scene.collection).children:
        (parent or bpy.context.scene.collection).children.link(c)
    if taille:
        c["taille"] = taille
    return c


class Construction:
    """Accumule des pièces (boîtes, cylindres, tubes, sphères bosselées) dans un seul maillage."""

    def __init__(self, nom, coll, M):
        self.nom, self.coll, self.M = nom, coll, M
        self.bm = bmesh.new()
        self.teinte = self.bm.verts.layers.float_color.new("teinte")
        # « donnee » : r = variante du motif (colombage, pierres), g = fenêtre allumée, b = libre
        self.donnee = self.bm.verts.layers.float_color.new("donnee")
        # Projection des UV « facade » : 0 = plan de la face, 1 = cylindre centré sur l'origine (remparts, tours)
        self.mode_uv = self.bm.faces.layers.int.new("mode_uv")
        self.mats = []
        self.donnee_courante = (0.0, 0.0, 0.0)
        self.cylindrique = False

    def _idx(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _finir(self, verts, mat, couleur=(1, 1, 1)):
        idx = self._idx(mat)
        faces = {f for v in verts for f in v.link_faces}
        for f in faces:
            f.material_index = idx
            f.smooth = True
            f[self.mode_uv] = 1 if self.cylindrique else 0
        for v in verts:
            v[self.teinte] = (*couleur, 1.0)
            v[self.donnee] = (*self.donnee_courante, 1.0)
        return faces

    def avec(self, donnee=None, cylindrique=None):
        """Change la donnée écrite sur les prochaines pièces (variante, fenêtre allumée) ou le mode des UV."""
        if donnee is not None:
            self.donnee_courante = tuple(donnee) + (0.0,) * (3 - len(donnee))
        if cylindrique is not None:
            self.cylindrique = cylindrique
        return self

    def boite(self, mat, m, taille, biseau=0.0, couleur=(1, 1, 1)):
        S = Matrix.Diagonal((*taille, 1.0))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m @ S)
        verts = r["verts"]
        faces = self._finir(verts, mat, couleur)
        for f in faces:
            f.smooth = False
        if biseau > 0:
            aretes = list({e for v in verts for e in v.link_edges})
            res = bmesh.ops.bevel(self.bm, geom=list(verts) + aretes, offset=biseau, offset_type="OFFSET",
                                  segments=2, profile=0.5, affect="EDGES", clamp_overlap=True)
            nv = {v for f in res["faces"] for v in f.verts}
            for v in nv:
                v[self.teinte] = (*couleur, 1.0)
            for f in res["faces"]:
                f.smooth = True
            verts = [v for v in set(verts) | nv if v.is_valid]
        return verts

    def cylindre(self, mat, m, r1, r2, h, segments=16, couleur=(1, 1, 1), lisse=True):
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segments,
                                  radius1=r1, radius2=r2, depth=h, matrix=m)
        faces = self._finir(r["verts"], mat, couleur)
        if not lisse:
            for f in faces:
                f.smooth = False
        return r["verts"]

    def sphere(self, mat, m, rayon, subdiv=2, couleur=(1, 1, 1)):
        r = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=rayon, matrix=m)
        self._finir(r["verts"], mat, couleur)
        return r["verts"]

    def tore(self, mat, m, rayon, epaisseur, segments=64, cotes=8):
        """Anneau plat (tore) dans le plan XY du repère m."""
        verts = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            for j in range(cotes):
                b = 2 * math.pi * j / cotes
                r = rayon + epaisseur * math.cos(b)
                verts.append(self.bm.verts.new(m @ Vector((r * math.cos(a), r * math.sin(a), epaisseur * math.sin(b)))))
        for i in range(segments):
            for j in range(cotes):
                a, b = i * cotes + j, i * cotes + (j + 1) % cotes
                c, d = ((i + 1) % segments) * cotes + (j + 1) % cotes, ((i + 1) % segments) * cotes + j
                self.bm.faces.new((verts[a], verts[d], verts[c], verts[b]))
        self._finir(verts, mat)
        return verts

    def tube(self, mat, points, rayons, cotes=8, couleur=(1, 1, 1), fermer=True):
        """Tube le long d'une suite de points (tronc, branche, racine), d'épaisseur variable."""
        anneaux = []
        n = len(points)
        normale = None
        for i, p in enumerate(points):
            t = (points[min(i + 1, n - 1)] - points[max(i - 1, 0)]).normalized()
            if normale is None:
                normale = t.orthogonal().normalized()
            else:
                normale = (normale - t * normale.dot(t)).normalized()
            b = t.cross(normale)
            r = rayons[i]
            anneaux.append([self.bm.verts.new(p + (normale * math.cos(2 * math.pi * k / cotes)
                                                   + b * math.sin(2 * math.pi * k / cotes)) * r) for k in range(cotes)])
        verts = [v for a in anneaux for v in a]
        for i in range(n - 1):
            for k in range(cotes):
                a, b = anneaux[i][k], anneaux[i][(k + 1) % cotes]
                c, d = anneaux[i + 1][(k + 1) % cotes], anneaux[i + 1][k]
                self.bm.faces.new((a, b, c, d))
        if fermer:
            bout = self.bm.verts.new(points[-1] + (points[-1] - points[-2]).normalized() * rayons[-1] * 0.5)
            verts.append(bout)
            for k in range(cotes):
                self.bm.faces.new((anneaux[-1][k], anneaux[-1][(k + 1) % cotes], bout))
        self._finir(verts, mat, couleur)
        return verts

    def demi_sphere(self, mat, m, rayon, couleur=(1, 1, 1)):
        r = bmesh.ops.create_uvsphere(self.bm, u_segments=20, v_segments=10, radius=rayon, matrix=m)
        centre = m.to_translation()
        haut = (m.to_3x3() @ Vector((0, 0, 1))).normalized()
        bas = [v for v in r["verts"] if (v.co - centre).dot(haut) < -1e-4]
        for v in bas:
            v.co -= haut * (v.co - centre).dot(haut)
        self._finir(r["verts"], mat, couleur)
        return r["verts"]

    def prisme(self, mat, pts, x0, x1, m, couleur=(1, 1, 1)):
        """Extrusion d'un polygone (y, z) entre x0 et x1, dans le repère m."""
        a = [self.bm.verts.new(m @ Vector((x0, y, z))) for y, z in pts]
        b = [self.bm.verts.new(m @ Vector((x1, y, z))) for y, z in pts]
        n = len(pts)
        self.bm.faces.new(list(reversed(a)))
        self.bm.faces.new(b)
        for i in range(n):
            j = (i + 1) % n
            self.bm.faces.new((a[i], a[j], b[j], b[i]))
        faces = self._finir(a + b, mat, couleur)
        for f in faces:
            f.smooth = False
        return a + b

    def bosseler(self, verts, centre, amplitude, frequence, graine=0.0):
        for v in verts:
            d = v.co - centre
            if d.length < 1e-6:
                continue
            v.co += d.normalized() * amplitude * fbm3(v.co * frequence + Vector((graine, 0, 0)), 3)

    def mur_ouvertures(self, mat, L, x0, x1, z0, z1, epaisseur, ouvertures=(), y=0.0, couleur=(1, 1, 1)):
        """Mur plein le long de l'axe X local (de x0 à x1, de z0 à z1), percé d'ouvertures (ox0, ox1, oz0, oz1).
        Le mur est découpé en colonnes ; chaque colonne garde les tranches de hauteur qui ne sont pas ouvertes."""
        bornes = sorted({x0, x1, *[max(x0, min(x1, o[0])) for o in ouvertures], *[max(x0, min(x1, o[1])) for o in ouvertures]})
        for a, b in zip(bornes[:-1], bornes[1:]):
            if b - a < 1e-3:
                continue
            m = (a + b) / 2
            trous = sorted((o[2], o[3]) for o in ouvertures if o[0] <= m <= o[1])
            plein, bas = [], z0
            for oz0, oz1 in trous:
                if oz0 > bas + 1e-3:
                    plein.append((bas, oz0))
                bas = max(bas, oz1)
            if z1 > bas + 1e-3:
                plein.append((bas, z1))
            for za, zb in plein:
                self.boite(mat, L @ Matrix.Translation(((a + b) / 2, y, (za + zb) / 2)), (b - a, epaisseur, zb - za), 0.0, couleur)

    def toit(self, mat, mat_pignon, L, larg, prof, zt, faitage, debord=0.4, epaisseur=0.16, couleur=(1, 1, 1),
             couleur_pignon=(1, 1, 1), croupe=False):
        """Toit à deux pans, faîtage le long de l'axe X local, pignons triangulaires aux deux bouts."""
        pente = math.atan2(faitage, prof / 2)
        long_pan = (prof / 2 + debord) / math.cos(pente)
        for cy in (-1, 1):
            cy_c = cy * (prof / 2 + debord) / 2
            cz = zt + faitage - (prof / 2 + debord) / 2 * math.tan(pente) + epaisseur * 0.6
            self.boite(mat, L @ Matrix.Translation((0, cy_c, cz)) @ Matrix.Rotation(cy * pente, 4, "X"),
                       (larg + 2 * debord * (0.3 if croupe else 1.0), long_pan + 0.05, epaisseur), 0.0, couleur)
        if not croupe:
            for cx in (-1, 1):
                self.prisme(mat_pignon, [(-prof / 2, zt), (prof / 2, zt), (0, zt + faitage)], cx * larg / 2 - 0.08,
                            cx * larg / 2 + 0.08, L, couleur_pignon)
        else:
            for cx in (-1, 1):
                pts = [(-prof / 2 - debord * 0.5, zt - 0.05), (prof / 2 + debord * 0.5, zt - 0.05), (0, zt + faitage + 0.1)]
                a = [self.bm.verts.new(L @ Vector((cx * (larg / 2 + debord * 0.3), y, z))) for y, z in pts[:2]]
                s1 = self.bm.verts.new(L @ Vector((cx * (larg / 2 - prof * 0.3), 0, zt + faitage + 0.1)))
                f = self.bm.faces.new((a[0], a[1], s1) if cx > 0 else (a[1], a[0], s1))
                self._finir([*a, s1], mat, couleur)
        return pente

    def arche(self, mat, L, rayon, epaisseur, profondeur, zc, n=9, couleur=(1, 1, 1), cle=True):
        """Arc en plein cintre de claveaux, dans le plan XZ local, centré en (0, 0, zc)."""
        for i in range(n):
            a = math.pi * (i + 0.5) / n
            X = Vector((math.sin(a), 0, -math.cos(a)))
            Y = Vector((0, 1, 0))
            Z = Vector((math.cos(a), 0, math.sin(a)))
            R = Matrix((X, Y, Z)).transposed().to_4x4()
            gros = cle and i == n // 2
            m = L @ Matrix.Translation((rayon * math.cos(a), 0, zc + rayon * math.sin(a) + (0.04 if gros else 0))) @ R
            longueur = math.pi * rayon / n * 0.96
            self.boite(mat, m, (longueur, profondeur * (1.06 if gros else 1.0), epaisseur * (1.15 if gros else 1.0)), 0.03, couleur)

    def uv_facade(self):
        """UV « facade » en mètres : les motifs (pierres, colombages, tuiles) gardent la même taille sur tous les bâtiments."""
        uv = self.bm.loops.layers.uv.get("facade") or self.bm.loops.layers.uv.new("facade")
        Z = Vector((0, 0, 1))
        for f in self.bm.faces:
            if f[self.mode_uv] == 1 and abs(f.normal.z) < 0.7:
                rayon = sum(math.hypot(v.co.x, v.co.y) for v in f.verts) / max(1, len(f.verts))
                a_ref = math.atan2(f.calc_center_median().y, f.calc_center_median().x)
                for l in f.loops:
                    a = math.atan2(l.vert.co.y, l.vert.co.x)
                    da = (a - a_ref + math.pi) % (2 * math.pi) - math.pi
                    l[uv].uv = ((a_ref + da) * rayon, l.vert.co.z)
                continue
            n = f.normal
            t = Z.cross(n)
            t = t.normalized() if t.length > 0.1 else Vector((1, 0, 0))
            b = n.cross(t)
            for l in f.loops:
                l[uv].uv = (l.vert.co.dot(t), l.vert.co.dot(b))

    def objet(self, recalculer=True, **props):
        if recalculer:
            bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        self.bm.normal_update()
        self.uv_facade()
        me = bpy.data.meshes.new(self.nom)
        self.bm.to_mesh(me)
        self.bm.free()
        for nom in self.mats:
            me.materials.append(self.M[nom])
        ob = bpy.data.objects.new(self.nom, me)
        self.coll.objects.link(ob)
        for k, v in props.items():
            ob[k] = v
        return ob


class Feuillage:
    """Cartes de feuilles : des rectangles pliés en V, découpés par la texture des feuilles.
    Les normales sont orientées depuis le centre de la couronne : l'arbre s'éclaire comme un volume."""

    def __init__(self):
        self.verts, self.faces, self.uv = [], [], []
        self.normales, self.teintes, self.balance = [], [], []
        self.nb = 0

    def carte(self, centre, normale, haut, largeur, hauteur, tuile, teinte, coeur, poids=0.5, phase=0.0, pli=0.22):
        n = normale.normalized()
        y = (haut - n * haut.dot(n))
        if y.length < 1e-4:
            y = n.orthogonal()
        y.normalize()
        x = y.cross(n).normalized()
        col, rang = tuile % 2, tuile // 2
        e = 0.004
        u0, u1 = col * 0.5 + e, col * 0.5 + 0.5 - e
        v0, v1 = rang * 0.5 + e, rang * 0.5 + 0.5 - e
        i0 = len(self.verts)
        for k, sy in enumerate((-0.5, 0.5)):
            for j, sx in enumerate((-0.5, 0.0, 0.5)):
                p = centre + x * (sx * largeur) + y * (sy * hauteur) + n * (pli * largeur * 0.5 if sx == 0.0 else 0.0)
                self.verts.append(tuple(p))
                vers_coeur = (p - coeur)
                vers_coeur = vers_coeur.normalized() if vers_coeur.length > 1e-4 else n
                self.normales.append(tuple((n * 0.3 + vers_coeur * 0.7).normalized()))
                self.teintes.append((*teinte, 1.0))
                self.balance.append((poids, phase, 0.0, 1.0))
        for a, b, c, d in ((0, 1, 4, 3), (1, 2, 5, 4)):
            self.faces.append((i0 + a, i0 + b, i0 + c, i0 + d))
        uvs = {0: (u0, v0), 1: ((u0 + u1) / 2, v0), 2: (u1, v0), 3: (u0, v1), 4: ((u0 + u1) / 2, v1), 5: (u1, v1)}
        for a, b, c, d in ((0, 1, 4, 3), (1, 2, 5, 4)):
            self.uv.extend([uvs[a], uvs[b], uvs[c], uvs[d]])
        self.nb += 1

    def objet(self, coll, M, nom="feuillage", **props):
        me = bpy.data.meshes.new(nom)
        me.from_pydata(self.verts, [], self.faces)
        couche = me.uv_layers.new(name="feuille")
        couche.data.foreach_set("uv", [c for uv in self.uv for c in uv])
        for nom_attr, donnees in (("teinte", self.teintes), ("balancement", self.balance)):
            a = me.color_attributes.new(nom_attr, "FLOAT_COLOR", "POINT")
            a.data.foreach_set("color", [c for t in donnees for c in t])
        me.materials.append(M["feuilles"])
        me.shade_smooth()
        me.normals_split_custom_set_from_vertices(self.normales)
        ob = bpy.data.objects.new(nom, me)
        coll.objects.link(ob)
        for k, v in props.items():
            ob[k] = v
        log(f"feuillage : {self.nb} cartes")
        return ob


def repere(x, y, z, rz=0.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, "Z")


def orientation(m_local, x, y, z, rx=0.0, ry=0.0, rz=0.0):
    return m_local @ Matrix.Translation((x, y, z)) @ (Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(ry, 4, "Y")
                                                      @ Matrix.Rotation(rx, 4, "X"))


def vers(dx, dy):
    """Rotation autour de Z pour que l'avant d'un bâtiment (son -Y local) regarde dans la direction (dx, dy)."""
    return math.atan2(dx, -dy)


def ancre(coll, nom, pos):
    e = bpy.data.objects.new(nom, None)
    e.empty_display_type = "SPHERE"
    e.empty_display_size = 0.3
    e.location = pos
    coll.objects.link(e)
    return e


def lierre(feuillage, centre, normale, rnd, nombre=6, etendue=0.8, taille=0.45):
    """Quelques petites cartes de feuilles plaquées contre un mur ou une pierre."""
    teinte = (lerp(0.75, 0.95, rnd.random()), lerp(0.85, 1.0, rnd.random()), lerp(0.6, 0.8, rnd.random()))
    for k in range(nombre):
        off = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * etendue
        off -= normale * off.dot(normale)
        c = centre + off + normale * 0.04
        n = (normale + Vector((rnd.gauss(0, 0.35), rnd.gauss(0, 0.35), rnd.gauss(0, 0.35)))).normalized()
        feuillage.carte(c, n, Vector((0, 0, 1)), taille, taille, TUILE_FEUILLU, teinte, c - normale, 0.1, rnd.random(), 0.15)


