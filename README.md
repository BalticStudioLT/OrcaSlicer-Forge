# OrcaSlicer Forge

OrcaSlicer 2.5.1 with experimental print-quality features from the community, combined in one build:

| Feature | What it does | Origin |
|---|---|---|
| **Nonplanar top surfaces** | The top shells of gently sloped tops (up to 12°, 5 mm height span) follow the surface instead of printing as stair steps. Every move is checked against a hotend model, and the print order is planned so the nozzle never hits printed material. | [fich-l/orcaslicer-nonplanar](https://github.com/fich-l/orcaslicer-nonplanar) v0.1 |
| **Wave overhangs** | Overhangs up to 90° without supports: the overhang is filled with wave rings that grow out from the supported edge. | [dennisklappe/OrcaSlicer-WaveOverhangs](https://github.com/dennisklappe/OrcaSlicer-WaveOverhangs) v0.4 |

More features are planned, one at a time, each after test prints: a per-printer hotend profile for the
nonplanar collision check, bridge line spacing for round mid-air beads, interlocking "brick" walls,
nonplanar ironing and arched (pre-cambered) bridges.

> **Experimental.** Check the G-code preview before printing. Report results in the issues.

## Install next to your normal OrcaSlicer

OrcaSlicer Forge has its **own settings folder** (`OrcaSlicerForge`) and its **own installer key**, so an
installed OrcaSlicer is never replaced or uninstalled. Both can run side by side.

Downloads: see the Actions artifacts / Releases of this repository (Windows x64 portable ZIP and installer).

## Where the settings are

- **Nonplanar:** Process > Quality > *Nonplanar layers* (Advanced mode). On by default: 12°, 5 mm.
  To print one object planar, right-click it > Add settings > Quality > *Use nonplanar layers* off.
- **Wave overhangs:** Process > *Wave overhangs* section. Off by default; switch *Use wave overhangs* on.

## Tested printers

Nonplanar v0.1 (community tests of the original fork): Bambu Lab A1 mini, A1, P1S, P2S, X1C, X2D, H2D;
Prusa MK4S, CORE One, XL; Creality K1C; Qidi Q2; Elegoo Centauri Carbon 2; Flashforge AD5C; FLSun V400.
The collision check uses one simplified hotend model (A1 mini) for every printer.

## Credits

- **OrcaSlicer** (SoftFever and contributors), Bambu Studio, PrusaSlicer, Slic3r. See [README.orcaslicer.md](README.orcaslicer.md).
- **Nonplanar:** fich-l (orcaslicer-nonplanar), Daniel Ahlers (nonplanar slicing research and the original slicer),
  Teaching Tech (PrusaSlicerNonplanar build).
- **Wave overhangs:** Janis Andersons, Salomé Sanchez and Tom Vaneker (research), Steven McCulloch
  (PrusaSlicer-WaveOverhangs, arc overhangs), Dennis Klappe (OrcaSlicer-WaveOverhangs).

## License

GNU AGPL-3.0, like OrcaSlicer and both source forks. See [LICENSE.txt](LICENSE.txt).
