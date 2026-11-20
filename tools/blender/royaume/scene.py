"""
L'étape « construire » : assemble tout le royaume, dans l'ordre où chaque partie a besoin des autres.

  1. le plan, la texture des feuilles, les matières
  2. le sol, la roche, les racines, les cristaux, les rochers flottants
  3. l'eau (la rivière décide de la hauteur de l'arche sous le rempart extérieur)
  4. les remparts, les intérieurs, la ville, le château, la campagne, le phare
  5. le trajet de la caméra (qui passe par les portes des bâtiments)
  6. la végétation (qui laisse libre le champ de vision de la caméra)
  7. les pièces des personnages, le studio, la carte de marche et les chemins
"""

import os
import random
import time

import bpy
from mathutils import Matrix

from . import plan
from .camera import construire_reperes_camera
from .campagne import construire_campagne
from .chateau import construire_chateau
from .construction import Feuillage, collection
from .eau import construire_eau, niveau_au_rempart
from .feuilles import peindre_feuilles
from .interieurs import construire_interieurs
from .matieres import creer_matieres
from .matieres_royaume import ajouter_matieres_royaume
from .navigation import carte_de_marche, chemins
from .outils import SORTIE_BLEND, log
from .personnages import construire_pieces
from .phare import construire_phare
from .remparts import construire_remparts
from .studio import construire_studio
from .terrain import construire_roche, construire_sols, racines_et_cristaux, rochers_flottants
from .vegetation import construire_vegetation
from .ville import construire_ville

# Atlas de lumière cuite : nom -> résolution
ATLAS = {
    "sol_ville": 4096, "sol_campagne": 4096, "roche": 4096,
    "remparts_ext": 4096, "remparts_int": 4096, "portes": 4096,
    "maisons_a": 4096, "maisons_b": 4096, "monuments": 4096, "chateau": 4096,
    "interieurs": 4096, "vegetation": 4096,
}


def lumieres(reperes, studio):
    """Vraies sources de lumière pour la cuisson : lanternes, lustres et feux, plus un éclairage doux au plafond
    de chaque intérieur. Elles restent dans le studio (jamais exportées)."""
    import math
    from mathutils import Vector
    puissances = (("lustre_", 160.0), ("lanterne_atelier", 110.0), ("feu_cheminee", 450.0), ("feu_forge", 550.0),
                  ("feu_brasero", 260.0), ("lanterne_", 55.0))
    n = 0
    for o in list(reperes.objects):
        for prefixe, puissance in puissances:
            if o.name.startswith(prefixe):
                lum = bpy.data.lights.new("lumiere_" + o.name, "POINT")
                lum.energy = puissance
                lum.color = (1.0, 0.6, 0.3) if not prefixe.startswith("feu") else (1.0, 0.45, 0.15)
                lum.shadow_soft_size = 0.15
                ob = bpy.data.objects.new("lumiere_" + o.name, lum)
                ob.location = o.location + Vector((0, 0, -0.05))
                studio.objects.link(ob)
                n += 1
                break
    for b in plan.INTERIEURS:
        L, w, d = b["L"], b["largeur"], b["profondeur"]
        lum = bpy.data.lights.new("plafond_" + b["nom"], "AREA")
        lum.shape = "RECTANGLE"
        lum.size, lum.size_y = w - 1.5, d - 1.5
        lum.energy = 150.0 * (w * d) / 100.0
        lum.color = (1.0, 0.78, 0.55)
        ob = bpy.data.objects.new("plafond_" + b["nom"], lum)
        ob.matrix_world = L @ Matrix.Translation((0, d / 2, b["sol"] - L.to_translation().z + 3.6))
        studio.objects.link(ob)
        n += 1
    log(f"lumières de cuisson : {n}")


def etape_construire(opts):
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    plan.preparer_plan()
    rnd = random.Random(2026)
    image_feuilles = peindre_feuilles(opts["sortie"])
    M = creer_matieres(image_feuilles)
    ajouter_matieres_royaume(M)
    racine = bpy.context.scene.collection
    C = {nom: collection(f"atlas_{nom}", racine, taille) for nom, taille in ATLAS.items()}
    vivant = collection("vivant", racine)
    reperes = collection("reperes", racine)
    studio = collection("studio", racine)
    feuillage = Feuillage()

    bords = construire_sols(M, C["sol_ville"], C["sol_campagne"])
    arbre_roche = construire_roche(M, C["roche"], bords)
    racines_et_cristaux(M, C["roche"], vivant, reperes, arbre_roche, bords, rnd)
    rochers_flottants(M, C["roche"], rnd)
    profil = construire_eau(M, vivant, reperes)
    chemins_ronde, _ = construire_remparts(M, C["remparts_ext"], C["remparts_int"], C["portes"], reperes, feuillage, rnd,
                                           niveau_au_rempart(profil))
    construire_interieurs(M, C["interieurs"], vivant, reperes, feuillage, rnd)
    construire_ville(M, [C["maisons_a"], C["maisons_b"]], C["monuments"], vivant, feuillage, reperes, rnd)
    construire_chateau(M, C["chateau"], feuillage, reperes, rnd)
    construire_campagne(M, C["monuments"], vivant, feuillage, reperes, profil, rnd)
    construire_phare(M, C["monuments"], reperes, feuillage, rnd)
    vues = construire_reperes_camera(reperes)
    construire_vegetation(M, C["vegetation"], C["roche"], feuillage, rnd, vues)
    feuillage.objet(C["vegetation"], M, "feuillage", groupe="feuillage", feuilles=1)
    construire_pieces(vivant)
    construire_studio(studio)
    lumieres(reperes, studio)
    n = carte_de_marche(opts["sortie"])
    chemins(opts["sortie"], n, chemins_ronde)

    total = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
    log(f"royaume construit : {total} faces, {time.time() - t0:.0f} s")
    os.makedirs(SORTIE_BLEND, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SORTIE_BLEND, "ile.blend"), compress=True)
