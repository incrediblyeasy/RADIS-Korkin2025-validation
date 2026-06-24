"""
Robustness check #1 -- run the RADIS slab-stack (aspect) for ALL SIX MODTRAN
standard atmospheres on the same gas/band and overplot.

This shows the single general driver (aspect_driver.run_aspect) handles every
standard model, not just US-1976. Default: O2 A-band full column.

    python run_all_atmospheres.py                 # O2 A-band, all 6
    python run_all_atmospheres.py --molecule CH4 --band ch4
"""
import os
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from atmospheres import all_modtran
from aspect_driver import run_aspect

OUT = "figures"
os.makedirs(OUT, exist_ok=True)
COLORS = ["tab:red", "tab:orange", "tab:blue", "tab:green", "tab:purple", "k"]
SHORT = ["Tropical", "Mid-Lat Summer", "Mid-Lat Winter",
         "Sub-Arc Summer", "Sub-Arc Winter", "US Std 1976"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--molecule", default="O2")
    p.add_argument("--band", default="o2a")
    a = p.parse_args()

    results = []
    print(f"Running {a.molecule} {a.band} full column for all 6 atmospheres...\n")
    for atm in all_modtran():
        res = run_aspect(atm, molecule=a.molecule, band=a.band,
                         z_targets=[0.0], verbose=False)
        results.append(res)
        print(f"  {atm.meta['key']:18s}  tau_max(full col) = "
              f"{res.tau_max[0.0]:8.3f}   band-integral = "
              f"{res.band_integral()[0.0]:10.3e} cm-1")

    # overlay full-column optical depth
    fig, ax = plt.subplots(figsize=(13, 6))
    for res, c, lab in zip(results, COLORS, SHORT):
        ax.plot(res.wavenumber, res.tau[0.0], lw=0.7, color=c, label=lab)
    ax.set(xlabel="wavenumber (cm$^{-1}$)",
           ylabel=r"full-column optical thickness $\tau(\nu,z{=}0)$",
           title=f"{a.molecule} {a.band}: RADIS slab-stack for all 6 MODTRAN "
                 f"standard atmospheres")
    ax.legend(ncol=2, fontsize=9)
    fig.tight_layout()
    f1 = f"{OUT}/all6_{a.molecule}_{a.band}_optical_depth.png"
    fig.savefig(f1, dpi=140); plt.close(fig)

    # bar chart of band-integrated absorption
    fig, ax = plt.subplots(figsize=(9, 5))
    vals = [r.band_integral()[0.0] for r in results]
    ax.bar(SHORT, vals, color=COLORS)
    ax.set(ylabel=r"band-integrated $\int\tau\,d\nu$ (cm$^{-1}$)",
           title=f"{a.molecule} {a.band} full-column absorption across the 6 models")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    fig.tight_layout()
    f2 = f"{OUT}/all6_{a.molecule}_{a.band}_bandintegral.png"
    fig.savefig(f2, dpi=140); plt.close(fig)
    print(f"\nSaved {f1}\n      {f2}")


if __name__ == "__main__":
    main()
