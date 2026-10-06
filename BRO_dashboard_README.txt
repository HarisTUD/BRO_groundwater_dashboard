BRO groundwater interactive dashboard
=====================================

This is a local Streamlit app, with a clickable Folium map and a
BRO-observed versus BASELINE-simulated hydrograph for 2017-2018.

Files used
----------
- BRO_final_wells_sensitivity_2017_2018.gpkg (two layers)
- 09_BRO_observations_usable_long_QC.csv
- BASELINE/modelled_BRO_heads_L1.csv etc.

Change GPKG_PATH, OBS_FILE and BASELINE_DIR near the top of
BRO_groundwater_dashboard.py if your files are in other folders.

On Windows in Anaconda Prompt or the terminal of the appropriate
Python environment:

    python -m pip install -r BRO_dashboard_requirements.txt
    python -m streamlit run BRO_groundwater_dashboard.py

Then open the local address printed in the terminal (usually
http://localhost:8501).

Click any mapped well. For multiple tubes at a single location, select
the tube from the dropdown above the hydrograph.

Only final QC-filtered and baseline-matched wells from the GPKG are shown.
The displayed metrics are recalculated from paired observations and
baseline values. No model rerun is needed.

Note: Streamlit is a separate web app, not a Jupyter/Spyder figure.
Run it from a terminal rather than through Spyder's F5 button.
