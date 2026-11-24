#!/usr/bin/env python3
"""news-image-20261124 — "The World in One Picture".

Draws a 1024x1024 newspaper front page summing up 24 November 2026 world
news, using ONLY the Python standard library: a hand-encoded PNG
(zlib + struct, no tIME chunk), a bitmap font defined in this file, and a
small rasterizer on a bytearray canvas. Deterministic: no timestamps, no
randomness, no network. Two runs produce byte-identical output.

Run: python3 main.py  (writes $MAKEFUN_OUTPUT_DIR/entry.png, default /output)
"""

import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (248, 244, 232)
INK = (26, 26, 26)
RED = (176, 30, 36)
DARKRED = (140, 20, 25)
BLUE = (28, 68, 128)
TEAL = (18, 110, 105)
ORANGE = (224, 110, 30)
GOLD = (212, 160, 32)
GREY = (110, 110, 108)
LIGHTGREY = (214, 208, 194)
SKY = (52, 68, 96)
SMOKE = (150, 148, 142)
EARTH = (146, 104, 62)
WHITE = (255, 255, 255)

# ------------------------------------------------------- 5x7 bitmap font
# Each glyph: 7 rows of 5 characters, '#' = on, '.' = off.
FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    'a': (".....", ".....", ".####.", "....#", ".####", "#...#", ".###."),
    'b': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    'c': (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    'd': ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".###."),
    'e': (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    'f': ("..##.", ".#..#", ".#...", "####.", ".#...", ".#...", ".#..."),
    'g': (".....", ".....", ".####", "#...#", "#...#", ".###.", "....#"),
    'h': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'i': ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    'j': ("...#.", ".....", "..##.", "...#.", "...#.", "...#.", "...#.", ".##.."),
    'k': ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    'l': (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'm': (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    'n': (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'o': (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    'p': (".....", ".....", "####.", "#...#", "#...#", "####.", "#...."),
    'q': (".....", ".....", ".####", "#...#", "#...#", ".###.", "....#"),
    'r': (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    's': (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    't': (".#...", ".#...", "####.", ".#...", ".#...", ".#...", "..##."),
    'u': (".....", ".....", "#...#", "#...#", "#...#", "#...#", ".###."),
    'v': (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'w': (".....", ".....", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'x': (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    'y': (".....", ".....", "#...#", "#...#", "#...#", ".###.", "....#"),
    'z': (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
}

# ------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        r, g, b = bg
        for i in range(0, len(self.px), 3):
            self.px[i] = r
            self.px[i + 1] = g
            self.px[i + 2] = b

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        r, g, b = color
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b

    def rect(self, x, y, w, h, color, t=1):
        for k in range(t):
            self.fill_rect(x, y + k, w, 1, color)
            self.fill_rect(x, y + h - 1 - k, w, 1, color)
            self.fill_rect(x + k, y, 1, h, color)
            self.fill_rect(x + w - 1 - k, y, 1, h, color)

    def hline(self, x, y, w, color, t=1):
        self.fill_rect(x, y, w, t, color)

    def vline(self, x, y, h, color, t=1):
        self.fill_rect(x, y, t, h, color)

    def line(self, x0, y0, x1, y1, color):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.set(x, y, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def fill_ellipse(self, cx, cy, rx, ry, color):
        for yy in range(cy - ry, cy + ry + 1):
            dy = (yy - cy) / float(ry)
            if abs(dy) > 1:
                continue
            dx = int(rx * (1 - dy * dy) ** 0.5)
            self.fill_rect(cx - dx, yy, 2 * dx + 1, 1, color)

    def fill_circle(self, cx, cy, r, color):
        self.fill_ellipse(cx, cy, r, r, color)

    def fill_polygon(self, pts, color):
        # scanline fill, deterministic order
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if y0 == y1:
                    continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / float(y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                x0 = int(xs[k] + 0.5)
                x1 = int(xs[k + 1] + 0.5)
                if x1 >= x0:
                    self.fill_rect(x0, y, x1 - x0 + 1, 1, color)


# ------------------------------------------------------------- text
def text_width(s, scale):
    return len(s) * 6 * scale


def draw_text(cv, x, y, s, scale, color):
    cx = x
    for ch in s:
        glyph = FONT.get(ch)
        if glyph is None:
            cx += 6 * scale
            continue
        for row in range(7):
            grow = glyph[row]
            for col in range(5):
                if grow[col] == '#':
                    cv.fill_rect(cx + col * scale, y + row * scale,
                                 scale, scale, color)
        cx += 6 * scale
    return cx


def wrap_text(s, scale, max_w):
    """Greedy word wrap; returns list of lines that fit max_w."""
    words = s.split(' ')
    lines = []
    cur = ''
    for wd in words:
        trial = wd if not cur else cur + ' ' + wd
        if text_width(trial, scale) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(cv, x, y, s, scale, color, max_w, leading=None):
    if leading is None:
        leading = 7 * scale + 4
    lines = wrap_text(s, scale, max_w)
    for ln in lines:
        draw_text(cv, x, y, ln, scale, color)
        y += leading
    return y

FONT.update({
    '0': (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "..#..", "..#..", ".#...", ".#..."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ';': (".....", ".....", ".##..", ".##..", ".....", ".##..", ".#..."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    '-': (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    '/': ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    '(': ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ')': (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    '\u2022': (".....", ".....", ".##..", ".##..", ".....", ".....", "....."),
    '\u2014': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    '%': ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
    '&': (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    '+': (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    '=': (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    '*': (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
    '$': ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    '@': (".###.", "#...#", "#.###", "#.#.#", "#.#..", "#....", ".###."),
    '#': (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    '_': (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    '~': (".....", ".....", ".##.#", "#.#..", ".....", ".....", "....."),
    '<': ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    '>': (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    '[': (".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    ']': (".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
    '{': ("..##.", "..#..", "..#..", ".##..", "..#..", "..#..", "..##."),
    '}': (".##..", "..#..", "..#..", "..##.", "..#..", "..#..", ".##.."),
    '|': ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    '\\': ("#....", "#....", ".#...", "..#..", "...#.", "....#", "....#"),
    '^': ("..#..", ".#.#.", ".....", ".....", ".....", ".....", "....."),
})


# ------------------------------------------------------------- PNG encode
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: none
        start = y * cv.w * 3
        raw += cv.px[start:start + cv.w * 3]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    return png


# ------------------------------------------------------------- icons
def icon_flame(cv, x, y):
    # stylised flame: outer orange, inner red, base gold
    cv.fill_polygon([(x + 30, y), (x + 52, y + 26), (x + 58, y + 44),
                     (x + 44, y + 56), (x + 16, y + 56), (x + 2, y + 44),
                     (x + 8, y + 26)], ORANGE)
    cv.fill_polygon([(x + 30, y + 20), (x + 44, y + 36), (x + 40, y + 52),
                     (x + 20, y + 52), (x + 16, y + 36)], RED)
    cv.fill_rect(x, y + 56, 60, 4, GOLD)


def icon_drone(cv, x, y):
    # quadcopter seen from above: body + 4 rotors
    cv.fill_rect(x + 20, y + 18, 20, 20, INK)
    cv.fill_rect(x + 24, y + 24, 12, 8, SKY)
    for (rx, ry) in ((x, y), (x + 44, y), (x, y + 40), (x + 44, y + 40)):
        cv.fill_circle(rx + 8, ry + 8, 8, GREY)
        cv.fill_circle(rx + 8, ry + 8, 3, INK)
        cv.line(rx + 8, ry + 8, x + 30, y + 28, INK)


def icon_chart(cv, x, y):
    # axes + falling line
    cv.vline(x + 4, y, 52, INK, 2)
    cv.hline(x + 4, y + 50, 56, INK, 2)
    pts = [(x + 8, y + 10), (x + 20, y + 16), (x + 30, y + 12),
           (x + 42, y + 30), (x + 54, y + 44)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], RED)
        cv.line(a[0], a[1] + 1, b[0], b[1] + 1, RED)
    cv.fill_polygon([(x + 48, y + 40), (x + 58, y + 44), (x + 50, y + 50)],
                    RED)


def icon_train(cv, x, y):
    # front of a train: body, windows, stripe, wheels
    cv.fill_rect(x + 6, y + 4, 48, 40, BLUE)
    cv.fill_rect(x + 6, y + 4, 48, 8, GOLD)
    cv.fill_rect(x + 12, y + 16, 14, 12, WHITE)
    cv.fill_rect(x + 34, y + 16, 14, 12, WHITE)
    cv.fill_rect(x + 6, y + 32, 48, 4, WHITE)
    cv.fill_circle(x + 16, y + 48, 6, INK)
    cv.fill_circle(x + 44, y + 48, 6, INK)
    cv.line(x + 4, y + 56, x + 56, y + 56, INK)
    cv.line(x + 10, y + 58, x + 50, y + 58, INK)


# ------------------------------------------------------------- layout
MX = 28            # left margin
RX = 996           # right edge (1024 - 28)
CW = RX - MX       # content width = 968


def draw_masthead(cv):
    title = "THE WORLD IN ONE PICTURE"
    tw = text_width(title, 5)
    draw_text(cv, (W - tw) // 2, 38, title, 5, INK)
    sub = "TUESDAY, 24 NOVEMBER 2026 - THE DAY'S NEWS IN A SINGLE IMAGE"
    sw = text_width(sub, 2)
    draw_text(cv, (W - sw) // 2, 92, sub, 2, RED)
    cv.hline(MX, 120, CW, INK, 3)
    cv.hline(MX, 127, CW, RED, 2)


def draw_lead(cv):
    y0 = 136
    draw_text(cv, MX + 16, y0 + 10, "CLIMATE - COP31, ANTALYA", 2, RED)
    draw_text(cv, MX + 16, y0 + 34, "COP31 COLLAPSES", 4, INK)
    draw_text(cv, MX + 16, y0 + 70, "WITHOUT A DEAL", 4, RED)
    deck = ("Climate talks in Antalya end with no deal on fossil fuels "
            "- the first COP breakdown since 2009.")
    draw_wrapped(cv, MX + 16, y0 + 116, deck, 2, INK, 640)
    # graphic: dark sky, orange sun, grey smoke, cracked earth
    gx, gy, gw, gh = 700, y0 + 10, 280, 222
    cv.fill_rect(gx, gy, gw, 150, SKY)
    cv.fill_circle(gx + 140, gy + 62, 34, ORANGE)
    cv.fill_circle(gx + 140, gy + 62, 22, GOLD)
    cv.fill_ellipse(gx + 64, gy + 96, 34, 16, SMOKE)
    cv.fill_ellipse(gx + 186, gy + 108, 44, 18, SMOKE)
    cv.fill_ellipse(gx + 120, gy + 122, 36, 12, SMOKE)
    cv.fill_rect(gx, gy + 150, gw, gh - 150, EARTH)
    cv.line(gx + 30, gy + 150, gx + 70, gy + 190, INK)
    cv.line(gx + 70, gy + 190, gx + 60, gy + 222, INK)
    cv.line(gx + 190, gy + 150, gx + 170, gy + 200, INK)
    cv.line(gx + 170, gy + 200, gx + 200, gy + 222, INK)
    cv.line(gx + 120, gy + 150, gx + 130, gy + 180, INK)
    cv.rect(gx, gy, gw, gh, INK, 2)
    draw_text(cv, gx + 16, gy + 136, "ANTALYA, TURKIYE", 1, WHITE)
    cv.hline(MX, 384, CW, INK, 2)


def draw_panel(cv, x, y, w, h, kicker, kcolor, lines, body, icon):
    cv.rect(x, y, w, h, INK, 1)
    cv.fill_rect(x + 1, y + 1, w - 2, 5, kcolor)
    draw_text(cv, x + 16, y + 18, kicker, 2, kcolor)
    ly = y + 48
    for ln, col in lines:
        draw_text(cv, x + 16, ly, ln, 3, col)
        ly += 26
    draw_wrapped(cv, x + 16, y + 112, body, 2, INK, w - 32)
    icon(cv, x + w - 84, y + 14)


def draw_grid(cv):
    pw, ph = 478, 196
    gap = 12
    y1, y2 = 396, 604
    draw_panel(cv, MX, y1, pw, ph, "INDONESIA - BANTEN", RED,
               [("FACTORY FIRE", INK), ("KILLS AT LEAST 24", RED)],
               "Candy factory blaze in Banten leaves 24 dead and about "
               "30 missing.", icon_flame)
    draw_panel(cv, MX + pw + gap, y1, pw, ph, "UKRAINE - KYIV", BLUE,
               [("DRONE STRIKE HITS", INK), ("KYIV REGION", BLUE)],
               "Several killed as Russian drones strike; a Russian "
               "warship is sunk off Libya.", icon_drone)
    draw_panel(cv, MX, y2, pw, ph, "MARKETS - WALL ST", TEAL,
               [("WALL STREET SHEDS", INK), ("$1 TRILLION", TEAL)],
               "Stocks plunge after the Democrats' midterm win; Trump "
               "blames Democrats.", icon_chart)
    draw_panel(cv, MX + pw + gap, y2, pw, ph, "INDIA-NEPAL - RAIL", ORANGE,
               [("NEW EXPRESS LINKS", INK), ("AYODHYA-JANAKPUR", ORANGE)],
               "Modi and Nepal PM flag off the Saryu-Kamala Express; "
               "Rs 15,000-crore package.", icon_train)
    cv.hline(MX, 812, CW, INK, 2)


def draw_bottom(cv):
    draw_text(cv, MX, 830, "SPORT", 2, RED)
    draw_wrapped(cv, MX, 858,
                 "Verstappen wins the Las Vegas Grand Prix, his 75th "
                 "victory. Pant hits 128 as India-NZ first Test ends in "
                 "a draw.", 2, INK, 446)
    cv.vline(506, 824, 116, INK, 1)
    draw_text(cv, 518, 830, "ALSO TODAY", 2, RED)
    draw_wrapped(cv, 518, 858,
                 "ICJ rules Myanmar committed genocide vs the Rohingya. "
                 "Lisbon marches over living costs. Dhaka vows Hasina "
                 "arrest if she returns.", 2, INK, 446)
    cv.hline(MX, 952, CW, INK, 2)
    foot = ("24 NOVEMBER 2026 - COP31 - BANTEN - KYIV - WALL STREET - "
            "AYODHYA-JANAKPUR")
    fw = text_width(foot, 2)
    draw_text(cv, (W - fw) // 2, 964, foot, 2, INK)


def render():
    cv = Canvas(W, H, PAPER)
    cv.rect(16, 16, W - 32, H - 32, INK, 2)
    draw_masthead(cv)
    draw_lead(cv)
    draw_grid(cv)
    draw_bottom(cv)
    return cv


def fallback():
    cv = Canvas(W, H, PAPER)
    cv.rect(16, 16, W - 32, H - 32, INK, 2)
    draw_text(cv, 137, 38, "THE WORLD IN ONE PICTURE", 5, INK)
    draw_text(cv, 152, 92,
              "TUESDAY, 24 NOVEMBER 2026 - THE DAY'S NEWS IN A SINGLE IMAGE",
              2, RED)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    try:
        cv = render()
    except Exception as exc:  # never fail the run on a render error
        print("render failed: %r; writing fallback" % (exc,),
              file=sys.stderr)
        try:
            cv = fallback()
        except Exception:
            cv = Canvas(W, H, PAPER)
    data = encode_png(cv)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(data)
    os.chmod(path, 0o644)
    print("wrote %s (%d bytes, %dx%d)" % (path, len(data), W, H))
    return 0


if __name__ == "__main__":
    sys.exit(main())

