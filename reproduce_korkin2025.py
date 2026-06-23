"""
Reproduction of the gas-cell (`gcell`) validation benchmarks from:

  Korkin, Sayer, Ibrahim & Lyapustin (2025),
  "A practical guide to coding line-by-line trace gas absorption in
   Earth's atmosphere", JQSRT 337, 109345.
  https://doi.org/10.1016/j.jqsrt.2025.109345

Two benchmarks are reproduced with RADIS (line-by-line, HITRAN, Voigt):

  Fig. 4 : O2 A-band gas cell  (Predoi-Cross et al. 2008)
           13006-13166 cm-1, T=296 K, p=0.724 bar, L=1633.6 cm, pure O2
  Fig. 5 : CH4 2.3 um gas cell (GATS / SpectralCalc)
           4081.901-4505.699 cm-1, T=296 K, p=1.0 bar, L=8 cm, pure CH4

Both cells are pure gas (mole_fraction = 1), which reproduces the column
densities quoted in the paper (2.892e22 and 1.958e20 molec/cm2).
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from radis import calc_spectrum

OUT = "figures"
import os
os.makedirs(OUT, exist_ok=True)


def gas_cell(molecule, wmin, wmax, pressure_bar, Tgas, path_length, wstep):
    s = calc_spectrum(
        wmin, wmax,
        molecule=molecule,
        isotope="1,2,3" if molecule == "O2" else "1,2,3,4",
        pressure=pressure_bar,
        Tgas=Tgas,
        path_length=path_length,
        mole_fraction=1,
        wstep=wstep,
        databank="hitran",
        warnings={"AccuracyWarning": "ignore"},
        verbose=False,
    )
    w, T = s.get("transmittance_noslit", wunit="cm-1")
    _, A = s.get("absorbance", wunit="cm-1")      # optical thickness tau = -ln(T)
    return np.asarray(w), np.asarray(T), np.asarray(A), s


# ----------------------------------------------------------------------
# Benchmark 1 : Fig. 4  -- O2 A-band
# ----------------------------------------------------------------------
print("== Fig.4  O2 A-band ==")
w, T, tau, s_o2 = gas_cell("O2", 13006, 13166, 0.724, 296, 1633.6, wstep=0.005)
n_o2 = 0.7145 * 101325 / (1.380649e-23 * 296) / 1e6 * 1633.6
print(f"   points={len(w)}  Tmin={T.min():.4f}  tau_max={tau.max():.3f}"
      f"  col.dens={n_o2:.4e} molec/cm2")

fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
ax[0].plot(w, T, lw=0.5, color="navy")
ax[0].set(xlabel="wavenumber (cm$^{-1}$)", ylabel="transmittance",
          title="Fig.4(a) O$_2$ A-band: direct transmission")
ax[0].set_xlim(13006, 13166)
ax2 = ax[1]
ax2.semilogy(w, tau, lw=0.5, color="firebrick")
ax2.set(xlabel="wavenumber (cm$^{-1}$)", ylabel=r"optical thickness $\tau$",
        title="Fig.4(a) O$_2$ A-band: optical thickness")
ax2.set_xlim(13006, 13166)
fig.tight_layout()
fig.savefig(f"{OUT}/fig4a_o2a_band.png", dpi=140)
plt.close(fig)

# sub-band Fig.4(b)
m = (w >= 13159.6) & (w <= 13165.6)
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
ax[0].plot(w[m], T[m], lw=0.8, color="navy")
ax[0].set(xlabel="wavenumber (cm$^{-1}$)", ylabel="transmittance",
          title="Fig.4(b) O$_2$ A-band sub-band: transmission")
ax[1].semilogy(w[m], tau[m], lw=0.8, color="firebrick")
ax[1].set(xlabel="wavenumber (cm$^{-1}$)", ylabel=r"optical thickness $\tau$",
          title="Fig.4(b) O$_2$ A-band sub-band: optical thickness")
fig.tight_layout()
fig.savefig(f"{OUT}/fig4b_o2a_subband.png", dpi=140)
plt.close(fig)

# ----------------------------------------------------------------------
# Benchmark 2 : Fig. 5  -- CH4 2.3 um band
# ----------------------------------------------------------------------
print("== Fig.5  CH4 2.3 um ==")
w2, T2, tau2, s_ch4 = gas_cell("CH4", 4081.901, 4505.699, 1.0, 296, 8.0, wstep=0.002)
n_ch4 = 0.986923 * 101325 / (1.380649e-23 * 296) / 1e6 * 8.0
print(f"   points={len(w2)}  Tmin={T2.min():.4f}  tau_max={tau2.max():.3f}"
      f"  col.dens={n_ch4:.4e} molec/cm2")

fig, ax = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
ax[0].plot(w2, tau2, lw=0.4, color="firebrick")
ax[0].set(ylabel=r"optical thickness $\tau$",
          title="Fig.5(a) CH$_4$ gas cell (8 cm, 296 K, 1 bar): optical thickness")
ax[1].plot(w2, T2, lw=0.4, color="navy")
ax[1].set(xlabel="wavenumber (cm$^{-1}$)", ylabel="transmittance",
          title="Fig.5(b) CH$_4$ gas cell: direct one-way transmittance")
ax[1].set_xlim(4081.901, 4505.699)
fig.tight_layout()
fig.savefig(f"{OUT}/fig5_ch4_band.png", dpi=140)
plt.close(fig)

# save numerical results to match paper's benchmark ASCII files
np.savetxt(f"{OUT}/o2a_radis.txt", np.column_stack([w, tau]),
           header="wavenumber_cm-1  optical_thickness  (O2 A-band, RADIS)")
np.savetxt(f"{OUT}/ch4_radis.txt", np.column_stack([w2, tau2]),
           header="wavenumber_cm-1  optical_thickness  (CH4 2.3um, RADIS)")
print("Saved figures and data to ./figures/")
