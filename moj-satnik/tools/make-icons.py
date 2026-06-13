#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dependency-free generator for the "Môj šatník" app icons + splash.
Draws a clothes-hanger glyph using signed-distance fields and writes
opaque truecolour PNGs (no alpha -> App-Store safe).
"""
import zlib, struct, math, os

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "icons")
os.makedirs(OUT, exist_ok=True)

ACCENT = (196, 102, 60)    # #c4663c
CREAM  = (250, 247, 242)   # #faf7f2
WHITE  = (255, 255, 255)

# ---- hanger geometry in normalised [0,1] canvas coords (y down) ----
A  = (0.50, 0.405)          # apex (top of triangle bar)
L  = (0.275, 0.605)         # bottom-left
R  = (0.725, 0.605)         # bottom-right
HC = (0.50, 0.340)          # hook ring centre
HR = 0.052                  # hook ring radius
STROKE = 0.020              # half stroke width

SEGMENTS = [(A, L), (A, R), (L, R), (A, (0.50, HC[1] + HR))]


def _dist_seg(px, py, a, b):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    ll = dx * dx + dy * dy
    t = 0.0 if ll == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ll))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def _motif_coverage(px, py, c, scale, stroke):
    """coverage 0..1 of the hanger stroke at normalised point, scaled about centre."""
    # transform point into unscaled motif space
    ux = c + (px - c) / scale
    uy = c + (py - c) / scale
    d = min(_dist_seg(ux, uy, a, b) for a, b in SEGMENTS)
    ring = abs(math.hypot(ux - HC[0], uy - HC[1]) - HR)
    d = min(d, ring)
    aa = 1.0 / (SIZE * scale)            # ~1px anti-alias band
    return max(0.0, min(1.0, (stroke - d) / aa + 0.5))


def render(size, bg, fg, scale=1.0, vignette=False, stroke=STROKE):
    global SIZE
    SIZE = size
    c = 0.5
    bg0 = bytes(bg)
    raw = bytearray()
    # motif bounding box (with generous margin) to skip work elsewhere
    lo = int(size * (c - (c - 0.20) * scale)) - 2
    hi = int(size * (c + (0.66 - c) * scale)) + 2
    for y in range(size):
        raw.append(0)  # PNG filter type 0 for this scanline
        ny = (y + 0.5) / size
        if not vignette and not (lo <= y <= hi):
            raw += bg0 * size
            continue
        row = bytearray()
        for x in range(size):
            nx = (x + 0.5) / size
            r, g, b = bg
            if vignette:
                # subtle corner darkening for depth
                dc = math.hypot(nx - 0.5, ny - 0.5) / 0.7071
                f = 1.0 - 0.16 * dc * dc
                r, g, b = int(r * f), int(g * f), int(b * f)
            cov = _motif_coverage(nx, ny, c, scale, stroke) if lo <= y <= hi else 0.0
            if cov > 0:
                r = int(r * (1 - cov) + fg[0] * cov)
                g = int(g * (1 - cov) + fg[1] * cov)
                b = int(b * (1 - cov) + fg[2] * cov)
            row += bytes((r, g, b))
        raw += row
    return _png(size, size, raw)


def _png(w, h, raw):
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)   # 8-bit truecolour RGB
    idat = zlib.compress(bytes(raw), 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


JOBS = [
    # filename, size, bg, fg, scale, vignette
    ("icon-1024.png",          1024, ACCENT, WHITE, 1.00, True),
    ("icon-512.png",            512, ACCENT, WHITE, 1.00, True),
    ("icon-192.png",            192, ACCENT, WHITE, 1.00, True),
    ("icon-180.png",            180, ACCENT, WHITE, 1.00, True),
    ("icon-maskable-512.png",   512, ACCENT, WHITE, 0.62, False),  # safe-zone padding
    ("splash-2732.png",        2732, CREAM,  ACCENT, 0.34, False),
]

for name, size, bg, fg, scale, vig in JOBS:
    data = render(size, bg, fg, scale=scale, vignette=vig)
    with open(os.path.join(OUT, name), "wb") as fh:
        fh.write(data)
    print("wrote %-24s %5d x %-5d %7d bytes" % (name, size, size, len(data)))
