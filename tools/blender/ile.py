"""
L'ÎLE DU PORTFOLIO · scène Blender de la version immersive (/3d/)

Ce script fabrique l'île dans Blender, « cuit » sa lumière avec Cycles dans des textures, puis
exporte le modèle et les textures pour le site, où Three.js les affiche.
Cuire la lumière veut dire : Cycles calcule une fois pour toutes l'éclairage réaliste (soleil, ciel,
ombres douces, lumière qui rebondit) et l'enregistre dans des images. Le navigateur n'a plus qu'à
afficher ces images : la scène a l'air rendue par Blender, et tourne pourtant sur un téléphone.

Utilisation, depuis la racine du dépôt :

  blender -b --factory-startup --python tools/blender/ile.py -- [options]

Étapes (--etapes, séparées par des virgules ; par défaut « construire,cuire ») :
  construire  modélise l'île et l'enregistre dans tools/blender/out/ile.blend
  apercu      rend une image d'un chapitre (--chapitre N, ou « tous ») dans tools/blender/out/
  affiche     rend l'image de secours du site (sans WebGL) : wwwroot/3d/assets/affiche.webp
  cuire       cuit la lumière, exporte ile.glb et les atlas dans wwwroot/3d/assets/

Retoucher l'île à la main : ouvrir tools/blender/out/ile.blend, modifier, enregistrer, puis
  blender -b tools/blender/out/ile.blend --python tools/blender/ile.py -- --etapes cuire

Conventions de la scène (à respecter si on ajoute des objets à la main) :
  collections « atlas_<nom> »  objets cuits dans l'atlas <nom> (propriété « taille » = résolution)
  collection « vivant »        objets exportés sans cuisson : le site leur donne une matière animée
  collection « reperes »       objets vides exportés : trajet de la caméra (cam_XX, cible_XX), ancres
  collection « studio »        soleil et réglages, jamais exportés
"""

import bpy
import bmesh
import math
import os
import random
import sys
import time
from mathutils import Matrix, Vector, noise
from mathutils.bvhtree import BVHTree

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.normpath(os.path.join(ICI, "..", ".."))
SORTIE_BLEND = os.path.join(ICI, "out")
SORTIE_SITE = os.path.join(DEPOT, "src", "ErnestWorld", "wwwroot", "3d", "assets")

# Soleil couchant : direction vers le soleil (azimut depuis +X vers +Y, hauteur au-dessus de l'horizon)
SOLEIL_AZIMUT = math.radians(22)
SOLEIL_HAUTEUR = math.radians(13)
SOLEIL_DIR = Vector((math.cos(SOLEIL_HAUTEUR) * math.cos(SOLEIL_AZIMUT),
                     math.cos(SOLEIL_HAUTEUR) * math.sin(SOLEIL_AZIMUT),
                     math.sin(SOLEIL_HAUTEUR)))


def log(*a):
    print("[ile]", *a, flush=True)


def lire_options():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"etapes": "construire,cuire", "chapitre": "0", "echantillons": "", "rapide": False,
            "sortie": SORTIE_SITE, "largeur": "1280", "hauteur": "720"}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--rapide":
            opts["rapide"] = True
        elif a.startswith("--") and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1]
            i += 1
        i += 1
    opts["etapes"] = [e.strip() for e in opts["etapes"].split(",") if e.strip()]
    return opts


# =========================================================================
#  BRUIT ET OUTILS
# =========================================================================

def n3(x, y, z):
    return noise.noise(Vector((x, y, z)))


def fbm2(x, y, octaves=4, graine=0.0):
    v, a, f = 0.0, 0.5, 1.0
    for i in range(octaves):
        v += a * n3(x * f, y * f, graine + i * 7.31)
        a *= 0.5
        f *= 2.03
    return v * 1.9


def fbm3(p, octaves=4):
    v, a, f = 0.0, 0.5, 1.0
    for i in range(octaves):
        v += a * noise.noise(p * f + Vector((i * 3.7, i * 1.3, i * 5.1)))
        a *= 0.5
        f *= 2.07
    return v * 1.9


def smoothstep(a, b, x):
    if a == b:
        return 0.0 if x < a else 1.0
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def dist_segment(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy)


def dist_polyligne(px, py, pts):
    return min(dist_segment(px, py, *pts[i], *pts[i + 1]) for i in range(len(pts) - 1))


# =========================================================================
#  PLAN DE L'ÎLE
# =========================================================================

# Lieux (x, y, rayon du replat). Le chemin de la caméra visite les lieux dans cet ordre.
SITES = {
    "arche": (0.0, -22.0, 4.0),
    "atelier": (-14.0, -6.0, 6.0),
    "cercle": (2.0, 6.0, 7.8),
    "cristaux": (15.0, -6.0, 4.2),
    "phare": (23.5, 19.5, 4.0),
}

CHEMIN = [(0.0, -27.0), (0.0, -22.0), (-1.5, -17.0), (-5.0, -12.0), (-9.0, -8.5), (-8.5, -3.0), (-5.0, 1.5),
          (-3.0, 5.0), (2.0, 6.0), (7.5, 3.5), (11.0, -1.5), (12.5, -5.0), (14.5, 1.0), (17.0, 8.0),
          (20.0, 14.5), (22.5, 18.0)]
CHEMIN_ATELIER = [(-9.0, -8.5), (-11.2, -7.4)]


def rayon_bord(theta):
    c, s = math.cos(theta), math.sin(theta)
    r = 30.0 + 3.6 * n3(c * 1.25 + 5.2, s * 1.25 + 1.7, 0.3) + 1.6 * n3(c * 3.1 + 2.0, s * 3.1 + 7.0, 1.1)
    r += 0.5 * n3(c * 7.0, s * 7.0, 4.4)
    # Promontoire du phare (nord-est) et avancée de l'arche (sud)
    r += 6.0 * max(0.0, math.cos(theta - math.atan2(19.5, 23.5))) ** 10
    r += 2.5 * max(0.0, math.cos(theta + math.pi / 2)) ** 14
    return r


def hauteur_brute(x, y):
    r = math.hypot(x, y)
    t = r / rayon_bord(math.atan2(y, x))
    h = 2.6 * (1.0 - t * t)
    h += 1.7 * fbm2(x * 0.045, y * 0.045, 4, 0.5)
    h += 4.2 * math.exp(-((x - 23.5) ** 2 + (y - 19.5) ** 2) / 60.0)   # colline du phare
    h += 3.4 * math.exp(-((x + 15) ** 2 + (y - 15) ** 2) / 70.0)       # colline boisée
    h += 0.12 * n3(x * 0.6, y * 0.6, 9.0)
    return h


HAUTEUR_SITE = {}


def hauteur(x, y, masque_chemin=0.0):
    h = hauteur_brute(x, y)
    for nom, (cx, cy, rr) in SITES.items():
        d = math.hypot(x - cx, y - cy)
        w = smoothstep(rr + 4.0, rr, d)
        if w > 0:
            h = lerp(h, HAUTEUR_SITE[nom], w)
    r = math.hypot(x, y)
    t = r / rayon_bord(math.atan2(y, x))
    h -= 1.1 * smoothstep(0.9, 1.0, t)
    h -= 0.07 * masque_chemin
    return h


def masque_chemin(x, y):
    d = min(dist_polyligne(x, y, CHEMIN), dist_polyligne(x, y, CHEMIN_ATELIER))
    largeur = 0.85 + 0.25 * n3(x * 0.4, y * 0.4, 2.0)
    return 1.0 - smoothstep(largeur, largeur + 0.55, d)


def preparer_plan():
    for nom, (cx, cy, rr) in SITES.items():
        HAUTEUR_SITE[nom] = hauteur_brute(cx, cy)


# =========================================================================
#  MATIÈRES (Cycles)
# =========================================================================

class Noeuds:
    """Petit assistant pour écrire des arbres de nœuds sans répéter dix lignes à chaque fois."""

    def __init__(self, nom):
        self.mat = bpy.data.materials.new(nom)
        self.nt = self.mat.node_tree
        self.nt.nodes.clear()
        self.sortie = self.nt.nodes.new("ShaderNodeOutputMaterial")
        self.bsdf = self.nt.nodes.new("ShaderNodeBsdfPrincipled")
        self.lien(self.bsdf.outputs[0], self.sortie.inputs[0])
        coord = self.nt.nodes.new("ShaderNodeTexCoord")
        self.pos = coord.outputs["Object"]
        self.geo = self.nt.nodes.new("ShaderNodeNewGeometry")

    def lien(self, a, b):
        self.nt.links.new(a, b)

    def _entree(self, sock, v):
        if isinstance(v, (int, float)):
            sock.default_value = v
        elif isinstance(v, tuple):
            sock.default_value = v if len(v) == 4 or sock.type != "RGBA" else (*v, 1.0)
        else:
            self.lien(v, sock)

    def bruit(self, echelle, detail=4.0, rugo=0.5, vec=None, distorsion=0.0):
        n = self.nt.nodes.new("ShaderNodeTexNoise")
        self.lien(vec or self.pos, n.inputs["Vector"])
        n.inputs["Scale"].default_value = echelle
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rugo
        n.inputs["Distortion"].default_value = distorsion
        return n.outputs["Factor"]

    def voronoi(self, echelle, vec=None, sortie="Distance", trait="F1"):
        n = self.nt.nodes.new("ShaderNodeTexVoronoi")
        n.feature = trait
        self.lien(vec or self.pos, n.inputs["Vector"])
        n.inputs["Scale"].default_value = echelle
        return n.outputs[sortie]

    def vague(self, echelle, distorsion=4.0, direction="Z", vec=None, detail=3.0):
        n = self.nt.nodes.new("ShaderNodeTexWave")
        n.bands_direction = direction
        self.lien(vec or self.pos, n.inputs["Vector"])
        n.inputs["Scale"].default_value = echelle
        n.inputs["Distortion"].default_value = distorsion
        n.inputs["Detail"].default_value = detail
        return n.outputs["Factor"]

    def brique(self, echelle, vec=None, mortier=0.02, largeur=0.5, hauteur=0.25):
        n = self.nt.nodes.new("ShaderNodeTexBrick")
        self.lien(vec or self.pos, n.inputs["Vector"])
        n.inputs["Scale"].default_value = echelle
        n.inputs["Mortar Size"].default_value = mortier
        n.inputs["Brick Width"].default_value = largeur
        n.inputs["Row Height"].default_value = hauteur
        n.inputs["Color1"].default_value = (1, 1, 1, 1)
        n.inputs["Color2"].default_value = (0.6, 0.6, 0.6, 1)
        n.inputs["Mortar"].default_value = (0, 0, 0, 1)
        return n.outputs["Color"], n.outputs["Factor"]

    def rampe(self, fac, arrets):
        n = self.nt.nodes.new("ShaderNodeValToRGB")
        r = n.color_ramp
        while len(r.elements) > 1:
            r.elements.remove(r.elements[-1])
        r.elements[0].position = arrets[0][0]
        r.elements[0].color = (*arrets[0][1], 1.0)
        for p, c in arrets[1:]:
            e = r.elements.new(p)
            e.color = (*c, 1.0)
        self._entree(n.inputs[0], fac)
        return n.outputs["Color"]

    def melange(self, fac, a, b, mode="MIX"):
        n = self.nt.nodes.new("ShaderNodeMix")
        n.data_type = "RGBA"
        n.blend_type = mode
        self._entree(n.inputs[0], fac)
        self._entree(n.inputs[6], a)
        self._entree(n.inputs[7], b)
        return n.outputs[2]

    def math(self, op, a, b=0.0, borner=False):
        n = self.nt.nodes.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = borner
        self._entree(n.inputs[0], a)
        self._entree(n.inputs[1], b)
        return n.outputs[0]

    def plage(self, v, de_min, de_max, a_min=0.0, a_max=1.0):
        n = self.nt.nodes.new("ShaderNodeMapRange")
        self._entree(n.inputs[0], v)
        n.inputs[1].default_value = de_min
        n.inputs[2].default_value = de_max
        n.inputs[3].default_value = a_min
        n.inputs[4].default_value = a_max
        n.clamp = True
        return n.outputs[0]

    def attribut(self, nom, sortie="Color"):
        n = self.nt.nodes.new("ShaderNodeAttribute")
        n.attribute_name = nom
        return n.outputs[sortie]

    def echelle_vec(self, sx, sy, sz):
        n = self.nt.nodes.new("ShaderNodeVectorMath")
        n.operation = "MULTIPLY"
        self.lien(self.pos, n.inputs[0])
        n.inputs[1].default_value = (sx, sy, sz)
        return n.outputs[0]

    def normale_z(self):
        n = self.nt.nodes.new("ShaderNodeSeparateXYZ")
        self.lien(self.geo.outputs["Normal"], n.inputs[0])
        return n.outputs["Z"]

    def relief(self, hauteur, force=0.3, distance=0.05):
        n = self.nt.nodes.new("ShaderNodeBump")
        self._entree(n.inputs["Height"], hauteur)
        n.inputs["Strength"].default_value = force
        n.inputs["Distance"].default_value = distance
        self.lien(n.outputs[0], self.bsdf.inputs["Normal"])

    def couleur(self, c):
        self._entree(self.bsdf.inputs["Base Color"], c)

    def rugosite(self, r):
        self._entree(self.bsdf.inputs["Roughness"], r)

    def emission(self, couleur, force):
        self._entree(self.bsdf.inputs["Emission Color"], couleur)
        self._entree(self.bsdf.inputs["Emission Strength"], force)


def teinte(m):
    return m.attribut("teinte")


def creer_matieres():
    M = {}

    # Herbe du dessus de l'île, avec le chemin de terre peint par l'attribut « chemin »
    m = Noeuds("herbe")
    grand = m.bruit(0.07, 5, 0.55)
    moyen = m.bruit(0.55, 6, 0.6)
    fin = m.bruit(6.0, 3, 0.7)
    herbe = m.rampe(grand, [(0.25, (0.065, 0.105, 0.022)), (0.5, (0.1, 0.15, 0.032)),
                            (0.7, (0.15, 0.17, 0.04)), (0.85, (0.23, 0.2, 0.07))])
    herbe = m.melange(m.plage(moyen, 0.3, 0.75, 0.0, 0.45), herbe, (0.03, 0.06, 0.015), "MULTIPLY")
    fleurs = m.plage(m.voronoi(2.2, trait="F1"), 0.0, 0.06, 1.0, 0.0)
    fleurs = m.math("MULTIPLY", fleurs, m.plage(m.bruit(0.25, 2), 0.55, 0.7))
    herbe = m.melange(m.math("MULTIPLY", fleurs, 0.7), herbe, (0.6, 0.45, 0.2))
    terre = m.rampe(m.bruit(1.4, 6), [(0.3, (0.075, 0.05, 0.03)), (0.7, (0.16, 0.115, 0.07))])
    cailloux = m.plage(m.voronoi(9.0), 0.0, 0.18, 1.0, 0.0)
    terre = m.melange(m.math("MULTIPLY", cailloux, 0.5), terre, (0.22, 0.2, 0.17))
    bord = m.plage(m.math("ADD", m.attribut("chemin", "Factor"), m.math("MULTIPLY", fin, 0.4)), 0.55, 0.85)
    m.couleur(m.melange(bord, herbe, terre))
    m.rugosite(0.95)
    m.relief(m.math("ADD", m.math("MULTIPLY", fin, 0.6), m.math("MULTIPLY", cailloux, bord)), 0.35, 0.04)
    M["herbe"] = m.mat

    # Roche de la falaise : strates, fissures, mousse sur les faces tournées vers le ciel
    m = Noeuds("roche")
    strates = m.vague(0.6, 16.0, "Z", m.echelle_vec(0.05, 0.05, 0.45), 6)
    var = m.math("ADD", m.math("MULTIPLY", m.bruit(0.35, 5, 0.6), 0.6), m.math("MULTIPLY", m.bruit(0.07, 3, 0.5), 0.4))
    roche = m.rampe(m.math("ADD", m.math("MULTIPLY", strates, 0.18), m.math("MULTIPLY", var, 0.82)),
                    [(0.2, (0.05, 0.04, 0.035)), (0.45, (0.12, 0.095, 0.075)),
                     (0.7, (0.2, 0.16, 0.12)), (0.9, (0.27, 0.22, 0.17))])
    # Fissures : seulement par endroits (masque de bruit), sinon on croirait un mur de pierres
    fissures = m.plage(m.voronoi(0.6, trait="DISTANCE_TO_EDGE"), 0.0, 0.03, 0.0, 1.0)
    zones = m.plage(m.bruit(0.45, 3), 0.52, 0.66)
    roche = m.melange(m.math("MULTIPLY", m.math("SUBTRACT", 1.0, fissures), m.math("MULTIPLY", zones, 0.75)),
                      roche, (0.02, 0.018, 0.016))
    fissures = m.math("MULTIPLY", fissures, 0.35)
    mousse = m.math("MULTIPLY", m.plage(m.normale_z(), 0.55, 0.85), m.plage(m.bruit(1.2, 4), 0.4, 0.6))
    roche = m.melange(mousse, roche, m.rampe(var, [(0.3, (0.04, 0.07, 0.015)), (0.7, (0.1, 0.12, 0.03))]))
    m.couleur(m.melange(1.0, roche, teinte(m), "MULTIPLY"))
    m.rugosite(0.9)
    m.relief(m.math("ADD", m.math("MULTIPLY", m.bruit(3.0, 6), 0.5), fissures), 0.6, 0.15)
    M["roche"] = m.mat

    # Pierre taillée (arche, menhirs, socles, soubassements)
    m = Noeuds("pierre")
    var = m.bruit(1.6, 6, 0.6)
    pierre = m.rampe(var, [(0.3, (0.17, 0.15, 0.125)), (0.55, (0.26, 0.235, 0.2)), (0.8, (0.34, 0.31, 0.27))])
    taches = m.plage(m.bruit(4.0, 3), 0.55, 0.75)
    pierre = m.melange(m.math("MULTIPLY", taches, 0.5), pierre, (0.08, 0.075, 0.07))
    mousse = m.math("MULTIPLY", m.plage(m.normale_z(), 0.7, 0.95), m.plage(m.bruit(2.0, 4), 0.45, 0.62))
    pierre = m.melange(mousse, pierre, (0.05, 0.08, 0.02))
    m.couleur(m.melange(1.0, pierre, teinte(m), "MULTIPLY"))
    m.rugosite(0.85)
    m.relief(m.math("ADD", m.bruit(9.0, 5), m.math("MULTIPLY", m.bruit(1.5, 3), 0.5)), 0.35, 0.03)
    M["pierre"] = m.mat

    # Bois des planches : veines étirées verticalement
    m = Noeuds("bois")
    veine = m.bruit(1.0, 6, 0.6, m.echelle_vec(9.0, 9.0, 0.35), 2.0)
    bois = m.rampe(veine, [(0.3, (0.07, 0.035, 0.016)), (0.6, (0.15, 0.08, 0.036)), (0.85, (0.22, 0.13, 0.06))])
    m.couleur(m.melange(1.0, bois, teinte(m), "MULTIPLY"))
    m.rugosite(0.7)
    m.relief(veine, 0.25, 0.02)
    M["bois"] = m.mat

    m = Noeuds("bois_sombre")
    veine = m.bruit(1.0, 5, 0.6, m.echelle_vec(8.0, 8.0, 0.4), 2.0)
    m.couleur(m.melange(1.0, m.rampe(veine, [(0.3, (0.035, 0.02, 0.012)), (0.8, (0.08, 0.045, 0.025))]),
                        teinte(m), "MULTIPLY"))
    m.rugosite(0.6)
    M["bois_sombre"] = m.mat

    # Tuiles du toit
    m = Noeuds("toit")
    couleur, fac = m.brique(3.2, m.echelle_vec(1.0, 1.0, 1.0), 0.03, 0.42, 0.22)
    var = m.bruit(3.0, 4)
    toit = m.rampe(var, [(0.3, (0.11, 0.035, 0.022)), (0.7, (0.2, 0.065, 0.035))])
    toit = m.melange(1.0, toit, couleur, "MULTIPLY")
    m.couleur(m.melange(1.0, toit, teinte(m), "MULTIPLY"))
    m.rugosite(0.75)
    m.relief(fac, 0.5, 0.03)
    M["toit"] = m.mat

    m = Noeuds("enduit")
    sale = m.plage(m.bruit(1.8, 6), 0.45, 0.8)
    m.couleur(m.melange(sale, (0.62, 0.58, 0.52), (0.36, 0.33, 0.29)))
    m.rugosite(0.8)
    m.relief(m.bruit(14.0, 3), 0.15, 0.01)
    M["enduit"] = m.mat

    m = Noeuds("rouge")
    sale = m.plage(m.bruit(1.8, 6), 0.45, 0.8)
    m.couleur(m.melange(sale, (0.42, 0.045, 0.03), (0.22, 0.03, 0.02)))
    m.rugosite(0.7)
    M["rouge"] = m.mat

    m = Noeuds("metal")
    m.couleur((0.025, 0.025, 0.03))
    m.bsdf.inputs["Metallic"].default_value = 0.6
    m.rugosite(0.45)
    M["metal"] = m.mat

    m = Noeuds("cuivre")
    m.couleur(m.rampe(m.bruit(3.0, 4), [(0.3, (0.09, 0.2, 0.15)), (0.7, (0.3, 0.17, 0.07))]))
    m.bsdf.inputs["Metallic"].default_value = 0.4
    m.rugosite(0.5)
    M["cuivre"] = m.mat

    # Fenêtres et lanternes allumées : leur lumière orangée est cuite sur les murs autour
    m = Noeuds("lumiere")
    m.couleur((1.0, 0.6, 0.3))
    m.emission((1.0, 0.52, 0.2), 7.0)
    M["lumiere"] = m.mat

    m = Noeuds("lumiere_phare")
    m.couleur((1.0, 0.85, 0.6))
    m.emission((1.0, 0.75, 0.42), 16.0)
    M["lumiere_phare"] = m.mat

    # Feuillage : une teinte par arbre (attribut « teinte »), des touffes de feuilles en relief
    m = Noeuds("feuillage")
    var = m.bruit(0.8, 4)
    touffes = m.voronoi(7.0)
    f = m.rampe(var, [(0.3, (0.55, 0.55, 0.5)), (0.7, (1.0, 1.0, 0.92))])
    f = m.melange(1.0, f, teinte(m), "MULTIPLY")
    f = m.melange(m.plage(touffes, 0.0, 0.5, 0.55, 0.0), f, (0.0, 0.0, 0.0))
    m.couleur(f)
    m.rugosite(0.8)
    m.relief(m.math("SUBTRACT", 1.0, touffes), 0.55, 0.12)
    M["feuillage"] = m.mat

    m = Noeuds("ecorce")
    stries = m.bruit(1.0, 6, 0.6, m.echelle_vec(14.0, 14.0, 1.2), 1.5)
    m.couleur(m.rampe(stries, [(0.3, (0.03, 0.022, 0.016)), (0.7, (0.09, 0.07, 0.05))]))
    m.rugosite(0.9)
    m.relief(stries, 0.5, 0.03)
    M["ecorce"] = m.mat

    # Objets vivants : rendus par le site, leurs matières ici servent seulement à éclairer la cuisson
    for nom, c, force in (("glyphe", (0.55, 0.32, 1.0), 6.0), ("anneau", (0.85, 0.3, 0.95), 2.5),
                          ("cristal_vert", (0.25, 1.0, 0.55), 5.0), ("cristal_violet", (0.6, 0.35, 1.0), 5.0),
                          ("cristal_rose", (1.0, 0.35, 0.75), 5.0)):
        m = Noeuds(nom)
        m.couleur(c)
        m.emission(c, force)
        M[nom] = m.mat
    return M


# =========================================================================
#  CONSTRUCTEUR DE MAILLAGES
# =========================================================================

def collection(nom, parent=None, taille=None):
    c = bpy.data.collections.get(nom) or bpy.data.collections.new(nom)
    if c.name not in (parent or bpy.context.scene.collection).children:
        (parent or bpy.context.scene.collection).children.link(c)
    if taille:
        c["taille"] = taille
    return c


class Construction:
    """Accumule des pièces (boîtes, cylindres, sphères bosselées) dans un seul maillage."""

    def __init__(self, nom, coll, M):
        self.nom, self.coll, self.M = nom, coll, M
        self.bm = bmesh.new()
        self.teinte = self.bm.verts.layers.float_color.new("teinte")
        self.mats = []

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
        for v in verts:
            v[self.teinte] = (*couleur, 1.0)
        return faces

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

    def objet(self, **props):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
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


def repere(x, y, z, rz=0.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, "Z")


def orientation(m_local, x, y, z, rx=0.0, ry=0.0, rz=0.0):
    return m_local @ Matrix.Translation((x, y, z)) @ (Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(ry, 4, "Y")
                                                      @ Matrix.Rotation(rx, 4, "X"))


def vers(dx, dy):
    """Rotation autour de Z pour que l'avant d'un bâtiment (son -Y local) regarde dans la direction (dx, dy)."""
    return math.atan2(dx, -dy)


# =========================================================================
#  L'ÎLE
# =========================================================================

NB_ANNEAUX, NB_SECTEURS, NB_ETAGES = 104, 384, 64


def construire_ile(M, c_terrain, c_roche):
    t0 = time.time()
    # --- Dessus : grille polaire, du centre jusqu'au bord, puis une lèvre d'herbe qui retombe
    verts, masque, faces = [], [], []
    verts.append((0.0, 0.0, hauteur(0, 0, masque_chemin(0, 0))))
    masque.append(masque_chemin(0, 0))
    bords = []
    for i in range(NB_SECTEURS):
        th = 2 * math.pi * i / NB_SECTEURS
        bords.append(rayon_bord(th))
    for j in range(1, NB_ANNEAUX + 2):
        for i in range(NB_SECTEURS):
            th = 2 * math.pi * i / NB_SECTEURS
            if j <= NB_ANNEAUX:
                rr = bords[i] * (j / NB_ANNEAUX) ** 0.92
                x, y = rr * math.cos(th), rr * math.sin(th)
                mc = masque_chemin(x, y)
                z = hauteur(x, y, mc)
            else:
                rr = bords[i] + 0.35
                x, y = rr * math.cos(th), rr * math.sin(th)
                mc = 0.0
                z = hauteur(bords[i] * math.cos(th), bords[i] * math.sin(th)) - 0.55
            verts.append((x, y, z))
            masque.append(mc)
    def idx(j, i):
        return 0 if j == 0 else 1 + (j - 1) * NB_SECTEURS + (i % NB_SECTEURS)
    for i in range(NB_SECTEURS):
        faces.append((0, idx(1, i), idx(1, i + 1)))
    for j in range(1, NB_ANNEAUX + 1):
        for i in range(NB_SECTEURS):
            faces.append((idx(j, i), idx(j + 1, i), idx(j + 1, i + 1), idx(j, i + 1)))
    me = bpy.data.meshes.new("ile_dessus")
    me.from_pydata(verts, [], faces)
    me.materials.append(M["herbe"])
    attr = me.color_attributes.new("chemin", "FLOAT_COLOR", "POINT")
    attr.data.foreach_set("color", [c for mval in masque for c in (mval, mval, mval, 1.0)])
    attr = me.color_attributes.new("teinte", "FLOAT_COLOR", "POINT")
    attr.data.foreach_set("color", [1.0] * (4 * len(verts)))
    me.shade_smooth()
    ob = bpy.data.objects.new("ile_dessus", me)
    c_terrain.objects.link(ob)
    log(f"dessus de l'île : {len(verts)} sommets ({time.time() - t0:.1f} s)")

    # --- Dessous : falaise puis rocher qui s'effile vers une pointe, en strates
    t0 = time.time()
    verts, faces = [], []
    pointe = Vector((3.0, -2.0, -34.0))
    for k in range(NB_ETAGES):
        t = k / NB_ETAGES
        for i in range(NB_SECTEURS):
            th = 2 * math.pi * i / NB_SECTEURS
            rb = bords[i]
            z_bord = hauteur(rb * math.cos(th), rb * math.sin(th)) - 0.45
            if t < 0.09:
                f = 0.99 - 0.25 * t
                z = z_bord - 0.15 - t / 0.09 * 3.05
            else:
                u = (t - 0.09) / 0.91
                f = 0.98 * (1.0 - u) ** 0.72
                z = z_bord - 3.2 - u ** 0.95 * (abs(pointe.z) + z_bord - 3.2 + 4 * n3(math.cos(th), math.sin(th), 3.0))
            cx, cy = lerp(0, pointe.x, t * t), lerp(0, pointe.y, t * t)
            x, y = cx + rb * f * math.cos(th), cy + rb * f * math.sin(th)
            p = Vector((x, y, z))
            ampl = 0.2 + 3.3 * smoothstep(0.0, 0.6, t) * (1.0 - smoothstep(0.85, 1.0, t))
            radial = Vector((math.cos(th), math.sin(th), 0.0))
            depl = ampl * fbm3(p * Vector((0.09, 0.09, 0.16)), 5)
            depl += 0.28 * math.sin(z * 1.7 + 4.0 * n3(x * 0.08, y * 0.08, 7.0)) * smoothstep(0.02, 0.2, t)
            depl += 0.6 * abs(n3(x * 0.35, y * 0.35, z * 0.5)) * smoothstep(0.0, 0.1, t)
            p += radial * depl
            verts.append(tuple(p))
    verts.append(tuple(pointe))
    for k in range(NB_ETAGES - 1):
        for i in range(NB_SECTEURS):
            a = k * NB_SECTEURS + i
            b = k * NB_SECTEURS + (i + 1) % NB_SECTEURS
            faces.append((a, a + NB_SECTEURS, b + NB_SECTEURS, b))
    dernier = (NB_ETAGES - 1) * NB_SECTEURS
    for i in range(NB_SECTEURS):
        faces.append((dernier + (i + 1) % NB_SECTEURS, dernier + i, len(verts) - 1))
    me = bpy.data.meshes.new("ile_roche")
    me.from_pydata(verts, [], faces)
    me.materials.append(M["roche"])
    attr = me.color_attributes.new("teinte", "FLOAT_COLOR", "POINT")
    attr.data.foreach_set("color", [1.0] * (4 * len(verts)))
    me.shade_smooth()
    ob = bpy.data.objects.new("ile_roche", me)
    c_roche.objects.link(ob)
    log(f"dessous de l'île : {len(verts)} sommets ({time.time() - t0:.1f} s)")


def rochers_flottants(M, c_roche, rnd):
    places = [(-46, -18, 4, 3.2), (-38, 30, -6, 2.4), (8, 48, 2, 3.6), (44, -26, -3, 2.8),
              (-20, -46, -10, 2.0), (52, 14, 8, 1.6), (-54, 6, 12, 1.4), (30, -44, 6, 1.8)]
    for n, (x, y, z, r) in enumerate(places):
        c = Construction(f"rocher_flottant_{n + 1}", c_roche, M)
        centre = Vector((x, y, z))
        m = Matrix.Translation(centre) @ Matrix.Diagonal((1.0, 1.0, 0.75, 1.0))
        v = c.sphere("roche", m, r, 3)
        # Dessus aplati, dessous en pointe
        for vv in v:
            d = vv.co - centre
            if d.z > 0:
                vv.co.z = centre.z + d.z * 0.35
            else:
                vv.co.z = centre.z + d.z * (1.6 + 0.6 * rnd.random())
        c.bosseler(v, centre, r * 0.22, 0.9 / r, rnd.random() * 50)
        c.objet(mobile=1, flotte=round(0.25 + rnd.random() * 0.35, 2))


# =========================================================================
#  BÂTIMENTS
# =========================================================================

def construire_arche(M, coll, vivant, rnd):
    x, y, _ = SITES["arche"]
    z0 = HAUTEUR_SITE["arche"]
    L = repere(x, y, z0, 0.0)
    c = Construction("arche", coll, M)
    for cote in (-1, 1):
        px = cote * 2.05
        c.boite("pierre", orientation(L, px, 0, 0.1), (1.25, 1.2, 0.6), 0.05, (0.9, 0.88, 0.85))
        zb = 0.4
        for k in range(6):
            h = 0.5
            t = 0.86 + 0.08 * rnd.random()
            c.boite("pierre", orientation(L, px + rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), zb + h / 2,
                                          rz=rnd.uniform(-0.05, 0.05)), (0.86, 0.86, h - 0.03), 0.045, (t, t, t * 0.97))
            zb += h
        c.boite("pierre", orientation(L, px, 0, zb + 0.13), (1.05, 1.0, 0.26), 0.04)
        # Muret en ruine qui prolonge l'arche
        for k in range(4):
            lx = px + cote * (1.0 + k * 0.8)
            hauteur_muret = 1.2 - k * 0.25 + rnd.uniform(-0.1, 0.1)
            for etage in range(max(1, int(hauteur_muret / 0.4))):
                t = 0.8 + 0.15 * rnd.random()
                c.boite("pierre", orientation(L, lx + rnd.uniform(-0.05, 0.05), rnd.uniform(-0.06, 0.06),
                                              0.0 + etage * 0.4 + 0.2, rz=rnd.uniform(-0.08, 0.08)),
                        (0.76, 0.6, 0.38), 0.05, (t, t * 0.98, t * 0.95))
    zc = 3.66
    n = 9
    for i in range(n):
        a = math.pi * (i + 0.5) / n
        rr = 2.05
        cle = i == n // 2
        X = Vector((math.sin(a), 0, -math.cos(a)))
        Y = Vector((0, 1, 0))
        Z = Vector((math.cos(a), 0, math.sin(a)))
        R = Matrix((X, Y, Z)).transposed().to_4x4()
        m = L @ Matrix.Translation((rr * math.cos(a), 0, zc + rr * math.sin(a) + (0.05 if cle else 0))) @ R
        c.boite("pierre", m, (0.66, 0.92 if cle else 0.86, 0.72 if cle else 0.6), 0.04, (0.95, 0.93, 0.9))
    # Lanternes de part et d'autre
    for cote in (-1, 1):
        lx, ly = cote * 3.3, -1.3
        c.cylindre("bois_sombre", orientation(L, lx, ly, 0.75), 0.06, 0.05, 1.5, 8)
        c.boite("metal", orientation(L, lx, ly, 1.55), (0.26, 0.26, 0.04))
        c.sphere("lumiere", orientation(L, lx, ly, 1.68), 0.1, 2)
        c.boite("metal", orientation(L, lx, ly, 1.86), (0.3, 0.3, 0.05))
        ancre(vivant, f"lanterne_arche_{1 if cote < 0 else 2}", L @ Vector((lx, ly, 1.68)))
    c.objet()


def construire_atelier(M, coll, vivant, rnd):
    x, y, _ = SITES["atelier"]
    z0 = HAUTEUR_SITE["atelier"]
    L = repere(x, y, z0, vers(5.0, -1.8))
    c = Construction("atelier", coll, M)
    larg, prof, hmur = 6.0, 4.4, 2.6
    base = 0.45
    c.boite("pierre", orientation(L, 0, 0, base / 2 - 0.25), (larg + 0.5, prof + 0.5, base + 0.5), 0.06)
    # Murs en planches verticales (une teinte par planche)
    zb = base
    for cote in (-1, 1):
        n = int(larg / 0.3)
        for k in range(n):
            t = 0.75 + 0.35 * rnd.random()
            px = -larg / 2 + (k + 0.5) * larg / n
            c.boite("bois", orientation(L, px, cote * prof / 2, zb + hmur / 2), (larg / n - 0.015, 0.09, hmur),
                    0.0, (t, t * 0.95, t * 0.9))
        n = int(prof / 0.3)
        for k in range(n):
            t = 0.75 + 0.35 * rnd.random()
            py = -prof / 2 + (k + 0.5) * prof / n
            c.boite("bois", orientation(L, cote * larg / 2, py, zb + hmur / 2), (0.09, prof / n - 0.015, hmur),
                    0.0, (t, t * 0.95, t * 0.9))
    for cx in (-1, 1):
        for cy in (-1, 1):
            c.boite("bois_sombre", orientation(L, cx * larg / 2, cy * prof / 2, zb + hmur / 2), (0.24, 0.24, hmur + 0.1), 0.02)
    for cy in (-1, 1):
        c.boite("bois_sombre", orientation(L, 0, cy * prof / 2, zb + hmur - 0.1), (larg + 0.2, 0.2, 0.2), 0.02)
    # Pignons
    zt = zb + hmur
    faitage = 1.8
    for cx in (-1, 1):
        c.prisme("bois", [(-prof / 2, zt), (prof / 2, zt), (0, zt + faitage)], cx * larg / 2 - 0.05,
                 cx * larg / 2 + 0.05, L, (0.85, 0.82, 0.78))
    # Toit en deux pans
    debord = 0.45
    pente = math.atan2(faitage, prof / 2)
    long_pan = (prof / 2 + debord) / math.cos(pente)
    for cy in (-1, 1):
        cy_c = cy * (prof / 2 + debord) / 2
        cz = zt + faitage - (prof / 2 + debord) / 2 * math.tan(pente) + 0.1
        c.boite("toit", orientation(L, 0, cy_c, cz, rx=cy * pente), (larg + 0.9, long_pan + 0.05, 0.16), 0.02)
    c.boite("bois_sombre", orientation(L, 0, 0, zt + faitage + 0.16), (larg + 1.0, 0.22, 0.2), 0.03)
    # Cheminée qui fume (ancre pour la fumée)
    c.boite("pierre", orientation(L, 1.7, 0.9, zt + 1.6), (0.65, 0.65, 2.3), 0.04)
    c.boite("pierre", orientation(L, 1.7, 0.9, zt + 2.8), (0.8, 0.8, 0.14), 0.03)
    ancre(vivant, "fumee", L @ Vector((1.7, 0.9, zt + 3.0)))
    # Fenêtres allumées et porte sur la façade avant (-Y)
    def fenetre(px, py, face_y, lx=0.95, lz=1.05, cz=1.55):
        # Le mur fait 9 cm d'épaisseur : la vitre et le cadre dépassent de sa face extérieure
        dy = face_y * 0.06
        c.boite("lumiere", orientation(L, px, py + dy, zb + cz), (lx, 0.04, lz))
        for s in (-1, 1):
            c.boite("bois_sombre", orientation(L, px + s * lx / 2, py + dy * 1.5, zb + cz), (0.1, 0.12, lz + 0.1))
            c.boite("bois_sombre", orientation(L, px, py + dy * 1.5, zb + cz + s * lz / 2), (lx + 0.1, 0.12, 0.1))
        c.boite("bois_sombre", orientation(L, px, py + dy * 1.3, zb + cz), (0.05, 0.1, lz))
        c.boite("bois_sombre", orientation(L, px, py + dy * 1.3, zb + cz), (lx, 0.1, 0.05))
        c.boite("bois", orientation(L, px, py + dy * 2.8, zb + cz - lz / 2 - 0.12), (lx + 0.3, 0.3, 0.12), 0.02)
    fenetre(-1.6, -prof / 2, -1)
    fenetre(1.7, -prof / 2, -1)
    fenetre(-1.2, prof / 2, 1)
    # Porte
    c.boite("bois_sombre", orientation(L, 0.05, -prof / 2 - 0.06, zb + 1.0), (1.0, 0.08, 2.0), 0.02, (0.9, 0.9, 0.9))
    for s in (-1, 1):
        c.boite("bois", orientation(L, 0.05 + s * 0.56, -prof / 2 - 0.09, zb + 1.05), (0.12, 0.1, 2.15))
    c.boite("bois", orientation(L, 0.05, -prof / 2 - 0.09, zb + 2.15), (1.25, 0.12, 0.12))
    c.sphere("metal", orientation(L, 0.4, -prof / 2 - 0.13, zb + 1.0), 0.04, 1)
    # Marche, lanterne, banc, tonneaux, caisses
    c.boite("pierre", orientation(L, 0.05, -prof / 2 - 0.45, base - 0.12), (1.6, 0.7, 0.24), 0.04)
    c.boite("metal", orientation(L, 0.85, -prof / 2 - 0.25, zb + 2.25), (0.05, 0.4, 0.05))
    c.sphere("lumiere", orientation(L, 0.85, -prof / 2 - 0.42, zb + 2.0), 0.09, 2)
    c.boite("metal", orientation(L, 0.85, -prof / 2 - 0.42, zb + 2.16), (0.22, 0.22, 0.04))
    ancre(vivant, "lanterne_atelier", L @ Vector((0.85, -prof / 2 - 0.42, zb + 2.0)))
    c.boite("bois", orientation(L, -1.6, -prof / 2 - 0.55, base + 0.0), (1.5, 0.38, 0.07), 0.015)
    for s in (-1, 1):
        c.boite("bois_sombre", orientation(L, -1.6 + s * 0.62, -prof / 2 - 0.55, base - 0.22), (0.08, 0.32, 0.42))
    for k, (bx, by) in enumerate(((larg / 2 + 0.55, -1.2), (larg / 2 + 0.6, -0.4), (larg / 2 + 0.5, 0.9))):
        v = c.cylindre("bois", orientation(L, bx, by, base - 0.25 + 0.45), 0.3, 0.3, 0.9, 14, (0.8, 0.75, 0.7))
        for vv in v:
            local = L.inverted() @ vv.co
            hz = (local.z - (base - 0.25 + 0.45)) / 0.45
            vv.co = L @ Vector((bx + (local.x - bx) * (1.0 + 0.12 * (1 - hz * hz)),
                                by + (local.y - by) * (1.0 + 0.12 * (1 - hz * hz)), local.z))
        if k < 2:
            c.cylindre("metal", orientation(L, bx, by, base - 0.25 + 0.2), 0.335, 0.335, 0.05, 14)
            c.cylindre("metal", orientation(L, bx, by, base - 0.25 + 0.7), 0.335, 0.335, 0.05, 14)
    c.boite("bois", orientation(L, -larg / 2 - 0.6, -1.0, base - 0.05, rz=0.2), (0.7, 0.7, 0.6), 0.03, (0.9, 0.8, 0.7))
    c.boite("bois", orientation(L, -larg / 2 - 0.55, -0.9, base + 0.5, rz=-0.15), (0.5, 0.5, 0.45), 0.03, (0.8, 0.75, 0.65))
    # Parabole et antenne sur le toit (un clin d'œil aux réseaux et à l'IoT)
    ax, ay = -1.9, 0.6
    az = zt + faitage - (0.6) * math.tan(pente)
    c.cylindre("metal", orientation(L, ax, ay, az + 0.6), 0.03, 0.03, 1.4, 8)
    c.cylindre("metal", orientation(L, ax + 0.9, -0.2, az + 0.9), 0.015, 0.01, 2.2, 6)
    disque = orientation(L, ax, ay - 0.15, az + 1.1, rx=math.radians(-60))
    c.demi_sphere("cuivre", disque @ Matrix.Diagonal((0.45, 0.45, 0.16, 1)), 1.0)
    # Clôture le long du chemin
    for k in range(7):
        px = larg / 2 + 1.6
        py = -prof / 2 - 1.2 + k * 1.15
        hv = 1.05 + rnd.uniform(-0.05, 0.05)
        c.boite("bois", orientation(L, px, py, base - 0.3 + hv / 2, rz=rnd.uniform(-0.1, 0.1)), (0.11, 0.11, hv), 0.015,
                (0.7, 0.68, 0.62))
        if k < 6:
            for hz in (0.45, 0.85):
                c.boite("bois", orientation(L, px, py + 0.575, base - 0.3 + hz, rx=rnd.uniform(-0.03, 0.03)),
                        (0.06, 1.15, 0.08), 0.01, (0.75, 0.72, 0.65))
    c.objet()


def construire_cercle(M, coll, vivant, rnd):
    cx, cy, _ = SITES["cercle"]
    z0 = HAUTEUR_SITE["cercle"]
    c = Construction("cercle", coll, M)
    # Dalle centrale et anneau lumineux (vivant)
    c.cylindre("pierre", repere(cx, cy, z0 + 0.05), 1.9, 1.85, 0.4, 40, (0.9, 0.88, 0.85))
    c.cylindre("pierre", repere(cx, cy, z0 + 0.3), 1.3, 1.25, 0.12, 40)
    for k in range(14):
        a = 2 * math.pi * k / 14
        c.boite("pierre", repere(cx + 2.6 * math.cos(a), cy + 2.6 * math.sin(a), z0 - 0.05, a),
                (0.5, 1.05, 0.14), 0.03, (0.8 + 0.15 * rnd.random(),) * 3)
    a = Construction("vivant_anneau", vivant, M)
    a.tore("anneau", repere(cx, cy, z0 + 0.38), 1.05, 0.035)
    a.tore("anneau", repere(cx, cy, z0 + 0.38), 0.62, 0.025, 48)
    a.objet(vivant="anneau")
    # Sept menhirs, un par famille de compétences, chacun avec un glyphe lumineux tourné vers le centre
    n = 7
    for k in range(n):
        ang = math.radians(150) + 2 * math.pi * (k + 0.5) / n
        rr = 5.0
        px, py = cx + rr * math.cos(ang), cy + rr * math.sin(ang)
        h = 2.6 + 0.8 * rnd.random()
        m = repere(px, py, z0 + h / 2 - 0.3, ang + math.pi / 2) @ Matrix.Rotation(rnd.uniform(-0.06, 0.06), 4, "X") \
            @ Matrix.Rotation(rnd.uniform(-0.05, 0.05), 4, "Y")
        # Les sommets déjà construits sont marqués : seuls ceux du nouveau menhir seront déformés
        for vv in c.bm.verts:
            vv.tag = True
        v = c.boite("pierre", m, (1.0, 0.62, h), 0.0, (0.85 + 0.15 * rnd.random(),) * 3)
        faces = list({f for vv in v for f in vv.link_faces})
        bmesh.ops.subdivide_edges(c.bm, edges=list({e for f in faces for e in f.edges}), cuts=5, use_grid_fill=True)
        tous = [vv for vv in c.bm.verts if not vv.tag]
        centre = m.to_translation()
        for vv in tous:
            lz = (vv.co - centre).dot(m.to_3x3() @ Vector((0, 0, 1))) / h + 0.5
            haut = m.to_3x3() @ Vector((0, 0, 1))
            d = vv.co - centre
            horiz = d - haut * d.dot(haut)
            vv.co -= horiz * (0.28 * lz * lz)
            if lz > 0.85:
                vv.co -= haut * (lz - 0.85) * 0.9 * (horiz.length / 0.5) ** 2
            vv.co += (d.normalized() if d.length > 0 else d) * 0.07 * fbm3(vv.co * 1.3 + Vector((k * 9.0, 0, 0)), 3)
            vv[c.teinte] = (0.85 + 0.1 * math.sin(k * 3.1),) * 3 + (1.0,)
        for f in {f for vv in tous for f in vv.link_faces}:
            f.smooth = True
        # Glyphe : posé sur la face intérieure, trouvée en lançant un rayon depuis le centre du cercle
        c.bm.normal_update()
        arbre = BVHTree.FromBMesh(c.bm)
        origine = Vector((cx, cy, z0 + 1.55))
        cible = Vector((px, py, z0 + 1.55))
        hit, nrm, _, _ = arbre.ray_cast(origine, (cible - origine).normalized(), 10.0)
        if hit is None:
            continue
        g = Construction(f"vivant_glyphe_{k + 1}", vivant, M)
        X = Vector((0, 0, 1)).cross(nrm).normalized()
        Z = nrm.normalized()
        Y = Z.cross(X)
        G = Matrix.Translation(hit + nrm * 0.012) @ Matrix((X, Y, Z)).transposed().to_4x4()
        motif = k % 4
        if motif == 0:
            for s in range(10):
                a2 = 2 * math.pi * s / 10
                g.boite("glyphe", G @ Matrix.Translation((0.2 * math.cos(a2), 0.2 * math.sin(a2), 0)) @ Matrix.Rotation(a2, 4, "Z"),
                        (0.05, 0.13, 0.03))
            g.boite("glyphe", G, (0.05, 0.22, 0.03))
        elif motif == 1:
            for s, l in ((-0.16, 0.18), (0.0, 0.34), (0.16, 0.18)):
                g.boite("glyphe", G @ Matrix.Translation((0, s, 0)), (l, 0.05, 0.03))
            g.boite("glyphe", G @ Matrix.Translation((0, 0, 0)), (0.05, 0.4, 0.03))
        elif motif == 2:
            for s in range(3):
                a2 = 2 * math.pi * s / 3 + math.pi / 2
                g.boite("glyphe", G @ Matrix.Translation((0.11 * math.cos(a2 + math.pi / 3) * 1.0, 0.11 * math.sin(a2 + math.pi / 3), 0))
                        @ Matrix.Rotation(a2 + math.pi / 3 + math.pi / 2, 4, "Z"), (0.36, 0.05, 0.03))
            g.boite("glyphe", G, (0.07, 0.07, 0.03))
        else:
            g.boite("glyphe", G @ Matrix.Translation((-0.08, 0, 0)) @ Matrix.Rotation(0.5, 4, "Z"), (0.05, 0.38, 0.03))
            g.boite("glyphe", G @ Matrix.Translation((0.08, 0, 0)) @ Matrix.Rotation(-0.5, 4, "Z"), (0.05, 0.38, 0.03))
            g.boite("glyphe", G @ Matrix.Translation((0, -0.2, 0)), (0.3, 0.05, 0.03))
        g.objet(vivant="glyphe", rang=k)
    c.objet()


def construire_cristaux(M, coll, vivant, rnd):
    sx, sy, _ = SITES["cristaux"]
    z0 = HAUTEUR_SITE["cristaux"]
    c = Construction("socles", coll, M)
    face = Vector((-6.5, 7.0)).normalized()          # vers le point de vue de la caméra
    perp = Vector((face.y, -face.x))
    couleurs = (("cristal_vert", "ecopay"), ("cristal_violet", "boutik"), ("cristal_rose", "monde"))
    for k, (mat, nom) in enumerate(couleurs):
        off = (k - 1) * 2.3
        recul = 0.6 if k == 1 else 0.0
        px, py = sx + perp.x * off - face.x * recul, sy + perp.y * off - face.y * recul
        hc = 1.05 + (0.25 if k == 1 else 0.0)
        c.cylindre("pierre", repere(px, py, z0 + 0.05), 0.62, 0.58, 0.3, 24, (0.9, 0.88, 0.85))
        c.cylindre("pierre", repere(px, py, z0 + 0.2 + hc / 2), 0.36, 0.3, hc, 16)
        c.cylindre("pierre", repere(px, py, z0 + 0.25 + hc), 0.52, 0.48, 0.14, 24)
        for s in range(3):
            a = rnd.random() * 2 * math.pi
            v = c.sphere("roche", repere(px + 0.85 * math.cos(a), py + 0.85 * math.sin(a), z0 + 0.0), 0.18 + 0.12 * rnd.random(), 2)
            c.bosseler(v, Vector((px + 0.85 * math.cos(a), py + 0.85 * math.sin(a), z0)), 0.05, 3.0, rnd.random() * 9)
        g = Construction(f"vivant_cristal_{k + 1}", vivant, M)
        cz = z0 + 0.32 + hc + 0.95
        centre = Vector((px, py, cz))
        bas = g.bm.verts.new(centre + Vector((0, 0, -0.5)))
        haut = g.bm.verts.new(centre + Vector((0, 0, 0.62)))
        anneau = [g.bm.verts.new(centre + Vector((0.24 * math.cos(2 * math.pi * s / 6), 0.24 * math.sin(2 * math.pi * s / 6), 0.06)))
                  for s in range(6)]
        for s in range(6):
            g.bm.faces.new((anneau[s], anneau[(s + 1) % 6], haut))
            g.bm.faces.new((anneau[(s + 1) % 6], anneau[s], bas))
        g._finir([bas, haut] + anneau, mat)
        for f in g.bm.faces:
            f.smooth = False
        g.objet(vivant="cristal", projet=nom, rang=k)
    c.objet()


def construire_phare(M, coll, vivant, rnd):
    px, py, _ = SITES["phare"]
    z0 = HAUTEUR_SITE["phare"]
    L = repere(px, py, z0, vers(-1.0, -1.1))
    c = Construction("phare", coll, M)
    c.cylindre("pierre", orientation(L, 0, 0, 0.1), 2.3, 2.2, 1.0, 32)
    hauteur_tour = 10.0
    tranches = 6
    for k in range(tranches):
        z1, z2 = 0.6 + hauteur_tour * k / tranches, 0.6 + hauteur_tour * (k + 1) / tranches
        r1 = lerp(1.7, 1.15, k / tranches)
        r2 = lerp(1.7, 1.15, (k + 1) / tranches)
        c.cylindre("rouge" if k % 2 else "enduit", orientation(L, 0, 0, (z1 + z2) / 2), r1, r2, z2 - z1 + 0.002, 32)
    zt = 0.6 + hauteur_tour
    c.cylindre("pierre", orientation(L, 0, 0, zt + 0.1), 1.75, 1.75, 0.22, 32)
    for k in range(18):
        a = 2 * math.pi * k / 18
        c.cylindre("metal", orientation(L, 1.62 * math.cos(a), 1.62 * math.sin(a), zt + 0.7), 0.025, 0.025, 1.0, 6)
    c.cylindre("metal", orientation(L, 0, 0, zt + 1.2), 1.66, 1.66, 0.05, 32)
    c.cylindre("metal", orientation(L, 0, 0, zt + 0.25), 1.0, 1.0, 0.1, 24)
    c.cylindre("lumiere_phare", orientation(L, 0, 0, zt + 1.0), 0.88, 0.88, 1.4, 16)
    for k in range(8):
        a = 2 * math.pi * k / 8
        c.boite("metal", orientation(L, 0.9 * math.cos(a), 0.9 * math.sin(a), zt + 1.0, rz=a), (0.06, 0.08, 1.45))
    c.cylindre("metal", orientation(L, 0, 0, zt + 1.75), 1.0, 1.0, 0.1, 24)
    c.demi_sphere("rouge", orientation(L, 0, 0, zt + 1.78), 1.02)
    c.cylindre("metal", orientation(L, 0, 0, zt + 3.05), 0.06, 0.02, 0.6, 8)
    c.sphere("metal", orientation(L, 0, 0, zt + 2.8), 0.1, 2)
    ancre(vivant, "phare_lampe", L @ Vector((0, 0, zt + 1.0)))
    # Porte et petites fenêtres
    c.boite("bois_sombre", orientation(L, 0, -1.66, 1.6), (0.85, 0.2, 1.8), 0.02)
    c.boite("pierre", orientation(L, 0, -1.72, 2.55), (1.1, 0.25, 0.18), 0.02)
    for k, hz in enumerate((4.2, 6.6, 8.9)):
        a = -math.pi / 2 + (0.5 if k % 2 else -0.4)
        rr = lerp(1.7, 1.15, (hz - 0.6) / hauteur_tour)
        c.boite("lumiere" if k == 1 else "metal", orientation(L, rr * math.cos(a), rr * math.sin(a), hz, rz=a + math.pi / 2),
                (0.35, 0.12, 0.55))
    # Muret de pierres sèches autour
    for k in range(26):
        a = math.radians(60) + 2 * math.pi * k / 34
        rr = 4.1 + rnd.uniform(-0.1, 0.1)
        t = 0.75 + 0.2 * rnd.random()
        c.boite("pierre", orientation(L, rr * math.cos(a), rr * math.sin(a), 0.2 + rnd.uniform(0, 0.05), rz=a + rnd.uniform(-0.2, 0.2)),
                (0.55, 0.8, 0.5), 0.06, (t, t, t))
    c.objet()


def ancre(coll, nom, pos):
    e = bpy.data.objects.new(nom, None)
    e.empty_display_type = "SPHERE"
    e.empty_display_size = 0.3
    e.location = pos
    coll.objects.link(e)
    return e


# =========================================================================
#  VÉGÉTATION
# =========================================================================

def arbre_feuillu(c, x, y, z, rnd, echelle):
    h = (3.2 + 1.4 * rnd.random()) * echelle
    pench = Vector((rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), 1.0)).normalized()
    m = Matrix.Translation((x, y, z + h / 2 - 0.2)) @ pench.to_track_quat("Z", "Y").to_matrix().to_4x4()
    c.cylindre("ecorce", m, 0.24 * echelle, 0.13 * echelle, h, 9)
    sommet = Vector((x, y, z - 0.2)) + pench * h
    for b in range(3):
        a = rnd.random() * 2 * math.pi
        d = Vector((math.cos(a), math.sin(a), 0.9)).normalized()
        base = Vector((x, y, z)) + pench * h * (0.55 + 0.15 * b)
        mb = Matrix.Translation(base + d * 0.6 * echelle) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        c.cylindre("ecorce", mb, 0.09 * echelle, 0.05 * echelle, 1.3 * echelle, 6)
    teinte_arbre = (lerp(0.13, 0.24, rnd.random()), lerp(0.19, 0.28, rnd.random()), lerp(0.04, 0.07, rnd.random()))
    rayon = (1.8 + 0.5 * rnd.random()) * echelle
    # Une couronne faite de nombreuses touffes : plus légère qu'une grosse boule
    for k in range(13):
        a = rnd.random() * 2 * math.pi
        e = rnd.random() ** 0.6
        off = Vector((math.cos(a) * rayon * 0.75 * e, math.sin(a) * rayon * 0.75 * e,
                      (rnd.random() - 0.35) * rayon * 0.8))
        centre = sommet + off
        r = rayon * (0.38 + 0.22 * rnd.random()) * (1.0 - 0.25 * e)
        v = c.sphere("feuillage", Matrix.Translation(centre) @ Matrix.Diagonal((1, 1, 0.85, 1)), r, 2, teinte_arbre)
        c.bosseler(v, centre, r * 0.2, 2.4 / r, rnd.random() * 99)


def arbre_conifere(c, x, y, z, rnd, echelle):
    h = (5.0 + 2.5 * rnd.random()) * echelle
    c.cylindre("ecorce", Matrix.Translation((x, y, z + h * 0.25)), 0.2 * echelle, 0.12 * echelle, h * 0.6, 8)
    teinte_arbre = (lerp(0.04, 0.07, rnd.random()), lerp(0.09, 0.13, rnd.random()), lerp(0.04, 0.06, rnd.random()))
    etages = 5
    for k in range(etages):
        t = k / etages
        r = (1.75 - 1.35 * t) * echelle
        hz = z + h * (0.18 + 0.72 * t)
        hc = h * 0.34
        m = Matrix.Translation((x, y, hz + hc / 2)) @ Matrix.Rotation(rnd.random() * 6.28, 4, "Z")
        v = c.cylindre("feuillage", m, r, 0.02, hc, 11, teinte_arbre)
        c.bosseler(v, Vector((x, y, hz + hc * 0.3)), r * 0.16, 2.2 / max(r, 0.3), rnd.random() * 99)


def cypres(c, x, y, z, rnd, echelle):
    h = (6.0 + 2.5 * rnd.random()) * echelle
    r = (0.8 + 0.25 * rnd.random()) * echelle
    teinte_arbre = (lerp(0.05, 0.08, rnd.random()), lerp(0.1, 0.13, rnd.random()), lerp(0.04, 0.05, rnd.random()))
    centre = Vector((x, y, z + h * 0.5))
    v = c.sphere("feuillage", Matrix.Translation(centre) @ Matrix.Diagonal((r, r, h * 0.5, 1)), 1.0, 3, teinte_arbre)
    for vv in v:
        lz = max(0.0, min(1.0, (vv.co.z - z) / h))
        d = Vector((vv.co.x - x, vv.co.y - y, 0))
        k = (1.0 - 0.55 * lz ** 1.5) * (1.12 if lz < 0.2 else 1.0)
        vv.co.x = x + d.x * k
        vv.co.y = y + d.y * k
    c.bosseler(v, centre, r * 0.22, 2.4, rnd.random() * 99)
    c.cylindre("ecorce", Matrix.Translation((x, y, z + 0.3)), 0.14 * echelle, 0.12 * echelle, 0.9, 7)


def buisson(c, x, y, z, rnd):
    t = (lerp(0.09, 0.18, rnd.random()), lerp(0.14, 0.2, rnd.random()), lerp(0.03, 0.05, rnd.random()))
    for k in range(2 + int(rnd.random() * 3)):
        r = 0.35 + 0.4 * rnd.random()
        centre = Vector((x + rnd.uniform(-0.6, 0.6), y + rnd.uniform(-0.6, 0.6), z + r * 0.35))
        v = c.sphere("feuillage", Matrix.Translation(centre) @ Matrix.Diagonal((1, 1, 0.75, 1)), r, 2, t)
        c.bosseler(v, centre, r * 0.28, 2.2 / r, rnd.random() * 99)


def caillou(c, x, y, z, rnd, r):
    centre = Vector((x, y, z + r * 0.15))
    m = Matrix.Translation(centre) @ Matrix.Rotation(rnd.random() * 6.3, 4, "Z") @ Matrix.Diagonal((1.0, 0.8, 0.55, 1))
    v = c.sphere("roche", m, r, 2 if r < 0.6 else 3, (0.95, 0.9, 0.85))
    c.bosseler(v, centre, r * 0.3, 1.2 / r, rnd.random() * 99)


def construire_vegetation(M, coll_veg, coll_roche, rnd, couloir, vues):
    def libre(x, y, marge):
        # Rien ne pousse entre la caméra et ce qu'elle regarde à chaque chapitre
        for (ax, ay), (bx, by) in vues:
            if dist_segment(x, y, ax, ay, bx, by) < 2.6 + marge:
                return False
        r = math.hypot(x, y)
        if r > rayon_bord(math.atan2(y, x)) - 2.8:
            return False
        if min(dist_polyligne(x, y, CHEMIN), dist_polyligne(x, y, CHEMIN_ATELIER)) < 1.6 + marge * 0.5:
            return False
        for nom, (cx, cy, rr) in SITES.items():
            if math.hypot(x - cx, y - cy) < rr + marge:
                return False
        if dist_polyligne(x, y, couloir) < 3.2 + marge:
            return False
        return True

    def bosquet(x, y):
        a = math.exp(-((x + 16) ** 2 + (y - 14) ** 2) / 90.0)
        b = math.exp(-((x - 12) ** 2 + (y + 18) ** 2) / 60.0)
        c = math.exp(-((x + 20) ** 2 + (y + 14) ** 2) / 50.0)
        d = math.exp(-((x - 4) ** 2 + (y - 22) ** 2) / 50.0)
        return max(a, b, c, d)

    places = []
    essais = 0
    while len(places) < 95 and essais < 20000:
        essais += 1
        a = rnd.random() * 2 * math.pi
        r = math.sqrt(rnd.random()) * 34
        x, y = r * math.cos(a), r * math.sin(a)
        if rnd.random() > 0.12 + 0.88 * bosquet(x, y):
            continue
        if not libre(x, y, 1.0):
            continue
        if any(math.hypot(x - px, y - py) < 2.6 for px, py in places):
            continue
        places.append((x, y))
    feuillus = Construction("arbres", coll_veg, M)
    for k, (x, y) in enumerate(places):
        z = hauteur(x, y)
        e = 0.85 + 0.35 * rnd.random()
        choix = rnd.random()
        if bosquet(x, y) > 0.5 and choix < 0.55:
            arbre_conifere(feuillus, x, y, z, rnd, e)
        elif choix < 0.82:
            arbre_feuillu(feuillus, x, y, z, rnd, e)
        else:
            cypres(feuillus, x, y, z, rnd, e)
    # Cyprès en alignement près du cercle et du phare
    for x, y in ((-3.5, 15.5), (-0.5, 16.8), (9.5, 13.5), (19.0, 22.5), (26.5, 15.0)):
        if libre(x, y, -1.5):
            cypres(feuillus, x, y, hauteur(x, y), rnd, 1.0)
            places.append((x, y))
    feuillus.objet()
    log(f"arbres : {len(places)}")

    buissons = Construction("buissons", coll_veg, M)
    n = 0
    essais = 0
    while n < 80 and essais < 20000:
        essais += 1
        a = rnd.random() * 2 * math.pi
        r = math.sqrt(rnd.random()) * 33
        x, y = r * math.cos(a), r * math.sin(a)
        if not libre(x, y, -0.8) or any(math.hypot(x - px, y - py) < 1.2 for px, py in places):
            continue
        buisson(buissons, x, y, hauteur(x, y), rnd)
        n += 1
    # Buissons au pied des bâtiments
    for nom, nb in (("atelier", 5), ("arche", 4), ("phare", 4), ("cristaux", 3)):
        cx, cy, rr = SITES[nom]
        for k in range(nb):
            a = rnd.random() * 2 * math.pi
            x, y = cx + (rr - 0.3) * math.cos(a), cy + (rr - 0.3) * math.sin(a)
            if min(dist_polyligne(x, y, CHEMIN), dist_polyligne(x, y, CHEMIN_ATELIER)) > 1.3 and dist_polyligne(x, y, couloir) > 2.0:
                buisson(buissons, x, y, hauteur(x, y), rnd)
    buissons.objet()

    cailloux = Construction("cailloux", coll_roche, M)
    for k in range(70):
        a = rnd.random() * 2 * math.pi
        r = 8 + math.sqrt(rnd.random()) * 26
        x, y = r * math.cos(a), r * math.sin(a)
        if r > rayon_bord(a) - 0.8:
            continue
        if min(dist_polyligne(x, y, CHEMIN), dist_polyligne(x, y, CHEMIN_ATELIER)) < 1.0 or dist_polyligne(x, y, couloir) < 1.5:
            continue
        grand = r > rayon_bord(a) - 5 and rnd.random() < 0.5
        caillou(cailloux, x, y, hauteur(x, y) - 0.1, rnd, (0.7 + 0.9 * rnd.random()) if grand else (0.15 + 0.3 * rnd.random()))
    # Petits cailloux le long du chemin
    for i in range(len(CHEMIN) - 1):
        (ax, ay), (bx, by) = CHEMIN[i], CHEMIN[i + 1]
        for s in range(4):
            t = rnd.random()
            nx, ny = -(by - ay), bx - ax
            l = math.hypot(nx, ny) or 1
            cote = 1 if rnd.random() < 0.5 else -1
            x = lerp(ax, bx, t) + cote * nx / l * (1.25 + 0.3 * rnd.random())
            y = lerp(ay, by, t) + cote * ny / l * (1.25 + 0.3 * rnd.random())
            if math.hypot(x, y) < rayon_bord(math.atan2(y, x)) - 1 and dist_polyligne(x, y, couloir) > 1.2:
                caillou(cailloux, x, y, hauteur(x, y) - 0.05, rnd, 0.12 + 0.18 * rnd.random())
    cailloux.objet()


# =========================================================================
#  TRAJET DE LA CAMÉRA
# =========================================================================

def cles_camera():
    A, B, C, D, E = (HAUTEUR_SITE[n] for n in ("arche", "atelier", "cercle", "cristaux", "phare"))

    def sol(x, y, dz):
        return (x, y, hauteur(x, y) + dz)

    # (position, cible, chapitre). Les clés sans chapitre arrondissent le trajet entre deux chapitres.
    return [
        ((-50.0, -49.0, 15.0), (1.0, 1.0, -5.0), 0),
        ((-30.0, -52.0, A + 7.0), (0.0, -22.0, A + 2.0), None),
        ((0.3, -33.5, A + 1.9), (0.0, -21.0, A + 2.5), 1),
        ((-0.3, -19.8, A + 2.2), (-9.0, -9.0, B + 1.5), None),
        (sol(-5.8, -13.2, 1.8), (-14.0, -6.0, B + 2.1), 2),
        (sol(-10.5, -0.5, 4.0), (2.0, 6.0, C + 0.6), None),
        ((-4.8, 11.8, C + 3.8), (2.0, 5.6, C + 0.9), 3),
        ((5.0, 15.5, C + 6.5), (14.0, -3.0, D + 1.2), None),
        (sol(9.6, 0.4, 1.8), (15.0, -6.0, D + 1.8), 4),
        (sol(10.5, 3.5, 3.2), (22.0, 17.0, E + 5.0), None),
        (sol(11.8, 7.6, 2.4), (23.5, 19.5, E + 6.2), 5),
    ]


def construire_reperes(reperes):
    cles = cles_camera()
    for k, (cam, cible, chap) in enumerate(cles):
        e = ancre(reperes, f"cam_{k:02d}", Vector(cam))
        e["chapitre"] = -1 if chap is None else chap
        ancre(reperes, f"cible_{k:02d}", Vector(cible))
    # Direction du soleil, pour que le ciel du site place son halo au même endroit que la cuisson
    ancre(reperes, "soleil", SOLEIL_DIR * 100.0)
    couloir =[(c[0][0], c[0][1]) for c in cles if c[0][2] < 40 and math.hypot(c[0][0], c[0][1]) < 36]
    vues = [((c[0][0], c[0][1]), (c[1][0], c[1][1])) for c in cles if c[2] and math.hypot(c[0][0], c[0][1]) < 40]
    return couloir, vues


# =========================================================================
#  STUDIO : soleil couchant et ciel
# =========================================================================

def construire_studio(studio):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        log("looks disponibles :", [i.identifier for i in sc.view_settings.bl_rna.properties["look"].enum_items])
    sc.view_settings.exposure = 0.95

    soleil = bpy.data.lights.new("soleil", "SUN")
    soleil.energy = 3.8
    soleil.color = (1.0, 0.6, 0.34)
    soleil.angle = math.radians(1.6)
    ob = bpy.data.objects.new("soleil", soleil)
    ob.rotation_euler = (-SOLEIL_DIR).to_track_quat("-Z", "Y").to_euler()
    studio.objects.link(ob)

    w = bpy.data.worlds.new("ciel")
    sc.world = w
    nt = w.node_tree
    nt.nodes.clear()
    sortie = nt.nodes.new("ShaderNodeOutputWorld")
    fond = nt.nodes.new("ShaderNodeBackground")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    plage = nt.nodes.new("ShaderNodeMapRange")
    nt.links.new(sep.outputs["Z"], plage.inputs[0])
    plage.inputs[1].default_value = -1.0
    plage.inputs[2].default_value = 1.0
    rampe = nt.nodes.new("ShaderNodeValToRGB")
    r = rampe.color_ramp
    arrets = [(0.0, (0.05, 0.03, 0.07)), (0.42, (0.32, 0.17, 0.2)), (0.49, (0.85, 0.45, 0.3)),
              (0.505, (1.0, 0.52, 0.27)), (0.54, (0.78, 0.33, 0.3)), (0.6, (0.38, 0.15, 0.34)),
              (0.72, (0.12, 0.07, 0.22)), (1.0, (0.02, 0.018, 0.06))]
    r.elements[0].position, r.elements[0].color = arrets[0][0], (*arrets[0][1], 1)
    r.elements[1].position, r.elements[1].color = arrets[-1][0], (*arrets[-1][1], 1)
    for p, c in arrets[1:-1]:
        e = r.elements.new(p)
        e.color = (*c, 1)
    nt.links.new(plage.outputs[0], rampe.inputs[0])
    # Halo autour du soleil
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(coord.outputs["Generated"], dot.inputs[0])
    dot.inputs[1].default_value = tuple(SOLEIL_DIR)
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    nt.links.new(dot.outputs["Value"], mx.inputs[0])
    mx.inputs[1].default_value = 0.0
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    nt.links.new(mx.outputs[0], pw.inputs[0])
    pw.inputs[1].default_value = 10.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "ADD"
    mix.inputs[0].default_value = 1.0
    nt.links.new(rampe.outputs[0], mix.inputs[6])
    halo = nt.nodes.new("ShaderNodeMath")
    halo.operation = "MULTIPLY"
    nt.links.new(pw.outputs[0], halo.inputs[0])
    halo.inputs[1].default_value = 1.6
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    for i, k in enumerate((1.0, 0.55, 0.25)):
        m2 = nt.nodes.new("ShaderNodeMath")
        m2.operation = "MULTIPLY"
        nt.links.new(halo.outputs[0], m2.inputs[0])
        m2.inputs[1].default_value = k
        nt.links.new(m2.outputs[0], comb.inputs[i])
    nt.links.new(comb.outputs[0], mix.inputs[7])
    nt.links.new(mix.outputs[2], fond.inputs["Color"])
    fond.inputs["Strength"].default_value = 1.15
    nt.links.new(fond.outputs[0], sortie.inputs[0])


def activer_gpu():
    sc = bpy.context.scene
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for t in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = t
        except TypeError:
            continue
        prefs.get_devices()
        if any(d.type == t for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == t
            sc.cycles.device = "GPU"
            log("Cycles sur", t)
            return
    sc.cycles.device = "CPU"
    log("Cycles sur le processeur")


# =========================================================================
#  ÉTAPES
# =========================================================================

def etape_construire(opts):
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    preparer_plan()
    rnd = random.Random(1209)
    M = creer_matieres()
    racine = bpy.context.scene.collection
    c_terrain = collection("atlas_terrain", racine, 4096)
    c_roche = collection("atlas_roche", racine, 2048)
    c_bat = collection("atlas_batiments", racine, 4096)
    c_veg = collection("atlas_vegetation", racine, 4096)
    vivant = collection("vivant", racine)
    reperes = collection("reperes", racine)
    studio = collection("studio", racine)

    couloir, vues = construire_reperes(reperes)
    construire_ile(M, c_terrain, c_roche)
    rochers_flottants(M, c_roche, rnd)
    construire_arche(M, c_bat, reperes, rnd)
    construire_atelier(M, c_bat, reperes, rnd)
    construire_cercle(M, c_bat, vivant, rnd)
    construire_cristaux(M, c_bat, vivant, rnd)
    construire_phare(M, c_bat, reperes, rnd)
    construire_vegetation(M, c_veg, c_roche, rnd, couloir, vues)
    construire_studio(studio)

    total = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
    log(f"scène construite : {total} faces, {time.time() - t0:.1f} s")
    os.makedirs(SORTIE_BLEND, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SORTIE_BLEND, "ile.blend"), compress=True)


def camera_chapitre(k):
    sc = bpy.context.scene
    cam = bpy.data.objects.get("camera_apercu")
    if cam is None:
        cam = bpy.data.objects.new("camera_apercu", bpy.data.cameras.new("camera_apercu"))
        bpy.data.collections["studio"].objects.link(cam)
    if isinstance(k, str) and k.startswith("cle"):
        e = bpy.data.objects[f"cam_{int(k[3:]):02d}"]
    else:
        e = next(o for o in bpy.data.objects if o.name.startswith("cam_") and o.get("chapitre") == int(k))
    cible = bpy.data.objects[e.name.replace("cam_", "cible_")]
    cam.location = e.location
    cam.rotation_euler = (cible.location - e.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "VERTICAL"
    cam.data.angle = math.radians(44)
    cam.data.clip_end = 2000
    sc.camera = cam
    return cam


def rendre(chemin, opts, echantillons, largeur, hauteur_img, format_image="PNG"):
    sc = bpy.context.scene
    activer_gpu()
    sc.cycles.samples = echantillons
    sc.cycles.use_denoising = True
    sc.cycles.sample_clamp_indirect = 4.0
    sc.render.resolution_x = largeur
    sc.render.resolution_y = hauteur_img
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = format_image
    if format_image == "WEBP":
        sc.render.image_settings.quality = 82
    sc.render.filepath = chemin
    bpy.ops.render.render(write_still=True)
    log("image :", chemin)


def etape_apercu(opts):
    chapitres = range(6) if opts["chapitre"] == "tous" else [c for c in opts["chapitre"].split(",")]
    for k in chapitres:
        camera_chapitre(k)
        rendre(os.path.join(SORTIE_BLEND, f"apercu_{k}.png"), opts, int(opts["echantillons"] or 48),
               int(opts["largeur"]), int(opts["hauteur"]))


def etape_affiche(opts):
    camera_chapitre(0)
    os.makedirs(opts["sortie"], exist_ok=True)
    rendre(os.path.join(opts["sortie"], "affiche.webp"), opts, int(opts["echantillons"] or 256), 1920, 1080, "WEBP")


def deplier_uv(objets, marge):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objets:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objets[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(62), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, rotate_method="ANY", scale=True, margin_method="FRACTION",
                            margin=marge, shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")


def etape_cuire(opts):
    t_total = time.time()
    sc = bpy.context.scene
    activer_gpu()
    rapide = opts["rapide"]
    sc.cycles.samples = int(opts["echantillons"] or (64 if rapide else 640))
    sc.cycles.sample_clamp_indirect = 4.0
    sc.cycles.max_bounces = 8
    sc.render.bake.margin_type = "EXTEND"
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    os.makedirs(opts["sortie"], exist_ok=True)

    atlas = []
    for coll in bpy.data.collections:
        if not coll.name.startswith("atlas_"):
            continue
        nom = coll.name[len("atlas_"):]
        taille = int(coll.get("taille", 2048))
        if rapide:
            taille = min(taille, 1024)
        objets = [o for o in coll.all_objects if o.type == "MESH"]
        if not objets:
            continue
        # On regroupe les objets fixes en un seul maillage par atlas : moins d'appels de dessin pour le navigateur
        fixes = [o for o in objets if not o.get("mobile")]
        if len(fixes) > 1:
            bpy.ops.object.select_all(action="DESELECT")
            for o in fixes:
                o.select_set(True)
            bpy.context.view_layer.objects.active = fixes[0]
            bpy.ops.object.join()
            fixes[0].name = nom
            fixes[0].data.name = nom
        objets = [o for o in coll.all_objects if o.type == "MESH"]
        for o in objets:
            o["atlas"] = nom
            o["atlas_max"] = taille
            while o.data.uv_layers:
                o.data.uv_layers.remove(o.data.uv_layers[0])
        t0 = time.time()
        deplier_uv(objets, 6.0 / taille)
        log(f"atlas {nom} : {len(objets)} objets, UV dépliés en {time.time() - t0:.1f} s")
        atlas.append((nom, taille, objets))

    # Cuisson : chaque atlas reçoit la lumière de toute la scène (y compris des objets vivants qui brillent)
    images = {}
    for nom, taille, objets in atlas:
        img = bpy.data.images.new(f"cuisson_{nom}", taille, taille, alpha=False, float_buffer=True)
        images[nom] = img
        mats = {s.material for o in objets for s in o.material_slots if s.material}
        for m in mats:
            nt = m.node_tree
            n = nt.nodes.get("cuisson") or nt.nodes.new("ShaderNodeTexImage")
            n.name = "cuisson"
            n.image = img
            nt.nodes.active = n
        bpy.ops.object.select_all(action="DESELECT")
        for o in objets:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objets[0]
        t0 = time.time()
        bpy.ops.object.bake(type="COMBINED", pass_filter={"DIRECT", "INDIRECT", "DIFFUSE", "EMIT"},
                            margin=max(4, taille // 256), margin_type="EXTEND", use_clear=True,
                            target="IMAGE_TEXTURES", save_mode="INTERNAL")
        log(f"atlas {nom} cuit en {time.time() - t0:.1f} s ({taille} px, {sc.cycles.samples} échantillons)")

    # Enregistrement : l'image est convertie par AgX, comme un rendu Blender, puis en WebP à plusieurs tailles
    sc.render.image_settings.file_format = "WEBP"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.quality = 84
    # Trois tailles par atlas (la plus grande, la moitié, 1024) : le site charge d'abord la petite,
    # puis remplace par la grande quand elle est arrivée.
    for nom, taille, objets in atlas:
        img = images[nom]
        img.save_render(os.path.join(SORTIE_BLEND, f"cuisson_{nom}.png"), scene=sc)
        tailles = sorted({taille, max(1024, taille // 2), 1024}, reverse=True)
        for t in tailles:
            if t > taille:
                continue
            if t != img.size[0]:
                img.scale(t, t)
            chemin = os.path.join(opts["sortie"], f"{nom}_{t}.webp")
            img.save_render(chemin, scene=sc)
            log("texture :", os.path.relpath(chemin, DEPOT), f"{os.path.getsize(chemin) / 1024:.0f} Ko")

    # Matière d'aperçu : la texture cuite seule (pour vérifier dans Blender), puis export
    for nom, taille, objets in atlas:
        m = bpy.data.materials.new(f"cuit_{nom}")
        nt = m.node_tree
        nt.nodes.clear()
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = images[nom]
        em = nt.nodes.new("ShaderNodeEmission")
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(tex.outputs[0], em.inputs[0])
        nt.links.new(em.outputs[0], out.inputs[0])
        for o in objets:
            o.data.materials.clear()
            o.data.materials.append(m)
            # Une seule matière : le maillage part en un seul morceau dans le glTF
            o.data.polygons.foreach_set("material_index", [0] * len(o.data.polygons))
            for nom_attr in [a.name for a in o.data.color_attributes]:
                o.data.color_attributes.remove(o.data.color_attributes[nom_attr])

    bpy.ops.object.select_all(action="DESELECT")
    for coll in bpy.data.collections:
        if coll.name.startswith("atlas_") or coll.name in ("vivant", "reperes"):
            for o in coll.all_objects:
                o.select_set(True)
    for o in bpy.data.collections["vivant"].all_objects:
        if o.type == "MESH":
            while o.data.uv_layers:
                o.data.uv_layers.remove(o.data.uv_layers[0])
            for nom_attr in [a.name for a in o.data.color_attributes]:
                o.data.color_attributes.remove(o.data.color_attributes[nom_attr])
    chemin_glb = os.path.join(opts["sortie"], "ile.glb")
    bpy.ops.export_scene.gltf(
        filepath=chemin_glb, export_format="GLB", use_selection=True, export_extras=True,
        export_materials="NONE", export_normals=True, export_texcoords=True, export_yup=True, export_apply=True,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
        export_draco_position_quantization=15, export_draco_texcoord_quantization=15,
        export_draco_normal_quantization=8, export_cameras=False, export_lights=False, export_animations=False)
    log("modèle :", os.path.relpath(chemin_glb, DEPOT), f"{os.path.getsize(chemin_glb) / 1024:.0f} Ko")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SORTIE_BLEND, "ile_cuite.blend"), compress=True)
    log(f"cuisson terminée en {time.time() - t_total:.0f} s")


def principal():
    opts = lire_options()
    log("étapes :", ", ".join(opts["etapes"]))
    if "construire" not in opts["etapes"]:
        preparer_plan()
    for e in opts["etapes"]:
        {"construire": etape_construire, "apercu": etape_apercu, "affiche": etape_affiche,
         "cuire": etape_cuire}[e](opts)


if __name__ == "__main__":
    principal()
