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
