"""
Extract the 6 MODTRAN / LOWTRAN-7 standard atmospheres from the paper's
`src/hprofiles.h` (Korkin et al. 2025, github.com/korkins/aspect_gcell) into a
clean, version-controlled JSON file: data/modtran_atmospheres.json

Run once after cloning aspect_gcell:

    python build_atmosphere_data.py

The header defines (see hprofiles.h, sourced from the MODTRAN 2 / LOWTRAN 7
report, Knezys et al. 1996):

    natm = 6   atmospheres : Tropical, Mid-Lat Summer, Mid-Lat Winter,
                             Sub-Arctic Summer, Sub-Arctic Winter, US Std 1976
    nz_mod = 50 height levels (0..120 km, 3 sub-grids)

    zkm_mod[50]              height grid (km)
    Pmbar_mod[6][50]         pressure (mbar)
    Tkelv_mod[6][50]         temperature (K)
    Dcm3_mod[6][50]          air number density (cm-3)
    H2O/O3/N2O/CO/CH4 [6][50]  ppmv, per-atmosphere (seasonal)
    CO2/O2/NO2 [50]          ppmv, seasonally invariant (same for all 6)

Number concentration of a gas at level i, atmosphere a:
    n_gas(a,i) = D(a,i) * ppmv(a,i) * 1e-6   [cm-3]
"""
import os
import re
import json

HERE = os.path.dirname(os.path.abspath(__file__))
HPROF = os.path.join(os.environ.get("ASPECT_GCELL", os.path.join(HERE, "aspect_gcell")),
                     "src", "hprofiles.h")
OUT = os.path.join(HERE, "data", "modtran_atmospheres.json")

ATM_NAMES = [
    "Tropical (15N Annual Average)",
    "Mid-Latitude Summer (45N July)",
    "Mid-Latitude Winter (45N Jan)",
    "Sub-Arctic Summer (60N July)",
    "Sub-Arctic Winter (60N Jan)",
    "U. S. Standard (1976)",
]
ATM_SHORT = ["tropical", "midlat_summer", "midlat_winter",
             "subarctic_summer", "subarctic_winter", "us_standard_1976"]
NATM, NZ = 6, 50


def grab_block(text, name):
    """Return the list of floats inside the `{ ... }` following `<name>[`."""
    # (?<![A-Za-z0-9_]) so "O2_ppmv" does not match inside "CO2_ppmv"
    m = re.search(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"\s*\[[^\{]*\{", text)
    if not m:
        raise ValueError(f"could not find array '{name}' in hprofiles.h")
    i = m.end()
    depth = 1
    while depth:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    body = text[m.end():i - 1]
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)   # strip comments
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", body)
    return [float(x) for x in nums]


def as_matrix(flat, nrows, ncols, name):
    if len(flat) != nrows * ncols:
        raise ValueError(f"{name}: expected {nrows*ncols} numbers, got {len(flat)}")
    return [flat[r * ncols:(r + 1) * ncols] for r in range(nrows)]


def main():
    with open(HPROF, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    zkm = grab_block(text, "zkm_mod")
    assert len(zkm) == NZ, f"zkm has {len(zkm)} levels"

    P = as_matrix(grab_block(text, "Pmbar_mod"), NATM, NZ, "Pmbar_mod")
    T = as_matrix(grab_block(text, "Tkelv_mod"), NATM, NZ, "Tkelv_mod")
    D = as_matrix(grab_block(text, "Dcm3_mod"), NATM, NZ, "Dcm3_mod")

    # per-atmosphere gas mixing ratios (ppmv)
    H2O = as_matrix(grab_block(text, "H2O_ppmv"), NATM, NZ, "H2O_ppmv")
    O3 = as_matrix(grab_block(text, "O3_ppmv"), NATM, NZ, "O3_ppmv")
    N2O = as_matrix(grab_block(text, "N2O_ppmv"), NATM, NZ, "N2O_ppmv")
    CO = as_matrix(grab_block(text, "CO_ppmv"), NATM, NZ, "CO_ppmv")
    CH4 = as_matrix(grab_block(text, "CH4_ppmv"), NATM, NZ, "CH4_ppmv")

    # seasonally invariant (single row -> broadcast to all 6)
    CO2_1 = grab_block(text, "CO2_ppmv")
    O2_1 = grab_block(text, "O2_ppmv")
    NO2_1 = grab_block(text, "NO2_ppmv")
    for nm, arr in [("CO2", CO2_1), ("O2", O2_1), ("NO2", NO2_1)]:
        assert len(arr) == NZ, f"{nm} has {len(arr)} levels"
    CO2 = [CO2_1[:] for _ in range(NATM)]
    O2 = [O2_1[:] for _ in range(NATM)]
    NO2 = [NO2_1[:] for _ in range(NATM)]

    # HITRAN molecule id -> ppmv table
    gases = {
        "H2O": {"hitran_id": 1, "ppmv": H2O},
        "CO2": {"hitran_id": 2, "ppmv": CO2},
        "O3":  {"hitran_id": 3, "ppmv": O3},
        "N2O": {"hitran_id": 4, "ppmv": N2O},
        "CO":  {"hitran_id": 5, "ppmv": CO},
        "CH4": {"hitran_id": 6, "ppmv": CH4},
        "O2":  {"hitran_id": 7, "ppmv": O2},
        "NO2": {"hitran_id": 10, "ppmv": NO2},
    }

    out = {
        "source": "MODTRAN 2 / LOWTRAN 7 report (Knezys et al. 1996), via "
                  "Korkin et al. 2025 hprofiles.h",
        "units": {"zkm": "km", "P": "mbar", "T": "K", "D": "cm-3", "gas": "ppmv"},
        "atmosphere_names": ATM_NAMES,
        "atmosphere_keys": ATM_SHORT,
        "zkm": zkm,
        "P_mbar": P,
        "T_K": T,
        "D_cm3": D,
        "gases_ppmv": gases,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    # quick sanity print: surface values for each atmosphere
    print(f"Wrote {OUT}")
    print(f"{NATM} atmospheres x {NZ} levels, 8 gases\n")
    print(f"{'atmosphere':32s} {'P0/mbar':>9s} {'T0/K':>7s} {'D0/cm-3':>10s} "
          f"{'H2O0/ppmv':>10s}")
    for a in range(NATM):
        print(f"{ATM_NAMES[a]:32s} {P[a][0]:9.1f} {T[a][0]:7.1f} {D[a][0]:10.3e} "
              f"{H2O[a][0]:10.1f}")


if __name__ == "__main__":
    main()
