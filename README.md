# RADIS vs Korkin et al. (2025) — line-by-line absorption validation

Reproducing the two open-source C codes from

> S. Korkin, A. M. Sayer, A. Ibrahim & A. Lyapustin (2025),
> *"A practical guide to coding line-by-line trace gas absorption in Earth's atmosphere"*,
> **JQSRT 337, 109345**. https://doi.org/10.1016/j.jqsrt.2025.109345

using **[RADIS](https://radis.readthedocs.io/)** (open-source Python line-by-line radiative-transfer
code), and checking the match by overplotting both on the same graph.

The paper ships two codes (reference repo: https://github.com/korkins/aspect_gcell):

| Code | What it does |
|------|--------------|
| `gcell`  | absorption in a homogeneous **gas cell** |
| `aspect` | absorption in **Earth's atmosphere**, with temperature/pressure varying with height |

## Result — it matches

RADIS reproduces both codes **line-by-line**, to within a few percent (the residual is explained by
HITRAN version, line-wing cut-off, and slab discretisation — not a modelling disagreement).

**Gas cell (`gcell`)**

| Test | paper τ_max | RADIS τ_max | rel-RMS |
|------|------------|-------------|---------|
| O₂ A-band (Fig. 4)  | 2.058 | 2.094 | **2.35 %** |
| CH₄ 2.3 µm (Fig. 5) | 6.409 | 6.395 | **7.65 %** |

**Atmosphere (`aspect`, US Standard 1976), reproduced with RADIS's slab-**stack** (`SerialSlabs`)**

| Partial column (TOA → z) | paper τ_max | RADIS τ_max | rel-RMS |
|--------------------------|------------|-------------|---------|
| 0.0 km (full column) | 570.3 | 563.6 | **2.67 %** |
| 1.0 km | 542.0 | 535.0 | 2.75 % |
| 2.5 km | 499.2 | 491.4 | 3.18 % |
| 8.0 km | 339.6 | 329.9 | 4.45 % |

Stacking slabs multiplies transmittances ⇔ adds optical depth. Verified identity:
`max | SerialSlabs(slabs) − Σ(slab optical depths) | = 2.3e-13`, i.e. the stack is exactly aspect's
height integration.

![O2 A-band overplot](figures/overplot_o2a_gcell_vs_radis.png)

## Repository contents

| File | Description |
|------|-------------|
| `compare_gcell_vs_paper.py` | Runs RADIS for the O₂ & CH₄ gas cells, overplots vs the paper's `gcell` output |
| `compare_aspect_vs_radis_stack.py` | Builds the US1976 atmosphere as a RADIS **slab-stack**, overplots vs `aspect` |
| `reproduce_korkin2025.py` | Earlier stand-alone reproduction of paper Figs. 4 & 5 |
| `make_validation_report.py` / `make_docx_report.py` | Build the PDF / Word reports |
| `figures/` | All overplots (PNG) |
| `RADIS_vs_Korkin2025_Validation_Report.pdf` / `.docx` | Human-readable write-up of method + results |

## How to reproduce

```bash
pip install radis python-docx matplotlib numpy

# get the authors' reference benchmarks (ground truth)
git clone https://github.com/korkins/aspect_gcell
export ASPECT_GCELL="$PWD/aspect_gcell"      # or place the folder next to the scripts

python compare_gcell_vs_paper.py
python compare_aspect_vs_radis_stack.py      # ~2 min: builds & stacks 49 atmospheric slabs
```

Outputs are written to `figures/`.

## Beyond US-1976: all 6 MODTRAN models, exact present-day & India atmospheres

The original reproduction used only the US-Standard-1976 profile. The code now
generalises to **any atmosphere and any gas/band** through a single driver, and
adds *current, location-specific* atmospheres to address the fact that the
MODTRAN/LOWTRAN models are 1970s-80s climatological averages.

### 1. All six MODTRAN/LOWTRAN standard atmospheres + paper Figure 6

`hprofiles.h` from the authors' repo contains all six standard atmospheres
(Tropical, Mid-Lat Summer/Winter, Sub-Arctic Summer/Winter, US-1976) with P, T,
air density and the mixing ratios of 8 gases (H₂O, CO₂, O₃, N₂O, CO, CH₄, O₂,
NO₂). These are extracted once into a version-controlled JSON file and exposed
through `atmospheres.py`.

```bash
python build_atmosphere_data.py     # parse hprofiles.h -> data/modtran_atmospheres.json
python atmospheres.py               # self-test + column-amount table (paper Sec. 6.2)
python plot_fig6_profiles.py        # reproduce paper Figure 6(a-f): figures/fig6*.png
python run_all_atmospheres.py       # run RADIS slab-stack for ALL 6 models (O2 A-band)
```

**Figure 6** of the paper is the MODTRAN profile set itself (height grid; P/T/D vs
height; gas number-concentration profiles) — `plot_fig6_profiles.py` regenerates
panels 6(a)–6(f) directly from the data.

### 2. Exact / present-day atmosphere (NASA PSG)  ·  3. India-specific model

`psg_atmosphere.py` pulls a real, date- and location-specific profile and returns
it as the same object the driver consumes, from **two independent sources**:

| Source | What it gives | Needs |
|--------|---------------|-------|
| **NASA PSG** (`get_psg`) — psg.gsfc.nasa.gov | GEOS-5 weather: P, T + mole fractions for H₂O, CO₂, O₃, N₂O, CO, CH₄, O₂ … at any lat/lon/date | internet (result cached under `data/psg_cache/`) |
| **NRLMSIS 2.1** (`get_nrlmsis`) — NASA/NRL 2021 empirical model via `pymsis` | T, total density, O₂/N₂/O number densities — exact O₂ & temperature profile | no API key |

```bash
python psg_atmosphere.py                                   # Mumbai, PSG vs NRLMSIS
python india_case.py                                       # IIT Bombay / Mumbai
python india_case.py --lat 28.61 --lon 77.21 --site Delhi  # any Indian site
python india_case.py --date "2024/01/15 06:00"             # any date/time
```

`india_case.py` compares **MODTRAN Tropical** (the closest 1970s model to India)
against the **PSG GEOS-5** (exact) and **NRLMSIS 2.1** (latest) profiles for the
O₂ A-band. Example result for Mumbai, 2024-06-15 (monsoon onset):

| Atmosphere | O₂ column (cm⁻²) | band-integrated τ | Δ vs MODTRAN |
|------------|------------------|-------------------|--------------|
| MODTRAN Tropical (1970s) | 4.523e24 | 1023 | — |
| PSG GEOS-5 (exact, that day) | 4.408e24 | 996 | **−2.6 %** |
| NRLMSIS 2.1 (latest) | 4.471e24 | 1011 | **−1.2 %** |

i.e. the generic tropical climatology over-predicts the real O₂ A-band absorption
over Mumbai by ~1–3 %, and the two independent present-day models agree to ~1.5 %.

### New repository files

| File | Description |
|------|-------------|
| `build_atmosphere_data.py` | Extract the 6 MODTRAN atmospheres from `hprofiles.h` → `data/modtran_atmospheres.json` |
| `atmospheres.py` | `Atmosphere` class + loaders for the 6 standard models; number-density / column helpers |
| `plot_fig6_profiles.py` | Reproduce paper **Figure 6**(a–f) |
| `psg_atmosphere.py` | Present-day atmospheres from **NASA PSG (GEOS-5)** and **NRLMSIS 2.1** |
| `aspect_driver.py` | General RADIS slab-stack — runs `aspect` for *any* atmosphere/gas/band |
| `run_all_atmospheres.py` | Sweep all 6 MODTRAN models for a chosen gas/band |
| `india_case.py` | MODTRAN-Tropical vs PSG vs NRLMSIS over an Indian site (O₂ A-band) |

## Notes

- The US Standard 1976 profile (T, p, density vs height) is taken from the paper's `src/hprofiles.h`.
- All 6 MODTRAN/LOWTRAN profiles trace to the MODTRAN 2 / LOWTRAN 7 report (Knezys et al. 1996), via the same header.
- The paper's PDF and its extracted text are **not** redistributed here (copyright); see the DOI above.
- Tools: RADIS 0.17, HITRAN, Python 3.11, `pymsis` (NRLMSIS 2.1), NASA PSG API.
