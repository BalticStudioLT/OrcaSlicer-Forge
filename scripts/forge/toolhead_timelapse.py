#!/usr/bin/env python3
"""Toolhead animation and still previews of an OrcaSlicer Forge G-code.

usage: toolhead_timelapse.py GCODE OUT_PREFIX "Title" [seconds]
writes OUT_PREFIX.mp4 (toolhead animation), OUT_PREFIX_final.png (finished part)
and OUT_PREFIX_top.png (top view, sloped moves highlighted).
"""
import math, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

path, prefix, title = sys.argv[1], sys.argv[2], sys.argv[3]
seconds = float(sys.argv[4]) if len(sys.argv) > 4 else 24.0
FPS, W, H = 30, 1280, 720
num = r"(-?(?:\d+\.?\d*|\.\d+))"
ARG = re.compile(r"([XYZEIJ])" + num)

# ---- parse: extrusion segments (with arcs split) ----
segs = []          # x0,y0,z0,x1,y1,z1,feature,sloped
x = y = z = 0.0
feature = ""
started = False
for raw in open(path, errors="replace"):
    line = raw.strip()
    if line.startswith(";TYPE:"):
        feature = line[6:].strip(); continue
    if line.startswith(";LAYER_CHANGE"):
        started = True; continue
    if not line or line[0] == ";":
        continue
    code = line.split(";", 1)[0].split()
    if not code or code[0] not in ("G0", "G1", "G2", "G3"):
        continue
    a = dict((k, float(v)) for k, v in ARG.findall(line.split(";", 1)[0]))
    tx, ty, tz, e = a.get("X", x), a.get("Y", y), a.get("Z", z), a.get("E", 0.0)
    pts = [(tx, ty, tz)]
    if code[0] in ("G2", "G3") and ("I" in a or "J" in a):
        cx, cy = x + a.get("I", 0), y + a.get("J", 0)
        r = math.hypot(x - cx, y - cy)
        a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ty - cy, tx - cx)
        sw = a1 - a0
        if code[0] == "G3" and sw <= 0: sw += 2 * math.pi
        if code[0] == "G2" and sw >= 0: sw -= 2 * math.pi
        n = max(1, int(abs(sw) * r / 0.5))
        pts = [(cx + r * math.cos(a0 + sw * k / n), cy + r * math.sin(a0 + sw * k / n), z + (tz - z) * k / n) for k in range(1, n + 1)]
    px, py, pz = x, y, z
    for qx, qy, qz in pts:
        if started:
            segs.append((px, py, pz, qx, qy, qz, feature if e > 0 else None, abs(qz - pz) > 1e-3 and e > 0))
        px, py, pz = qx, qy, qz
    x, y, z = tx, ty, tz

ext = [s for s in segs if s[6] is not None]
xs = [v for s in ext for v in (s[0], s[3])]; ys = [v for s in ext for v in (s[1], s[4])]; zs = [v for s in ext for v in (s[2], s[5])]
cx0, cy0 = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
zmax = max(zs)

# ---- isometric projection, scaled to fit ----
ang = math.radians(30)
def proj_raw(px, py, pz):
    u = (px - cx0) * math.cos(ang) - (py - cy0) * math.cos(ang)
    v = (px - cx0) * math.sin(ang) + (py - cy0) * math.sin(ang) - pz * ZEX
    return u, v
ZEX = 2.0      # vertical exaggeration: thin parts read better
us, vs = zip(*[proj_raw(s[i], s[i + 1], s[i + 2]) for s in ext for i in (0, 3)])
span = max(max(us) - min(us), (max(vs) - min(vs)) * 1.6)
scale = 0.80 * W / span
ou, ov = (max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2
def P(px, py, pz):
    u, v = proj_raw(px, py, pz)
    return (W / 2 + (u - ou) * scale, H * 0.56 + (v - ov) * scale)

def colour(feat, sloped, zz):
    shade = 0.55 + 0.45 * (zz / zmax if zmax > 0 else 1)
    f = (feat or "").lower()
    if sloped:                      base = (225, 45, 45)
    elif "top" in f:                base = (235, 120, 110)
    elif "outer wall" in f:         base = (240, 160, 60)
    elif "wall" in f:               base = (210, 170, 110)
    elif "overhang" in f:           base = (60, 120, 220)
    elif "support" in f:            base = (120, 200, 120)
    else:                           base = (190, 190, 190)
    return tuple(int(c * shade) for c in base)

BG = (24, 26, 30)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
except OSError:
    font = small = ImageFont.load_default()

canvas = Image.new("RGB", (W, H), BG)
cd = ImageDraw.Draw(canvas)
lw = max(1, int(round(0.42 * scale)))

def draw_seg(s):
    if s[6] is None:
        return
    cd.line([P(s[0], s[1], s[2]), P(s[3], s[4], s[5])], fill=colour(s[6], s[7], max(s[2], s[5])), width=lw)

def nozzle(img, px, py, pz, active):
    d = ImageDraw.Draw(img)
    tx, ty = P(px, py, pz)
    h = 7.5 * ZEX * scale * 0.35          # drawn heater block height (not to scale of the planner model)
    w = 9.0 * scale * 0.35
    # nozzle cone
    d.polygon([(tx, ty), (tx - w * 0.25, ty - h * 0.35), (tx + w * 0.25, ty - h * 0.35)], fill=(200, 170, 70))
    # heater block
    d.rectangle([tx - w * 0.7, ty - h * 0.35 - h * 0.45, tx + w * 0.7, ty - h * 0.35], fill=(170, 175, 185), outline=(90, 95, 105))
    # carriage
    d.rectangle([tx - w * 1.1, ty - h * 1.4, tx + w * 1.1, ty - h * 0.8], fill=(60, 62, 70), outline=(110, 115, 125))
    if active:
        d.ellipse([tx - 3, ty - 3, tx + 3, ty + 3], fill=(255, 240, 120))

# ---- frame schedule: extrusion-weighted, sloped moves get 6x the screen time ----
weights = np.array([0.0 if s[6] is None else (6.0 if s[7] else 1.0) * max(0.05, math.dist(s[:3], s[3:6])) for s in segs])
cum = np.cumsum(weights)
total = cum[-1]
nframes = int(seconds * FPS)
targets = np.linspace(0, total, nframes)
idx = np.searchsorted(cum, targets)
idx[-1] = len(segs) - 1

ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                       "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", prefix + ".mp4"],
                      stdin=subprocess.PIPE)
done = 0
nsl = sum(1 for s in segs if s[7])
for fi, k in enumerate(idx):
    while done <= k:
        draw_seg(segs[done]); done += 1
    s = segs[k]
    frame = canvas.copy()
    nozzle(frame, s[3], s[4], s[5], s[6] is not None)
    d = ImageDraw.Draw(frame)
    d.text((24, 18), title, font=font, fill=(235, 235, 235))
    tag = "non-planar top: nozzle follows the slope" if s[7] else (s[6] or "travel")
    d.text((24, 50), f"Z {s[5]:.2f} mm   {tag}", font=small, fill=(255, 120, 110) if s[7] else (190, 190, 190))
    d.text((24, H - 34), f"red = sloped (non-planar) moves ({nsl})   orange = outer wall   grey = infill   height x{ZEX:.0f}",
           font=small, fill=(160, 160, 160))
    ff.stdin.write(frame.tobytes())
for _ in range(FPS * 2):                       # hold the finished part
    ff.stdin.write(frame.tobytes())
ff.stdin.close(); ff.wait()

# ---- stills ----
fin = canvas.copy()
ImageDraw.Draw(fin).text((24, 18), title + " — finished", font=font, fill=(235, 235, 235))
fin.save(prefix + "_final.png")

# top view: sloped moves coloured by height
top = Image.new("RGB", (W, H), BG); td = ImageDraw.Draw(top)
spanxy = max(max(xs) - min(xs), (max(ys) - min(ys)) * W / H)
sc2 = 0.85 * W / spanxy
T = lambda px, py: (W / 2 + (px - cx0) * sc2, H / 2 - (py - cy0) * sc2)
zl = [min(s[2], s[5]) for s in ext if s[7]]
zlo, zhi = (min(zl), max(zl)) if zl else (0, 1)
import matplotlib.cm as cm
for s in ext:
    if s[7]:
        c = cm.turbo((max(s[2], s[5]) - zlo) / max(1e-6, zhi - zlo))
        td.line([T(s[0], s[1]), T(s[3], s[4])], fill=tuple(int(255 * v) for v in c[:3]), width=max(1, int(0.42 * sc2)))
    elif "outer wall" in (s[6] or "").lower() and s[5] > zmax - 0.3:
        td.line([T(s[0], s[1]), T(s[3], s[4])], fill=(110, 110, 110), width=1)
td.text((24, 18), title + " — top view, sloped moves by height", font=font, fill=(235, 235, 235))
td.text((24, H - 34), f"blue {zlo:.2f} mm  ->  red {zhi:.2f} mm (nozzle height on the non-planar top)", font=small, fill=(170, 170, 170))
top.save(prefix + "_top.png")
print("frames", nframes, "segments", len(segs), "sloped", nsl)
