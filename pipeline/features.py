"""Stage 2: raw Statcast -> cleaned pitch-level feature table.

python -m pipeline.features            # all seasons found in data/raw
Writes data/interim/pitches.parquet (git-ignored, ~2M rows).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from deeppitch import physics as ph

RAW = Path("data/raw")
INTERIM = Path("data/interim")

KEEP = [
    "game_pk", "game_date", "game_year", "game_type", "at_bat_number", "pitch_number",
    "pitcher", "player_name", "batter", "p_throws", "stand", "home_team", "away_team", "inning_topbot",
    "balls", "strikes", "outs_when_up", "inning",
    "pitch_type", "release_speed", "effective_speed", "release_spin_rate", "spin_axis",
    "release_extension", "release_pos_x", "release_pos_z", "arm_angle",
    "pfx_x", "pfx_z", "plate_x", "plate_z", "sz_top", "sz_bot", "zone",
    "vx0", "vy0", "vz0", "ax", "ay", "az",
    "description", "events", "type", "bb_type", "launch_speed", "launch_angle",
    "estimated_woba_using_speedangle", "woba_value", "woba_denom", "delta_run_exp",
    "bat_speed", "swing_length",
]
DROP_TYPES = {"PO", "IN", "AB", "UN", "EP", "FA", "CS", "SC"}
# FA (generic "fastball") is usually position players pitching; CS/SC are tiny samples.

SWINGS = {"swinging_strike", "swinging_strike_blocked", "foul", "foul_tip", "hit_into_play",
          "foul_bunt", "missed_bunt", "bunt_foul_tip"}
WHIFFS = {"swinging_strike", "swinging_strike_blocked", "missed_bunt"}
CALLED = {"called_strike"}


def load_raw() -> pd.DataFrame:
    frames = []
    for p in sorted(RAW.glob("statcast_*_raw.parquet")):
        cols = [c for c in KEEP if c in __import__("pyarrow.parquet", fromlist=["x"]).read_schema(p).names]
        frames.append(pd.read_parquet(p, columns=cols))
        print(f"loaded {p.name}: {len(frames[-1]):,}")
    df = pd.concat(frames, ignore_index=True)
    for c in df.columns:
        if str(df[c].dtype) in ("Int64", "Float64", "Int32", "Int16", "Int8"):
            df[c] = df[c].astype("float64")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    n0 = len(df)
    df = df[~df["game_type"].isin(["S", "E", "A"])]
    df = df[df["pitch_type"].notna() & ~df["pitch_type"].isin(DROP_TYPES)]
    need = ["release_speed", "pfx_x", "pfx_z", "plate_x", "plate_z", "vx0", "vy0", "vz0",
            "ax", "ay", "az", "release_extension", "release_spin_rate", "spin_axis"]
    df = df.dropna(subset=need)
    df = df[(df["release_extension"].between(3.5, 8.5)) & (df["release_speed"] > 50)]
    df = df.drop_duplicates(["game_pk", "at_bat_number", "pitch_number"])
    df["game_date"] = pd.to_datetime(df["game_date"])
    df["game_year"] = df["game_year"].astype(int)
    print(f"clean: {n0:,} -> {len(df):,}")
    return df.reset_index(drop=True)


def add_context(df: pd.DataFrame) -> pd.DataFrame:
    d = df
    desc = d["description"].fillna("")
    d["is_swing"] = desc.isin(SWINGS)
    d["is_whiff"] = desc.isin(WHIFFS)
    d["is_csw"] = desc.isin(WHIFFS | CALLED)
    d["in_zone"] = d["zone"].between(1, 9)
    d["is_chase"] = d["is_swing"] & ~d["in_zone"]
    d["is_bip"] = desc.eq("hit_into_play")
    d["team"] = np.where(d["inning_topbot"].eq("Top"), d["home_team"], d["away_team"])
    d["platoon"] = np.where(d["p_throws"] == d["stand"], "same", "opposite")
    d["count"] = d["balls"].astype(int).astype(str) + "-" + d["strikes"].astype(int).astype(str)
    d["release_side"] = d["release_pos_x"] * ph.arm_side_sign(d["p_throws"]) * -1  # + = arm side
    # Normalised height in the zone (0 = bottom, 1 = top) — removes batter-height effects.
    d["zone_height"] = (d["plate_z"] - d["sz_bot"]) / (d["sz_top"] - d["sz_bot"])
    return d


def location_adjusted_vaa(d: pd.DataFrame) -> pd.Series:
    """VAA relative to what's typical *for that height in the zone*.

    VAA is mostly decided by where the pitch is thrown (high pitches arrive
    flatter). We fit VAA ~ plate_z per season x pitch type and keep the
    residual, so a positive value means 'flatter than expected for location'.
    """
    out = pd.Series(np.nan, index=d.index)
    for _, g in d.groupby(["game_year", "pitch_type"]):
        if len(g) < 200:
            continue
        b = np.polyfit(g["plate_z"], g["vaa"], 1)
        out.loc[g.index] = g["vaa"] - np.polyval(b, g["plate_z"])
    return out


def fastball_deltas(d: pd.DataFrame) -> pd.DataFrame:
    """Difference of each pitch from the pitcher's primary fastball that season."""
    fb = d[d["pitch_type"].isin(ph.FASTBALLS)]
    usage = fb.groupby(["pitcher", "game_year", "pitch_type"]).size().rename("n").reset_index()
    primary = usage.sort_values("n").groupby(["pitcher", "game_year"]).tail(1)
    ref = (fb.merge(primary[["pitcher", "game_year", "pitch_type"]])
             .groupby(["pitcher", "game_year"])[["release_speed", "ivb", "hb"]].mean()
             .add_prefix("fb_").reset_index())
    d = d.merge(ref, on=["pitcher", "game_year"], how="left")
    d["velo_diff"] = d["release_speed"] - d["fb_release_speed"]
    d["ivb_diff"] = d["ivb"] - d["fb_ivb"]
    d["hb_diff"] = d["hb"] - d["fb_hb"]
    return d.drop(columns=["fb_release_speed", "fb_ivb", "fb_hb"])


def main() -> None:
    INTERIM.mkdir(parents=True, exist_ok=True)
    df = clean(load_raw())
    df, ref = ph.add_physics(df)
    df = add_context(df)
    df["vaa_aa"] = location_adjusted_vaa(df)
    df = fastball_deltas(df)
    df.to_parquet(INTERIM / "pitches.parquet", index=False)
    (INTERIM / "calibration.json").write_text(json.dumps({"spin_eff_reference": ref}))
    print(f"wrote {len(df):,} pitches, {df.columns.size} columns; seasons {sorted(df.game_year.unique())}")


if __name__ == "__main__":
    main()
