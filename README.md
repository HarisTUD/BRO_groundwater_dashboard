# BRO groundwater dashboard (2017–2018)

Interactive monitoring-well map with QC-filtered BRO observations and baseline-model heads.

## Data files needed before deploying

The GeoPackage is already included. **Copy the following files from your own Windows folders** into the repository:

```text
BRO_GitHub_Ready/
  app.py
  requirements.txt
  data/
    BRO_final_wells_sensitivity_2017_2018.gpkg
    09_BRO_observations_usable_long_QC.csv          <-- ADD
    BASELINE/
      modelled_BRO_heads_L1.csv                     <-- ADD
      modelled_BRO_heads_L3.csv                     <-- ADD
      modelled_BRO_heads_L5.csv                     <-- ADD
      modelled_BRO_heads_L7.csv                     <-- ADD
    Aa_catchment.gpkg                               <-- OPTIONAL
    plots/                                          <-- OPTIONAL
```

Source locations on the research computer:

- `C:\D\Data\BRO_GW_DATA\BRO_catchment_Aa_new_rd\09_BRO_observations_usable_long_QC.csv`
- `E:\Model\RESULTS\sensitivity\_SENSITIVITY_ANALYSIS_BRO\BASELINE\modelled_BRO_heads_L*.csv`

The baseline head tables must contain a date index and a column for each `series_id`.

## Deploy to Community Cloud

1. Verify permission to publish groundwater locations, observations and model results.
2. Copy the five required CSV files into the folders above.
3. Create a GitHub repository; upload `app.py`, `requirements.txt`, and the entire `data/` folder.
4. Visit https://share.streamlit.io, create an app, select the repo and set **Main file path: `app.py`**.
5. Open the resulting URL to verify map clicks, tube selection and plots.

## Local test from Windows Command Prompt

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Optional background: `data/Aa_catchment.gpkg`; optional saved PNGs: `data/plots/`.
Neither is needed for the main observed-vs-baseline plots. The app uses OpenStreetMap
background tiles, which do not require an API key.

Note: GitHub repositories containing the data may be accessible to others, depending on the repo settings.
Do not upload restricted data to a public repository without authorization.
