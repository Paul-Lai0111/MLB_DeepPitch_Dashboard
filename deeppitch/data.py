"""Cached access to the precomputed tables in data/app."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from deeppitch import physics as ph

APP = Path(__file__).resolve().parent.parent / "data" / "app"


@st.cache_data(show_spinner=False)
def table(name: str) -> pd.DataFrame:
    df = pd.read_parquet(APP / f"{name}.parquet")
    for c in ("pitcher", "game_year"):
        if c in df.columns:
            df[c] = df[c].astype("int32")
    if "pitch_type" in df.columns:
        df["pitch_type"] = df["pitch_type"].astype(str)
    return df


@st.cache_data(show_spinner=False)
def meta() -> dict:
    return json.loads((APP / "meta.json").read_text())


@st.cache_data(show_spinner=False)
def model_report() -> dict:
    return json.loads((APP / "model_report.json").read_text())


def seasons() -> list[int]:
    return meta()["seasons"]


@st.cache_data(show_spinner=False)
def pitcher_index() -> pd.DataFrame:
    """One row per pitcher (latest season first) for search boxes."""
    p = table("pitchers").sort_values(["game_year", "n"], ascending=[False, False])
    return p.drop_duplicates("pitcher")[["pitcher", "name", "team", "hand", "game_year", "n"]]


@st.cache_data(show_spinner=False)
def pitcher_labels() -> dict[int, str]:
    """{pitcher id: 'Name · TEAM · RHP'} ordered by most recent season, then workload."""
    return {int(r["pitcher"]): f"{r['name']} · {r['team']} · {r['hand']}HP" for r in pitcher_index().to_dict("records")}


def find_pitcher(name_like: str) -> int | None:
    idx = pitcher_index()
    hit = idx[idx["name"].str.contains(name_like, case=False, regex=False)]
    return int(hit.iloc[0]["pitcher"]) if len(hit) else None


def arsenal(pitcher: int, year: int) -> pd.DataFrame:
    a = table("arsenal")
    return a[(a["pitcher"] == pitcher) & (a["game_year"] == year)].sort_values("usage", ascending=False)


def pitcher_row(pitcher: int, year: int) -> pd.Series | None:
    p = table("pitchers")
    r = p[(p["pitcher"] == pitcher) & (p["game_year"] == year)]
    return r.iloc[0] if len(r) else None


def pitcher_years(pitcher: int) -> list[int]:
    p = table("pitchers")
    return sorted(p.loc[p["pitcher"] == pitcher, "game_year"].astype(int).unique(), reverse=True)


def trajectory_from_arsenal(row: pd.Series, n: int = 70) -> pd.DataFrame:
    r = {k[2:]: row[k] for k in row.index if k.startswith("t_")}
    return ph.trajectory(r, n=n)


def flight_payload(rows: pd.DataFrame, label_fn, n: int = 70) -> list[dict]:
    """Arsenal rows -> list of {label,color,pts,ghost} for the flight canvas."""
    from deeppitch.theme import pitch_color
    out = []
    for _, r in rows.iterrows():
        if pd.isna(r.get("t_vy0")):
            continue
        tr = trajectory_from_arsenal(r, n)
        out.append({
            "label": label_fn(r), "color": pitch_color(r["pitch_type"]),
            "pts": np.round(tr[["t", "x", "y", "z"]].to_numpy(), 4).tolist(),
            "ghost": np.round(tr[["x_nospin", "z_nospin"]].to_numpy(), 4).tolist(),
        })
    return out
