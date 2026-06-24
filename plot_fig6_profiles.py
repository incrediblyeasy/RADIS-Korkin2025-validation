"""
Reproduce Figure 6 of Korkin, Sayer, Ibrahim & Lyapustin (2025), JQSRT 337,
109345 -- the MODTRAN / LOWTRAN-7 standard-atmosphere profiles that drive the
paper's `aspect` code.

Panels (as in the paper):
  6(a)  the 3-part height grid (steps 1 / 2.5 / 5 km below 25 / 25-50 / 50-120)
  6(b)  pressure p (log x), temperature T (linear x), air number density D (log x)
        vs height, for all 6 atmospheres
  6(c)  number concentration n = D * vmr  for H2O (#1) and CO2 (#2)
  6(d)  ... O3 (#3) and N2O (#4)
  6(e)  ... CO (#5) and CH4 (#6)
  6(f)  ... O2 (#7) and NO2 (#10)
Each gas panel shows the full 0-120 km range (left) and the lower 0-25 km (right).

Data: data/modtran_atmospheres.json (built from the paper's hprofiles.h).
Run:  python plot_fig6_profiles.py
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from atmospheres import all_modtran, get_modtran

OUT = "figures"
os.makedirs(OUT, exist_ok=True)

ATMS = all_modtran()
# distinct colour per atmosphere, in paper order
COLORS = ["tab:red", "tab:orange", "tab:blue", "tab:green", "tab:purple", "k"]
SHORT = ["Tropical", "Mid-Lat Summer", "Mid-Lat Winter",
         "Sub-Arc Summer", "Sub-Arc Winter", "US Std 1976"]


# --------------------------------------------------------------------- 6(a)
def fig6a():
    z = ATMS[0].zkm
    dz = np.diff(z)
    fig, ax = plt.subplots(1, 2, figsize=(11, 5))
    ax[0].plot(np.arange(len(z)), z, "o-", ms=4, color="tab:blue")
    ax[0].axhspan(0, 25, alpha=0.08, color="tab:green")
    ax[0].axhspan(25, 50, alpha=0.08, color="tab:orange")
    ax[0].axhspan(50, 120, alpha=0.08, color="tab:red")
    ax[0].set(xlabel="level index", ylabel="height z (km)",
              title="6(a) MODTRAN height grid (50 levels)")
    ax[0].text(2, 12, "step 1 km\n(0-25)", fontsize=9)
    ax[0].text(2, 37, "step 2.5 km\n(25-50)", fontsize=9)
    ax[0].text(2, 85, "step 5 km\n(50-120)", fontsize=9)
    ax[0].grid(alpha=0.3)
    ax[1].step(z[:-1], dz, where="post", color="tab:purple")
    ax[1].set(xlabel="height z (km)", ylabel="grid step dz (km)",
              title="6(a) grid spacing vs height")
    ax[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig6a_height_grid.png", dpi=140)
    plt.close(fig)


# --------------------------------------------------------------------- 6(b)
def fig6b():
    fig, ax = plt.subplots(1, 3, figsize=(15, 6), sharey=True)
    for atm, c, lab in zip(ATMS, COLORS, SHORT):
        ax[0].plot(atm.P_mbar, atm.zkm, color=c, label=lab)
        ax[1].plot(atm.T_K, atm.zkm, color=c, label=lab)
        ax[2].plot(atm.D_cm3, atm.zkm, color=c, label=lab)
    ax[0].set_xscale("log"); ax[0].set(xlabel="pressure p (mbar)", ylabel="z (km)",
                                       title="6(b) pressure")
    ax[1].set(xlabel="temperature T (K)", title="6(b) temperature")
    ax[2].set_xscale("log"); ax[2].set(xlabel="air density D (cm$^{-3}$)",
                                       title="6(b) number density")
    for a in ax:
        a.grid(alpha=0.3)
    ax[1].legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig6b_PTD_profiles.png", dpi=140)
    plt.close(fig)


# ----------------------------------------------------------------- 6(c-f)
def fig_gas_pair(tag, g1, g2):
    """Two gases, each: full 0-120 km (left) + lower 0-25 km (right)."""
    fig, ax = plt.subplots(2, 2, figsize=(13, 9))
    for row, gas in enumerate((g1, g2)):
        for atm, c, lab in zip(ATMS, COLORS, SHORT):
            if not atm.has(gas):
                continue
            n = atm.number_density(gas)
            ax[row, 0].plot(n, atm.zkm, color=c, label=lab)
            lo = atm.zkm <= 25
            ax[row, 1].plot(n[lo], atm.zkm[lo], color=c, marker=".", ms=4, label=lab)
        for col in (0, 1):
            ax[row, col].set_xscale("log")
            ax[row, col].set_xlabel(f"n({gas}) (cm$^{{-3}}$)")
            ax[row, col].grid(alpha=0.3)
        ax[row, 0].set_ylabel("z (km)")
        ax[row, 0].set_title(f"{gas} (#{_hid(gas)})  full column 0-120 km")
        ax[row, 1].set_title(f"{gas}  lower atmosphere 0-25 km")
    ax[0, 0].legend(fontsize=8)
    fig.suptitle(f"Fig. 6({tag}) MODTRAN number-concentration profiles: "
                 f"{g1} & {g2}", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(f"{OUT}/fig6{tag}_{g1}_{g2}.png", dpi=140)
    plt.close(fig)


def _hid(gas):
    from atmospheres import HITRAN_ID
    return HITRAN_ID[gas]


def main():
    print("Reproducing paper Figure 6 (MODTRAN atmosphere profiles)...")
    fig6a()
    fig6b()
    fig_gas_pair("c", "H2O", "CO2")
    fig_gas_pair("d", "O3", "N2O")
    fig_gas_pair("e", "CO", "CH4")
    fig_gas_pair("f", "O2", "NO2")
    print(f"Saved fig6a..fig6f to ./{OUT}/")

    # also dump the column-amount table (paper Sec. 6.2 / Table 5 analogue)
    print("\nColumn number density N_C (molec/cm2), Simpson over 0-120 km:")
    hdr = ["atmosphere", "air"] + ATMS[0].gases
    print("  ".join(f"{h:>12s}" for h in hdr))
    for atm in ATMS:
        row = [atm.meta["key"], f"{atm.air_column():.4e}"]
        row += [f"{atm.column(g):.4e}" for g in atm.gases]
        print("  ".join(f"{v:>12s}" for v in row))


if __name__ == "__main__":
    main()
