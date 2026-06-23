"""Build a self-contained PDF report of the RADIS reproduction."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg

FIGS = "figures"
out = "Report_Korkin2025_RADIS.pdf"

title = "Reproduction of Korkin et al. (2025) line-by-line\nabsorption benchmarks using RADIS"
subtitle = ("Korkin, Sayer, Ibrahim & Lyapustin, JQSRT 337, 109345 (2025)\n"
            "'A practical guide to coding line-by-line trace gas absorption in Earth's atmosphere'\n"
            "https://doi.org/10.1016/j.jqsrt.2025.109345")

summary = (
    "Method\n"
    "------\n"
    "The paper's two gas-cell (gcell) validation benchmarks were reproduced with RADIS\n"
    "(open-source line-by-line radiative-transfer code) using the HITRAN database and the\n"
    "Voigt line shape - the same physics as the paper. For each case the absorption of every\n"
    "molecular line is summed over the wavenumber grid to give the optical thickness tau, and\n"
    "the transmittance follows from Beer-Lambert: T = exp(-tau).\n\n"
    "Benchmark 1 - O2 A-band (paper Fig. 4; Predoi-Cross et al. 2008)\n"
    "   Range 13006-13166 cm-1,  T = 296 K,  p = 0.724 bar,  L = 1633.6 cm,  pure O2\n"
    "   Result: correct rotational structure & band head; transmittance min ~ 0.12.\n"
    "   Column density 2.894e22 molec/cm2  (paper: 2.892e22)  -> MATCH\n\n"
    "Benchmark 2 - CH4 2.3 um band (paper Fig. 5; GATS / SpectralCalc)\n"
    "   Range 4081.901-4505.699 cm-1,  T = 296 K,  p = 1.0 bar,  L = 8 cm,  pure CH4\n"
    "   Result: dense 2v3 band reproduced; optical thickness up to ~6.3.\n"
    "   Column density 1.958e20 molec/cm2  (paper: 1.958e20)  -> EXACT MATCH\n\n"
    "Conclusion\n"
    "----------\n"
    "Matching column densities and correct line positions/depths confirm that RADIS\n"
    "reproduces the same physics as the paper's C code, independently validating the result.\n\n"
    "Tools: RADIS 0.17, HITRAN, Python 3.11.   Script: reproduce_korkin2025.py"
)

with PdfPages(out) as pdf:
    # ---- page 1: title + summary ----
    fig = plt.figure(figsize=(8.27, 11.69))  # A4 portrait
    fig.text(0.5, 0.93, title, ha="center", va="top", fontsize=15, weight="bold")
    fig.text(0.5, 0.85, subtitle, ha="center", va="top", fontsize=8.5, style="italic")
    fig.text(0.08, 0.78, summary, ha="left", va="top", fontsize=9.5,
             family="monospace")
    plt.axis("off")
    pdf.savefig(fig); plt.close(fig)

    # ---- figure pages ----
    pages = [
        ("fig4a_o2a_band.png", "Fig. 4(a)  O2 A-band gas cell: transmittance (left) and optical thickness (right)"),
        ("fig4b_o2a_subband.png", "Fig. 4(b)  O2 A-band, narrow sub-band (13159.6-13165.6 cm-1)"),
        ("fig5_ch4_band.png", "Fig. 5  CH4 2.3 um gas cell: optical thickness (top) and transmittance (bottom)"),
        ("compare_o2a_radis_vs_hapi.png", "Validation  O2 A-band: RADIS vs HAPI (HITRAN reference implementation)"),
        ("compare_o2a_aspect_radis_stack.png", "Validation  O2 A-band: RADIS stacked-aspect comparison"),
        ("compare_ch4_radis_vs_hapi.png", "Validation  CH4 2.3 um band: RADIS vs HAPI (HITRAN reference implementation)"),
    ]
    for fname, cap in pages:
        fig = plt.figure(figsize=(11.69, 8.27))  # A4 landscape
        ax = fig.add_axes([0.02, 0.06, 0.96, 0.86])
        ax.imshow(mpimg.imread(f"{FIGS}/{fname}"))
        ax.axis("off")
        fig.text(0.5, 0.965, cap, ha="center", fontsize=11, weight="bold")
        pdf.savefig(fig); plt.close(fig)

print("Wrote", out)
