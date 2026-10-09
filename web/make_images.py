# make_images.py
# -*- coding: utf-8 -*-
#
# Render the images for the interactive planisphere web page in this folder.
#
# Run from the root of the repository, e.g. in Docker:
#   docker compose run --rm python sh -c "pip install -q pillow && python3 web/make_images.py"

"""
Render the star wheel and the front of the holder as PNG images for web/index.html.

The star wheel is drawn on a white disc. The holder is cut down to its front face, backed with white paper, and
its viewing window is made transparent, so that the star wheel shows through it on the web page.
"""

import os
import sys

from math import pi, sin, cos, atan2

from PIL import Image, ImageDraw
from numpy import arange

sys.path.insert(0, '.')

from constants import r_1, r_2, fold_gap, unit_mm, unit_cm, unit_deg, radius, transform, pos
from starwheel import StarWheel
from holder import Holder

# Resolution of the images; the web page scales them to fit the screen
DPI: int = 300
dpm: float = DPI * 39.370079

# The planisphere to show. The web page's text assumes 50N in German.
settings: dict = {'latitude': 50, 'language': 'de', 'theme': 'default',
                  'time_format': '24h', 'dst': True, 'deep_sky': True}

out_dir: str = "web"
h: float = r_1 + fold_gap
a: float = 6 * unit_cm

# Star wheel on a white disc (the wheel's own background is transparent)
StarWheel(settings=settings).render_to_file(filename=os.path.join(out_dir, "_starwheel_raw"), img_format="png",
                                            dots_per_inch=DPI)
star_wheel = Image.open(os.path.join(out_dir, "_starwheel_raw.png")).convert("RGBA")
centre: float = (r_1 + 4 * unit_mm) * dpm
disc = Image.new("RGBA", star_wheel.size, (0, 0, 0, 0))
ImageDraw.Draw(disc).ellipse((centre - r_1 * dpm, centre - r_1 * dpm, centre + r_1 * dpm, centre + r_1 * dpm),
                             fill=(255, 255, 255, 255))
disc.alpha_composite(star_wheel)
disc.save(os.path.join(out_dir, "starwheel.png"), optimize=True)

# Holder: white paper, the printed drawing, and the viewing window cut out
Holder(settings=settings).render_to_file(filename=os.path.join(out_dir, "_holder_raw"), img_format="png",
                                         dots_per_inch=DPI)
holder = Image.open(os.path.join(out_dir, "_holder_raw.png")).convert("RGBA")
x_min: float = -r_1 - 4 * unit_mm
y_min: float = -r_2 - h - 4 * unit_mm


def px(x: float, y: float) -> tuple:
    """
    Convert a position on the holder, in metres, into pixel coordinates in the rendered image.
    """
    return (x - x_min) * dpm, (y - y_min) * dpm


# Outline of the front face of the holder, as drawn in holder.py
theta: float = pi - atan2(r_1, h - a)
outline = [px(r_2 * cos(f), -h + r_2 * sin(f))
           for f in arange(-theta - pi / 2, theta - pi / 2 + 1e-9, 0.002)]
outline += [px(r_1, -a), px(r_1, 0), px(-r_1, 0), px(-r_1, -a)]

# Outline of the viewing window, which is the horizon, as drawn in holder.py
window = []
for az in arange(0, 360.5, 0.25):
    pp = transform(alt=0, az=az, latitude=settings['latitude'])
    r = radius(dec=pp[1] / unit_deg, latitude=settings['latitude'])
    p = pos(r=r, t=pp[0])
    window.append(px(p['x'], -h + p['y']))

paper = Image.new("RGBA", holder.size, (0, 0, 0, 0))
ImageDraw.Draw(paper).polygon(outline, fill=(255, 255, 255, 255))
paper.alpha_composite(holder)
alpha = paper.getchannel("A")
ImageDraw.Draw(alpha).polygon(window, fill=0)
paper.putalpha(alpha)
ImageDraw.Draw(paper).line(window + [window[0]], fill=(0, 0, 0, 255), width=3)

# Keep only the front face, above the fold line
front = paper.crop((0, 0, paper.size[0], int(round((0 - y_min) * dpm))))
front.save(os.path.join(out_dir, "holder_front.png"), optimize=True)

# Clean up the intermediate images
for name in ("_starwheel_raw.png", "_holder_raw.png"):
    os.remove(os.path.join(out_dir, name))

print("Written {} and {}".format(os.path.join(out_dir, "starwheel.png"), os.path.join(out_dir, "holder_front.png")))
