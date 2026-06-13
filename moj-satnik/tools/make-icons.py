#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generátor ikon + splash pre "Môj šatník" – NOVÝ vizuál.
Gradient (fialová -> ružová) + biely vešiak a iskričky (sparkles),
kreslené cez signed-distance fields. Výstup: nepriehľadné PNG (RGB),
bez alfa kanála -> bezpečné pre App Store.
"""
import zlib, struct, math, os

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "icons")
os.makedirs(OUT, exist_ok=True)

# ---- nová paleta ----
GRAD_A = (124, 92, 255)    # #7c5cff  fialová (vľavo hore)
GRAD_B = (255, 79, 154)    # #ff4f9a  ružová  (vpravo dole)
INK    = (23, 20, 31)      # #17141f  tmavé pozadie (splash)
WHITE  = (255, 255, 255)

# ---- vešiak (normalizované [0,1], y dole) ----
A  = (0.50, 0.430)
L  = (0.285, 0.620)
R  = (0.715, 0.620)
HC = (0.50, 0.365)         # stred háčika
HR = 0.050
STROKE = 0.022
SEGMENTS = [(A, L), (A, R), (L, R), (A, (0.50, HC[1] + HR))]

# ---- iskričky: (stred_x, stred_y, vonkajší_polomer, štíhlosť) ----
SPARKLES = [
    (0.730, 0.275, 0.082, 0.30),   # veľká vpravo hore
    (0.300, 0.300, 0.046, 0.30),   # malá vľavo hore
]


def _dist_seg(px, py, a, b):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    ll = dx * dx + dy * dy
    t = 0.0 if ll == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ll))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _hanger_cov(ux, uy, size, scale):
    d = min(_dist_seg(ux, uy, a, b) for a, b in SEGMENTS)
    d = min(d, abs(math.hypot(ux - HC[0], uy - HC[1]) - HR))
    aa = 1.0 / (size * scale)
    return max(0.0, min(1.0, (STROKE - d) / aa + 0.5))


def _sparkle_cov(ux, uy, size, scale):
    best = 0.0
    aa = 1.0 / (size * scale)
    for cx, cy, ro, k in SPARKLES:
        dx = abs(ux - cx); dy = abs(uy - cy)
        sc = ro * k
        gv = dx / sc + dy / ro          # zvislý štíhly kosoštvorec
        gh = dx / ro + dy / sc          # vodorovný štíhly kosoštvorec
        s = max((1 - gv) * sc, (1 - gh) * sc)   # zjednotenie -> 4-cípa hviezda
        cov = max(0.0, min(1.0, s / aa + 0.5))
        if cov > best:
            best = cov
    return best


def _grad(nx, ny):
    t = (nx + ny) * 0.5
    return (GRAD_A[0] + (GRAD_B[0] - GRAD_A[0]) * t,
            GRAD_A[1] + (GRAD_B[1] - GRAD_A[1]) * t,
            GRAD_A[2] + (GRAD_B[2] - GRAD_A[2]) * t)


def render(size, mode, scale=1.0):
    """mode: 'grad' = gradient pozadie, 'ink' = tmavé jednofarebné pozadie."""
    c = 0.5
    flat = bytes(INK) if mode == "ink" else None
    # bounding box motívu (vešiak + iskričky) so scale, s rezervou
    lo = int(size * (c - (c - 0.18) * scale)) - 2
    hi = int(size * (c + (0.66 - c) * scale)) + 2
    raw = bytearray()
    for y in range(size):
        raw.append(0)  # filter byte
        ny = (y + 0.5) / size
        in_band = lo <= y <= hi
        if mode == "ink" and not in_band:
            raw += flat * size
            continue
        row = bytearray()
        for x in range(size):
            nx = (x + 0.5) / size
            if mode == "grad":
                r, g, b = _grad(nx, ny)
                dc = math.hypot(nx - 0.5, ny - 0.5) / 0.7071
                f = 1.0 - 0.12 * dc * dc            # jemná vinetácia
                r, g, b = r * f, g * f, b * f
            else:
                r, g, b = INK
            if in_band:
                ux = c + (nx - c) / scale
                uy = c + (ny - c) / scale
                cov = _hanger_cov(ux, uy, size, scale)
                cov = max(cov, _sparkle_cov(ux, uy, size, scale))
                if cov > 0:
                    r = r * (1 - cov) + WHITE[0] * cov
                    g = g * (1 - cov) + WHITE[1] * cov
                    b = b * (1 - cov) + WHITE[2] * cov
            row += bytes((int(r), int(g), int(b)))
        raw += row
    return _png(size, size, raw)


def _png(w, h, raw):
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


JOBS = [
    # filename, size, mode, scale
    ("icon-1024.png",          1024, "grad", 1.00),
    ("icon-512.png",            512, "grad", 1.00),
    ("icon-192.png",            192, "grad", 1.00),
    ("icon-180.png",            180, "grad", 1.00),
    ("icon-maskable-512.png",   512, "grad", 0.64),  # safe-zone pre Android
    ("splash-icon-1024.png",   1024, "ink",  1.00),  # Expo splash (na INK pozadí)
    ("splash-2732.png",        2732, "ink",  0.42),  # Capacitor full splash
]

for name, size, mode, scale in JOBS:
    data = render(size, mode, scale=scale)
    with open(os.path.join(OUT, name), "wb") as fh:
        fh.write(data)
    print("wrote %-26s %5d  %-5s scale=%.2f  %7d B" % (name, size, mode, scale, len(data)))
