#!/usr/bin/env python3
"""Generate label overlays for the G502 button diagram.

Outputs two same-size layers (1500x620) that line up in GIMP:
  g502-base.png     - photo on a heather grey canvas   (bottom layer)
  g502-labels.png   - transparent callout layer        (top layer)

Edit DOTS/LABELS below and re-run to regenerate.
"""
import subprocess

CW, CH = 1500, 620          # canvas size
OX, OY = 0, 32              # photo offset within canvas
BG = "#b8bcc0"              # heather grey

# Dot positions in ORIGINAL photo coordinates (1024x555)
DOTS = {
    "0":  (300, 200),   # left click
    "1":  (430, 180),   # right click
    "2":  (340, 250),   # wheel click
    "10": (328, 232),   # tilt left
    "9":  (350, 260),   # tilt right
    "6":  (470, 143),   # G7 DPI down
    "7":  (525, 113),   # G8 DPI up
    "8":  (505, 125),   # G9 profile   <-- needs correcting
    "3":  (755, 227),   # G4 back
    "4":  (670, 292),   # G5 forward
    "5":  (622, 377),   # G6 sniper
}

# key: (name, sublabel, label_x, label_y, anchor)
LABELS = {
    "0":  ("Left click",    "ratbag 0",    55, 140, "start"),
    "1":  ("Right click",   "ratbag 1",  1075, 120, "start"),
    "2":  ("Wheel click",   "ratbag 2",    55, 310, "start"),
    "10": ("Tilt left",     "ratbag 10",   55, 410, "start"),
    "9":  ("Tilt right",    "ratbag 9",    55, 505, "start"),
    "6":  ("G7 · DPI down", "ratbag 6",   370, 105, "end"),
    "7":  ("G8 · DPI up",   "ratbag 7",   370, 190, "end"),
    "8":  ("G9 · Profile",  "ratbag 8",   370, 285, "end"),
    "3":  ("G4 · Back",     "ratbag 3",  1180, 265, "start"),
    "4":  ("G5 · Forward",  "ratbag 4",  1180, 370, "start"),
    "5":  ("G6 · Sniper",   "ratbag 5",  1180, 475, "start"),
}

ACCENT = "#00b4d8"
DARK = "#07242e"
MUTED = "#4a6b78"


def svg(keys):
    p = []
    for k in keys:
        x, y = DOTS[k]
        cx, cy = x + OX, y + OY
        name, sub, lx, ly, anchor = LABELS[k]

        # target ring + centre dot
        p.append(f'<circle cx="{cx}" cy="{cy}" r="13" fill="none" stroke="{ACCENT}" stroke-width="3"/>')
        p.append(f'<circle cx="{cx}" cy="{cy}" r="4" fill="{ACCENT}"/>')

        # leader line from dot to the numbered badge
        bx = lx - 20 if anchor == "end" else lx + 20
        p.append(f'<line x1="{cx}" y1="{cy}" x2="{bx}" y2="{ly}" stroke="{ACCENT}" '
                 f'stroke-width="2" opacity="0.9"/>')

        # numbered badge
        p.append(f'<circle cx="{bx}" cy="{ly}" r="19" fill="#ffffff" '
                 f'stroke="{ACCENT}" stroke-width="3"/>')
        p.append(f'<text x="{bx}" y="{ly+7}" font-family="Helvetica" font-size="20" '
                 f'font-weight="bold" fill="{DARK}" text-anchor="middle">{k}</text>')

        # text block
        tx = bx - 30 if anchor == "end" else bx + 30
        ta = 'text-anchor="end"' if anchor == "end" else ""
        p.append(f'<text x="{tx}" y="{ly-3}" font-family="Helvetica" font-size="22" '
                 f'font-weight="bold" fill="{DARK}" {ta}>{name}</text>')
        p.append(f'<text x="{tx}" y="{ly+19}" font-family="Helvetica" font-size="15" '
                 f'fill="{MUTED}" {ta}>{sub}</text>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{CW}" height="{CH}">'
            f'{"".join(p)}</svg>')


def main():
    keys = list(DOTS)

    open("/tmp/g502-labels.svg", "w").write(svg(keys))

    # bottom layer: photo on grey canvas
    subprocess.run([
        "magick", "-size", f"{CW}x{CH}", f"xc:{BG}",
        "g502-photo.png", "-geometry", f"+{OX}+{OY}", "-composite",
        "g502-base.png"], check=True)

    # top layer: labels only, transparent background
    subprocess.run([
        "magick", "-size", f"{CW}x{CH}", "xc:none",
        "(", "-background", "none", "/tmp/g502-labels.svg", ")",
        "-composite", "g502-labels.png"], check=True)

    print(f"wrote g502-base.png and g502-labels.png ({CW}x{CH})")


if __name__ == "__main__":
    main()
