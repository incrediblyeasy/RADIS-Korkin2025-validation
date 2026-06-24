"""
"Exact" / present-day atmospheres for the RADIS-Korkin pipeline.

The 6 MODTRAN/LOWTRAN models (atmospheres.py) are climatological averages from
the 1970s-80s. Korkin et al. (2025) note they can differ from the *actual*
atmosphere on a given day. This module pulls a real, location- and date-specific
profile and returns it as the same `Atmosphere` object used everywhere else, so
the line-by-line driver does not care where the numbers came from.

Two independent sources are provided:

  get_psg(lat, lon, date)      NASA Planetary Spectrum Generator (psg.gsfc.nasa.gov)
                               -> GEOS-5/MERRA-2 weather: P, T and mole fractions
                               for H2O, CO2, O3, N2O, CO, CH4, O2 ... (all gases).
                               Requires internet; result is cached under data/.

  get_nrlmsis(lat, lon, date)  NRLMSIS 2.1 empirical model (NASA/NRL, 2021) via the
                               `pymsis` package. No API key. Gives T, total density
                               and O2/N2/O number densities -> exact O2 & temperature
                               profile for any place/time (incl. India). Independent
                               cross-check of PSG for the O2 A-band.

Both return geometric height by hydrostatic integration of the (P, T) profile.

CLI:  python psg_atmosphere.py            # demo: Mumbai today, PSG vs NRLMSIS
"""
import os
import re
import json
import numpy as np

from atmospheres import Atmosphere, HITRAN_ID

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "psg_cache")
PSG_URL = os.environ.get("PSG_URL", "https://psg.gsfc.nasa.gov/api.php")
PSG_KEY = os.environ.get("PSG_API_KEY", "")     # optional, raises rate limits

R_UNIV = 8.314462618      # J/mol/K
kB = 1.380649e-23         # J/K
G0 = 9.80665              # m/s2
M_AIR = 0.0289644         # kg/mol (dry air)

# PSG molecule label -> our gas key (only the ones we model)
PSG_TO_GAS = {"H2O": "H2O", "CO2": "CO2", "O3": "O3", "N2O": "N2O",
              "CO": "CO", "CH4": "CH4", "O2": "O2", "NO2": "NO2"}


# ---------------------------------------------------------------------------
# Hydrostatic height from a (P, T) profile ordered bottom -> top.
# ---------------------------------------------------------------------------
def _heights_from_PT(P_pa, T_k, z0_km=0.0):
    z = np.zeros_like(P_pa)
    z[0] = z0_km * 1e3
    for i in range(len(P_pa) - 1):
        Tm = 0.5 * (T_k[i] + T_k[i + 1])
        # dz = (R* Tm / (M g)) * ln(P_i / P_{i+1})
        z[i + 1] = z[i] + (R_UNIV * Tm / (M_AIR * G0)) * np.log(P_pa[i] / P_pa[i + 1])
    return z / 1e3   # km


# ===========================================================================
# NASA Planetary Spectrum Generator (GEOS-5 weather)
# ===========================================================================
def _psg_config(lat, lon, date_str, gases):
    g = ",".join(gases)
    types = ",".join(f"HIT[{HITRAN_ID[x]}]" for x in gases)
    return (
        f"<OBJECT>Earth\n"
        f"<OBJECT-DATE>{date_str}\n"
        f"<OBJECT-OBS-LATITUDE>{lat}\n"
        f"<OBJECT-OBS-LONGITUDE>{lon}\n"
        f"<GEOMETRY>Nadir\n"
        f"<ATMOSPHERE-STRUCTURE>Equilibrium\n"
        f"<ATMOSPHERE-NGAS>{len(gases)}\n"
        f"<ATMOSPHERE-GAS>{g}\n"
        f"<ATMOSPHERE-TYPE>{types}\n"
        f"<ATMOSPHERE-LAYERS>0\n"
    )


def _psg_post(cfg, timeout=180):
    import requests
    data = {"type": "cfg", "watm": "y", "file": cfg}
    if PSG_KEY:
        data["key"] = PSG_KEY
    r = requests.post(PSG_URL, data=data, timeout=timeout)
    r.raise_for_status()
    return r.text


def _parse_psg_cfg(text):
    """Parse a PSG cfg response into (P_bar, T_K, {gas: mole_fraction}, punit)."""
    err = [ln for ln in text.splitlines() if ln.startswith("# ERROR")]
    if err:
        raise RuntimeError("PSG error: " + " | ".join(e[8:] for e in err))

    def field(tag):
        m = re.search(rf"<{tag}>(.*)", text)
        return m.group(1).strip() if m else None

    nlay = field("ATMOSPHERE-LAYERS")
    mols = field("ATMOSPHERE-LAYERS-MOLECULES")
    if not nlay or not mols or int(nlay) == 0:
        raise RuntimeError("PSG returned no atmospheric layers (weather retrieval "
                           "failed). Check the date is within the GEOS-5 range.")
    nlay = int(nlay)
    mols = [m.strip() for m in mols.split(",")]
    punit = field("ATMOSPHERE-PUNIT") or "bar"

    P, T, frac = [], [], {g: [] for g in mols}
    for i in range(1, nlay + 1):
        ln = field(f"ATMOSPHERE-LAYER-{i}")
        vals = [float(x) for x in ln.split(",")]
        P.append(vals[0]); T.append(vals[1])
        for j, m in enumerate(mols):
            frac[m].append(vals[2 + j])
    P, T = np.array(P), np.array(T)
    # PSG orders layers surface -> top; ensure that (P decreasing)
    if P[0] < P[-1]:
        order = np.argsort(-P)
        P, T = P[order], T[order]
        frac = {m: list(np.array(v)[order]) for m, v in frac.items()}
    return P, T, frac, punit, mols


def _punit_to_bar(P, punit):
    u = punit.lower()
    return {"bar": 1.0, "mb": 1e-3, "mbar": 1e-3, "pa": 1e-5,
            "hpa": 1e-3, "atm": 1.01325}.get(u, 1.0) * P


def get_psg(lat, lon, date, gases=("H2O", "CO2", "O3", "N2O", "CO", "CH4", "O2"),
            use_cache=True, name=None):
    """Fetch a present-day atmosphere from NASA PSG (GEOS-5) as an Atmosphere.

    date : 'YYYY/MM/DD HH:MM' string (PSG format) or anything with strftime.
    """
    date_str = date if isinstance(date, str) else date.strftime("%Y/%m/%d %H:%M")
    gases = [g for g in gases if g in HITRAN_ID]
    os.makedirs(CACHE, exist_ok=True)
    tag = re.sub(r"[^0-9A-Za-z]+", "_", f"psg_{lat}_{lon}_{date_str}")
    cpath = os.path.join(CACHE, tag + ".cfg")

    if use_cache and os.path.exists(cpath):
        text = open(cpath, encoding="utf-8").read()
    else:
        text = _psg_post(_psg_config(lat, lon, date_str, gases))
        with open(cpath, "w", encoding="utf-8") as f:
            f.write(text)

    P_raw, T, frac, punit, mols = _parse_psg_cfg(text)
    P_bar = _punit_to_bar(P_raw, punit)
    P_pa = P_bar * 1e5
    zkm = _heights_from_PT(P_pa, T)
    D_cm3 = P_pa / (kB * T) * 1e-6                      # total air, cm-3
    ppmv = {}
    for m, key in PSG_TO_GAS.items():
        if m in frac:
            ppmv[key] = np.array(frac[m]) * 1e6
    return Atmosphere(
        name=name or f"PSG GEOS-5 @ ({lat},{lon}) {date_str}",
        zkm=zkm, T_K=T, P_mbar=P_bar * 1e3, D_cm3=D_cm3, ppmv_by_gas=ppmv,
        meta={"source": "NASA PSG / GEOS-5", "lat": lat, "lon": lon,
              "date": date_str, "n_layers": len(zkm), "cache": cpath},
    )


# ===========================================================================
# NRLMSIS 2.1 (NASA/NRL empirical model) -- no API key, offline after install
# ===========================================================================
def get_nrlmsis(lat, lon, date, alts_km=None, name=None):
    """Exact O2 + temperature + density profile from NRLMSIS 2.1 (pymsis).

    Covers O2, N2, O number densities and temperature -> ideal for the O2 A-band.
    date : numpy datetime64 / datetime / 'YYYY-MM-DDTHH:MM' string.
    """
    import pymsis
    if alts_km is None:
        alts_km = np.concatenate([np.arange(0, 25, 1.0), np.arange(25, 50, 2.5),
                                   np.arange(50, 121, 5.0)])
    d = np.datetime64(date) if not isinstance(date, np.datetime64) else date
    out = np.squeeze(pymsis.calculate(d, lon, lat, np.asarray(alts_km, float)))
    V = pymsis.Variable
    T = out[:, V.TEMPERATURE]
    n_O2 = out[:, V.O2] * 1e-6                      # m-3 -> cm-3
    # total air number density = sum over all neutral species columns (N2..NO).
    # MSIS returns NaN for species absent at a given altitude (e.g. atomic O near
    # the ground), so use a NaN-safe sum.
    species = [V.N2, V.O2, V.O, V.HE, V.H, V.AR, V.N, V.ANOMALOUS_O, V.NO]
    n_total = np.nansum(out[:, species], axis=1) * 1e-6             # cm-3
    ppmv = {"O2": n_O2 / n_total * 1e6}
    P_mbar = n_total * 1e6 * kB * T / 1e2           # cm-3->m-3, Pa->mbar
    return Atmosphere(
        name=name or f"NRLMSIS-2.1 @ ({lat},{lon}) {np.datetime_as_string(d, unit='m')}",
        zkm=np.asarray(alts_km, float), T_K=T, P_mbar=P_mbar, D_cm3=n_total,
        ppmv_by_gas=ppmv,
        meta={"source": "NRLMSIS 2.1 (pymsis)", "lat": lat, "lon": lon,
              "date": str(d)},
    )


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Fetch a present-day atmosphere.")
    p.add_argument("--lat", type=float, default=19.13, help="latitude (deg N)")
    p.add_argument("--lon", type=float, default=72.92, help="longitude (deg E)")
    p.add_argument("--date", default="2024/06/15 12:00", help="YYYY/MM/DD HH:MM")
    p.add_argument("--source", choices=["psg", "nrlmsis", "both"], default="both")
    a = p.parse_args()

    if a.source in ("psg", "both"):
        try:
            atm = get_psg(a.lat, a.lon, a.date)
            print(atm)
            print(f"  surface: T={atm.T_K[0]:.1f} K  P={atm.P_mbar[0]:.1f} mbar  "
                  f"H2O={atm.ppmv('H2O')[0]:.0f} ppmv  O2={atm.ppmv('O2')[0]:.0f} ppmv")
            print(f"  O2 column  = {atm.column('O2'):.3e} molec/cm2")
            if atm.has("H2O"):
                print(f"  H2O column = {atm.column('H2O'):.3e} molec/cm2")
        except Exception as e:
            print("PSG fetch failed:", e)

    if a.source in ("nrlmsis", "both"):
        try:
            d = a.date.replace("/", "-").replace(" ", "T")
            atm = get_nrlmsis(a.lat, a.lon, d)
            print(atm)
            print(f"  surface: T={atm.T_K[0]:.1f} K  O2={atm.ppmv('O2')[0]:.0f} ppmv")
            print(f"  O2 column  = {atm.column('O2'):.3e} molec/cm2")
        except Exception as e:
            print("NRLMSIS fetch failed:", e)
