# -*- coding: utf-8 -*-
"""
BRO groundwater validation dashboard (2017-2018)
Run using:
    streamlit run BRO_groundwater_dashboard.py

Click a BRO well on the map to display its observed-versus-baseline
groundwater hydrograph. Choose the monitoring tube for multi-tube wells.
"""

from io import BytesIO
from pathlib import Path

import folium
import geopandas as gpd
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# ------------------------------------------------------------
# PATHS: adapt only if your files are stored elsewhere
# ------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"

# GeoPackage created by create_final_BRO_sensitivity_wells_GPKG.py.
GPKG_PATH = (
    DATA_DIR / "BRO_final_wells_sensitivity_2017_2018.gpkg"
)

OBS_FILE = (
    DATA_DIR / "09_BRO_observations_usable_long_QC.csv"
)

BASELINE_DIR = DATA_DIR / "BASELINE"

BOUNDARY_SHP = DATA_DIR / "Aa_catchment.gpkg"

PREGENERATED_PLOT_DIR = DATA_DIR / "plots"

START_DATE = pd.Timestamp("2017-01-01")
END_DATE = pd.Timestamp("2018-12-31")

st.set_page_config(
    page_title="BRO groundwater | 2017-2018",
    page_icon="💧",
    layout="wide",
)

st.title("BRO groundwater validation dashboard")
st.caption(
    "Aa of Weerijs catchment · 2017–2018 · "
    "QC-filtered BRO observations versus simplified-model baseline"
)


@st.cache_data(show_spinner=False)
def read_gpkg(path_str):
    path = Path(path_str)
    wells = gpd.read_file(path, layer="BRO_wells").to_crs("EPSG:4326")
    tubes = gpd.read_file(path, layer="BRO_tubes")
    wells["BRO_GMW_ID"] = wells["BRO_GMW_ID"].astype(str).str.strip()
    tubes["BRO_GMW_ID"] = tubes["BRO_GMW_ID"].astype(str).str.strip()
    tubes["GLD_ID"] = tubes["GLD_ID"].astype(str).str.strip()
    tubes["series_id"] = tubes["series_id"].astype(str).str.strip()
    tubes["tube_number"] = pd.to_numeric(
        tubes["tube_number"], errors="coerce"
    ).astype("Int64")
    tubes["physical_model_layer"] = pd.to_numeric(
        tubes["physical_model_layer"], errors="coerce"
    ).astype("Int64")
    return wells, tubes


@st.cache_data(show_spinner=False)
def read_observations(path_str):
    df = pd.read_csv(path_str)
    for col in ("BRO_GMW_ID", "GLD_ID"):
        df[col] = df[col].astype(str).str.strip()
    df["tube_number"] = pd.to_numeric(
        df["tube_number"], errors="coerce"
    ).astype("Int64")
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["groundwater_level_m_NAP"] = pd.to_numeric(
        df["groundwater_level_m_NAP"], errors="coerce"
    )
    df = df.dropna(
        subset=["date", "groundwater_level_m_NAP", "tube_number"]
    )
    return df.loc[df["date"].between(START_DATE, END_DATE)].copy()


@st.cache_data(show_spinner=False)
def read_baseline(path_str):
    df = pd.read_csv(path_str, index_col=0)
    df.index = pd.to_datetime(df.index, errors="coerce").normalize()
    df = df.loc[df.index.notna()].sort_index()
    return df.loc[(df.index >= START_DATE) & (df.index <= END_DATE)]


@st.cache_data(show_spinner=False)
def read_boundary(path_str):
    return gpd.read_file(path_str).to_crs("EPSG:4326")


def calculate_metrics(comparison):
    if comparison.empty:
        return {
            "N": 0, "Bias (m)": np.nan, "RMSE (m)": np.nan,
            "r": np.nan, "NSE": np.nan
        }

    obs = comparison["BRO observed"].to_numpy(dtype=float)
    sim = comparison["Baseline model"].to_numpy(dtype=float)
    d = sim - obs

    r = (
        float(np.corrcoef(obs, sim)[0, 1])
        if len(obs) >= 2 and np.std(obs) > 0 and np.std(sim) > 0
        else np.nan
    )
    denominator = np.sum((obs - np.mean(obs)) ** 2)

    return {
        "N": len(obs),
        "Bias (m)": float(np.mean(d)),
        "RMSE (m)": float(np.sqrt(np.mean(d ** 2))),
        "r": r,
        "NSE": (
            float(1.0 - np.sum(d ** 2) / denominator)
            if denominator > 0 else np.nan
        ),
    }


def safe_float_label(number, decimals=2):
    return f"{number:.{decimals}f}" if np.isfinite(number) else "N/A"


def groundwater_plot(obs, sim, well_id, tube_number, gld_id, layer):
    fig, ax = plt.subplots(figsize=(11, 4.8))
    # Drop NaN values so that sparse model dates still draw a line.
    model_clean = sim.dropna()
    obs_clean = obs.dropna()

    ax.plot(
        model_clean.index,
        model_clean.values,
        color="#1164a3", linewidth=2.0, marker="o",
        markersize=2.5, label="Baseline model", zorder=3,
    )
    ax.scatter(
        obs_clean.index, obs_clean.values,
        s=12, color="#1e1e1e", label="BRO observed", zorder=4,
    )
    ax.set_xlim(START_DATE, END_DATE)
    ax.set_xlabel("Date")
    ax.set_ylabel("Groundwater head (m NAP)")
    ax.set_title(
        f"{well_id} | tube {tube_number} | {gld_id} | model L{layer}",
        fontsize=11,
    )
    ax.grid(alpha=0.25)
    ax.legend(loc="best")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def safe_file_name(series_id):
    return "".join(
        c if (c.isalnum() or c in "_.-") else "_"
        for c in str(series_id)
    )


# ------------------------------------------------------------
# READ INPUTS
# ------------------------------------------------------------

missing = [
    str(path)
    for path in (GPKG_PATH, OBS_FILE, BASELINE_DIR)
    if not path.exists()
]
if missing:
    st.error(
        "Required files/folders were not found. Update the paths "
        "at the top of this script:\n\n" + "\n".join(missing)
    )
    st.stop()

try:
    wells, tubes = read_gpkg(str(GPKG_PATH))
    obs_data = read_observations(str(OBS_FILE))
except Exception as exc:
    st.error(f"Unable to read inputs: {exc}")
    st.stop()

if wells.empty or tubes.empty:
    st.error("GeoPackage contains no final BRO wells/tubes.")
    st.stop()

# Each point on the map is a unique GMW. One GMW can contain several tubes.
wells = wells.sort_values("BRO_GMW_ID").reset_index(drop=True)
available_well_ids = wells["BRO_GMW_ID"].tolist()

if "selected_well" not in st.session_state:
    st.session_state.selected_well = available_well_ids[0]

if st.session_state.selected_well not in available_well_ids:
    st.session_state.selected_well = available_well_ids[0]

st.sidebar.header("Display settings")
show_boundary = st.sidebar.checkbox("Show catchment boundary", value=True)
show_precomputed_png = st.sidebar.checkbox(
    "Show original saved PNG too", value=False
)

layer_values = sorted(
    int(x) for x in tubes["physical_model_layer"].dropna().unique()
)
selected_layers = st.sidebar.multiselect(
    "Map filter: model layers",
    options=layer_values,
    default=layer_values,
)
if not selected_layers:
    st.info("Select at least one model layer in the sidebar.")
    st.stop()

filtered_tubes = tubes.loc[
    tubes["physical_model_layer"].isin(selected_layers)
]
filtered_well_ids = set(filtered_tubes["BRO_GMW_ID"].unique())
map_wells = wells.loc[
    wells["BRO_GMW_ID"].isin(filtered_well_ids)
].copy()

if map_wells.empty:
    st.info("No monitoring wells match the current layer filter.")
    st.stop()

st.sidebar.caption("Click a marker on the map to select a BRO well.")

# Keep selection consistent if the layer filter hides the selected well.
if st.session_state.selected_well not in filtered_well_ids:
    st.session_state.selected_well = sorted(filtered_well_ids)[0]

left, right = st.columns([1.05, 1.25], gap="large")

with left:
    st.subheader("Monitoring wells")
    st.caption("Click a point; one point can contain several monitoring tubes.")

    center_lat = float(map_wells.geometry.y.median())
    center_lon = float(map_wells.geometry.x.median())
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11, tiles="OpenStreetMap",
        control_scale=True,
    )

    if show_boundary and BOUNDARY_SHP.exists():
        try:
            boundary = read_boundary(str(BOUNDARY_SHP))
            folium.GeoJson(
                boundary,
                style_function=lambda _: {
                    "color": "#137f81",
                    "weight": 2,
                    "fillOpacity": 0.04,
                },
                name="Catchment",
            ).add_to(m)
        except Exception as exc:
            st.warning(f"Catchment boundary could not be displayed: {exc}")

    for _, well in map_wells.iterrows():
        well_id = str(well["BRO_GMW_ID"])
        is_selected = well_id == st.session_state.selected_well
        marker_color = "#e76528" if is_selected else "#167b9f"

        folium.CircleMarker(
            location=[float(well.geometry.y), float(well.geometry.x)],
            radius=8 if is_selected else 5,
            color=marker_color,
            fill=True, fill_color=marker_color,
            fill_opacity=0.9,
            weight=2 if is_selected else 1,
            tooltip=well_id,
            popup=folium.Popup(
                f"<b>{well_id}</b><br>{int(well['n_tubes'])} tube(s)",
                max_width=260,
            ),
        ).add_to(m)

    map_result = st_folium(
        m,
        height=540,
        width=None,
        key="bro_map",
        returned_objects=["last_object_clicked_tooltip"],
    )

    clicked_id = (map_result or {}).get("last_object_clicked_tooltip")
    if clicked_id and clicked_id in filtered_well_ids:
        if clicked_id != st.session_state.selected_well:
            st.session_state.selected_well = clicked_id
            st.rerun()

    st.caption(
        f"{len(map_wells)} wells shown · "
        f"{len(filtered_tubes)} tube/GLD series in the selected layers"
    )

with right:
    chosen_well = st.session_state.selected_well
    if chosen_well not in filtered_well_ids:
        chosen_well = sorted(filtered_well_ids)[0]

    st.subheader(f"Groundwater hydrograph — {chosen_well}")

    matching_tubes = (
        filtered_tubes.loc[filtered_tubes["BRO_GMW_ID"] == chosen_well]
        .sort_values(["physical_model_layer", "tube_number", "GLD_ID"])
        .reset_index(drop=True)
    )
    tube_choices = matching_tubes["series_id"].tolist()

    selected_sid = st.selectbox(
        "Monitoring tube / GLD series",
        options=tube_choices,
        format_func=lambda sid: (
            f"Tube {int(matching_tubes.loc[matching_tubes['series_id'] == sid, 'tube_number'].iloc[0])}"
            f" · L{int(matching_tubes.loc[matching_tubes['series_id'] == sid, 'physical_model_layer'].iloc[0])}"
            f" · {sid.rsplit('_', 1)[-1]}"
        ),
        key=f"tube_select_{chosen_well}",
    )

    t = matching_tubes.loc[
        matching_tubes["series_id"] == selected_sid
    ].iloc[0]
    tube_no = int(t["tube_number"])
    layer_no = int(t["physical_model_layer"])
    gld_id = str(t["GLD_ID"])

    tube_obs = obs_data.loc[
        (obs_data["BRO_GMW_ID"] == chosen_well)
        & (obs_data["tube_number"] == tube_no)
        & (obs_data["GLD_ID"] == gld_id)
    ]
    observed = (
        tube_obs.groupby("date")["groundwater_level_m_NAP"]
        .mean().sort_index()
    )

    baseline_path = BASELINE_DIR / f"modelled_BRO_heads_L{layer_no}.csv"
    if baseline_path.exists():
        baseline_table = read_baseline(str(baseline_path))
        if selected_sid in baseline_table.columns:
            simulated = pd.to_numeric(
                baseline_table[selected_sid], errors="coerce"
            )
        else:
            simulated = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
            st.warning(
                f"{selected_sid} is not present in "
                f"{baseline_path.name}."
            )
    else:
        simulated = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
        st.warning(f"Missing baseline file: {baseline_path}")

    paired = pd.concat(
        [observed.rename("BRO observed"),
         simulated.rename("Baseline model")],
        axis=1, join="inner"
    ).dropna()
    metrics = calculate_metrics(paired)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("RMSE", safe_float_label(metrics["RMSE (m)"]) + " m")
    col2.metric("Bias (sim − obs)", safe_float_label(metrics["Bias (m)"]) + " m")
    col3.metric("Pearson r", safe_float_label(metrics["r"]))
    col4.metric("NSE", safe_float_label(metrics["NSE"]))

    filter_midpoint = pd.to_numeric(
        t.get("filter_midpoint_m_NAP", np.nan), errors="coerce"
    )
    st.caption(
        f"{metrics['N']} common dates · "
        f"physical model layer L{layer_no} · "
        f"filter midpoint {safe_float_label(filter_midpoint)} m NAP"
    )

    if observed.empty and simulated.empty:
        st.warning("No observations or baseline heads found for this tube.")
    else:
        fig = groundwater_plot(
            observed, simulated, chosen_well, tube_no, gld_id, layer_no
        )
        st.pyplot(fig, use_container_width=True)

        png_buffer = BytesIO()
        fig.savefig(png_buffer, format="png", dpi=220, bbox_inches="tight")
        plt.close(fig)

        raw_table = pd.concat(
            [observed.rename("BRO observed"),
             simulated.rename("Baseline model")],
            axis=1
        ).sort_index()
        raw_table.index.name = "date"

        b1, b2 = st.columns(2)
        with b1:
            st.download_button(
                "Download plot (PNG)",
                data=png_buffer.getvalue(),
                file_name=f"{safe_file_name(selected_sid)}_observed_baseline.png",
                mime="image/png",
                use_container_width=True,
            )
        with b2:
            st.download_button(
                "Download time series (CSV)",
                data=raw_table.to_csv().encode("utf-8-sig"),
                file_name=f"{safe_file_name(selected_sid)}_observed_baseline.csv",
                mime="text/csv",
                use_container_width=True,
            )

        if show_precomputed_png:
            path = (
                PREGENERATED_PLOT_DIR
                / f"{selected_sid}_L{layer_no}_observed_vs_baseline.png"
            )
            if path.exists():
                st.image(str(path), caption="Previously generated static figure")
            else:
                st.info("No saved PNG was found for this series.")

with st.expander("All final monitoring tubes and model performance"):
    visible_columns = [
        "BRO_GMW_ID", "tube_number", "GLD_ID", "physical_model_layer",
        "screen_top_m_NAP", "screen_bottom_m_NAP",
        "n_common_dates", "bias_m", "rmse_m", "pearson_r", "nse",
    ]
    available = [col for col in visible_columns if col in tubes.columns]
    st.dataframe(
        tubes[available].sort_values(
            ["BRO_GMW_ID", "tube_number"]
        ),
        use_container_width=True,
        hide_index=True,
    )
