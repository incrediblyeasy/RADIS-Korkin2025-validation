"""
Reproduce the paper's atmospheric code `aspect` with RADIS, using RADIS's
slab-STACKING (SerialSlabs) to build a layered Earth atmosphere -- exactly the
"stack function" approach.

Paper : Korkin, Sayer, Ibrahim & Lyapustin (2025), JQSRT 337, 109345.
Ref.  : github.com/korkins/aspect_gcell  -> benchmarks/Section6p2p2___test_aspect_o2a.txt
        O2 A-band, US Standard 1976 atmosphere (iatm=6), O2 well-mixed 0.209,
        cumulative optical thickness tau(nu, z) from Top-Of-Atmosphere down to
        z = 0.0, 1.0, 2.5, 8.0 km. Grid 12822-13364.4 cm-1, dv=0.01.

How `aspect` works (main_aspect.cpp): at every MODTRAN level z_i it evaluates the
Voigt cross-section sigma(nu; T_i, P_i), forms extinction k(nu,z)=sigma*n_O2(z),
and integrates k over height from z up to TOA (tauabs25.cpp, Simpson rule).

RADIS analogue: treat each gap between MODTRAN levels as one homogeneous slab,
compute its spectrum with calc_spectrum, then STACK the slabs with SerialSlabs.
Stacking multiplies transmittances  <=>  adds optical thickness, so the partial
column tau(TOA->z) is the sum of all slab optical thicknesses lying above z.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from radis import calc_spectrum, SerialSlabs

OUT = "figures"
os.makedirs(OUT, exist_ok=True)
# Path to the authors' reference benchmarks. Clone github.com/korkins/aspect_gcell
# and either set ASPECT_GCELL to its location or place it next to this script.
_default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aspect_gcell")
BENCH = os.path.join(os.environ.get("ASPECT_GCELL", _default),
                     "benchmarks", "Section6p2p2___test_aspect_o2a.txt")
kB = 1.380649e-23  # J/K

# ----------------------------------------------------------------------
# US Standard 1976 profile (AFGL/MODTRAN), taken verbatim from the paper's
# src/hprofiles.h  (atmosphere index 6).  50 levels.
# ----------------------------------------------------------------------
zkm = np.array([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,
                25,27.5,30,32.5,35,37.5,40,42.5,45,47.5,50,55,60,65,70,75,80,85,
                90,95,100,105,110,115,120], float)
Pmbar = np.array([1.013e3,8.988e2,7.950e2,7.012e2,6.166e2,5.405e2,4.722e2,4.111e2,
    3.565e2,3.080e2,2.650e2,2.270e2,1.940e2,1.658e2,1.417e2,1.211e2,1.035e2,
    8.850e1,7.565e1,6.467e1,5.529e1,4.729e1,4.047e1,3.467e1,2.972e1,2.549e1,
    1.743e1,1.197e1,8.010,5.746,4.150,2.871,2.060,1.491,1.090,7.978e-1,4.250e-1,
    2.190e-1,1.090e-1,5.220e-2,2.400e-2,1.050e-2,4.460e-3,1.840e-3,7.600e-4,
    3.200e-4,1.450e-4,7.100e-5,4.010e-5,2.540e-5], float)
Tk = np.array([288.2,281.7,275.2,268.7,262.2,255.7,249.2,242.7,236.2,229.7,223.3,
    216.8,216.7,216.7,216.7,216.7,216.7,216.7,216.7,216.7,216.7,217.6,218.6,
    219.6,220.6,221.6,224.0,226.5,230.0,236.5,242.9,250.4,257.3,264.2,270.6,
    270.7,260.8,247.0,233.3,219.6,208.4,198.6,188.9,186.9,188.4,195.1,208.8,
    240.0,300.0,360.0], float)
Dcm3 = np.array([2.548e19,2.313e19,2.094e19,1.891e19,1.704e19,1.532e19,1.373e19,
    1.228e19,1.094e19,9.719e18,8.602e18,7.589e18,6.489e18,5.546e18,4.739e18,
    4.050e18,3.462e18,2.960e18,2.530e18,2.163e18,1.849e18,1.575e18,1.342e18,
    1.144e18,9.765e17,8.337e17,5.640e17,3.830e17,2.524e17,1.761e17,1.238e17,
    8.310e16,5.803e16,4.090e16,2.920e16,2.136e16,1.181e16,6.426e15,3.386e15,
    1.723e15,8.347e14,3.832e14,1.711e14,7.136e13,2.924e13,1.189e13,5.033e12,
    2.144e12,9.688e11,5.114e11], float)
O2vmr = np.array([2.09e5]*42 + [2.00e5,1.90e5,1.80e5,1.60e5,1.40e5,1.20e5,9.40e4,
                  7.25e4], float) / 1e6   # mole fraction

WMIN, WMAX, WSTEP = 12822.0, 13364.4, 0.01

# ----------------------------------------------------------------------
# Build one RADIS slab per gap between MODTRAN levels, then STACK them.
# ----------------------------------------------------------------------
slabs = []          # RADIS Spectrum objects (for SerialSlabs demo)
layer_tau = []      # optical thickness of each layer, on the benchmark grid
wb = np.round(np.arange(0, 54241) * WSTEP + WMIN, 2)   # benchmark nu grid

print(f"Building {len(zkm)-1} atmospheric slabs (US1976, O2 A-band)...")
for i in range(len(zkm) - 1):
    dz_cm = (zkm[i + 1] - zkm[i]) * 1e5
    T_l = 0.5 * (Tk[i] + Tk[i + 1])
    D_l = 0.5 * (Dcm3[i] + Dcm3[i + 1])           # total air density, cm-3
    x_l = 0.5 * (O2vmr[i] + O2vmr[i + 1])         # O2 mole fraction
    # pressure self-consistent with this density & temperature -> RADIS O2
    # column becomes exactly x_l * D_l * dz_cm  (matches aspect's k*n*dz)
    P_bar = D_l * 1e6 * kB * T_l / 1e5
    s = calc_spectrum(
        WMIN, WMAX, molecule="O2", isotope="1,2,3",
        pressure=P_bar, Tgas=T_l, path_length=dz_cm, mole_fraction=x_l,
        wstep=WSTEP, databank="hitran",
        warnings={"AccuracyWarning": "ignore", "GaussianBroadeningWarning": "ignore"},
        verbose=False,
    )
    s.name = f"{zkm[i]:.0f}-{zkm[i+1]:.0f}km"
    slabs.append(s)
    w, T = s.get("transmittance_noslit", wunit="cm-1")
    tau = -np.log(np.clip(np.asarray(T), 1e-300, None))
    layer_tau.append(np.interp(wb, np.asarray(w), tau))
    if i % 10 == 0:
        print(f"  slab {i:2d}  z={zkm[i]:6.1f}-{zkm[i+1]:5.1f} km  "
              f"T={T_l:5.1f}K P={P_bar:9.3e}bar  tau_max={tau.max():.3e}")

layer_tau = np.array(layer_tau)                   # shape (nlayers, nnu)

# ----------------------------------------------------------------------
# Demonstrate the STACK explicitly: SerialSlabs over the whole column.
# Its optical thickness must equal the simple sum of layer tau.
# ----------------------------------------------------------------------
print("\nStacking full column with RADIS SerialSlabs(*slabs)...")
s_total = SerialSlabs(*slabs)
w_st, T_st = s_total.get("transmittance_noslit", wunit="cm-1")
tau_serial = np.interp(wb, np.asarray(w_st),
                       -np.log(np.clip(np.asarray(T_st), 1e-300, None)))
tau_sum = layer_tau.sum(axis=0)
print(f"  max|SerialSlabs - sum(layers)| = {np.max(np.abs(tau_serial - tau_sum)):.2e}"
      "   (should be ~0  -> stacking == adding optical depth)")

# ----------------------------------------------------------------------
# Partial columns tau(TOA -> z) by summing slabs above z.
# z=0 : all layers ; z=1km : level 1 ; z=8km : level 8 ;
# z=2.5km : layers above 3km + upper half of the 2-3 km layer.
# ----------------------------------------------------------------------
def col_above(z):
    if abs(z - 2.5) < 1e-6:
        return layer_tau[3:].sum(axis=0) + 0.5 * layer_tau[2]
    lvl = int(round(z))                            # 0,1,8 are exact grid levels
    return layer_tau[lvl:].sum(axis=0)

z_list = [0.0, 1.0, 2.5, 8.0]
radis_cols = {z: col_above(z) for z in z_list}

# ----------------------------------------------------------------------
# Load aspect benchmark: cols index, nu, tau(z=0), tau(z=1), tau(z=2.5), tau(z=8)
# ----------------------------------------------------------------------
B = np.loadtxt(BENCH, comments="#")
nu_b = B[:, 1]
bench_cols = {0.0: B[:, 2], 1.0: B[:, 3], 2.5: B[:, 4], 8.0: B[:, 5]}

print("\n  z(km)   tau_max(aspect)  tau_max(RADIS)   rel-RMS%(tau>0.01*max)")
rel = {}
for z in z_list:
    tb, tr = bench_cols[z], radis_cols[z]
    m = tb > 0.01 * tb.max()
    r = np.sqrt(np.mean(((tr[m] - tb[m]) / tb[m]) ** 2)) * 100
    rel[z] = r
    print(f"  {z:5.1f}   {tb.max():13.4f}   {tr.max():12.4f}   {r:12.2f}")

# ================================================================ PLOTS
colors = {0.0: "tab:blue", 1.0: "tab:green", 2.5: "tab:orange", 8.0: "tab:red"}
fig, ax = plt.subplots(figsize=(14, 7))
for z in z_list:
    ax.plot(nu_b, bench_cols[z], lw=1.0, color=colors[z],
            label=f"aspect C-code  TOA$\\to${z:g} km")
    ax.plot(wb, radis_cols[z], lw=0.7, ls="--", color="black")
ax.plot([], [], "k--", label="RADIS stack (SerialSlabs)")
ax.set(xlabel="wavenumber (cm$^{-1}$)", ylabel=r"optical thickness $\tau(\nu,z)$",
       title="O$_2$ A-band in US1976 atmosphere: RADIS slab-stack vs paper's `aspect` C-code\n"
             "(partial column from Top-of-Atmosphere down to z)")
ax.set_xlim(13000, 13200)
ax.legend(ncol=2, fontsize=9)
fig.tight_layout()
fig.savefig(f"{OUT}/overplot_aspect_o2a_radis_stack.png", dpi=140)
plt.close(fig)

# zoom: band head + residual for z=0 (full column)
fig, ax = plt.subplots(2, 1, figsize=(13, 8), sharex=True,
                       gridspec_kw={"height_ratios": [3, 1]})
ax[0].plot(nu_b, bench_cols[0.0], lw=1.0, color="black", label="aspect C-code (full column)")
ax[0].plot(wb, radis_cols[0.0], lw=0.7, ls="--", color="tab:red", label="RADIS stack")
ax[0].set(ylabel=r"$\tau(\nu, z{=}0)$",
          title=f"O$_2$ A-band full-column optical thickness: RADIS stack vs aspect "
                f"[rel-RMS = {rel[0.0]:.2f}%]")
ax[0].legend(); ax[0].set_xlim(13050, 13170)
ti = np.interp(nu_b, wb, radis_cols[0.0])
ax[1].plot(nu_b, ti - bench_cols[0.0], lw=0.5, color="tab:blue")
ax[1].axhline(0, color="k", lw=0.5)
ax[1].set(xlabel="wavenumber (cm$^{-1}$)", ylabel=r"$\Delta\tau$")
fig.tight_layout()
fig.savefig(f"{OUT}/overplot_aspect_o2a_fullcolumn_zoom.png", dpi=140)
plt.close(fig)

# height variation of the column (integrated band tau vs z) -- the aspect feature
fig, ax = plt.subplots(figsize=(7, 6))
zfine = np.array(z_list)
_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))
band_aspect = [_trapz(bench_cols[z], nu_b) for z in z_list]
band_radis = [_trapz(radis_cols[z], wb) for z in z_list]
ax.plot(band_aspect, zfine, "ko-", label="aspect C-code")
ax.plot(band_radis, zfine, "r^--", label="RADIS stack")
ax.set(xlabel=r"band-integrated $\int\tau\,d\nu$ (cm$^{-1}$)", ylabel="z (km)",
       title="O$_2$ A-band absorption vs height\n(partial column TOA$\\to$z)")
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(f"{OUT}/aspect_o2a_height_variation.png", dpi=140)
plt.close(fig)

np.savetxt(f"{OUT}/aspect_o2a_radis_stack.txt",
           np.column_stack([wb] + [radis_cols[z] for z in z_list]),
           header="nu  tau(z=0)  tau(z=1)  tau(z=2.5)  tau(z=8)  [RADIS SerialSlabs stack]")
print("\nSaved aspect/stack overplots to ./figures/")
