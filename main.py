#!/usr/bin/env python3
"""The World in One Picture -- 24 November 2026 world news, one image.

Draws a 1024x1024 newspaper front page summarising the day's world news
and writes it to $MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png).

STDLIB ONLY: no Pillow, no third-party imports, no external font files.
The PNG is encoded by hand (zlib + struct, IHDR/IDAT/IEND, no tIME chunk)
and every letter is rendered from a 5x7 bitmap font defined below, scaled
for headlines vs body text. Shapes are drawn with a small rasterizer on a
bytearray canvas. The output is fully deterministic: no timestamps, no
randomness, no dict-order dependence -- two runs are byte-identical.

Runs on a stock python:3.13 image with no network:  python3 -P -s main.py
"""

import binascii
import math
import os
import struct
import sys
import zlib

WIDTH = 1024
HEIGHT = 1024

# ---------------------------------------------------------------- palette
PAPER = (248, 244, 232)
INK = (22, 22, 22)
RED = (178, 34, 34)
BLUE = (30, 80, 140)
GREEN = (28, 110, 58)
ORANGE = (205, 105, 25)
GREY_RULE = (140, 130, 115)
SKY = (38, 48, 66)
SUN = (235, 130, 35)
SUN_CORE = (250, 180, 60)
SMOKE = (150, 150, 150)
SMOKE_DARK = (110, 110, 110)
EARTH = (122, 88, 52)
CRACK = (60, 40, 20)
FLAME = (220, 90, 20)
FLAME_CORE = (250, 200, 60)
STEEL = (40, 40, 50)
TRAIN = (30, 90, 160)
CHART_RED = (180, 40, 40)

# ------------------------------------------------------- 5x7 bitmap font
# Each glyph is 7 rows of 5 bits ("1" = ink). Space is blank. Unknown
# characters fall back to a blank glyph. Curly quotes / dashes are
# normalised to ASCII before drawing.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10000", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    "h": ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "00010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    "q": ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11110", "01000", "01000", "01000", "00110"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "11110", "10001", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ";": ("00000", "01100", "00000", "01100", "00100", "00000", "01000"),
    ":": ("00000", "01100", "00000", "01100", "00000", "01100", "01100"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "\u2022": ("00000", "00000", "01100", "01100", "01100", "00000", "00000"),
    "\u2014": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "*": ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
}

_BLANK = ("00000",) * 7

_NORMALISE = {
    "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u00a0": " ", "\u2011": "-",
}


def normalise(text):
    return "".join(_NORMALISE.get(ch, ch) for ch in text)


def text_width(text, scale):
    return len(normalise(text)) * 6 * scale


def wrap_text(text, scale, max_width):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    lines = []
    for paragraph in normalise(text).split("\n"):
        words = paragraph.split(" ")
        line = ""
        for word in words:
            trial = word if not line else line + " " + word
            if text_width(trial, scale) <= max_width or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
    return lines


# ------------------------------------------------------------------ canvas
class Canvas(object):
    def __init__(self, width, height, bg):
        self.w = width
        self.h = height
        self.px = bytearray(bytes(bg) * (width * height))

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        n = len(row)
        for yy in range(y0, y1):
            off = (yy * self.w + x0) * 3
            self.px[off:off + n] = row

    def rect_outline(self, x, y, w, h, color, thick=1):
        self.fill_rect(x, y, w, thick, color)
        self.fill_rect(x, y + h - thick, w, thick, color)
        self.fill_rect(x, y, thick, h, color)
        self.fill_rect(x + w - thick, y, thick, h, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        half = thick // 2
        while True:
            self.fill_rect(x - half, y - half, thick, thick, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def polyline(self, points, color, thick=1):
        for i in range(len(points) - 1):
            self.line(points[i][0], points[i][1],
                      points[i + 1][0], points[i + 1][1], color, thick)

    def fill_ellipse(self, cx, cy, rx, ry, color):
        if rx <= 0 or ry <= 0:
            return
        for dy in range(-ry, ry + 1):
            t = 1.0 - (dy * dy) / float(ry * ry)
            dx = int(rx * math.sqrt(t)) if t > 0.0 else 0
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def fill_circle(self, cx, cy, r, color):
        self.fill_ellipse(cx, cy, r, r, color)

    def fill_poly(self, pts, color):
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(min(ys), max(ys) + 1):
            xs = []
            for i in range(n):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % n]
                if (y1 <= y < y2) or (y2 <= y < y1):
                    xs.append(x1 + (y - y1) * (x2 - x1) / float(y2 - y1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                xa = int(xs[i])
                xb = int(xs[i + 1])
                self.fill_rect(xa, y, xb - xa + 1, 1, color)

    def draw_text(self, x, y, text, scale, color, align="left"):
        text = normalise(text)
        w = len(text) * 6 * scale
        if align == "center":
            x = x - w // 2
        elif align == "right":
            x = x - w
        cx = x
        for ch in text:
            glyph = FONT.get(ch, _BLANK)
            for r in range(7):
                row = glyph[r]
                for c in range(5):
                    if row[c] == "1":
                        self.fill_rect(cx + c * scale, y + r * scale,
                                       scale, scale, color)
            cx += 6 * scale


# ------------------------------------------------------------- PNG encoder
def _chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", binascii.crc32(typ + data) & 0xffffffff)
    return out


def encode_png(canvas):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)  # filter: none
        raw += canvas.px[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    return png


# ------------------------------------------------------------- page layout
def draw_lead_graphic(cv, x0, y0, w, h):
    """Antalya climate scene: dark sky, orange sun, smoke, cracked earth."""
    cv.fill_rect(x0, y0, w, h, SKY)
    cx = x0 + w // 2
    cv.fill_circle(cx, y0 + 58, 30, SUN)
    cv.fill_circle(cx, y0 + 58, 18, SUN_CORE)
    cv.fill_ellipse(x0 + 52, y0 + 118, 42, 14, SMOKE)
    cv.fill_ellipse(x0 + 130, y0 + 106, 48, 16, SMOKE_DARK)
    cv.fill_ellipse(x0 + 210, y0 + 120, 40, 13, SMOKE)
    cv.fill_ellipse(x0 + 168, y0 + 128, 34, 11, SMOKE_DARK)
    earth_y = y0 + h - 44
    cv.fill_rect(x0, earth_y, w, 44, EARTH)
    cv.polyline([(x0 + 40, earth_y + 44), (x0 + 52, earth_y + 26),
                 (x0 + 44, earth_y + 12), (x0 + 58, earth_y)],
                CRACK, 2)
    cv.polyline([(x0 + 150, earth_y + 44), (x0 + 146, earth_y + 22),
                 (x0 + 162, earth_y + 8), (x0 + 156, earth_y)],
                CRACK, 2)
    cv.polyline([(x0 + 240, earth_y + 44), (x0 + 232, earth_y + 28),
                 (x0 + 244, earth_y + 14), (x0 + 238, earth_y)],
                CRACK, 2)


def draw_flame_icon(cv, x, y):
    pts = [(x + 22, y), (x + 38, y + 18), (x + 44, y + 34),
           (x + 40, y + 52), (x + 4, y + 52), (x, y + 34), (x + 8, y + 20)]
    cv.fill_poly(pts, FLAME)
    inner = [(x + 22, y + 20), (x + 32, y + 32), (x + 34, y + 44),
             (x + 10, y + 44), (x + 12, y + 32)]
    cv.fill_poly(inner, FLAME_CORE)


def draw_drone_icon(cv, x, y):
    cv.fill_rect(x + 12, y + 22, 26, 10, STEEL)
    for ax, ay in ((x + 4, y + 8), (x + 42, y + 8),
                   (x + 4, y + 40), (x + 42, y + 40)):
        cv.line(x + 25, y + 27, ax, ay, STEEL, 2)
        cv.fill_circle(ax, ay, 5, STEEL)
        cv.fill_rect(ax - 9, ay - 1, 18, 2, STEEL)
    cv.line(x + 16, y + 32, x + 14, y + 50, STEEL, 2)
    cv.line(x + 34, y + 32, x + 36, y + 50, STEEL, 2)


def draw_chart_icon(cv, x, y):
    cv.line(x + 4, y + 50, x + 4, y + 6, INK, 2)
    cv.line(x + 4, y + 50, x + 50, y + 50, INK, 2)
    cv.polyline([(x + 8, y + 10), (x + 18, y + 20), (x + 26, y + 16),
                 (x + 34, y + 30), (x + 42, y + 26), (x + 48, y + 44)],
                CHART_RED, 3)
    cv.fill_poly([(x + 48, y + 44), (x + 40, y + 40), (x + 40, y + 48)],
                 CHART_RED)


def draw_train_icon(cv, x, y):
    cv.fill_rect(x + 2, y + 12, 50, 26, TRAIN)
    cv.fill_rect(x + 8, y + 18, 12, 8, PAPER)
    cv.fill_rect(x + 24, y + 18, 12, 8, PAPER)
    cv.fill_rect(x + 40, y + 18, 8, 8, PAPER)
    cv.fill_circle(x + 14, y + 42, 5, STEEL)
    cv.fill_circle(x + 40, y + 42, 5, STEEL)
    cv.line(x, y + 50, x + 54, y + 50, INK, 2)


def draw_panel(cv, x0, y0, w, h, kicker, kicker_color, headline_lines,
               body, icon):
    cv.rect_outline(x0, y0, w, h, GREY_RULE, 1)
    cv.fill_rect(x0, y0, w, 4, kicker_color)
    cv.draw_text(x0 + 14, y0 + 14, kicker, 2, kicker_color)
    hy = y0 + 42
    for line in headline_lines:
        cv.draw_text(x0 + 14, hy, line, 3, INK)
        hy += 24
    body_lines = wrap_text(body, 2, w - 28)
    by = y0 + 98
    for line in body_lines[:3]:
        cv.draw_text(x0 + 14, by, line, 2, INK)
        by += 18
    icon(cv, x0 + w - 68, y0 + 12)


def render_newspaper():
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    cv.rect_outline(16, 16, WIDTH - 32, HEIGHT - 32, INK, 2)

    # Masthead
    cv.draw_text(WIDTH // 2, 36, "THE WORLD IN ONE PICTURE", 6, INK,
                 align="center")
    cv.draw_text(WIDTH // 2, 94,
                 "TUESDAY, 24 NOVEMBER 2026 \u2022 THE DAY'S NEWS IN A "
                 "SINGLE IMAGE", 2, INK, align="center")
    cv.fill_rect(28, 120, WIDTH - 56, 4, RED)
    cv.fill_rect(28, 128, WIDTH - 56, 2, INK)

    # Lead story: COP31 collapses
    cv.draw_text(28, 146, "CLIMATE - COP31, ANTALYA", 2, RED)
    cv.draw_text(28, 172, "COP31 COLLAPSES", 5, INK)
    cv.draw_text(28, 212, "WITHOUT A DEAL", 5, RED)
    deck = ("Climate talks in Antalya end with no deal on fossil fuels - "
            "the first COP breakdown since 2009.")
    dy = 256
    for line in wrap_text(deck, 2, 660):
        cv.draw_text(28, dy, line, 2, INK)
        dy += 18
    draw_lead_graphic(cv, 704, 148, 292, 204)
    cv.draw_text(850, 360, "ANTALYA, TURKIYE", 2, INK, align="center")
    cv.fill_rect(28, 388, WIDTH - 56, 2, INK)

    # 2x2 story grid
    panels = [
        (28, 400, RED, "INDONESIA", ["FACTORY FIRE", "KILLS 24 IN BANTEN"],
         "Blaze at a candy factory in Banten leaves at least 24 dead and "
         "about 30 missing as rescue work goes on.", draw_flame_icon),
        (524, 400, BLUE, "UKRAINE", ["DRONE STRIKE", "HITS KYIV REGION"],
         "Several killed in a Russian drone strike; Ukraine says it sank "
         "a Russian warship off Libya.", draw_drone_icon),
        (28, 604, GREEN, "MARKETS", ["WALL STREET SHEDS", "$1 TRILLION"],
         "Stocks fall about $1 trillion after the Democrats' midterm win; "
         "Trump blames Democrats for the sell-off.", draw_chart_icon),
        (524, 604, ORANGE, "INDIA-NEPAL", ["NEW RAIL LINK",
                                            "OPENS IN AYODHYA"],
         "Modi and Nepal PM Balendra Shah flag off the Saryu-Kamala "
         "Express; Rs 15,000-crore package, 8 MoUs.", draw_train_icon),
    ]
    for (x0, y0, color, kicker, headline, body, icon) in panels:
        draw_panel(cv, x0, y0, 472, 192, kicker, color, headline, body,
                   icon)

    # Bottom strip
    cv.fill_rect(28, 804, WIDTH - 56, 2, INK)
    cv.draw_text(28, 816, "SPORT", 3, RED)
    sport = ("Verstappen wins the Las Vegas Grand Prix, his 75th victory. "
           "Pant hits 128 as the India-New Zealand 1st Test in Wellington "
           "ends in a draw.")
    sy = 848
    for line in wrap_text(sport, 2, 444):
        cv.draw_text(28, sy, line, 2, INK)
        sy += 18
    cv.fill_rect(512, 812, 2, 122, GREY_RULE)
    cv.draw_text(524, 816, "ALSO TODAY", 3, RED)
    also = ("Jensen Huang returns as Nvidia CEO. ICJ: Myanmar committed "
          "genocide against the Rohingya. Lisbon marches over living "
          "costs. Bangladesh vows to arrest Sheikh Hasina.")
    ay = 848
    for line in wrap_text(also, 2, 444):
        cv.draw_text(524, ay, line, 2, INK)
        ay += 18

    # Footer
    cv.fill_rect(28, 946, WIDTH - 56, 2, INK)
    cv.draw_text(WIDTH // 2, 958,
                 "24 NOVEMBER 2026 \u2022 COP31 \u2022 BANTEN \u2022 KYIV "
                 "\u2022 WALL STREET \u2022 AYODHYA-JANAKPUR", 2, INK,
                 align="center")
    return cv


def render_fallback():
    """Minimal page used only if the main render throws."""
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    cv.rect_outline(16, 16, WIDTH - 32, HEIGHT - 32, INK, 2)
    cv.draw_text(WIDTH // 2, 200, "THE WORLD IN ONE PICTURE", 5, INK,
                 align="center")
    cv.draw_text(WIDTH // 2, 260, "24 NOVEMBER 2026", 3, INK,
                 align="center")
    cv.draw_text(WIDTH // 2, 300, "COP31 COLLAPSES WITHOUT A DEAL", 2, RED,
                 align="center")
    return cv


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    try:
        canvas = render_newspaper()
    except Exception:
        canvas = render_fallback()
    data = encode_png(canvas)
    with open(path, "wb") as f:
        f.write(data)
    try:
        os.chmod(path, 0o644)
    except OSError:
        pass
    print("Wrote %s (%d bytes, %dx%d)" % (path, len(data), WIDTH, HEIGHT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
