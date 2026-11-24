#!/usr/bin/env python3
"""news-image-20261124 — Sum up 24 November 2026's world news in one image.

Draws a 1024x1024 newspaper front page with Pillow. Fully deterministic:
fixed fonts, fixed layout, no network, no timestamps, no randomness, so two
runs produce byte-identical PNG output.

Run:  python3 main.py
Writes: /output/entry.png  (PNG, 1024x1024, mode 0644)
"""

import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
MARGIN = 36

PAPER = (248, 244, 232)
INK = (26, 26, 26)
RED = (176, 30, 30)
BLUE = (30, 70, 140)
GREEN = (20, 110, 60)
ORANGE = (200, 90, 20)
GREY = (110, 110, 105)
LIGHT_GREY = (200, 196, 184)

SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, max_width):
    """Wrap text into lines that fit max_width pixels (measured, not guessed)."""
    lines = []
    for para in text.split("\n"):
        words = para.split()
        if not words:
            lines.append("")
            continue
        cur = words[0]
        for word in words[1:]:
            trial = cur + " " + word
            if draw.textlength(trial, font=fnt) <= max_width:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def draw_centered(draw, y, text, fnt, fill, x0=0, x1=W):
    w = draw.textlength(text, font=fnt)
    draw.text(((x0 + x1 - w) / 2, y), text, font=fnt, fill=fill)


def draw_lead_graphic(draw):
    """COP31 graphic: dark sky, orange sun, grey smoke, cracked earth."""
    x0, y0, x1, y1 = 684, 158, 988, 384
    draw.rectangle([x0, y0, x1, y1], fill=(52, 58, 74), outline=INK, width=2)
    # Orange sun, half-hidden by smoke.
    draw.ellipse([x0 + 160, y0 + 22, x0 + 240, y0 + 102], fill=(232, 120, 30))
    # Grey smoke clouds, kept small so the sun stays visible.
    for cx, cy, rx, ry in ((x0 + 55, y0 + 55, 48, 22), (x0 + 120, y0 + 36, 55, 20),
                           (x0 + 225, y0 + 105, 55, 22), (x0 + 80, y0 + 120, 52, 20)):
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(120, 122, 126))
    # Cracked earth at the bottom.
    draw.rectangle([x0, y1 - 52, x1, y1], fill=(146, 104, 62))
    draw.line([x0 + 210, y1 - 52, x0 + 240, y1 - 26, x0 + 228, y1 - 8],
              fill=(70, 45, 20), width=3)
    draw.line([x0 + 260, y1 - 52, x0 + 272, y1 - 30, x0 + 258, y1 - 10],
              fill=(70, 45, 20), width=3)
    draw.text((x0 + 8, y1 - 22), "ANTALYA, TURKIYE", font=font(SANS_BOLD, 15),
              fill=(255, 255, 255))


def draw_flame(draw, cx, cy, s):
    """Simple flame icon centred at (cx, cy), size s."""
    pts = [(cx, cy - s), (cx + s * 0.62, cy - s * 0.1), (cx + s * 0.45, cy + s * 0.5),
           (cx + s * 0.15, cy + s * 0.75), (cx - s * 0.3, cy + s * 0.75),
           (cx - s * 0.55, cy + s * 0.4), (cx - s * 0.5, cy - s * 0.2)]
    draw.polygon(pts, fill=(220, 70, 20))
    inner = [(cx, cy + s * 0.1), (cx + s * 0.28, cy + s * 0.35),
             (cx + s * 0.1, cy + s * 0.6), (cx - s * 0.2, cy + s * 0.6),
             (cx - s * 0.25, cy + s * 0.3)]
    draw.polygon(inner, fill=(250, 200, 40))


def draw_drone(draw, cx, cy, s):
    """Simple drone icon centred at (cx, cy), size s."""
    draw.rectangle([cx - s * 0.45, cy - s * 0.18, cx + s * 0.45, cy + s * 0.18],
                   fill=(40, 60, 90))
    for dx in (-1, 1):
        draw.ellipse([cx + dx * s * 0.75 - s * 0.28, cy - s * 0.55,
                      cx + dx * s * 0.75 + s * 0.28, cy - s * 0.05],
                     outline=(40, 60, 90), width=3)
        draw.line([cx + dx * s * 0.45, cy, cx + dx * s * 0.75, cy - s * 0.3],
                  fill=(40, 60, 90), width=3)


def draw_chart(draw, cx, cy, s):
    """Rising chart icon centred at (cx, cy), size s."""
    draw.line([cx - s * 0.8, cy + s * 0.6, cx + s * 0.8, cy + s * 0.6],
              fill=INK, width=2)
    pts = [(cx - s * 0.7, cy + s * 0.35), (cx - s * 0.3, cy + s * 0.05),
           (cx, cy + s * 0.2), (cx + s * 0.35, cy - s * 0.35),
           (cx + s * 0.7, cy - s * 0.55)]
    draw.line(pts, fill=GREEN, width=4, joint="curve")
    draw.polygon([(cx + s * 0.7, cy - s * 0.55), (cx + s * 0.45, cy - s * 0.55),
                  (cx + s * 0.7, cy - s * 0.3)], fill=GREEN)


def draw_train(draw, cx, cy, s):
    """Simple train icon centred at (cx, cy), size s."""
    draw.rectangle([cx - s * 0.75, cy - s * 0.5, cx + s * 0.75, cy + s * 0.35],
                   fill=(180, 60, 20))
    draw.rectangle([cx - s * 0.6, cy - s * 0.35, cx - s * 0.15, cy - s * 0.05],
                   fill=(255, 255, 255))
    draw.rectangle([cx + s * 0.05, cy - s * 0.35, cx + s * 0.5, cy - s * 0.05],
                   fill=(255, 255, 255))
    for wx in (-0.45, 0.0, 0.45):
        draw.ellipse([cx + wx * s - s * 0.14, cy + s * 0.35,
                      cx + wx * s + s * 0.14, cy + s * 0.63],
                     fill=INK)
    draw.line([cx - s * 0.9, cy + s * 0.7, cx + s * 0.9, cy + s * 0.7],
              fill=INK, width=3)


def draw_panel(draw, x, y, w, h, kicker, kcolor, headline, body, icon):
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=2)
    draw.text((x + 14, y + 10), kicker, font=font(SANS_BOLD, 15), fill=kcolor)
    icon(draw, x + w - 52, y + 34, 26)
    head_lines = wrap(draw, headline, font(SERIF_BOLD, 25), w - 110)
    hy = y + 38
    for line in head_lines[:2]:
        draw.text((x + 14, hy), line, font=font(SERIF_BOLD, 25), fill=INK)
        hy += 31
    body_lines = wrap(draw, body, font(SANS, 16), w - 28)
    by = hy + 6
    for line in body_lines[:3]:
        draw.text((x + 14, by), line, font=SANS and font(SANS, 16), fill=(50, 50, 50))
        by += 21


def main():
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    # Borders.
    draw.rectangle([8, 8, W - 9, H - 9], outline=INK, width=3)
    draw.rectangle([16, 16, W - 17, H - 17], outline=INK, width=1)

    # Masthead.
    draw_centered(draw, 30, "THE WORLD IN ONE PICTURE",
                  font(SERIF_BOLD, 46), INK)
    draw_centered(draw, 96,
                  "TUESDAY, 24 NOVEMBER 2026  \u2022  THE DAY'S NEWS IN A SINGLE IMAGE",
                  font(SANS_BOLD, 15), RED)
    draw.line([MARGIN, 126, W - MARGIN, 126], fill=INK, width=3)
    draw.line([MARGIN, 132, W - MARGIN, 132], fill=INK, width=1)

    # Lead story: COP31 collapses.
    draw.text((MARGIN, 146), "CLIMATE  \u2022  COP31, ANTALYA",
              font=font(SANS_BOLD, 16), fill=RED)
    draw.text((MARGIN, 172), "COP31 COLLAPSES", font=font(SERIF_BOLD, 44), fill=INK)
    draw.text((MARGIN, 222), "WITHOUT A DEAL", font=font(SERIF_BOLD, 44), fill=RED)
    deck = ("After a record two-day overtime, the climate talks end with no pact: "
            "the EU and island states reject a text with no fossil-fuel phase-out.")
    deck_lines = wrap(draw, deck, font(SANS, 17), 620)
    dy = 282
    for line in deck_lines[:3]:
        draw.text((MARGIN, dy), line, font=font(SANS, 17), fill=(50, 50, 50))
        dy += 23
    draw.text((MARGIN, dy + 8), "Longest COP on record \u2022 first breakdown since 2009",
              font=font(SANS_BOLD, 15), fill=INK)
    draw_lead_graphic(draw)
    draw.line([MARGIN, 404, W - MARGIN, 404], fill=INK, width=2)

    # 2x2 story grid.
    panels = [
        ("INDONESIA", RED,
         "24 DEAD IN FACTORY FIRE",
         "A blaze at a candy factory in Cikande, Banten, leaves about 30 workers "
         "missing as rescuers search the ruins.",
         draw_flame),
        ("UKRAINE", BLUE,
         "KYIV SINKS RUSSIAN WARSHIP",
         "Ukraine says it sank a Russian warship off Libya; a NYT analysis puts "
         "Russian war dead past 700,000.",
         draw_drone),
        ("MARKETS", GREEN,
         "HUANG IS BACK AT NVIDIA",
         "Jensen Huang returns as CEO and Nvidia gains almost $1 trillion as "
         "tech stocks rally.",
         draw_chart),
        ("INDIA \u2013 NEPAL", ORANGE,
         "NEW RAIL LINK OPENS",
         "Modi and Nepal's PM flag off the Saryu\u2013Kamala Express, with a "
         "Rs 15,000-crore package and 8 MoUs.",
         draw_train),
    ]
    col_w, row_h, gap = 470, 186, 12
    for i, (kicker, kcolor, headline, body, icon) in enumerate(panels):
        x = MARGIN + (i % 2) * (col_w + gap)
        y = 420 + (i // 2) * (row_h + gap)
        draw_panel(draw, x, y, col_w, row_h, kicker, kcolor, headline, body, icon)

    # Bottom strip: sport + also today.
    draw.line([MARGIN, 818, W - MARGIN, 818], fill=INK, width=2)
    mid = W // 2
    draw.line([mid, 830, mid, 946], fill=LIGHT_GREY, width=2)
    draw.text((MARGIN, 830), "SPORT", font=font(SANS_BOLD, 15), fill=RED)
    sport = ("Verstappen wins a chaotic Las Vegas Grand Prix \u2014 his 75th win. "
             "Pant hits 128 as India\u2013New Zealand's 1st Test in Wellington "
             "ends in a draw.")
    sy = 854
    for line in wrap(draw, sport, font(SANS, 16), mid - MARGIN - 20)[:4]:
        draw.text((MARGIN, sy), line, font=font(SANS, 16), fill=(50, 50, 50))
        sy += 21
    draw.text((mid + 16, 830), "ALSO TODAY", font=font(SANS_BOLD, 15), fill=RED)
    also = ("The ICJ rules Myanmar committed genocide against the Rohingya. "
            "Thousands march in Lisbon over the cost of living. Bangladesh vows "
            "to arrest ex-PM Hasina if she returns.")
    ay = 854
    for line in wrap(draw, also, font(SANS, 16), W - MARGIN - mid - 36)[:4]:
        draw.text((mid + 16, ay), line, font=font(SANS, 16), fill=(50, 50, 50))
        ay += 21

    # Footer.
    draw.line([MARGIN, 962, W - MARGIN, 962], fill=INK, width=1)
    draw_centered(draw, 972,
                  "24 NOVEMBER 2026  \u2022  COP31  \u2022  BANTEN  \u2022  KYIV  \u2022  "
                  "NVIDIA  \u2022  AYODHYA\u2013JANAKPUR",
                  font(SANS, 13), GREY)

    os.makedirs("/output", exist_ok=True)
    out = "/output/entry.png"
    img.save(out, format="PNG")
    os.chmod(out, 0o644)
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
