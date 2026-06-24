"""
Unified atmosphere interface for the RADIS / Korkin-2025 reproduction.

Every atmosphere -- whether one of the 6 MODTRAN/LOWTRAN standard models, or an
"exact" present-day profile pulled from NASA's Planetary Spectrum Generator
(see psg_atmosphere.py) -- is returned as the same `Atmosphere` object, so the
line-by-line driver (aspect_driver.py) and the Figure-6 plotter never care where
the numbers came from.

    from atmospheres import get_modtran, list_modtran
    atm = get_modtran("tropical")          # or 1..6, or "us_standard_1976"
    atm.zkm, atm.T_K, atm.P_mbar, atm.D_cm3
    atm.ppmv("O2")                         # volume mixing ratio profile (ppmv)
    atm.number_density("O2")               # molec/cm3 profile  = D * ppmv * 1e-6
    atm.column("O2")                       # column molec/cm2   (Simpson over z)

MODTRAN profiles come from data/modtran_atmospheres.json, built once from the
paper's hprofiles.h by build_atmosphere_data.py.
"""
import os
import json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(HERE, "data", "modtran_atmospheres.json")
KM_TO_CM = 1.0e5

# HITRAN molecule id -> name, for convenience both directions
HITRAN_ID = {"H2O": 1, "CO2": 2, "O3": 3, "N2O": 4, "CO": 5,
             "CH4": 6, "O2": 7, "NO2": 10}


def _simpson(y, x):
    """Composite integration; SciPy Simpson if available, else trapezoid."""
    try:
        from scipy.integrate import simpson
        return float(simpson(y, x=x))
    except Exception:
        trap = getattr(np, "trapezoid", None) or np.trapz
        return float(trap(y, x))


class Atmosphere:
    """A T/P/density + gas-mixing-ratio profile on a height grid."""

    def __init__(self, name, zkm, T_K, P_mbar, D_cm3, ppmv_by_gas, meta=None):
        self.name = name
        self.zkm = np.asarray(zkm, float)
        self.T_K = np.asarray(T_K, float)
        self.P_mbar = np.asarray(P_mbar, float)
        self.D_cm3 = np.asarray(D_cm3, float)
        self._ppmv = {g: np.asarray(v, float) for g, v in ppmv_by_gas.items()}
        self.meta = meta or {}

    # ---- accessors -------------------------------------------------------
    @property
    def gases(self):
        return sorted(self._ppmv, key=lambda g: HITRAN_ID.get(g, 99))

    def has(self, gas):
        return gas in self._ppmv

    def ppmv(self, gas):
        if gas not in self._ppmv:
            raise KeyError(f"{self.name}: no profile for {gas} "
                           f"(have {self.gases})")
        return self._ppmv[gas]

    def mole_fraction(self, gas):
        return self.ppmv(gas) * 1e-6

    def number_density(self, gas):
        """Gas number concentration profile, molec/cm3  (= D * ppmv * 1e-6)."""
        return self.D_cm3 * self.ppmv(gas) * 1e-6

    def column(self, gas):
        """Vertical column amount, molec/cm2: integral of n_gas(z) dz."""
        return _simpson(self.number_density(gas), self.zkm) * KM_TO_CM

    def air_column(self):
        return _simpson(self.D_cm3, self.zkm) * KM_TO_CM

    def __repr__(self):
        return (f"<Atmosphere {self.name!r}: {len(self.zkm)} levels "
                f"{self.zkm[0]:.0f}-{self.zkm[-1]:.0f} km, gases={self.gases}>")


# ---------------------------------------------------------------------------
# MODTRAN / LOWTRAN-7 standard atmospheres (the 6 models in the paper)
# ---------------------------------------------------------------------------
_cache = None


def _load():
    global _cache
    if _cache is None:
        if not os.path.exists(_DATA):
            raise FileNotFoundError(
                f"{_DATA} not found. Run `python build_atmosphere_data.py` "
                "after cloning github.com/korkins/aspect_gcell.")
        with open(_DATA, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def list_modtran():
    """Return [(index, key, full_name), ...] for the 6 standard atmospheres."""
    d = _load()
    return [(i + 1, k, n) for i, (k, n) in
            enumerate(zip(d["atmosphere_keys"], d["atmosphere_names"]))]


def _resolve_index(which):
    """Accept 1..6, a short key, or a full name -> 0-based index."""
    d = _load()
    if isinstance(which, (int, np.integer)):
        if not 1 <= int(which) <= 6:
            raise ValueError("MODTRAN iatm must be 1..6")
        return int(which) - 1
    w = str(which).strip().lower()
    for i, k in enumerate(d["atmosphere_keys"]):
        if w == k or w == d["atmosphere_names"][i].lower():
            return i
    # loose contains-match (e.g. "tropical", "us standard")
    for i, k in enumerate(d["atmosphere_keys"]):
        if w in k or w in d["atmosphere_names"][i].lower():
            return i
    raise ValueError(f"unknown atmosphere {which!r}; choose from "
                     f"{[k for k in d['atmosphere_keys']]} or 1..6")


def get_modtran(which):
    """Get one of the 6 standard atmospheres by index (1..6), key, or name."""
    d = _load()
    a = _resolve_index(which)
    ppmv = {g: d["gases_ppmv"][g]["ppmv"][a] for g in d["gases_ppmv"]}
    return Atmosphere(
        name=d["atmosphere_names"][a],
        zkm=d["zkm"], T_K=d["T_K"][a], P_mbar=d["P_mbar"][a], D_cm3=d["D_cm3"][a],
        ppmv_by_gas=ppmv,
        meta={"source": "MODTRAN/LOWTRAN-7", "iatm": a + 1,
              "key": d["atmosphere_keys"][a]},
    )


def all_modtran():
    return [get_modtran(i) for i in range(1, 7)]


if __name__ == "__main__":
    # tiny self-test / column-amount table (mirrors paper Sec. 6.2)
    print("MODTRAN standard atmospheres:")
    for i, k, n in list_modtran():
        print(f"  {i}  {k:18s}  {n}")
    print("\nColumn number density N_C (molec/cm2), Simpson over 0-120 km:")
    print(f"{'atmosphere':20s} {'air':>11s} {'O2':>11s} {'H2O':>11s} {'CH4':>11s}")
    for atm in all_modtran():
        print(f"{atm.meta['key']:20s} {atm.air_column():11.4e} "
              f"{atm.column('O2'):11.4e} {atm.column('H2O'):11.4e} "
              f"{atm.column('CH4'):11.4e}")
