"""
LE ROYAUME D'ERNEST · scène Blender de la version immersive (/3d/)

Ce script fabrique un royaume fortifié sur une île volante, au-dessus des nuages : trois remparts
concentriques, une ville à colombages, un château, une campagne, un phare. On entre dans plusieurs
bâtiments (l'atelier, la bibliothèque des guildes, la grande salle, la forge) et des personnages y vivent.
Blender « cuit » la lumière du couchant avec Cycles dans des textures, puis exporte le modèle pour le site,
où Three.js l'affiche, anime les personnages et permet de se promener librement.

Le code est rangé dans le dossier royaume/ (un module par partie du royaume) ; ce fichier le lance.

Utilisation, depuis la racine du dépôt :

  blender -b --factory-startup --python tools/blender/ile.py -- [options]

Étapes (--etapes, séparées par des virgules ; par défaut « construire,affiche,cuire ») :
  construire  modélise le royaume (tools/blender/out/ile.blend), peint la texture des feuilles,
              écrit la carte de marche et les chemins des personnages (wwwroot/3d/assets/royaume_*)
  apercu      rend une image d'un chapitre (--chapitre N, « tous », ou « cleN » pour une clé de caméra)
  affiche     rend l'image de secours du site (sans WebGL) : wwwroot/3d/assets/affiche.webp
  cuire       cuit la lumière, enregistre les atlas puis exporte ile.glb dans wwwroot/3d/assets/
  exporter    réexporte seulement ile.glb (à lancer sur tools/blender/out/ile_cuite.blend)

Options : --echantillons N, --rapide (cuisson d'essai en 1024 px), --largeur / --hauteur (aperçus).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from royaume.etapes_communes import etape_affiche, etape_apercu, etape_cuire, etape_exporter  # noqa: E402
from royaume.outils import lire_options, log  # noqa: E402
from royaume.plan import preparer_plan  # noqa: E402
from royaume.scene import etape_construire  # noqa: E402


def principal():
    opts = lire_options()
    log("étapes :", ", ".join(opts["etapes"]))
    if "construire" not in opts["etapes"]:
        preparer_plan()
    for e in opts["etapes"]:
        {"construire": etape_construire, "apercu": etape_apercu, "affiche": etape_affiche,
         "cuire": etape_cuire, "exporter": etape_exporter}[e](opts)


if __name__ == "__main__":
    principal()
