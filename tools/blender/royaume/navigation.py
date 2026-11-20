"""
Carte de marche et chemins des personnages, pour le mode « Explorer librement » du site.

  royaume_carte.png   une grille de 0,5 m sur tout le royaume. Rouge et vert : la hauteur du sol (16 bits,
                      de -20 m à +80 m). Bleu : bit 0 = praticable, bit 1 = à l'intérieur d'un bâtiment,
                      bits 2 à 4 = numéro du bâtiment (1 atelier, 2 guilde, 3 grande salle, 4 forge).
  royaume.json        la taille de la grille, et les chemins des personnages (rues, piste, avenue,
                      chemins de ronde, place, champs, pâturage), en coordonnées du site (Y vers le haut).

On marque d'abord les obstacles (bâtiments, meubles, arbres, murs, eau) dans la grille, puis on calcule
la hauteur de chaque case praticable.
"""

import json
import math
import os
import random
import time

import bpy
import numpy as np

from . import plan
from .outils import log, polaire, reechantillonner

PAS = 0.5
DEMI = 128.0          # la grille couvre [-128 m, 128 m] en x et en y
H_MIN, H_MAX = -20.0, 80.0


def _vers_site(x, y, z):
    """Coordonnées de Blender (Z vers le haut) vers celles du site (Y vers le haut)."""
    return [round(x, 2), round(z, 2), round(-y, 2)]


def _cases_rect(cx, cy, ang, dx, dy, n, X, Y):
    """Masque des cases dans un rectangle orienté."""
    r = math.hypot(dx, dy) + PAS
    i0, i1 = max(0, int((cx - r + DEMI) / PAS)), min(n, int((cx + r + DEMI) / PAS) + 1)
    j0, j1 = max(0, int((cy - r + DEMI) / PAS)), min(n, int((cy + r + DEMI) / PAS) + 1)
    if i1 <= i0 or j1 <= j0:
        return None
    sx, sy = X[j0:j1, i0:i1] - cx, Y[j0:j1, i0:i1] - cy
    u = sx * math.cos(ang) + sy * math.sin(ang)
    v = -sx * math.sin(ang) + sy * math.cos(ang)
    return (slice(j0, j1), slice(i0, i1)), (np.abs(u) <= dx) & (np.abs(v) <= dy), u, v


def carte_de_marche(sortie):
    t0 = time.time()
    n = int(2 * DEMI / PAS)
    xs = -DEMI + (np.arange(n) + 0.5) * PAS
    X, Y = np.meshgrid(xs, xs)
    R = np.hypot(X, Y)
    A = np.arctan2(Y, X)
    bloque = np.zeros((n, n), dtype=bool)
    interieur = np.zeros((n, n), dtype=np.uint8)
    hauteur = np.full((n, n), np.nan, dtype=np.float32)
    # Bord de l'île
    angles = np.linspace(-math.pi, math.pi, 721)
    bords = np.array([plan.rayon_bord(a) for a in angles])
    bloque |= R > np.interp(A, angles, bords) - 1.2
    # Remparts (sauf dans le passage des portes)
    for nom, m in plan.REMPARTS.items():
        bande = np.abs(R - m["rayon"]) < m["epaisseur"] / 2 + 0.5
        for a in plan.PORTES[nom]:
            ecart = np.abs((A - a + math.pi) % (2 * math.pi) - math.pi) * R
            passage = (ecart < (2.3 if nom == "interieur" else 2.6)) & (np.abs(R - m["rayon"]) < m["epaisseur"] / 2 + 2.5)
            bande &= ~passage
        bloque |= bande
    # Eau : la rivière et l'étang (les ponts sont rouverts plus bas)
    pts = np.array(plan.RIVIERE)
    d = np.full((n, n), 1e9, dtype=np.float32)
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        vx, vy = bx - ax, by - ay
        l2 = vx * vx + vy * vy
        t = np.clip(((X - ax) * vx + (Y - ay) * vy) / l2, 0, 1)
        d = np.minimum(d, np.hypot(X - (ax + t * vx), Y - (ay + t * vy)))
    bloque |= (d < plan.LARGEUR_RIVIERE + 0.2) & (R > 60)
    (ex, ey), er = plan.ETANG
    bloque |= np.hypot(X - ex, Y - ey) < er + 0.6
    # Bâtiments, meubles, arbres, étals
    for cx, cy, ang, dx, dy in plan.EMPRISES:
        r = _cases_rect(cx, cy, ang, dx + 0.15, dy + 0.15, n, X, Y)
        if r:
            (sj, si), masque, _, _ = r
            bloque[sj, si] |= masque
    for ox, oy, orr in plan.OBSTACLES:
        i0, i1 = max(0, int((ox - orr + DEMI) / PAS)), min(n, int((ox + orr + DEMI) / PAS) + 1)
        j0, j1 = max(0, int((oy - orr + DEMI) / PAS)), min(n, int((oy + orr + DEMI) / PAS) + 1)
        if i1 > i0 and j1 > j0:
            bloque[j0:j1, i0:i1] |= np.hypot(X[j0:j1, i0:i1] - ox, Y[j0:j1, i0:i1] - oy) < orr
    # Hauteur du sol des cases restées libres
    libres = np.argwhere(~bloque)
    for j, i in libres:
        hauteur[j, i] = plan.hauteur(float(X[j, i]), float(Y[j, i]))
    # Ponts : on marche sur le tablier
    for px, py, ang, dl, dw, hz in plan.PONTS:
        r = _cases_rect(px, py, ang, dl, dw, n, X, Y)
        if r:
            (sj, si), masque, u, _ = r
            courbe = hz - 0.55 * (2 * u / dl) ** 2
            bloque[sj, si] &= ~masque
            hauteur[sj, si] = np.where(masque, courbe, hauteur[sj, si])
    # Intérieurs : le plancher, les murs (sauf la porte), et le numéro du bâtiment
    for b in plan.INTERIEURS:
        L, w, dd, sol = b["L"], b["largeur"], b["profondeur"], b["sol"]
        centre = L @ __import__("mathutils").Vector((0, dd / 2, 0))
        axe = L.to_3x3() @ __import__("mathutils").Vector((1, 0, 0))
        ang = math.atan2(axe.y, axe.x)
        r = _cases_rect(centre.x, centre.y, ang, w / 2 + 0.6, dd / 2 + 0.6, n, X, Y)
        if not r:
            continue
        (sj, si), masque, u, v = r
        v = v + dd / 2                     # v : profondeur depuis la façade
        dedans = (np.abs(u) < w / 2 - 0.55) & (v > 0.55) & (v < dd - 0.55)
        mur = masque & ~dedans
        porte = (u > b["porte"][0] + 0.3) & (u < b["porte"][1] - 0.3) & (v < 1.0) & (v > -0.6)
        meubles = bloque[sj, si] & dedans
        bloque[sj, si] = np.where(mur & ~porte, True, np.where(dedans, meubles, bloque[sj, si]))
        hauteur[sj, si] = np.where(dedans | porte, sol, hauteur[sj, si])
        interieur[sj, si] = np.where(dedans, 2 | (b["zone"] << 2), interieur[sj, si])
    # Pentes trop raides
    gy, gx = np.gradient(np.nan_to_num(hauteur, nan=0.0), PAS)
    bloque |= np.hypot(gx, gy) > 1.1
    bloque |= np.isnan(hauteur)
    # Encodage RGBA (ligne 0 = y le plus grand, comme une image vue de dessus avec le nord en haut)
    h = np.clip((np.nan_to_num(hauteur, nan=H_MIN) - H_MIN) / (H_MAX - H_MIN), 0, 1)
    h16 = np.round(h * 65535).astype(np.uint32)
    drapeaux = np.where(bloque, 0, 1).astype(np.uint8) | interieur
    rgba = np.zeros((n, n, 4), dtype=np.float32)
    rgba[..., 0] = (h16 >> 8) / 255.0
    rgba[..., 1] = (h16 & 255) / 255.0
    rgba[..., 2] = drapeaux / 255.0
    rgba[..., 3] = 1.0
    img = bpy.data.images.new("royaume_carte", n, n, alpha=True)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(rgba.ravel())       # la ligne 0 de Blender est en bas : y croissant vers le haut de l'image
    img.filepath_raw = os.path.join(sortie, "royaume_carte.png")
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    log(f"carte de marche : {n} × {n} cases, {int((~bloque).sum())} praticables ({time.time() - t0:.0f} s)")
    return n


def chemins(sortie, n, chemins_ronde):
    rnd = random.Random(5)
    donnees = {"pas": PAS, "demi": DEMI, "taille": n, "hauteurMin": H_MIN, "hauteurMax": H_MAX}
    rue = []
    for k in range(240):
        a = 2 * math.pi * k / 240
        x, y = polaire(plan.R_RUE, a)
        if plan.dist_place(x, y) < 0:
            continue
        rue.append(_vers_site(x, y, 0))
    donnees["rue"] = rue
    donnees["radiales"] = []
    for a in plan.RADIALES:
        if abs(a - plan.SUD) < 0.01:
            continue
        seg = [_vers_site(*polaire(r, a), 0) for r in np.linspace(30.5, 54.0, 12)]
        donnees["radiales"].append(seg)
    donnees["avenue"] = [_vers_site(0.0, y, 0) for y in np.linspace(-108.0, -20.0, 45)]
    donnees["piste"] = [_vers_site(*polaire(plan.R_PISTE, 2 * math.pi * k / 160), 0) for k in range(160)]
    px, py, pr = plan.PLACE
    donnees["place"] = [_vers_site(px + math.cos(a) * r, py + math.sin(a) * r, 0)
                        for a, r in ((rnd.uniform(-math.pi, math.pi), rnd.uniform(4.0, pr - 1.5)) for _ in range(40))]
    champs = []
    for _ in range(400):
        x, y = polaire(rnd.uniform(63.0, 79.0), rnd.uniform(-math.pi, math.pi))
        c = plan.champ(x, y)
        if c is not None and c[0] in (1, 2, 4, 6) and plan.libre(x, y, 0.5):
            champs.append(_vers_site(x, y, 0))
        if len(champs) >= 40:
            break
    donnees["champs"] = champs
    a0, a1, r0, r1 = plan.PATURAGE
    donnees["paturage"] = {"angles": [a0, a1], "rayons": [r0 + 1.0, r1 - 1.0]}
    donnees["remparts"] = {nom: [_vers_site(*p) for p in pts] for nom, pts in chemins_ronde.items()}
    donnees["cheminPhare"] = [_vers_site(x, y, 0) for x, y in plan.CHEMIN_PHARE]
    chemin = os.path.join(sortie, "royaume.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, separators=(",", ":"))
    log(f"chemins des personnages : {os.path.getsize(chemin) / 1024:.0f} Ko")
