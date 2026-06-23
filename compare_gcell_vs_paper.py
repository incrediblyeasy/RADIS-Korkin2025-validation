"""
Overplot RADIS (Python LBL) against the paper's OWN C-code reference output
(`gcell`) from Korkin, Sayer, Ibrahim & Lyapustin (2025), JQSRT 337, 109345.

Reference data are the benchmark files shipped in the authors' repository
    github.com/korkins/aspect_gcell  ->  benchmarks/
  Section5p4p1___test_gcell_o2a.txt   (Fig.4  O2 A-band)
  Section5p4p2___test_gcell_ch4.txt   (Fig.5  CH4 2.3 um)

Both are pure-gas cells (mole_fraction = 1), matching the *.inp files:
  O2 : 13006-13166 cm-1, dv 0.01, L=1633.6 cm, T=296 K, p=0.7145 atm
  CH4: 4081.901-4505.699 cm-1, dv 0.002, L=8 cm, T=296 K, p=1.0 atm
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from radis import calc_spectrum

# Path to the authors' reference benchmarks. Clone github.com/korkins/aspect_gcell
# and either set ASPECT_GCELL to its location or place it next to this script.
_default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aspect_gcell")
BENCH = os.path.join(os.environ.get("ASPECT_GCELL", _default), "benchmarks")
OUT = "figures"
os.makedirs(OUT, exist_ok=True)
ATM = 1.01325  # bar per atm


def radis_tau(molecule, wmin, wmax, p_atm, Tgas, L_cm, wstep, iso):
    s = calc_spectrum(
        wmin, wmax, molecule=molecule, isotope=iso,
        pressure=p_atm * ATM, Tgas=Tgas, path_length=L_cm,
        mole_fraction=1, wstep=wstep, databank="hitran",
        warnings={"AccuracyWarning": "ignore"}, verbose=False,
    )
    w, A = s.get("absorbance", wunit="cm-1")      # absorbance = tau/ln(10)? -> see below
    # RADIS 'absorbance' is log10-based; optical thickness tau = -ln(T):
    _, T = s.get("transmittance_noslit", wunit="cm-1")
    tau = -np.log(np.clip(np.asarray(T), 1e-300, None))
    return np.asarray(w), tau


def load_bench(path, col_nu=0, col_tau=1, skip_top=0):
    data = np.loadtxt(path, comments="#")
    if skip_top:
        data = data[skip_top:]
    return data[:, col_nu], data[:, col_tau]


def metrics(w_r, t_r, w_b, t_b):
    """Interpolate RADIS onto benchmark grid, return rel-RMS over significant tau."""
    t_ri = np.interp(w_b, w_r, t_r)
    m = t_b > 0.01 * t_b.max()
    rms = np.sqrt(np.mean((t_ri[m] - t_b[m]) ** 2))
    rel = np.sqrt(np.mean(((t_ri[m] - t_b[m]) / t_b[m]) ** 2)) * 100
    return t_ri, rms, rel, m


# ---------------------------------------------------------------- O2 A-band
print("== O2 A-band (Fig.4) ==")
wb_o2, tb_o2 = load_bench(os.path.join(BENCH, "Section5p4p1___test_gcell_o2a.txt"),
                          skip_top=1)  # drop the (-999, n_column) header row
wr_o2, tr_o2 = radis_tau("O2", 13006, 13166, 0.7145, 296, 1633.6, 0.01, "1,2,3")
tri_o2, rms_o2, rel_o2, m_o2 = metrics(wr_o2, tr_o2, wb_o2, tb_o2)
print(f"   paper points={len(wb_o2)}  RADIS points={len(wr_o2)}")
print(f"   tau_max paper={tb_o2.max():.3f}  RADIS={tr_o2.max():.3f}")
print(f"   rel-RMS (significant lines) = {rel_o2:.2f}%   abs-RMS = {rms_o2:.2e}")

# ---------------------------------------------------------------- CH4 band
print("== CH4 2.3 um (Fig.5) ==")
wb_c, tb_c = load_bench(os.path.join(BENCH, "Section5p4p2___test_gcell_ch4.txt"),
                        col_nu=0, col_tau=1)
wr_c, tr_c = radis_tau("CH4", 4081.901, 4505.699, 1.0, 296, 8.0, 0.002, "1,2,3,4")
tri_c, rms_c, rel_c, m_c = metrics(wr_c, tr_c, wb_c, tb_c)
print(f"   paper points={len(wb_c)}  RADIS points={len(wr_c)}")
print(f"   tau_max paper={tb_c.max():.3f}  RADIS={tr_c.max():.3f}")
print(f"   rel-RMS (significant lines) = {rel_c:.2f}%   abs-RMS = {rms_c:.2e}")

# ================================================================ PLOT O2
fig, ax = plt.subplots(2, 1, figsize=(13, 8), sharex=True,
                       gridspec_kw={"height_ratios": [3, 1]})
ax[0].plot(wb_o2, tb_o2, lw=1.1, color="black", label="paper C-code (gcell)")
ax[0].plot(wr_o2, tr_o2, lw=0.8, color="tab:red", ls="--", label="RADIS (Python)")
ax[0].set(ylabel=r"optical thickness $\tau$",
          title="O$_2$ A-band gas cell (Fig.4): RADIS vs paper's gcell C-code  "
                f"[rel-RMS = {rel_o2:.2f}%]")
ax[0].legend(); ax[0].set_yscale("log"); ax[0].set_ylim(1e-5, None)
ax[1].plot(wb_o2, tri_o2 - tb_o2, lw=0.6, color="tab:blue")
ax[1].axhline(0, color="k", lw=0.5)
ax[1].set(xlabel="wavenumber (cm$^{-1}$)", ylabel=r"$\tau_{RADIS}-\tau_{paper}$")
ax[1].set_xlim(13006, 13166)
fig.tight_layout()
fig.savefig(f"{OUT}/overplot_o2a_gcell_vs_radis.png", dpi=140)
plt.close(fig)

# zoom on the band head (Fig.4b region)
fig, ax = plt.subplots(figsize=(11, 5))
mm = (wb_o2 >= 13120) & (wb_o2 <= 13166)
ax.plot(wb_o2[mm], tb_o2[mm], lw=1.4, color="black", label="paper C-code (gcell)")
mr = (wr_o2 >= 13120) & (wr_o2 <= 13166)
ax.plot(wr_o2[mr], tr_o2[mr], lw=1.0, color="tab:red", ls="--", label="RADIS")
ax.set(xlabel="wavenumber (cm$^{-1}$)", ylabel=r"optical thickness $\tau$",
       title="O$_2$ A-band head (zoom): RADIS vs paper gcell")
ax.legend(); fig.tight_layout()
fig.savefig(f"{OUT}/overplot_o2a_gcell_zoom.png", dpi=140)
plt.close(fig)

# ================================================================ PLOT CH4
fig, ax = plt.subplots(2, 1, figsize=(13, 8), sharex=True,
                       gridspec_kw={"height_ratios": [3, 1]})
ax[0].plot(wb_c, tb_c, lw=0.7, color="black", label="paper C-code (gcell)")
ax[0].plot(wr_c, tr_c, lw=0.5, color="tab:red", ls="--", label="RADIS (Python)")
ax[0].set(ylabel=r"optical thickness $\tau$",
          title="CH$_4$ 2.3 $\\mu$m gas cell (Fig.5): RADIS vs paper's gcell C-code  "
                f"[rel-RMS = {rel_c:.2f}%]")
ax[0].legend()
ax[1].plot(wb_c, tri_c - tb_c, lw=0.4, color="tab:blue")
ax[1].axhline(0, color="k", lw=0.5)
ax[1].set(xlabel="wavenumber (cm$^{-1}$)", ylabel=r"$\tau_{RADIS}-\tau_{paper}$")
ax[1].set_xlim(4081.901, 4505.699)
fig.tight_layout()
fig.savefig(f"{OUT}/overplot_ch4_gcell_vs_radis.png", dpi=140)
plt.close(fig)

print("\nSaved overplots to ./figures/")
