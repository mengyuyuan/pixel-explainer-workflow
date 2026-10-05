#!/usr/bin/env python3
"""Minimal pixel-sprite kit: palette grids -> PNG, with auto-outline and a preview sheet. Standard library only.

Author a character as rows of palette letters ('.' = transparent), build poses by composing parts, save each pose as a
PNG, and review them on an enlarged sheet. Scale sprites only by integers in the video (CSS image-rendering: pixelated).

Run the demo:  python3 pixel_sprite.py demo_out/
It draws a small character with 4 poses (idle, blink, talk, cheer) and writes demo_out/hero-*.png + preview.png.
"""
import os, sys, zlib, struct

PAL = {  # edit per project: one letter -> hex colour
    "K": "1a1426",                    # outline ink
    "H": "2a2230", "h": "4a4058",     # hair + sheen
    "S": "f7dac6", "s": "e3b59b",     # skin, skin shade
    "E": "1a1418", "L": "ffffff",     # eye, glint
    "R": "c9636b", "r": "5e1f2b",     # lips, mouth inside
    "U": "3a6fd8", "u": "274ea0",     # shirt, shade
    "P": "2c3446", "p": "1c2233",     # trousers
    "F": "f4f4f2", "f": "c3c6cb",     # shoes
}

def rgba(c):
    if c == ".": return (0, 0, 0, 0)
    h = PAL[c]; return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)

class Grid:
    def __init__(s, w, h): s.w, s.h = w, h; s.px = [["."] * w for _ in range(h)]
    def put(s, x, y, c):
        if 0 <= x < s.w and 0 <= y < s.h: s.px[y][x] = c
    def rect(s, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): s.put(x, y, c)
    def blit(s, rows, x0, y0):
        for j, row in enumerate(rows):
            for i, c in enumerate(row):
                if c != ".": s.put(x0 + i, y0 + j, c)
    def outline(s, ink="K"):
        add = [(x, y) for y in range(s.h) for x in range(s.w) if s.px[y][x] == "." and any(
            0 <= x + dx < s.w and 0 <= y + dy < s.h and s.px[y + dy][x + dx] not in (".", ink)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        for x, y in add: s.px[y][x] = ink
        return s

def write_png(path, rgba_rows):
    h, w = len(rgba_rows), len(rgba_rows[0])
    raw = b"".join(b"\x00" + bytes(v for p in row for v in p) for row in rgba_rows)
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))

def save(g, path): write_png(path, [[rgba(c) for c in row] for row in g.px])

def sheet(grids, path, scale=6, pad=2, bg=(40, 40, 48, 255)):
    """Enlarged review sheet of several poses side by side."""
    W = sum(g.w for g in grids) + pad * (len(grids) + 1); H = max(g.h for g in grids) + 2 * pad
    canvas = [[bg] * (W * scale) for _ in range(H * scale)]
    x0 = pad
    for g in grids:
        for y in range(g.h):
            for x in range(g.w):
                c = rgba(g.px[y][x])
                if c[3] == 0: continue
                for yy in range(scale):
                    row = canvas[(pad + y) * scale + yy]
                    for xx in range(scale): row[(x0 + x) * scale + xx] = c
        x0 += g.w + pad
    write_png(path, canvas)

# ── demo character: 20×30 art px ──
HEAD = ["....HHHHHHHHHH......", "...HHHhHHHHhHHH.....", "..HHHHHHHHHHHHHH....", "..HHSSSSSSSSSSHH....",
        "..HSSSSSSSSSSSSH....", "..SSSEESSSSEESSS....", "..SSSEESSSSEESSS....", "..SSSSSSSsSSSSSS....",
        "..SSSSSSSSSSSSSS....", "..SSSSSRRRRSSSSS....", "...SSSSSSSSSSSS.....", "....ssSSSSSSss......"]

def pose(name):
    g = Grid(20, 30)
    head = list(HEAD)
    if name == "blink": head[5] = "..SSSSSSSSSSSSSS...."; head[6] = "..SSSEESSSSEESSS...."
    if name in ("talk", "cheer"): head[9] = "..SSSSSRrrRSSSSS...."
    g.blit(head, 0, 1)
    g.rect(4, 13, 13, 21, "U"); g.rect(12, 13, 13, 21, "u")          # torso
    if name == "cheer":
        g.rect(1, 6, 2, 13, "S"); g.rect(15, 6, 16, 13, "S")          # arms up
    else:
        g.rect(2, 14, 3, 20, "S"); g.rect(14, 14, 15, 20, "S")        # arms down
    g.rect(5, 22, 8, 27, "P"); g.rect(9, 22, 12, 27, "p")              # legs
    g.rect(4, 28, 8, 29, "F"); g.rect(9, 28, 13, 29, "f")              # shoes
    return g.outline()

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "demo_out"; os.makedirs(out, exist_ok=True)
    poses = {n: pose(n) for n in ("idle", "blink", "talk", "cheer")}
    for n, g in poses.items(): save(g, os.path.join(out, f"hero-{n}.png"))
    sheet(list(poses.values()), os.path.join(out, "preview.png"))
    print(f"wrote {len(poses)} poses + preview.png to {out}/")
