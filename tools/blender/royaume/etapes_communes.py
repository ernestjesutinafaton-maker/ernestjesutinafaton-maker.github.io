"""Aperçus, affiche, cuisson et export (communs à toute la scène)."""

import math
import os
import time

import bpy
import numpy as np

from .outils import DEPOT, SORTIE_BLEND, log
from .studio import activer_gpu


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
    cam.data.angle = math.radians(e.get("fov", 44))
    cam.data.clip_end = 2000
    sc.camera = cam
    return cam


def rendre(chemin, echantillons, largeur, hauteur_img, format_image="PNG"):
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
    chapitres = [str(k) for k in range(7)] if opts["chapitre"] == "tous" else opts["chapitre"].split(",")
    rendre_sans = [o for o in bpy.data.objects if o.get("vivant") == "piece"]
    for o in rendre_sans:
        o.hide_render = True
    for k in chapitres:
        camera_chapitre(k)
        rendre(os.path.join(SORTIE_BLEND, f"apercu_{k}.png"), int(opts["echantillons"] or 48),
               int(opts["largeur"]), int(opts["hauteur"]))


def etape_affiche(opts):
    camera_chapitre(0)
    os.makedirs(opts["sortie"], exist_ok=True)
    rendre(os.path.join(opts["sortie"], "affiche.webp"), int(opts["echantillons"] or 256), 1920, 1080, "WEBP")


def preparer_uv_cuisson(o):
    """La couche « cuisson » passe en premier (TEXCOORD_0 dans le glTF) ; la couche « feuille » est gardée en second."""
    me = o.data
    gardees = {}
    for nom in ("feuille", "facade"):
        if nom in me.uv_layers:
            gardees[nom] = np.empty(len(me.loops) * 2, dtype=np.float32)
            me.uv_layers[nom].data.foreach_get("uv", gardees[nom])
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    cuisson = me.uv_layers.new(name="cuisson")
    for nom in ("feuille", "facade"):
        if nom in gardees:
            f = me.uv_layers.new(name=nom)
            f.data.foreach_set("uv", gardees[nom])
    me.uv_layers.active = me.uv_layers["cuisson"]
    me.uv_layers["cuisson"].active_render = True


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
    sc.cycles.transparent_max_bounces = 16
    sc.render.bake.margin_type = "EXTEND"
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    os.makedirs(opts["sortie"], exist_ok=True)

    # L'eau et la cascade sont rendues par le site : on les retire de la cuisson (le lit reste éclairé)
    for o in [o for o in bpy.data.collections["vivant"].all_objects if o is not None]:
        if o.get("vivant") in ("eau", "cascade", "piece"):
            o.hide_render = True

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
        # Les objets fixes d'un même groupe deviennent un seul maillage : moins d'appels de dessin
        groupes = {}
        for o in objets:
            if not o.get("mobile"):
                groupes.setdefault(o.get("groupe", nom), []).append(o)
        for g, membres in groupes.items():
            if len(membres) > 1:
                bpy.ops.object.select_all(action="DESELECT")
                for o in membres:
                    o.select_set(True)
                bpy.context.view_layer.objects.active = membres[0]
                bpy.ops.object.join()
            membres[0].name = g
            membres[0].data.name = g
        objets = [o for o in coll.all_objects if o.type == "MESH"]
        for o in objets:
            o["atlas"] = nom
            o["atlas_max"] = taille
            preparer_uv_cuisson(o)
        t0 = time.time()
        deplier_uv(objets, 6.0 / taille)
        log(f"atlas {nom} : {len(objets)} objets ({', '.join(o.name for o in objets[:6])}), UV dépliés en {time.time() - t0:.1f} s")
        atlas.append((nom, taille, objets))

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

    # Enregistrement : l'image est convertie par AgX, comme un rendu Blender, puis en WebP à plusieurs tailles.
    # Le site charge d'abord la 1024, puis la plus grande quand elle est arrivée.
    sc.render.image_settings.file_format = "WEBP"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.quality = 84
    for nom, taille, objets in atlas:
        img = images[nom]
        img.save_render(os.path.join(SORTIE_BLEND, f"cuisson_{nom}.png"), scene=sc)
        for t in sorted({taille, max(1024, taille // 2), 1024}, reverse=True):
            if t > taille:
                continue
            if t != img.size[0]:
                img.scale(t, t)
            chemin = os.path.join(opts["sortie"], f"{nom}_{t}.webp")
            img.save_render(chemin, scene=sc)
            log("texture :", os.path.relpath(chemin, DEPOT), f"{os.path.getsize(chemin) / 1024:.0f} Ko")

    # Matière d'aperçu : la texture cuite seule, puis nettoyage avant l'export
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
            if "facade" in o.data.uv_layers:
                o.data.uv_layers.remove(o.data.uv_layers["facade"])
            for nom_attr in [a.name for a in o.data.color_attributes if a.name != "balancement"]:
                o.data.color_attributes.remove(o.data.color_attributes[nom_attr])

    # La cuisson est faite : on l'enregistre avant l'export, pour pouvoir réexporter sans tout recuire
    for img in images.values():
        img.pack()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SORTIE_BLEND, "ile_cuite.blend"), compress=True)
    log(f"cuisson terminée en {time.time() - t_total:.0f} s")
    etape_exporter(opts)


def etape_exporter(opts):
    """Exporte ile.glb depuis une scène déjà cuite (après l'étape « cuire », ou en ouvrant ile_cuite.blend)."""
    # On fige la liste avant de modifier les maillages (sinon Blender peut renvoyer des objets vides)
    vivants = [o for o in bpy.data.collections["vivant"].all_objects if o is not None]
    for o in vivants:
        o.hide_render = False
        if o.type == "MESH" and not o.get("garder_uv"):
            while o.data.uv_layers:
                o.data.uv_layers.remove(o.data.uv_layers[0])
        if o.type == "MESH":
            for nom_attr in [a.name for a in o.data.color_attributes]:
                o.data.color_attributes.remove(o.data.color_attributes[nom_attr])
    bpy.ops.object.select_all(action="DESELECT")
    for coll in bpy.data.collections:
        if coll.name.startswith("atlas_") or coll.name in ("vivant", "reperes"):
            for o in [o for o in coll.all_objects if o is not None]:
                o.select_set(True)
    chemin_glb = os.path.join(opts["sortie"], "ile.glb")
    bpy.ops.export_scene.gltf(
        filepath=chemin_glb, export_format="GLB", use_selection=True, export_extras=True,
        export_materials="NONE", export_normals=True, export_texcoords=True, export_yup=True, export_apply=True,
        export_vertex_color="NAME", export_vertex_color_name="balancement",
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
        export_draco_position_quantization=15, export_draco_texcoord_quantization=15,
        export_draco_normal_quantization=8, export_draco_color_quantization=8,
        export_cameras=False, export_lights=False, export_animations=False)
    log("modèle :", os.path.relpath(chemin_glb, DEPOT), f"{os.path.getsize(chemin_glb) / 1024:.0f} Ko")


