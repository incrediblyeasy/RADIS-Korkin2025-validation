"""
General RADIS slab-stack driver -- the `aspect` reproduction, but for ANY
atmosphere and ANY gas/band.

It takes an `Atmosphere` object (one of the 6 MODTRAN models from atmospheres.py,
or a present-day PSG/NRLMSIS profile from psg_atmosphere.py), splits it into one
homogeneous RADIS slab per layer, stacks the slabs (SerialSlabs == adding optical
depth), and returns the cumulative optical thickness tau(nu, z) from the
top-of-atmosphere down to each requested height z.

This is the same physics as the paper's aspect/tauabs25.cpp (sigma(T,P)*n*dz,
integrated over height), so the same code now runs every case the professor asked
for: all 6 standard atmospheres, the exact PSG atmosphere, and the India profile.

    from atmospheres import get_modtran
    from aspect_driver import run_aspect, BANDS
    res = run_aspect(get_modtran("tropical"), molecule="O2", band="o2a")
    res.wavenumber, res.tau[0.0], res.tau_max   # optical depth, full column

Bands (paper Sec. 5-6):
    o2a  : O2 A-band   12950-13200 cm-1   (~0.76 um)
    ch4  : CH4 2.3 um   4100-4500 cm-1
"""
import numpy as np
from radis import calc_spectrum, SerialSlabs

kB = 1.380649e-23  # J/K
_TRAPZ = getattr(np, "trapezoid", None) or np.trapz   # numpy>=2.0 renamed trapz

# isotopologue strings RADIS expects, by molecule
ISOTOPE = {"O2": "1,2,3", "CH4": "1,2,3,4", "H2O": "1,2,3,4,5,6,7",
           "CO2": "1,2,3,4", "CO": "1,2,3,4,5,6", "N2O": "1,2,3,4,5",
           "O3": "1,2,3,4,5", "NO2": "1"}

# named bands: (wmin, wmax, wstep) in cm-1
BANDS = {
    "o2a": (12950.0, 13200.0, 0.01),     # O2 A-band, ~760 nm
    "o2a_full": (12822.0, 13364.4, 0.01),  # full paper window
    "ch4": (4100.0, 4500.0, 0.01),       # CH4 2.3 um
}


class AspectResult:
    def __init__(self, wavenumber, tau_by_z, layer_tau, atm, molecule, band):
        self.wavenumber = wavenumber
        self.tau = tau_by_z                 # {z_km: tau(nu)}
        self.layer_tau = layer_tau          # (nlayer, nnu)
        self.atm = atm
        self.molecule = molecule
        self.band = band

    @property
    def z_targets(self):
        return sorted(self.tau)

    @property
    def tau_max(self):
        return {z: float(np.max(t)) for z, t in self.tau.items()}

    def band_integral(self):
        return {z: float(_TRAPZ(t, self.wavenumber)) for z, t in self.tau.items()}


def run_aspect(atm, molecule="O2", band="o2a", z_targets=None,
               max_top_km=None, verbose=True):
    """Build & stack per-layer RADIS slabs for `atm`; return cumulative tau(nu,z).

    atm        : Atmosphere object (must carry a profile for `molecule`)
    molecule   : 'O2', 'CH4', ...
    band       : key in BANDS, or a (wmin, wmax, wstep) tuple
    z_targets  : list of heights (km) for partial columns TOA->z; default
                 a few representative levels within the atmosphere.
    max_top_km : ignore layers above this altitude (speed; default = all)
    """
    if not atm.has(molecule):
        raise ValueError(f"{atm.name} has no {molecule} profile "
                         f"(gases: {atm.gases})")
    wmin, wmax, wstep = BANDS[band] if isinstance(band, str) else band
    iso = ISOTOPE.get(molecule, "1")

    z = atm.zkm
    top = z[-1] if max_top_km is None else min(max_top_km, z[-1])
    use = np.where(z <= top + 1e-9)[0]
    z = z[use]
    T = atm.T_K[use]; D = atm.D_cm3[use]; x = atm.mole_fraction(molecule)[use]

    if z_targets is None:
        # representative set within this atmosphere's range
        cand = [0.0, 1.0, 2.5, 5.0, 8.0]
        z_targets = [c for c in cand if c <= z[-1]]

    nnu = int(round((wmax - wmin) / wstep)) + 1
    wb = np.round(wmin + np.arange(nnu) * wstep, 6)

    if verbose:
        print(f"[aspect] {atm.name}\n         {molecule} {band}  "
              f"{len(z)-1} slabs  {z[0]:.0f}-{z[-1]:.0f} km  grid {nnu} pts")

    layer_tau = []
    for i in range(len(z) - 1):
        dz_cm = (z[i + 1] - z[i]) * 1e5
        T_l = 0.5 * (T[i] + T[i + 1])
        D_l = 0.5 * (D[i] + D[i + 1])
        x_l = 0.5 * (x[i] + x[i + 1])
        if x_l <= 0 or dz_cm <= 0:
            layer_tau.append(np.zeros(nnu)); continue
        # pressure self-consistent with this layer's density & temperature, so the
        # RADIS column = x_l * D_l * dz_cm  (matches aspect's sigma * n * dz)
        P_bar = D_l * 1e6 * kB * T_l / 1e5
        s = calc_spectrum(
            wmin, wmax, molecule=molecule, isotope=iso,
            pressure=P_bar, Tgas=T_l, path_length=dz_cm, mole_fraction=x_l,
            wstep=wstep, databank="hitran",
            warnings={"AccuracyWarning": "ignore",
                      "GaussianBroadeningWarning": "ignore",
                      "NegativeEnergiesWarning": "ignore"},
            verbose=False,
        )
        w, Tr = s.get("transmittance_noslit", wunit="cm-1")
        tau = -np.log(np.clip(np.asarray(Tr), 1e-300, None))
        layer_tau.append(np.interp(wb, np.asarray(w), tau))
        if verbose and i % 10 == 0:
            print(f"         slab {i:2d}  z={z[i]:6.1f}-{z[i+1]:5.1f} km  "
                  f"T={T_l:5.1f}K  tau_max={tau.max():.3e}")

    layer_tau = np.array(layer_tau)

    # partial column TOA -> z: sum of all layer taus lying above z
    def col_above(zt):
        # layer i spans [z[i], z[i+1]]; include layers whose base >= zt,
        # plus the partial fraction of the layer straddling zt
        out = np.zeros(layer_tau.shape[1])
        for i in range(len(z) - 1):
            if z[i] >= zt - 1e-9:
                out += layer_tau[i]
            elif z[i + 1] > zt:                       # straddling layer
                frac = (z[i + 1] - zt) / (z[i + 1] - z[i])
                out += frac * layer_tau[i]
        return out

    tau_by_z = {zt: col_above(zt) for zt in z_targets}
    return AspectResult(wb, tau_by_z, layer_tau, atm, molecule, band)
