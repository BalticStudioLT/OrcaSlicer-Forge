#!/usr/bin/env python3
"""Independent check of a finished OrcaSlicer Forge G-code file.

It replays every move against a height map of the material printed so far
and reports:
  - nozzle collisions: tip, cone and heater block (same hotend shape the
    slicer plans with) hitting material that is already printed
  - extrusion slopes steeper than the nonplanar limit
  - moves outside the P1S bed (0..256 mm) or below the bed
  - odd extrusion amounts (E per mm far above the normal for that feature)
  - total filament, to compare against the flat slice of the same model

usage: check_gcode.py FILE.gcode [--planar FLAT.gcode] [--json OUT.json]
"""
import json, math, re, sys
import numpy as np

CELL = 0.1                 # fine grid (mm)
COARSE = 2.0               # coarse max grid (mm)
BED = 256.0
TIP_R, TIP_ALLOW = 0.5504, 0.12
CONE = []                  # (bottom, radius) like NonplanarClearanceModel::rings()
cb, cbr, ct, ctr, n = 0.15, 0.613, 2.5, 1.5979, 24
for k in range(n):
    lo = cb + k * (ct - cb) / n
    hi = lo + (ct - cb) / n
    CONE.append((lo - 0.02, cbr + (ctr - cbr) * (hi - cb) / (ct - cb) + 0.02))
BOXES = [(2.35, 7.0379, 9.4243), (2.65, 8.4493, 10.8357), (2.95, 9.8606, 12.2470), (3.25, 11.2720, 13.6584),
         (3.55, 12.6834, 15.0698), (3.85, 14.0948, 16.4812), (4.15, 15.5062, 17.8926), (4.45, 16.9176, 19.3040),
         (4.75, 18.3290, 20.7154), (5.05, 19.7404, 22.1268), (5.35, 21.1518, 23.5382), (5.65, 22.5631, 24.9495),
         (5.95, 23.9745, 26.3609), (6.25, 25.3859, 27.7723), (6.55, 26.7973, 29.1837), (6.85, 28.2087, 30.5951),
         (7.15, 29.1496, 31.5360), (7.20, 29.2996, 31.6860)]
REACH_X, REACH_Y = 29.3, 31.7
SLACK = 0.05               # measurement slack on top of the model (mm)
MAX_SLOPE_DEG = 12.0

NF = int(BED / CELL) + 1
NC = int(BED / COARSE) + 1
H = np.full((NF, NF), -1.0, dtype=np.float32)
SRC = np.zeros((NF, NF), dtype=np.int32)      # G-code line that deposited the cell's top
CUR_LINE = [0]
HC = np.full((NC, NC), -1.0, dtype=np.float32)
hmax = -1.0

num = r"(-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)"
ARG = re.compile(r"([XYZEFIJR])" + num)


def fi(v):
    return min(NF - 1, max(0, int(round(v / CELL))))


def ci(v):
    return min(NC - 1, max(0, int(v // COARSE)))


def region_max(x0, y0, x1, y1):
    a = H[fi(x0):fi(x1) + 1, fi(y0):fi(y1) + 1]
    return float(a.max()) if a.size else -1.0


def deposit(x0, y0, x1, y1, z0, z1, hw):
    global hmax
    mnx, mxx = min(x0, x1) - hw, max(x0, x1) + hw
    mny, mxy = min(y0, y1) - hw, max(y0, y1) + hw
    ix0, ix1, iy0, iy1 = fi(mnx), fi(mxx), fi(mny), fi(mxy)
    xs = np.arange(ix0, ix1 + 1) * CELL
    ys = np.arange(iy0, iy1 + 1) * CELL
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    if L2 < 1e-12:
        t = np.zeros_like(X)
    else:
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0, 1)
    d = np.hypot(X - (x0 + t * dx), Y - (y0 + t * dy))
    m = d <= hw
    zz = z0 + t * (z1 - z0)
    sub = H[ix0:ix1 + 1, iy0:iy1 + 1]
    newv = np.where(m, zz, -1.0).astype(np.float32)
    SRC[ix0:ix1 + 1, iy0:iy1 + 1][newv > sub] = CUR_LINE[0]
    np.maximum(sub, newv, out=sub)
    z = max(z0, z1)
    for cx in range(ci(mnx), ci(mxx) + 1):
        for cy in range(ci(mny), ci(mxy) + 1):
            HC[cx, cy] = max(HC[cx, cy], z)
    hmax = max(hmax, z)


def check_point(x, y, z, extruding):
    """Return (kind, overlap_mm) of the worst violation at this tool position, or None."""
    worst = None
    allow = TIP_ALLOW if extruding else 0.0
    h = region_max(x - TIP_R, y - TIP_R, x + TIP_R, y + TIP_R)
    if h > z + allow + SLACK:
        # exact disc test
        ix0, ix1, iy0, iy1 = fi(x - TIP_R), fi(x + TIP_R), fi(y - TIP_R), fi(y + TIP_R)
        xs = np.arange(ix0, ix1 + 1) * CELL - x
        ys = np.arange(iy0, iy1 + 1) * CELL - y
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        sub = H[ix0:ix1 + 1, iy0:iy1 + 1]
        v = sub[np.hypot(X, Y) <= TIP_R]
        if v.size and v.max() > z + allow + SLACK:
            src = int(sub[np.hypot(X, Y) <= TIP_R][int(np.argmax(v))]) if False else int(SRC[ix0:ix1 + 1, iy0:iy1 + 1][np.hypot(X, Y) <= TIP_R][int(np.argmax(v))])
            worst = ("tip", float(v.max() - z - allow), src, float(v.max()))
    for bottom, r in CONE:
        if region_max(x - r, y - r, x + r, y + r) > z + bottom + SLACK:
            ix0, ix1, iy0, iy1 = fi(x - r), fi(x + r), fi(y - r), fi(y + r)
            xs = np.arange(ix0, ix1 + 1) * CELL - x
            ys = np.arange(iy0, iy1 + 1) * CELL - y
            X, Y = np.meshgrid(xs, ys, indexing="ij")
            mask = np.hypot(X, Y) <= r
            v = H[ix0:ix1 + 1, iy0:iy1 + 1][mask]
            if v.size and v.max() > z + bottom + SLACK:
                o = float(v.max() - z - bottom)
                src = int(SRC[ix0:ix1 + 1, iy0:iy1 + 1][mask][int(np.argmax(v))])
                if worst is None or o > worst[1]:
                    worst = ("cone r%.2f" % r, o, src, float(v.max()))
                break
    for bottom, hx, hy in BOXES:
        h = region_max(x - hx, y - hy, x + hx, y + hy)
        if h > z + bottom + SLACK:
            o = h - z - bottom
            if worst is None or o > worst[1]:
                worst = ("heater block", o, -1, h)
            break
    return worst


def self_step(st, x, y, z, nx, ny, nz, e, rel_e, feature, width, ln):
    CUR_LINE[0] = ln
    st["moves"] += 1
    st["z_max"] = max(st["z_max"], nz)
    if not (-3.0 <= nx <= BED + 0.5 and -3.0 <= ny <= BED + 0.5) or nz < -0.01:
        if len(st["out_of_bed"]) < 10:
            st["out_of_bed"].append(dict(line=ln, x=nx, y=ny, z=nz))
    xy = math.hypot(nx - x, ny - y)
    dz = nz - z
    extruding = e > 0 and rel_e and (xy > 1e-6 or abs(dz) > 1e-6)
    # Vertical moves and sub-0.05 mm repositioning at a bead end count like
    # extrusion (the slicer grants them the same tip contact allowance).
    vertical = (xy < 1e-6 and abs(dz) > 1e-6) or (xy < 0.05 and abs(dz) < 1e-6)
    if extruding:
        st["extrusions"] += 1
        st["filament_mm"] += e
        L = math.hypot(xy, dz)
        if abs(dz) > 1e-4 and xy > 1e-6:
            st["sloped"] += 1
            ang = math.degrees(math.atan2(abs(dz), xy))
            if xy > 0.3:
                st["max_slope_deg"] = max(st["max_slope_deg"], ang)
                if ang > MAX_SLOPE_DEG + 1.0 and len(st["steep"]) < 10:
                    st["steep"].append(dict(line=ln, deg=round(ang, 1), xy=round(xy, 2), dz=round(dz, 3)))
    # collision check, only where printed material can be above the tool
    zlow = min(z, nz)
    if hmax > zlow + TIP_ALLOW + SLACK and (xy > 1e-6 or abs(dz) > 1e-6):
        bx0, bx1 = min(x, nx) - REACH_X, max(x, nx) + REACH_X
        by0, by1 = min(y, ny) - REACH_Y, max(y, ny) + REACH_Y
        cmax = float(HC[ci(bx0):ci(bx1) + 1, ci(by0):ci(by1) + 1].max())
        if cmax > zlow + min(TIP_ALLOW, 0.0) + SLACK:
            steps = max(1, int(math.ceil(max(xy, abs(dz)) / 0.2)))
            worst = None
            for s in range(1, steps + 1):
                t = s / steps
                st["checked"] += 1
                r = check_point(x + (nx - x) * t, y + (ny - y) * t, z + (nz - z) * t, extruding or vertical)
                if r and (worst is None or r[1] > worst[1]):
                    worst = (r[0], r[1], x + (nx - x) * t, y + (ny - y) * t, z + (nz - z) * t, r[2], r[3])
            if worst and len(st["collisions"]) < 2000:
                st["collisions"].append(dict(line=ln, kind=worst[0], overlap=round(worst[1], 3),
                    x=round(worst[2], 2), y=round(worst[3], 2), z=round(worst[4], 3), by_line=worst[5], obstacle_z=round(worst[6], 3),
                    feature=feature if extruding else "travel"))
    if extruding:
        deposit(x, y, nx, ny, z, nz, max(0.1, width / 2))
    return nx, ny, nz


def run(path):
    global hmax
    H.fill(-1.0); HC.fill(-1.0); hmax = -1.0
    x = y = z = 0.0
    rel_e = True
    started = False
    feature = ""
    width = 0.42
    layer = -1
    st = dict(moves=0, extrusions=0, sloped=0, checked=0, filament_mm=0.0, z_max=0.0, layers=0,
              max_slope_deg=0.0, steep=[], collisions=[], out_of_bed=[], odd_e=[], arcs=0)
    e_per_mm = {}
    pending_odd = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for ln, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            if line[0] == ";":
                if line.startswith("; FEATURE:") or line.startswith(";TYPE:"):
                    feature = line.split(":", 1)[1].strip()
                elif line.startswith("; LINE_WIDTH:") or line.startswith(";WIDTH:"):
                    try: width = float(line.split(":", 1)[1])
                    except ValueError: pass
                elif line.startswith("; CHANGE_LAYER") or line.startswith(";LAYER_CHANGE"):
                    started = True
                    layer += 1
                elif "filament end gcode" in line or line.startswith("; EXECUTABLE_BLOCK_END"):
                    if started:
                        break
                continue
            code = line.split(";", 1)[0].strip()
            if code.startswith("M83"):
                rel_e = True; continue
            if code.startswith("M82"):
                rel_e = False; continue
            if code.startswith("G92"):
                continue
            g = code.split(" ", 1)[0]
            if g not in ("G0", "G1", "G2", "G3"):
                continue
            if g in ("G2", "G3"):
                st["arcs"] += 1
            args = dict((k, float(v)) for k, v in ARG.findall(code))
            tx, ty, tz = args.get("X", x), args.get("Y", y), args.get("Z", z)
            etot = args.get("E", 0.0)
            if not started:
                x, y, z = tx, ty, tz
                continue
            # Arcs: split into short chords along the real curve.
            pts = [(tx, ty, tz)]
            if g in ("G2", "G3") and ("I" in args or "J" in args):
                cx, cy = x + args.get("I", 0.0), y + args.get("J", 0.0)
                r = math.hypot(x - cx, y - cy)
                a0 = math.atan2(y - cy, x - cx); a1 = math.atan2(ty - cy, tx - cx)
                sweep = a1 - a0
                if g == "G3" and sweep <= 0: sweep += 2 * math.pi
                if g == "G2" and sweep >= 0: sweep -= 2 * math.pi
                nseg = max(1, int(math.ceil(abs(sweep) * r / 0.3)))
                pts = [(cx + r * math.cos(a0 + sweep * k / nseg), cy + r * math.sin(a0 + sweep * k / nseg),
                        z + (tz - z) * k / nseg) for k in range(1, nseg + 1)]
                pts[-1] = (tx, ty, tz)
            true_len = sum(math.hypot(px - qx, py - qy) for (px, py, _), (qx, qy, _) in zip([(x, y, z)] + pts[:-1], pts))
            arc_total_len = math.hypot(true_len, tz - z)
            total = true_len or 1.0
            seg_list = []
            px, py, pz = x, y, z
            for (qx, qy, qz) in pts:
                frac = math.hypot(qx - px, qy - py) / total if total > 0 else 1.0 / len(pts)
                seg_list.append((qx, qy, qz, etot * frac))
                px, py, pz = qx, qy, qz
            if etot > 0 and arc_total_len > 0.3:
                e_per_mm.setdefault(feature, []).append(etot / arc_total_len)
                pending_odd.append((feature, etot / arc_total_len, ln, arc_total_len))
            for nx, ny, nz, e in seg_list:
                x, y, z = self_step(st, x, y, z, nx, ny, nz, e, rel_e, feature, width, ln)
            continue
    st["layers"] = layer + 1
    med = {f: float(np.median(v)) for f, v in e_per_mm.items() if len(v) >= 20}
    for f, r, ln, L in pending_odd:
        if f in med and r > 2.5 * med[f] and r > 0.08 and len(st["odd_e"]) < 10:
            st["odd_e"].append(dict(line=ln, feature=f, e_per_mm=round(r, 4), median=round(med[f], 4)))
    return st


def main():
    a = sys.argv[1:]
    path = a[0]
    planar = a[a.index("--planar") + 1] if "--planar" in a else None
    out = a[a.index("--json") + 1] if "--json" in a else None
    st = run(path)
    if planar:
        st["planar_filament_mm"] = run(planar)["filament_mm"]
        st["filament_ratio"] = round(st["filament_mm"] / st["planar_filament_mm"], 4) if st["planar_filament_mm"] else None
    big = [c for c in st["collisions"] if c["overlap"] > 0.05]
    st["collision_count"] = len(st["collisions"])
    st["serious_collisions"] = len(big)
    verdict = "PASS"
    if big or st["out_of_bed"] or st["steep"] or st["odd_e"]:
        verdict = "FAIL"
    elif st["collisions"]:
        verdict = "WARN"
    # More filament than the flat slice is extra solid infill under the shells
    # (checked separately: not material inside the shell stack); less is missing material.
    if planar and st.get("filament_ratio") and st["filament_ratio"] < 0.9:
        verdict = "FAIL"
    elif planar and st.get("filament_ratio") and st["filament_ratio"] > 1.15 and verdict == "PASS":
        verdict = "WARN"
    st["verdict"] = verdict
    st["collisions"] = sorted(st["collisions"], key=lambda c: -c["overlap"])[:15]
    s = json.dumps(st, indent=1)
    if out:
        open(out, "w").write(s)
    print(f"{verdict} {path.split('/')[-1]}: moves {st['moves']}, sloped {st['sloped']}, max slope {st['max_slope_deg']:.1f}°, "
          f"collisions {st['collision_count']} (serious {st['serious_collisions']}), out of bed {len(st['out_of_bed'])}, "
          f"odd E {len(st['odd_e'])}, filament {st['filament_mm']:.0f} mm" +
          (f", vs flat {st['filament_ratio']}" if planar else ""))


if __name__ == "__main__":
    main()
