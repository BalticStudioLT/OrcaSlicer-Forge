#!/usr/bin/env python3
"""Difficult test models for OrcaSlicer Forge (nonplanar tops, bands, wave overhangs)."""
import numpy as np, trimesh, sys, os
out = sys.argv[1]; os.makedirs(out, exist_ok=True)

def heightfield(f, w, d, base, n=120):
    """Closed solid: flat bottom at z=0, top z = base + f(x,y)."""
    xs = np.linspace(0, w, n); ys = np.linspace(0, d, n)
    X, Y = np.meshgrid(xs, ys); Z = base + f(X, Y)
    v_top = np.c_[X.ravel(), Y.ravel(), Z.ravel()]
    v_bot = np.c_[X.ravel(), Y.ravel(), np.zeros(X.size)]
    V = np.vstack([v_top, v_bot]); N = n*n; F = []
    idx = lambda i, j: i*n + j
    for i in range(n-1):
        for j in range(n-1):
            a, b, c, e = idx(i,j), idx(i,j+1), idx(i+1,j+1), idx(i+1,j)
            F += [[a,b,c],[a,c,e],[a+N,c+N,b+N],[a+N,e+N,c+N]]
    border = [idx(0,j) for j in range(n)] + [idx(i,n-1) for i in range(1,n)] + \
             [idx(n-1,j) for j in range(n-2,-1,-1)] + [idx(i,0) for i in range(n-2,0,-1)]
    for k in range(len(border)):
        p, q = border[k], border[(k+1) % len(border)]
        F += [[p,p+N,q],[q,p+N,q+N]]
    m = trimesh.Trimesh(V, np.array(F), process=True); m.fix_normals(); return m

def save(name, m):
    assert m.is_watertight, name
    m.export(os.path.join(out, name + ".stl")); print(name, m.bounds.round(1).tolist())

# 1 shallow dome: slope grows from 0 to past the 12 deg limit at the rim
save("01_dome", heightfield(lambda x,y: np.clip(6 - ((x-30)**2+(y-30)**2)/150, 0, None) + 0*x, 60, 60, 4))
# 2 saddle: curves up in X, down in Y
save("02_saddle", heightfield(lambda x,y: 4 + ((x-25)**2 - (y-25)**2)/300, 50, 50, 4))
# 3 egg-crate waves: many small peaks, nozzle clearance between bumps
save("03_waves", heightfield(lambda x,y: 1.2*np.sin(x/4)*np.sin(y/4), 60, 60, 5))
# 4 tall shallow wedge 60x60, rises 9 deg -> ~9.5 mm: needs bands + toothed joins
save("04_tall_wedge", heightfield(lambda x,y: x*np.tan(np.radians(9)), 60, 60, 3))
# 5 car-hood: compound curve with a crease
save("05_hood", heightfield(lambda x,y: 3*np.cos((y-25)/30) + x*0.12 - 1.5*np.abs(np.sin((y-25)/8))*0.5, 70, 50, 3))
# 6 ramp with holes and a slot (top surface broken into many islands)
r = heightfield(lambda x,y: x*np.tan(np.radians(8)), 50, 40, 3)
for cx, cy in [(12,12),(25,28),(38,12)]:
    r = r.difference(trimesh.creation.cylinder(radius=4, height=40, sections=48).apply_translation([cx,cy,10]))
r = r.difference(trimesh.creation.box([30,3,40]).apply_translation([25,20,10]))
save("06_ramp_holes", r)
# 7 mushroom: thin stem + wide domed cap -> big overhang ring (wave) + nonplanar cap
stem = trimesh.creation.cylinder(radius=6, height=12, sections=64).apply_translation([0,0,6])
cap = heightfield(lambda x,y: np.clip(4 - ((x-20)**2+(y-20)**2)/100, 0, None), 40, 40, 2).apply_translation([-20,-20,12])
cyl = trimesh.creation.cylinder(radius=19.5, height=40, sections=96).apply_translation([0,0,25])
save("07_mushroom", stem.union(cap.intersection(cyl)))
# 8 bridge arch: two pillars, flat span (bridge) with a sloped top
span = heightfield(lambda x,y: 2 + 0.08*x, 60, 20, 3).apply_translation([0,0,15])
p1 = trimesh.creation.box([10,20,15]).apply_translation([5,10,7.5])
p2 = trimesh.creation.box([10,20,15]).apply_translation([55,10,7.5])
save("08_bridge_slope", p1.union(p2).union(span))
# 9 neighbours: three ramps tilted different ways 3 mm apart (collision with nozzle/cone)
parts = []
for k, ang in enumerate([6, -8, 10]):
    a = np.radians(abs(ang))
    f = (lambda a: (lambda x,y: x*np.tan(a)))(a) if ang > 0 else (lambda a: (lambda x,y: (15-x)*np.tan(a)))(a)
    parts.append(heightfield(f, 15, 40, 4 + 4*k).apply_translation([k*18, 0, 0]))
save("09_neighbours", trimesh.util.concatenate(parts) if False else parts[0].union(parts[1]).union(parts[2]))
# 10 thin fin with sloped top (narrow top: 2 mm wide)
save("10_thin_fin", heightfield(lambda x,y: x*np.tan(np.radians(10)), 50, 2, 6, n=60))
