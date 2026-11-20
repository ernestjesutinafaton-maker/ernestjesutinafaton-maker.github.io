"""Matières Cycles de la scène. Elles ne servent qu'à la cuisson : le site affiche les textures cuites."""

import bpy


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


def creer_matieres(image_feuilles):
    M = {}

    # Herbe du dessus de l'île : chemin de terre (attribut « chemin »), berges mouillées (attribut « eau »)
    m = Noeuds("herbe")
    grand = m.bruit(0.07, 5, 0.55)
    moyen = m.bruit(0.55, 6, 0.6)
    fin = m.bruit(6.0, 3, 0.7)
    herbe = m.rampe(grand, [(0.25, (0.07, 0.11, 0.024)), (0.5, (0.105, 0.155, 0.034)),
                            (0.7, (0.16, 0.18, 0.045)), (0.85, (0.24, 0.21, 0.075))])
    herbe = m.melange(m.plage(moyen, 0.3, 0.75, 0.0, 0.4), herbe, (0.035, 0.065, 0.016), "MULTIPLY")
    fleurs = m.plage(m.voronoi(2.2, trait="F1"), 0.0, 0.06, 1.0, 0.0)
    fleurs = m.math("MULTIPLY", fleurs, m.plage(m.bruit(0.25, 2), 0.55, 0.7))
    herbe = m.melange(m.math("MULTIPLY", fleurs, 0.7), herbe, (0.6, 0.45, 0.2))
    terre = m.rampe(m.bruit(1.4, 6), [(0.3, (0.075, 0.05, 0.03)), (0.7, (0.16, 0.115, 0.07))])
    cailloux = m.plage(m.voronoi(9.0), 0.0, 0.18, 1.0, 0.0)
    terre = m.melange(m.math("MULTIPLY", cailloux, 0.5), terre, (0.22, 0.2, 0.17))
    bord = m.plage(m.math("ADD", m.attribut("chemin", "Factor"), m.math("MULTIPLY", fin, 0.4)), 0.55, 0.85)
    sol = m.melange(bord, herbe, terre)
    # Berges : boue sombre et galets
    eau = m.plage(m.math("ADD", m.attribut("eau", "Factor"), m.math("MULTIPLY", fin, 0.3)), 0.35, 0.75)
    galets = m.plage(m.voronoi(5.0), 0.0, 0.3, 1.0, 0.0)
    berge = m.melange(m.math("MULTIPLY", galets, 0.6), (0.035, 0.03, 0.025), (0.16, 0.15, 0.13))
    m.couleur(m.melange(eau, sol, berge))
    m.rugosite(0.95)
    m.relief(m.math("ADD", m.math("MULTIPLY", fin, 0.6), m.math("MULTIPLY", cailloux, bord)), 0.35, 0.04)
    M["herbe"] = m.mat

    # Roche de la falaise : strates, fissures par endroits, mousse sur les faces tournées vers le ciel
    m = Noeuds("roche")
    strates = m.vague(0.6, 16.0, "Z", m.echelle_vec(0.05, 0.05, 0.45), 6)
    var = m.math("ADD", m.math("MULTIPLY", m.bruit(0.35, 5, 0.6), 0.6), m.math("MULTIPLY", m.bruit(0.07, 3, 0.5), 0.4))
    roche = m.rampe(m.math("ADD", m.math("MULTIPLY", strates, 0.07), m.math("MULTIPLY", var, 0.93)),
                    [(0.2, (0.05, 0.04, 0.035)), (0.45, (0.12, 0.095, 0.075)),
                     (0.7, (0.2, 0.16, 0.12)), (0.9, (0.27, 0.22, 0.17))])
    fissures = m.plage(m.voronoi(0.6, trait="DISTANCE_TO_EDGE"), 0.0, 0.03, 0.0, 1.0)
    zones = m.plage(m.bruit(0.3, 3), 0.6, 0.72)
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
    mousse = m.math("MULTIPLY", m.plage(m.bruit(1.5, 4), 0.55, 0.7), 0.6)
    toit = m.melange(mousse, toit, (0.06, 0.08, 0.025))
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

    # Fenêtres et lanternes allumées : leur lumière orangée est cuite sur ce qui les entoure
    m = Noeuds("lumiere")
    m.couleur((1.0, 0.6, 0.3))
    m.emission((1.0, 0.52, 0.2), 7.0)
    M["lumiere"] = m.mat

    m = Noeuds("lanterne")
    m.couleur((1.0, 0.65, 0.35))
    m.emission((1.0, 0.55, 0.22), 14.0)
    M["lanterne"] = m.mat

    m = Noeuds("lumiere_phare")
    m.couleur((1.0, 0.85, 0.6))
    m.emission((1.0, 0.75, 0.42), 16.0)
    M["lumiere_phare"] = m.mat

    m = Noeuds("ecorce")
    stries = m.bruit(1.0, 6, 0.6, m.echelle_vec(14.0, 14.0, 1.2), 1.5)
    m.couleur(m.melange(1.0, m.rampe(stries, [(0.3, (0.035, 0.026, 0.02)), (0.7, (0.1, 0.078, 0.058))]),
                        teinte(m), "MULTIPLY"))
    m.rugosite(0.9)
    m.relief(stries, 0.5, 0.03)
    M["ecorce"] = m.mat

    # Feuilles : cartes découpées par la texture peinte (UV « feuille »), teintées arbre par arbre
    m = Noeuds("feuilles")
    uv = m.nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "feuille"
    tex = m.nt.nodes.new("ShaderNodeTexImage")
    tex.image = image_feuilles
    tex.interpolation = "Linear"
    m.lien(uv.outputs["UV"], tex.inputs["Vector"])
    m.couleur(m.melange(1.0, tex.outputs["Color"], teinte(m), "MULTIPLY"))
    m.lien(tex.outputs["Alpha"], m.bsdf.inputs["Alpha"])
    m.rugosite(0.75)
    m.bsdf.inputs["Specular IOR Level"].default_value = 0.25
    M["feuilles"] = m.mat

    # Objets vivants : rendus par le site, leurs matières ici servent seulement à éclairer la cuisson
    for nom, c, force in (("glyphe", (0.55, 0.32, 1.0), 6.0), ("anneau", (0.85, 0.3, 0.95), 2.5),
                          ("cristal_vert", (0.25, 1.0, 0.55), 5.0), ("cristal_violet", (0.6, 0.35, 1.0), 5.0),
                          ("cristal_rose", (1.0, 0.35, 0.75), 5.0), ("cristal_roche", (0.45, 0.6, 1.0), 9.0)):
        m = Noeuds(nom)
        m.couleur(c)
        m.emission(c, force)
        M[nom] = m.mat

    m = Noeuds("eau")
    m.couleur((0.05, 0.08, 0.12))
    m.rugosite(0.05)
    M["eau"] = m.mat
    return M


