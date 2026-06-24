"""Build a LAYMAN-FRIENDLY PDF report of the atmosphere-model extension.

Plain-language explanation of:
  (1) what was asked (the 6 MODTRAN models, an exact present-day model, and an
      India-specific model),
  (2) what was built, and
  (3) the comparison results over Mumbai (generic climatology vs present-day).

Run AFTER generating the figures:
    python plot_fig6_profiles.py
    python india_case.py
    python make_atmosphere_report.py     ->  Atmosphere_Models_Report.pdf
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg

FIGS = "figures"
OUT = "Atmosphere_Models_Report.pdf"


def text_page(pdf, title, body, title_size=16):
    fig = plt.figure(figsize=(8.27, 11.69))  # A4 portrait
    fig.text(0.5, 0.96, title, ha="center", va="top",
             fontsize=title_size, weight="bold")
    fig.text(0.07, 0.89, body, ha="left", va="top", fontsize=10.2,
             family="sans-serif", linespacing=1.5)
    plt.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


def figure_page(pdf, fname, heading, caption):
    path = os.path.join(FIGS, fname)
    if not os.path.exists(path):
        return
    fig = plt.figure(figsize=(11.69, 8.27))  # A4 landscape
    fig.text(0.5, 0.97, heading, ha="center", fontsize=14, weight="bold")
    ax = fig.add_axes([0.03, 0.12, 0.94, 0.80])
    ax.imshow(mpimg.imread(path))
    ax.axis("off")
    fig.text(0.5, 0.08, caption, ha="center", va="top", fontsize=10.5,
             style="italic", wrap=True)
    pdf.savefig(fig)
    plt.close(fig)


def main():
    with PdfPages(OUT) as pdf:
        # ---- title ----
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.5, 0.66, "Updating the Atmosphere Models", ha="center",
                 fontsize=23, weight="bold")
        fig.text(0.5, 0.60, "From six generic 1970s atmospheres to a real,\n"
                 "present-day, India-specific atmosphere", ha="center",
                 fontsize=13)
        fig.text(0.5, 0.50, "Line-by-line O$_2$ A-band absorption with RADIS\n"
                 "Validation of Korkin et al. (2025), JQSRT 337, 109345",
                 ha="center", fontsize=11, style="italic")
        fig.text(0.5, 0.06, "Plain-language summary", ha="center", fontsize=10,
                 color="gray")
        plt.axis("off")
        pdf.savefig(fig)
        plt.close(fig)

        # ---- what I was asked ----
        text_page(pdf, "1.  What I was asked to do",
            "The earlier work checked our absorption code (RADIS) against the\n"
            "Korkin et al. (2025) reference code, using ONE atmosphere: the\n"
            "\"US Standard 1976\" model. Three follow-up questions were raised:\n\n"
            "POINT 1 -  The reference code is built on the MODTRAN database, which\n"
            "  defines SIX standard atmospheres (Tropical, Mid-Latitude Summer,\n"
            "  Mid-Latitude Winter, Sub-Arctic Summer, Sub-Arctic Winter, and\n"
            "  US Standard 1976).\n"
            "  -> Do we have that data, and can we reproduce Figure 6 of the paper?\n\n"
            "POINT 2 -  These six models are generic and decades old. The real\n"
            "  atmosphere on any given day differs from them. We should add an\n"
            "  EXACT, up-to-date atmosphere - for example from NASA's Planetary\n"
            "  Spectrum Generator (PSG) - and include those variations in the code.\n\n"
            "POINT 3 -  None of the six models is specific to India. Can we use a\n"
            "  model suitable for the Indian subcontinent, ideally a recent one?")

        # ---- what I did ----
        text_page(pdf, "2.  What I did (overview)",
            "POINT 1  -  DONE.\n"
            "  All six MODTRAN atmospheres were extracted from the reference code\n"
            "  (pressure, temperature, air density, and the amounts of 8 gases at\n"
            "  50 heights from ground to 120 km). Paper Figure 6 was reproduced\n"
            "  directly from this data, and the absorption code now runs for ALL\n"
            "  six models - not just US-1976.\n\n"
            "POINT 2  -  DONE.\n"
            "  The code can now pull a REAL atmosphere for any place and date from\n"
            "  two independent, authoritative sources:\n"
            "    - NASA PSG (GEOS-5 weather data): pressure, temperature and the\n"
            "      actual amount of water vapour, CO2, ozone, methane, oxygen, etc.\n"
            "    - NRLMSIS 2.1 (NASA/US Navy, 2021): the latest empirical model of\n"
            "      temperature and density - an independent cross-check.\n\n"
            "POINT 3  -  DONE.\n"
            "  These real atmospheres work for any Indian location. The worked\n"
            "  example uses Mumbai / IIT Bombay and compares it against the closest\n"
            "  generic model (MODTRAN Tropical).")

        # ---- background ----
        text_page(pdf, "3.  Background, in plain terms",
            "WHAT IS AN 'ATMOSPHERE MODEL'?\n"
            "  To compute how much sunlight a gas absorbs, the code needs to know,\n"
            "  at every height, how cold/thin the air is and how much of each gas\n"
            "  is present. A table of (height -> temperature, pressure, density,\n"
            "  gas amounts) is an 'atmosphere model'.\n\n"
            "THE SIX MODTRAN MODELS\n"
            "  These are textbook averages built in the 1970s-80s for typical\n"
            "  conditions (a tropical year, an Arctic winter, and so on). They are\n"
            "  convenient but generic - they are NOT today's weather, and none is\n"
            "  tuned for India.\n\n"
            "WHY IT MATTERS\n"
            "  Real air over Mumbai during the monsoon is hotter and far more humid\n"
            "  than a 1970s average. Temperature and density set how strongly\n"
            "  oxygen absorbs in its 'A-band' near 760 nm, so using the wrong\n"
            "  atmosphere gives a small but real error in the predicted absorption.")

        figure_page(pdf, "fig6b_PTD_profiles.png",
            "Paper Figure 6 reproduced: the six MODTRAN atmospheres",
            "Pressure, temperature and air density versus height for all six standard "
            "models. As the paper notes, temperature (middle) varies a lot between "
            "models; pressure and density (sides) barely differ. This is the data "
            "the reference code is built on.")

        # ---- exact atmosphere ----
        text_page(pdf, "4.  Adding a real, present-day atmosphere",
            "Instead of picking a generic table, the code can now download the\n"
            "ACTUAL atmosphere for a chosen place, day and time:\n\n"
            "  NASA PSG (GEOS-5):  gives the real pressure, temperature and the\n"
            "    measured amounts of water vapour, CO2, ozone, methane and oxygen,\n"
            "    layer by layer. For Mumbai on 15 June 2024 it reported a surface\n"
            "    temperature of 303.5 K and very high humidity (~2.9% water vapour),\n"
            "    exactly as expected at monsoon onset.\n\n"
            "  NRLMSIS 2.1 (2021):  the latest empirical model of temperature and\n"
            "    air density, used here as an independent second opinion.\n\n"
            "Both are fed into the SAME absorption calculation as the generic\n"
            "models, so results are directly comparable.")

        figure_page(pdf, "india_profiles_Mumbai_IIT_Bombay.png",
            "Mumbai: generic model vs the real atmosphere",
            "Temperature (left) and oxygen amount (right) versus height over Mumbai. "
            "The two present-day models (blue = NASA PSG, green = NRLMSIS) agree "
            "closely with each other and differ from the generic 1970s 'Tropical' "
            "model (grey), most visibly near the 17 km tropopause and in the "
            "stratosphere.")

        figure_page(pdf, "india_o2a_optical_depth_Mumbai_IIT_Bombay.png",
            "The effect on oxygen A-band absorption over Mumbai",
            "Computed oxygen A-band absorption (optical thickness vs wavelength) "
            "for the three atmospheres. The curves nearly overlap, but the real "
            "present-day atmosphere absorbs slightly LESS than the generic model "
            "predicts - quantified on the next page.")

        # ---- results ----
        text_page(pdf, "5.  Result of the comparison (Mumbai, 15 Jun 2024)",
            "Total oxygen along the vertical column, and the total oxygen A-band\n"
            "absorption, for each atmosphere:\n\n"
            "  Atmosphere                 O2 column     Total       vs generic\n"
            "                             (per cm^2)    absorption  Tropical\n"
            "  ------------------------------------------------------------------\n"
            "  MODTRAN Tropical (1970s)   4.523 x10^24   1023          -\n"
            "  NASA PSG  (exact, that day) 4.408 x10^24   996         -2.6 %\n"
            "  NRLMSIS 2.1 (latest)       4.471 x10^24   1011         -1.2 %\n\n"
            "WHAT THIS MEANS\n"
            "  - The generic 'Tropical' model OVER-predicts the real oxygen A-band\n"
            "    absorption over Mumbai by about 1-3 % on this day.\n"
            "  - The two independent present-day models agree with each other to\n"
            "    about 1.5 %, which gives confidence the difference is real and not\n"
            "    a quirk of one data source.\n"
            "  - The same machinery runs for all six MODTRAN models too: their\n"
            "    full-column absorption agrees within ~1 % of each other, since\n"
            "    oxygen is well-mixed and changes little between climates.")

        figure_page(pdf, "all6_O2_o2a_bandintegral.png",
            "Robustness: the code runs for every standard model",
            "Total oxygen A-band absorption computed for all six MODTRAN atmospheres "
            "through the single, general code path. The values are close because "
            "oxygen is well-mixed; the point is that one code now handles every "
            "case - the six standard models AND any real present-day atmosphere.")

        # ---- summary ----
        text_page(pdf, "6.  Summary",
            "STARTING POINT\n"
            "  Absorption code validated, but using only one generic 1970s\n"
            "  atmosphere (US Standard 1976).\n\n"
            "DELIVERED TODAY\n"
            "  1. All six MODTRAN standard atmospheres are now in the code, and\n"
            "     paper Figure 6 is reproduced from that data.\n"
            "  2. The code can fetch a real, present-day atmosphere for any place\n"
            "     and date from NASA PSG (GEOS-5) and NRLMSIS 2.1.\n"
            "  3. A worked India example (Mumbai / IIT Bombay) shows the real\n"
            "     atmosphere absorbs ~1-3 % less oxygen A-band than the generic\n"
            "     model predicts, with two independent models agreeing.\n\n"
            "WHY IT IS USEFUL\n"
            "  The absorption calculation is no longer tied to decades-old averages.\n"
            "  It can use the actual atmosphere over an Indian site on a chosen day,\n"
            "  making the validation realistic and locally relevant - and the design\n"
            "  is general enough to add other gases, bands and data sources later.")

    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
