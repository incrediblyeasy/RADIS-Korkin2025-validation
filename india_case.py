"""
India / current-atmosphere case -- the professor's points #2 and #3.

The 6 MODTRAN models are 1970s-80s climatological averages and are not specific
to the Indian subcontinent. Here we replace them with a real, present-day,
location-specific profile over an Indian site and run the SAME RADIS slab-stack
(aspect_driver), comparing three atmospheres for the O2 A-band:

  * MODTRAN "Tropical"        -- the closest standard model to India (15N average)
  * NASA PSG / GEOS-5         -- exact weather profile at the site & date  (point #2)
  * NRLMSIS 2.1 (2021)        -- latest empirical model, independent cross-check (#3)

Default site: IIT Bombay / Mumbai (19.13 N, 72.92 E). Change with --lat/--lon.

    python india_case.py                                  # Mumbai, default date
    python india_case.py --lat 28.61 --lon 77.21          # New Delhi
    python india_case.py --date "2024/01/15 06:00"        # winter morning

Outputs to figures/: profile comparison + O2 A-band optical depth + summary table.
"""
import os
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from atmospheres import get_modtran
from psg_atmosphere import get_psg, get_nrlmsis
from aspect_driver import run_aspect

OUT = "figures"
os.makedirs(OUT, exist_ok=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, default=19.13)
    p.add_argument("--lon", type=float, default=72.92)
    p.add_argument("--date", default="2024/06/15 12:00", help="YYYY/MM/DD HH:MM")
    p.add_argument("--site", default="Mumbai (IIT Bombay)")
    p.add_argument("--band", default="o2a")
    a = p.parse_args()

    print(f"Site: {a.site}  ({a.lat} N, {a.lon} E)  {a.date}\n")

    atms = []
    atms.append(("MODTRAN Tropical", get_modtran("tropical"), "tab:gray"))

    try:
        psg = get_psg(a.lat, a.lon, a.date, name=f"PSG GEOS-5 {a.site}")
        atms.append(("PSG GEOS-5 (exact)", psg, "tab:blue"))
        print(f"PSG    : {psg.zkm.size} layers, surface T={psg.T_K[0]:.1f} K, "
              f"H2O={psg.ppmv('H2O')[0]:.0f} ppmv")
    except Exception as e:
        print("PSG fetch failed (skipping):", e)

    try:
        nrl = get_nrlmsis(a.lat, a.lon, a.date.replace("/", "-").replace(" ", "T"),
                          name=f"NRLMSIS-2.1 {a.site}")
        atms.append(("NRLMSIS 2.1 (latest)", nrl, "tab:green"))
        print(f"NRLMSIS: {nrl.zkm.size} levels, surface T={nrl.T_K[0]:.1f} K")
    except Exception as e:
        print("NRLMSIS fetch failed (skipping):", e)

    # ---- profile comparison (T and O2 number density) -------------------
    fig, ax = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
    for lab, atm, c in atms:
        ax[0].plot(atm.T_K, atm.zkm, color=c, label=lab)
        ax[1].plot(atm.number_density("O2"), atm.zkm, color=c, label=lab)
    ax[0].set(xlabel="temperature T (K)", ylabel="z (km)", title="Temperature")
    ax[1].set_xscale("log")
    ax[1].set(xlabel="O$_2$ number density (cm$^{-3}$)", title="O$_2$ concentration")
    for x in ax:
        x.set_ylim(0, 60); x.grid(alpha=0.3); x.legend(fontsize=9)
    fig.suptitle(f"{a.site}: MODTRAN climatology vs present-day atmospheres "
                 f"({a.date})", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(f"{OUT}/india_profiles_{_slug(a.site)}.png", dpi=140); plt.close(fig)

    # ---- run the O2 A-band slab-stack for each ---------------------------
    print(f"\nRunning O2 A-band slab-stack for each atmosphere...")
    runs = []
    for lab, atm, c in atms:
        res = run_aspect(atm, molecule="O2", band=a.band, z_targets=[0.0],
                         verbose=False)
        runs.append((lab, res, c))
        print(f"  {lab:24s}  O2 col = {atm.column('O2'):.3e} cm-2   "
              f"tau_max = {res.tau_max[0.0]:8.3f}   "
              f"band-int = {res.band_integral()[0.0]:.3e} cm-1")

    fig, ax = plt.subplots(figsize=(13, 6))
    for lab, res, c in runs:
        ax.plot(res.wavenumber, res.tau[0.0], lw=0.7, color=c, label=lab)
    ax.set(xlabel="wavenumber (cm$^{-1}$)",
           ylabel=r"full-column optical thickness $\tau(\nu)$",
           title=f"O$_2$ A-band over {a.site} ({a.date}): "
                 f"MODTRAN vs present-day atmospheres")
    ax.legend(fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{OUT}/india_o2a_optical_depth_{_slug(a.site)}.png", dpi=140)
    plt.close(fig)

    # ---- relative differences vs MODTRAN tropical -----------------------
    base = next((r for l, r, c in runs if l.startswith("MODTRAN")), None)
    if base is not None and len(runs) > 1:
        print(f"\nRelative difference in band-integrated O2 absorption vs MODTRAN "
              f"Tropical:")
        b = base.band_integral()[0.0]
        for lab, res, c in runs:
            d = (res.band_integral()[0.0] - b) / b * 100
            print(f"  {lab:24s}  {d:+6.2f} %")
    print(f"\nSaved India figures to ./{OUT}/")


def _slug(s):
    import re
    return re.sub(r"[^0-9A-Za-z]+", "_", s).strip("_")


if __name__ == "__main__":
    main()
