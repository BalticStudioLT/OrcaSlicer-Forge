# Owner ideas and requests (Valdas)

Running log of every idea and request for OrcaSlicer Forge, newest last. Times are Europe/Vilnius.

## 2026-11-22

- 21:17 — Saw the r/BambuLab post "RELEASE - Orca Slicer with Nonplanar Printing" (fich-l/orcaslicer-nonplanar).
  Asked: are there more projects like this, and which are the most successful?
- 21:18 — Shared a screenshot of that post (confirmed working on Bambu A1 mini, A1, P1S, P2S, X1C, X2D, H2D, Prusa MK4S, CORE One, XL 5T).
- 21:19 — "Can we improve it?"
- 21:43 — What else could be integrated: supports, first layer, etc.
- 21:44 — Focus: overhangs, undersides ("underhangs"), bridges.
- 21:52 — "Integrate all of it."
- Decisions: base on **Orca 2.5.1**; build with **GitHub Actions** (repo under BalticStudioLT);
  order **proven first**: nonplanar tops + wave overhangs → P1S hotend profile → bridge bead spacing →
  BrickLayers / Smoothificator → nonplanar ironing → arched (pre-cambered) bridges.
  Each stage ends with test prints on the P1S before the next.

## 2026-11-23

- 08:22 — How do slopes taller than 5 or 10 mm work? Does the top stop at an edge and continue later, or is it seamless?
- 08:25 — Go with bands (split tall slopes), but make the bands overlap: no hard line in one place. E.g. first shell
  joins every 3 mm, the next every 4 mm, the last (visible) every 5 mm, staggered like bricks.
  Result: banding works (aligned joins). Staggered joins are not printable in this method: each lower shell must be
  printed before the shell on top of it, so all shells must break at the same place (lower shells may break more often).
  Offered instead: toothed / wavy join line and nonplanar ironing over the join.
- 15:59 — Yes to both (toothed join, then ironing over the join). Asked: will supports have this?
  Done: toothed joins (±0.6 mm, 8 mm period, shared by all shells). Next: nonplanar ironing over the join.
- 20:3x — "continue work. you can use this computer" / "continue. coolmaster on": tested the GitHub Windows build on
  coolmaster (P1S profile). Nonplanar + band/join/ironing options show up and slicing works.
- 20:38 — Asked: "https://github.com/fich-l/orcaslicer-nonplanar we work on this?"
  Answer: yes. Forge = fich-l's nonplanar code ported to Orca 2.5.1 + wave overhangs + bands/toothed joins/join ironing.
- 20:43 — "test with different models. difficult models."
  Result (difficult-model test, 18 models: 10 generated shapes + Benchy, propeller, tree, dino, bridge/overhang tests,
  RotBot wave tests):
  - Fixed bug 1: tall wedge (bands) crashed "moved extrusions were never written" (a layer whose material all moved
    into a band was never visited, so its "after layer" material was lost). Now written at the next layer start.
  - Fixed bug 2: propeller crashed "fill surface without target surface" (wave-overhang floor pass rebuilt
    nonplanar shells without their identity). Nonplanar shells are now left alone by that pass.
  - Still failing at the default 12°: saddle, egg-crate waves, car hood ("no print order avoids a hotend collision"
    where the surface dips into a valley at the model edge). All three slice at 8°. Egg-crate at 8° = all planar.
  - Slow: up to 8 min for the hood at 8° on 2 CPU cores (planner).
  Follow-up (same evening): GitHub's Orca regression tests showed the Stanford Bunny failing with default settings.
  Added automatic fallback: the planner runs during slicing; if no safe order exists the object is re-sliced at 8°,
  then flat, with a warning. Re-test: all 19 models slice at default settings (saddle, hood: auto 8°; egg-crate:
  auto 8° ends up flat).
- 2026-11-24 00:29 — "try more models from internet. check each final gcode"
  Plan: 29 more models (Stanford/graphics test models: bunny, dragon, armadillo, Lucy, Buddha, busts, teapot, cow…;
  Prusa MK3S functional parts) + an independent G-code checker (scripts/forge/check_gcode.py) that replays every move
  against the printed material: tip/cone/heater-block collisions, slope limit, bed bounds, extrusion amounts,
  filament vs flat slice. Checker verified: finds 693 collisions on a dome sliced with the planner disabled, 0 with it.
- 00:48 — "i tried slicing project and it looks like stuck" (bandymas_medalio laikiklis (2).stl, 109x118x5.9 mm plate
  with a recessed pattern, old build A:\forge\dl, 80% Generating G-code). Cause: the collision planner, one thread,
  hours on this model (every flat plate layer within the heater-block reach is checked against the sloped faces).
  Done: flat (horizontal) faces never become nonplanar; dependency collection runs on all cores; planning has a
  180 s budget, after which the object prints with flat tops and a warning. Next: algorithmic speed-up.
  Big test (P1S profile, 48 models incl. 29 more from GitHub: Stanford/graphics models, Prusa MK3S parts), every final
  G-code checked. Found and fixed: band-join ironing was never ordered by the planner -> nozzle collisions (thin fin
  105); now ordered, and join ironing is OFF by default (ironing a 12° slope brushes the nozzle cone). Known: teapot
  lid has a ~0.05 mm cone graze inside one shell (beads of one shell keep their order); nonplanar slices use up to
  ~20% more filament (solid infill under the shells instead of sparse, not double material). Local test profile was
  A1 mini until now; switched to a flattened P1S profile. The hotend shape is still the A1 mini one.
