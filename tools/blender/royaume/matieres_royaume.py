"""
Matières propres au royaume, ajoutées à celles de l'île (matieres.py).

Les motifs d'architecture (pierres des remparts, colombages, tuiles) sont dessinés dans les UV « facade »,
exprimées en mètres : un colombage a la même taille sur une maison étroite et sur une grande auberge.
L'attribut « donnee » porte des réglages par pièce : r = variante du motif, g = fenêtre allumée,
b = hauteur du pied de la maison / 20 (pour aligner les poutres sur les planchers).
"""

from .matieres import Noeuds, teinte


def uv(m, nom="facade"):
    n = m.nt.nodes.new("ShaderNodeUVMap")
    n.uv_map = nom
    return n.outputs["UV"]


def separer(m, vec):
    n = m.nt.nodes.new("ShaderNodeSeparateXYZ")
    m.lien(vec, n.inputs[0])
    return n.outputs["X"], n.outputs["Y"], n.outputs["Z"]


def separer_couleur(m, coul):
    n = m.nt.nodes.new("ShaderNodeSeparateColor")
    m.lien(coul, n.inputs[0])
    return n.outputs[0], n.outputs[1], n.outputs[2]


def combiner(m, x, y, z=0.0):
    n = m.nt.nodes.new("ShaderNodeCombineXYZ")
    for i, v in enumerate((x, y, z)):
        m._entree(n.inputs[i], v)
    return n.outputs[0]


def bande(m, valeur, periode, demi_largeur, decalage=0.0):
    """1 près des multiples de « periode » (à demi_largeur près), 0 ailleurs : poteaux, poutres, sillons."""
    f = m.math("FRACT", m.math("DIVIDE", m.math("ADD", valeur, decalage), periode))
    d = m.math("MINIMUM", f, m.math("SUBTRACT", 1.0, f))
    d = m.math("MULTIPLY", d, periode)
    return m.plage(d, demi_largeur, demi_largeur + 0.012, 1.0, 0.0)


def ajouter_matieres_royaume(M):
    # ------------------------------------------------------------------ sol
    m = Noeuds("sol")
    grand = m.bruit(0.035, 5, 0.55)
    moyen = m.bruit(0.4, 6, 0.6)
    fin = m.bruit(5.0, 3, 0.7)
    herbe = m.rampe(grand, [(0.25, (0.07, 0.115, 0.026)), (0.5, (0.105, 0.16, 0.036)),
                            (0.7, (0.16, 0.19, 0.05)), (0.85, (0.24, 0.22, 0.08))])
    herbe = m.melange(m.plage(moyen, 0.3, 0.75, 0.0, 0.4), herbe, (0.035, 0.065, 0.016), "MULTIPLY")
    fleurs = m.plage(m.voronoi(1.8, trait="F1"), 0.0, 0.05, 1.0, 0.0)
    fleurs = m.math("MULTIPLY", fleurs, m.plage(m.bruit(0.2, 2), 0.55, 0.7))
    herbe = m.melange(m.math("MULTIPLY", fleurs, 0.7), herbe, (0.62, 0.42, 0.55))
    # Champs : culture (r), angle des sillons (g), variation (b)
    c_r, c_g, c_b = separer_couleur(m, m.attribut("champ"))
    est_champ = m.plage(c_r, 0.05, 0.08)
    culture = m.rampe(c_r, [(0.0, (0.1, 0.16, 0.04)), (0.12, (0.09, 0.15, 0.035)), (0.24, (0.42, 0.3, 0.08)),
                            (0.37, (0.28, 0.16, 0.42)), (0.49, (0.14, 0.085, 0.045)), (0.62, (0.09, 0.2, 0.05)),
                            (0.74, (0.55, 0.45, 0.05)), (0.87, (0.06, 0.12, 0.035))])
    m.nt.nodes[-1].color_ramp.interpolation = "CONSTANT"
    terre_champ = (0.11, 0.07, 0.04)
    angle = m.math("MULTIPLY", c_g, 3.14159)
    px, py, pz = separer(m, m.pos)
    le_long = m.math("ADD", m.math("MULTIPLY", px, m.math("COSINE", angle)), m.math("MULTIPLY", py, m.math("SINE", angle)))
    sillon = m.math("SINE", m.math("MULTIPLY", le_long, 7.0))
    sillon = m.plage(sillon, -0.3, 0.5)
    force = m.rampe(c_r, [(0.0, (0.0, 0.0, 0.0)), (0.24, (0.25, 0.25, 0.25)), (0.37, (0.95, 0.95, 0.95)),
                          (0.49, (0.6, 0.6, 0.6)), (0.62, (0.85, 0.85, 0.85)), (0.74, (0.2, 0.2, 0.2)), (0.87, (0.9, 0.9, 0.9))])
    m.nt.nodes[-1].color_ramp.interpolation = "CONSTANT"
    f_r, _, _ = separer_couleur(m, force)
    champs = m.melange(m.math("MULTIPLY", m.math("SUBTRACT", 1.0, sillon), f_r), culture, terre_champ)
    champs = m.melange(m.plage(m.bruit(0.15, 3), 0.3, 0.8, 0.0, 0.25), champs, (0.0, 0.0, 0.0), "MULTIPLY")
    champs = m.melange(m.math("MULTIPLY", c_b, 0.25), champs, (1.0, 0.9, 0.7), "MULTIPLY")
    sol = m.melange(est_champ, herbe, champs)
    # Chemins de terre
    terre = m.rampe(m.bruit(1.2, 6), [(0.3, (0.08, 0.055, 0.032)), (0.7, (0.17, 0.12, 0.075))])
    cailloux = m.plage(m.voronoi(8.0), 0.0, 0.18, 1.0, 0.0)
    terre = m.melange(m.math("MULTIPLY", cailloux, 0.4), terre, (0.22, 0.2, 0.17))
    bord = m.plage(m.math("ADD", m.attribut("chemin", "Factor"), m.math("MULTIPLY", fin, 0.4)), 0.55, 0.85)
    sol = m.melange(bord, sol, terre)
    # Pavés de la ville
    pave = m.voronoi(4.2, trait="DISTANCE_TO_EDGE")
    joints = m.plage(pave, 0.0, 0.06, 0.0, 1.0)
    pierre_pave = m.rampe(m.voronoi(4.2, sortie="Color"), [(0.0, (0.13, 0.12, 0.11)), (0.5, (0.22, 0.2, 0.17)), (1.0, (0.3, 0.27, 0.23))])
    pierre_pave = m.melange(m.math("SUBTRACT", 1.0, joints), pierre_pave, (0.05, 0.05, 0.045))
    pierre_pave = m.melange(m.plage(m.bruit(0.3, 4), 0.45, 0.8, 0.0, 0.4), pierre_pave, (0.08, 0.075, 0.07), "MULTIPLY")
    est_pave = m.plage(m.attribut("pave", "Factor"), 0.4, 0.6)
    sol = m.melange(est_pave, sol, pierre_pave)
    # Berges mouillées
    eau = m.plage(m.math("ADD", m.attribut("eau", "Factor"), m.math("MULTIPLY", fin, 0.3)), 0.35, 0.75)
    galets = m.plage(m.voronoi(5.0), 0.0, 0.3, 1.0, 0.0)
    berge = m.melange(m.math("MULTIPLY", galets, 0.6), (0.035, 0.03, 0.025), (0.16, 0.15, 0.13))
    m.couleur(m.melange(eau, sol, berge))
    m.rugosite(0.95)
    relief = m.math("ADD", m.math("MULTIPLY", fin, 0.5), m.math("MULTIPLY", m.math("SUBTRACT", 1.0, joints), est_pave))
    m.relief(relief, 0.4, 0.03)
    M["sol"] = m.mat

    # ------------------------------------------------------------------ pierre des remparts
    m = Noeuds("remparts")
    briques, fac = m.brique(0.42, uv(m), 0.022, 0.5, 0.25)
    var = m.bruit(0.08, 4)
    pierre = m.rampe(m.math("ADD", m.math("MULTIPLY", var, 0.6), m.math("MULTIPLY", separer_couleur(m, briques)[0], 0.4)),
                     [(0.3, (0.16, 0.145, 0.12)), (0.55, (0.25, 0.225, 0.19)), (0.8, (0.33, 0.3, 0.26))])
    pierre = m.melange(m.math("SUBTRACT", 1.0, fac), pierre, (0.05, 0.045, 0.04))
    u_, v_, _ = separer(m, uv(m))
    coulures = m.bruit(1.0, 4, 0.6, combiner(m, m.math("MULTIPLY", u_, 0.6), m.math("MULTIPLY", v_, 0.04)))
    pierre = m.melange(m.plage(coulures, 0.5, 0.75, 0.0, 0.45), pierre, (0.06, 0.06, 0.055), "MULTIPLY")
    mousse = m.math("MULTIPLY", m.plage(m.normale_z(), 0.6, 0.9), m.plage(m.bruit(0.6, 4), 0.42, 0.6))
    pierre = m.melange(mousse, pierre, (0.05, 0.08, 0.02))
    m.couleur(m.melange(1.0, pierre, teinte(m), "MULTIPLY"))
    m.rugosite(0.88)
    m.relief(m.math("ADD", fac, m.math("MULTIPLY", m.bruit(6.0, 4), 0.4)), 0.45, 0.04)
    M["remparts"] = m.mat

    # ------------------------------------------------------------------ colombage
    m = Noeuds("colombage")
    u_, v_, _ = separer(m, uv(m))
    d_r, _, d_b = separer_couleur(m, m.attribut("donnee"))
    v_loc = m.math("SUBTRACT", v_, m.math("MULTIPLY", d_b, 20.0))
    periode = m.math("ADD", 0.95, m.math("MULTIPLY", d_r, 0.4))
    poteaux = bande(m, u_, periode, 0.075)
    planchers = m.math("MAXIMUM", bande(m, v_loc, 2.9, 0.11), bande(m, v_loc, 2.9, 0.06, -0.95))
    pu = m.math("FRACT", m.math("DIVIDE", u_, periode))
    pv = m.math("DIVIDE", m.math("SUBTRACT", m.math("FRACT", m.math("DIVIDE", v_loc, 2.9)), 0.33), 0.67)
    croix = m.math("MINIMUM", m.math("ABSOLUTE", m.math("SUBTRACT", pv, pu)),
                   m.math("ABSOLUTE", m.math("SUBTRACT", pv, m.math("SUBTRACT", 1.0, pu))))
    croix = m.plage(croix, 0.07, 0.1, 1.0, 0.0)
    choix = m.plage(m.voronoi(0.7, combiner(m, m.math("FLOOR", m.math("DIVIDE", u_, periode)),
                                            m.math("FLOOR", m.math("DIVIDE", v_loc, 2.9))), "Distance"), 0.35, 0.37)
    croix = m.math("MULTIPLY", m.math("MULTIPLY", croix, choix), m.plage(pv, -0.02, 0.02))
    bois = m.math("MAXIMUM", m.math("MAXIMUM", poteaux, planchers), croix)
    enduit = m.melange(1.0, teinte(m), m.rampe(m.bruit(1.5, 5), [(0.3, (0.8, 0.78, 0.74)), (0.75, (1.0, 1.0, 1.0))]), "MULTIPLY")
    enduit = m.melange(m.plage(m.bruit(0.6, 3), 0.55, 0.75, 0.0, 0.25), enduit, (0.3, 0.27, 0.22), "MULTIPLY")
    poutre = m.rampe(m.bruit(3.0, 5, 0.6, combiner(m, m.math("MULTIPLY", u_, 8.0), v_)), [(0.3, (0.05, 0.03, 0.018)), (0.8, (0.11, 0.065, 0.035))])
    m.couleur(m.melange(bois, enduit, poutre))
    m.rugosite(0.85)
    m.relief(m.math("ADD", m.math("MULTIPLY", bois, 0.6), m.math("MULTIPLY", m.bruit(12.0, 3), 0.2)), 0.35, 0.02)
    M["colombage"] = m.mat

    # Enduit uni (rez-de-chaussée, pignons), teinté maison par maison
    m = Noeuds("enduit_maison")
    enduit = m.melange(1.0, teinte(m), m.rampe(m.bruit(1.5, 5), [(0.3, (0.78, 0.76, 0.72)), (0.75, (1.0, 1.0, 1.0))]), "MULTIPLY")
    u_, v_, _ = separer(m, uv(m))
    salissure = m.bruit(1.0, 4, 0.6, combiner(m, m.math("MULTIPLY", u_, 0.8), m.math("MULTIPLY", v_, 0.1)))
    m.couleur(m.melange(m.plage(salissure, 0.5, 0.8, 0.0, 0.35), enduit, (0.25, 0.22, 0.18), "MULTIPLY"))
    m.rugosite(0.85)
    m.relief(m.bruit(14.0, 3), 0.15, 0.01)
    M["enduit_maison"] = m.mat

    # Tuiles, alignées sur la pente du toit (UV « facade »)
    m = Noeuds("tuiles")
    couleur, fac = m.brique(3.3, uv(m), 0.03, 0.4, 0.2)
    toit = m.melange(1.0, m.rampe(m.bruit(2.0, 4), [(0.3, (0.6, 0.6, 0.6)), (0.8, (1.0, 1.0, 1.0))]), couleur, "MULTIPLY")
    toit = m.melange(1.0, toit, teinte(m), "MULTIPLY")
    mousse = m.math("MULTIPLY", m.plage(m.bruit(0.8, 4), 0.58, 0.72), 0.5)
    m.couleur(m.melange(mousse, toit, (0.05, 0.07, 0.025)))
    m.rugosite(0.75)
    m.relief(fac, 0.5, 0.025)
    M["tuiles"] = m.mat

    # Ardoises (château, chapelle) : petites écailles sombres
    m = Noeuds("ardoises")
    couleur, fac = m.brique(5.5, uv(m), 0.025, 0.35, 0.18)
    ard = m.melange(1.0, m.rampe(m.bruit(3.0, 4), [(0.3, (0.04, 0.045, 0.06)), (0.8, (0.09, 0.095, 0.12))]), couleur, "MULTIPLY")
    m.couleur(m.melange(1.0, ard, teinte(m), "MULTIPLY"))
    m.rugosite(0.5)
    m.relief(fac, 0.4, 0.02)
    M["ardoises"] = m.mat

    # Fenêtres : verre sombre, ou lumière chaude si l'attribut le dit (donnee.g = 1)
    m = Noeuds("fenetre")
    _, d_g, _ = separer_couleur(m, m.attribut("donnee"))
    u_, v_, _ = separer(m, uv(m))
    carreaux = m.math("MAXIMUM", bande(m, u_, 0.28, 0.012), bande(m, v_, 0.32, 0.012))
    m.couleur(m.melange(carreaux, (0.02, 0.025, 0.035), (0.03, 0.02, 0.015)))
    m.emission(m.melange(carreaux, (1.0, 0.55, 0.22), (0.1, 0.05, 0.02)), m.math("MULTIPLY", d_g, 6.0))
    m.rugosite(0.2)
    M["fenetre"] = m.mat

    # Vitraux de la chapelle : une mosaïque colorée, éclairée de l'intérieur
    m = Noeuds("vitrail")
    cellules = m.voronoi(5.0, uv(m), "Color")
    plomb = m.plage(m.voronoi(5.0, uv(m), trait="DISTANCE_TO_EDGE"), 0.0, 0.04, 0.0, 1.0)
    verre = m.rampe(separer_couleur(m, cellules)[0], [(0.0, (0.8, 0.15, 0.25)), (0.3, (0.2, 0.3, 0.9)),
                                                       (0.55, (0.95, 0.7, 0.15)), (0.8, (0.45, 0.2, 0.8))])
    m.couleur((0.02, 0.02, 0.02))
    m.emission(m.melange(plomb, (0.0, 0.0, 0.0), verre), 1.4)
    M["vitrail"] = m.mat

    m = Noeuds("tissu")
    m.couleur(m.melange(1.0, teinte(m), m.rampe(m.bruit(4.0, 3), [(0.3, (0.75, 0.75, 0.75)), (0.8, (1.0, 1.0, 1.0))]), "MULTIPLY"))
    m.rugosite(0.9)
    m.bsdf.inputs["Sheen Weight"].default_value = 0.3
    M["tissu"] = m.mat

    m = Noeuds("livres")
    u_, v_, _ = separer(m, uv(m))
    dos = m.rampe(m.bruit(1.0, 2, 0.5, combiner(m, m.math("MULTIPLY", u_, 30.0), 0.0)),
                  [(0.2, (0.25, 0.05, 0.04)), (0.4, (0.06, 0.12, 0.25)), (0.6, (0.08, 0.18, 0.08)), (0.8, (0.4, 0.28, 0.1))])
    m.nt.nodes[-1].color_ramp.interpolation = "CONSTANT"
    filets = bande(m, v_, 0.11, 0.01)
    m.couleur(m.melange(m.math("MULTIPLY", filets, 0.7), dos, (0.5, 0.38, 0.12)))
    m.rugosite(0.7)
    M["livres"] = m.mat

    m = Noeuds("or")
    m.couleur((0.85, 0.6, 0.2))
    m.bsdf.inputs["Metallic"].default_value = 1.0
    m.rugosite(0.3)
    M["or"] = m.mat

    m = Noeuds("paille")
    stries = m.bruit(1.0, 6, 0.6, m.echelle_vec(20.0, 20.0, 1.0), 1.5)
    m.couleur(m.rampe(stries, [(0.3, (0.3, 0.2, 0.06)), (0.7, (0.55, 0.42, 0.14))]))
    m.rugosite(0.95)
    m.relief(stries, 0.4, 0.02)
    M["paille"] = m.mat

    # Écrans et voyants de l'atelier (le NAS, l'ordinateur) : une lueur froide
    m = Noeuds("ecran")
    m.couleur((0.02, 0.03, 0.05))
    m.emission((0.35, 0.65, 1.0), 3.0)
    M["ecran"] = m.mat

    # Dallage des intérieurs : grandes dalles irrégulières, sans mousse
    m = Noeuds("dalles")
    couleur, fac = m.brique(1.3, uv(m), 0.012, 0.5, 0.5)
    var = m.rampe(m.math("ADD", m.math("MULTIPLY", separer_couleur(m, couleur)[0], 0.5), m.math("MULTIPLY", m.bruit(0.8, 4), 0.5)),
                  [(0.3, (0.16, 0.14, 0.12)), (0.6, (0.24, 0.21, 0.18)), (0.85, (0.3, 0.27, 0.23))])
    m.couleur(m.melange(m.math("SUBTRACT", 1.0, fac), var, (0.06, 0.055, 0.05)))
    m.rugosite(0.6)
    m.relief(fac, 0.3, 0.02)
    M["dalles"] = m.mat

    # Haies taillées des jardins du château
    m = Noeuds("haie")
    touffes = m.voronoi(6.0)
    m.couleur(m.melange(m.plage(touffes, 0.0, 0.45, 0.6, 0.0), m.rampe(m.bruit(1.2, 4), [(0.3, (0.03, 0.07, 0.02)), (0.7, (0.07, 0.13, 0.035))]),
                        (0.0, 0.0, 0.0)))
    m.rugosite(0.85)
    m.relief(m.math("SUBTRACT", 1.0, touffes), 0.6, 0.08)
    M["haie"] = m.mat

    m = Noeuds("braise")
    m.couleur((1.0, 0.4, 0.1))
    m.emission((1.0, 0.35, 0.08), 12.0)
    M["braise"] = m.mat
    return M
