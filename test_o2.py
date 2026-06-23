from radis import calc_spectrum
s = calc_spectrum(
    13006, 13166,           # cm-1
    molecule='O2',
    isotope='1,2,3',
    pressure=0.724,         # bar  (0.7145 atm)
    Tgas=296,               # K
    path_length=1633.6,     # cm
    mole_fraction=1,
    wstep=0.02,
    databank='hitran',
    verbose=False,
)
import numpy as np
w, T = s.get('transmittance_noslit', wunit='cm-1')
print('points', len(w), 'Tmin', round(float(np.min(T)),4), 'Tmax', round(float(np.max(T)),4))
print('lines used:', s.conditions.get('lines_calculated', s.conditions.get('lines_in_spectral_range','?')))
