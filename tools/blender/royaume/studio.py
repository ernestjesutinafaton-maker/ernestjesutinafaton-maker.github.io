"""Studio : soleil couchant, ciel de cuisson et carte graphique."""

import math

import bpy

from .outils import SOLEIL_DIR, log


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


