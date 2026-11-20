"""Texture des feuilles : quatre tuiles peintes avec numpy (feuillu, aiguilles, cyprès, buisson fleuri)."""

import math
import os
import random
import time

import bpy
import numpy as np

from .outils import DEPOT, TUILE_AIGUILLES, TUILE_BUISSON, TUILE_CYPRES, TUILE_FEUILLU, lerp, log


class Peintre:
    """Peint des feuilles, des aiguilles et des fleurs dans une image RGBA (ligne 0 = haut de l'image)."""

    def __init__(self, taille):
        self.n = taille
        self.img = np.zeros((taille, taille, 4), dtype=np.float32)

    def _zone(self, x0, y0, x1, y1):
        x0, y0 = max(0, int(math.floor(x0))), max(0, int(math.floor(y0)))
        x1, y1 = min(self.n, int(math.ceil(x1)) + 1), min(self.n, int(math.ceil(y1)) + 1)
        if x1 <= x0 or y1 <= y0:
            return None
        Y, X = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        return x0, y0, X + 0.5, Y + 0.5

    def _poser(self, x0, y0, couleur, masque):
        h, w = masque.shape
        zone = self.img[y0:y0 + h, x0:x0 + w]
        m = masque[..., None]
        zone[..., :3] = zone[..., :3] * (1.0 - m) + couleur * m
        zone[..., 3:] = zone[..., 3:] * (1.0 - m) + m

    def feuille(self, cx, cy, ang, L, W, rgb, lumiere=1.0):
        ca, sa = math.cos(ang), math.sin(ang)
        mx, my = cx + ca * L * 0.5, cy + sa * L * 0.5
        r = L * 0.5 + W + 3
        z = self._zone(mx - r, my - r, mx + r, my + r)
        if z is None:
            return
        x0, y0, X, Y = z
        dx, dy = X - cx, Y - cy
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
        t = np.clip(u / L, 0.0, 1.0)
        # sin(pi) vaut un tout petit nombre négatif en float32 : on borne avant la puissance (sinon NaN)
        demi = 0.5 * W * np.power(np.clip(np.sin(np.pi * t), 0.0, 1.0), 0.68) * (1.0 - 0.22 * t)
        d = demi - np.abs(v)
        dedans = (u >= 0) & (u <= L)
        masque = np.where(dedans, np.clip(d + 0.5, 0.0, 1.0), 0.0).astype(np.float32)
        petiole = (u < 0) & (u > -L * 0.12) & (np.abs(v) < 1.0)
        masque = np.maximum(masque, petiole.astype(np.float32))
        if masque.max() <= 0:
            return
        bombe = np.clip(d / (demi + 1e-3), 0.0, 1.0) ** 0.5
        ton = (0.66 + 0.34 * bombe) * (0.9 + 0.15 * t) * lumiere
        ton = np.where((np.abs(v) < 1.1) & (t < 0.88) & (t > 0.02), ton * 1.16, ton)
        ton = np.where(d < 1.3, ton * 0.8, ton)
        coul = np.asarray(rgb, np.float32)[None, None, :] * ton[..., None]
        self._poser(x0, y0, coul, masque)

    def trait(self, xa, ya, xb, yb, ep, rgb_a, rgb_b=None):
        rgb_b = rgb_a if rgb_b is None else rgb_b
        z = self._zone(min(xa, xb) - ep, min(ya, yb) - ep, max(xa, xb) + ep, max(ya, yb) + ep)
        if z is None:
            return
        x0, y0, X, Y = z
        dx, dy = xb - xa, yb - ya
        l2 = dx * dx + dy * dy + 1e-6
        t = np.clip(((X - xa) * dx + (Y - ya) * dy) / l2, 0.0, 1.0)
        qx, qy = xa + t * dx, ya + t * dy
        d = np.hypot(X - qx, Y - qy)
        largeur = ep * (1.0 - 0.6 * t)
        masque = np.clip(largeur * 0.5 - d + 0.5, 0.0, 1.0)
        if masque.max() <= 0:
            return
        a, b = np.asarray(rgb_a, np.float32), np.asarray(rgb_b, np.float32)
        coul = a[None, None, :] * (1 - t[..., None]) + b[None, None, :] * t[..., None]
        self._poser(x0, y0, coul, masque)

    def ellipse(self, cx, cy, rx, ry, ang, rgb, relief=0.35):
        r = max(rx, ry) + 2
        z = self._zone(cx - r, cy - r, cx + r, cy + r)
        if z is None:
            return
        x0, y0, X, Y = z
        ca, sa = math.cos(ang), math.sin(ang)
        dx, dy = X - cx, Y - cy
        u = (dx * ca + dy * sa) / rx
        v = (-dx * sa + dy * ca) / ry
        q = np.sqrt(u * u + v * v)
        masque = np.clip((1.0 - q) * min(rx, ry) + 0.5, 0.0, 1.0)
        if masque.max() <= 0:
            return
        ton = 1.0 - relief * np.clip(q, 0, 1) ** 2 + 0.12 * np.clip(-v, 0, 1)
        coul = np.asarray(rgb, np.float32)[None, None, :] * ton[..., None]
        self._poser(x0, y0, coul, masque)


def varier(rgb, rnd, ampl=0.12, chaleur=0.0):
    k = 1.0 + rnd.uniform(-ampl, ampl)
    r, g, b = rgb
    return (min(1, r * k * (1 + chaleur)), min(1, g * k), min(1, b * k * (1 - chaleur * 0.5)))


def tuile_feuillu(p, ox, oy, t, rnd):
    c = (ox + t / 2, oy + t / 2)
    # Brindilles depuis le centre, puis les feuilles du fond vers le devant
    for k in range(9):
        a = rnd.uniform(0, 2 * math.pi)
        l = t * rnd.uniform(0.25, 0.42)
        p.trait(c[0], c[1] + t * 0.12, c[0] + math.cos(a) * l, c[1] + math.sin(a) * l, 5.0, (0.2, 0.14, 0.09))
    verts = [(0.2, 0.32, 0.1), (0.26, 0.38, 0.12), (0.32, 0.42, 0.13), (0.22, 0.36, 0.14), (0.36, 0.4, 0.12)]
    for k in range(190):
        a = rnd.uniform(0, 2 * math.pi)
        r = t * 0.42 * math.sqrt(rnd.uniform(0.02, 1.0))
        x, y = c[0] + math.cos(a) * r, c[1] + math.sin(a) * r
        ang = a + rnd.gauss(0, 0.7)
        L = rnd.uniform(0.075, 0.13) * t
        prof = 0.72 + 0.28 * min(1.0, r / (t * 0.42)) + (0.08 if k > 140 else 0.0)
        chaleur = 0.25 if rnd.random() < 0.12 else 0.0
        p.feuille(x, y, ang, L, L * rnd.uniform(0.4, 0.52), varier(rnd.choice(verts), rnd, 0.12, chaleur), prof)


def tuile_aiguilles(p, ox, oy, t, rnd):
    # Rameau de sapin : une tige du bas vers le haut, des rameaux, puis des aiguilles
    base = (ox + t * 0.5, oy + t * 0.97)
    haut = (ox + t * 0.5 + rnd.uniform(-0.05, 0.05) * t, oy + t * 0.06)
    tiges = [(base, haut)]
    for k in range(12):
        s = 0.12 + 0.07 * k
        px = lerp(base[0], haut[0], s)
        py = lerp(base[1], haut[1], s)
        cote = -1 if k % 2 else 1
        l = t * (0.36 - 0.022 * k) * rnd.uniform(0.85, 1.1)
        a = -math.pi / 2 + cote * rnd.uniform(0.75, 1.05)
        tiges.append(((px, py), (px + math.cos(a) * l, py + math.sin(a) * l)))
    for (xa, ya), (xb, yb) in tiges:
        p.trait(xa, ya, xb, yb, 4.0, (0.16, 0.11, 0.07))
    for (xa, ya), (xb, yb) in tiges:
        l = math.hypot(xb - xa, yb - ya)
        da = math.atan2(yb - ya, xb - xa)
        n = int(l / 2.6)
        for k in range(n):
            s = (k + 0.5) / n
            x, y = lerp(xa, xb, s), lerp(ya, yb, s)
            for cote in (-1, 1):
                a = da + cote * rnd.uniform(0.6, 1.0)
                la = t * rnd.uniform(0.045, 0.075) * (1.0 - 0.35 * s)
                ton = rnd.uniform(0.8, 1.15)
                p.trait(x, y, x + math.cos(a) * la, y + math.sin(a) * la, 2.4,
                        (0.07 * ton, 0.16 * ton, 0.09 * ton), (0.16 * ton, 0.3 * ton, 0.14 * ton))


def tuile_cypres(p, ox, oy, t, rnd):
    # Panache dense de petites écailles, plus clair vers le haut et vers la lumière
    for k in range(1300):
        u = rnd.gauss(0, 0.17)
        v = rnd.uniform(0.04, 0.96)
        lim = 0.36 * math.sin(math.pi * v) ** 0.6
        if abs(u) > lim:
            continue
        x, y = ox + t * (0.5 + u), oy + t * v
        r = t * rnd.uniform(0.012, 0.024)
        ton = (0.75 + 0.35 * (1 - v)) * rnd.uniform(0.85, 1.15) * (0.8 + 0.4 * (1 - abs(u) / (lim + 1e-3)) * 0.5)
        p.ellipse(x, y, r * 1.5, r, rnd.uniform(0, math.pi), (0.1 * ton, 0.21 * ton, 0.11 * ton), 0.5)


def tuile_buisson(p, ox, oy, t, rnd):
    c = (ox + t / 2, oy + t / 2)
    verts = [(0.2, 0.33, 0.12), (0.25, 0.37, 0.12), (0.3, 0.4, 0.14)]
    for k in range(420):
        a = rnd.uniform(0, 2 * math.pi)
        r = t * 0.43 * math.sqrt(rnd.uniform(0.0, 1.0))
        x, y = c[0] + math.cos(a) * r, c[1] + math.sin(a) * r
        L = rnd.uniform(0.045, 0.075) * t
        p.feuille(x, y, a + rnd.gauss(0, 0.9), L, L * rnd.uniform(0.55, 0.7), varier(rnd.choice(verts), rnd), 0.75 + 0.3 * r / (t * 0.43))
    couleurs = [(0.95, 0.55, 0.75), (0.98, 0.92, 0.95), (0.8, 0.55, 0.95), (1.0, 0.8, 0.45)]
    for k in range(46):
        a = rnd.uniform(0, 2 * math.pi)
        r = t * 0.4 * math.sqrt(rnd.uniform(0.05, 1.0))
        x, y = c[0] + math.cos(a) * r, c[1] + math.sin(a) * r
        coul = rnd.choice(couleurs)
        rp = t * rnd.uniform(0.012, 0.018)
        for s in range(5):
            b = 2 * math.pi * s / 5 + rnd.uniform(0, 0.3)
            p.ellipse(x + math.cos(b) * rp, y + math.sin(b) * rp, rp * 1.05, rp * 0.7, b, coul, 0.3)
        p.ellipse(x, y, rp * 0.55, rp * 0.55, 0, (1.0, 0.8, 0.3), 0.2)


def peindre_feuilles(sortie):
    """Texture 2048 × 2048 en 4 tuiles. Renvoie l'image Blender (pour la cuisson)."""
    t0 = time.time()
    N = 2048
    t = N // 2
    p = Peintre(N)
    rnd = random.Random(77)
    # Tuile k : colonne k % 2, rangée k // 2 en partant du BAS de l'image (convention des UV de Blender)
    for k, fn in ((TUILE_FEUILLU, tuile_feuillu), (TUILE_AIGUILLES, tuile_aiguilles),
                  (TUILE_CYPRES, tuile_cypres), (TUILE_BUISSON, tuile_buisson)):
        ox = (k % 2) * t
        oy = (1 - k // 2) * t
        fn(p, ox, oy, t, rnd)
    img = np.nan_to_num(p.img, nan=0.0)
    # Les pixels transparents prennent la couleur moyenne des feuilles : pas de liseré sombre à distance
    a = img[..., 3]
    moyenne = (img[..., :3] * a[..., None]).sum(axis=(0, 1)) / max(1.0, a.sum())
    vide = a < 0.02
    img[vide, :3] = moyenne
    img[..., :3] = np.clip(img[..., :3], 0, 1)

    def vers_blender(nom, tableau, taille):
        im = bpy.data.images.new(nom, taille, taille, alpha=True)
        im.pixels.foreach_set(np.flipud(tableau).ravel())
        return im

    os.makedirs(sortie, exist_ok=True)
    grande = vers_blender("feuilles", img, N)
    petite_np = img.reshape(N // 2, 2, N // 2, 2, 4).mean(axis=(1, 3))
    petite = vers_blender("feuilles_1024", petite_np, N // 2)
    for im, nom in ((grande, "feuilles_2048.webp"), (petite, "feuilles_1024.webp")):
        im.file_format = "WEBP"
        im.filepath_raw = os.path.join(sortie, nom)
        im.save(quality=90)
        log("texture :", os.path.relpath(im.filepath_raw, DEPOT), f"{os.path.getsize(im.filepath_raw) / 1024:.0f} Ko")
    bpy.data.images.remove(petite)
    grande.pack()
    log(f"feuilles peintes en {time.time() - t0:.1f} s")
    return grande


