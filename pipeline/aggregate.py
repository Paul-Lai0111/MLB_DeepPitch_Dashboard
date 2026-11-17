"""Stage 4: pitch-level table -> compact tables the Streamlit app ships with.

python -m pipeline.aggregate
Reads data/interim/*.parquet, writes data/app/*.parquet (committed to git,
small enough for Streamlit Community Cloud).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from deeppitch import physics as ph
from deeppitch.features import FEATURES

INTERIM = Path("data/interim")
APP = Path("data/app")
MIN_PITCHES_TYPE = 50      # an arsenal row must have this many pitches
QUAL_PCTL = 100            # minimum to be ranked in percentiles / leaderboards
SAMPLE_PER_COMBO = 60
KEY = ["pitcher", "game_year", "pitch_type"]


def f32(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.select_dtypes("float64").columns:
        df[c] = df[c].astype("float32")
    return df


def rate(num, den):
    return np.where(den > 0, num / np.maximum(den, 1), np.nan)


def display_name(s: pd.Series) -> pd.Series:
    parts = s.str.split(", ", n=1)
    return parts.str[1].fillna("") + " " + parts.str[0].fillna("")


def outcome_aggs(g) -> pd.DataFrame:
    out = g.agg(
        n=("pitch_type", "size"),
        swings=("is_swing", "sum"), whiffs=("is_whiff", "sum"), csw=("is_csw", "sum"),
        chases=("is_chase", "sum"), out_zone=("in_zone", lambda s: (~s).sum()), in_zone=("in_zone", "sum"),
        rv=("delta_run_exp", "sum"), xwoba_con=("estimated_woba_using_speedangle", "mean"),
        bat_speed=("bat_speed", "mean"), stuff_plus=("stuff_plus", "mean"),
    )
    out["whiff_pct"] = rate(out["whiffs"], out["swings"]) * 100
    out["csw_pct"] = rate(out["csw"], out["n"]) * 100
    out["chase_pct"] = rate(out["chases"], out["out_zone"]) * 100
    out["zone_pct"] = rate(out["in_zone"], out["n"]) * 100
    out["rv100"] = -100 * out["rv"] / out["n"]  # + = good for the pitcher
    return out.drop(columns=["csw", "chases", "out_zone", "in_zone", "rv"])


def circular_mean_deg(s: pd.Series) -> float:
    r = np.radians(s.dropna().to_numpy())
    return float(np.degrees(np.arctan2(np.sin(r).mean(), np.cos(r).mean())) % 360) if len(r) else np.nan


def build_arsenal(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby(KEY)
    phys = g.agg(
        velo=("release_speed", "mean"), velo_max=("release_speed", "max"), eff_velo=("effective_speed", "mean"),
        spin=("release_spin_rate", "mean"), spin_eff=("spin_eff", "mean"),
        ivb=("ivb", "mean"), hb=("hb", "mean"), vaa=("vaa", "mean"), vaa_aa=("vaa_aa", "mean"), haa=("haa", "mean"),
        ext=("release_extension", "mean"), rel_z=("release_pos_z", "mean"), rel_side=("release_side", "mean"),
        arm_angle=("arm_angle", "mean"), ssw_deg=("ssw_deg", "mean"), flight_time=("flight_time", "mean"),
        velo_diff=("velo_diff", "mean"), ivb_diff=("ivb_diff", "mean"), hb_diff=("hb_diff", "mean"),
    )
    phys["spin_axis"] = g["spin_axis"].agg(circular_mean_deg)
    a = phys.join(outcome_aggs(g)).reset_index()
    a = a[a["n"] >= MIN_PITCHES_TYPE]
    tot = d.groupby(["pitcher", "game_year"]).size().rename("total")
    a = a.merge(tot, on=["pitcher", "game_year"])
    a["usage"] = 100 * a["n"] / a["total"]
    a = a.drop(columns="total")
    a["axis_clock"] = ph.axis_to_clock(a["spin_axis"])

    # Percentile within season x pitch type among qualified pitches.
    q = a["n"] >= QUAL_PCTL
    for col, asc in [("velo", True), ("ivb", True), ("vaa_aa", True), ("spin_eff", True),
                     ("stuff_plus", True), ("whiff_pct", True), ("rv100", True), ("ext", True),
                     ("spin", True), ("chase_pct", True)]:
        a[f"{col}_pctl"] = np.nan
        a.loc[q, f"{col}_pctl"] = a[q].groupby(["game_year", "pitch_type"])[col].rank(pct=True, ascending=asc) * 100
    a["hb_abs"] = a["hb"].abs()
    a["hb_pctl"] = np.nan
    a.loc[q, "hb_pctl"] = a[q].groupby(["game_year", "pitch_type"])["hb_abs"].rank(pct=True) * 100
    a = a.drop(columns="hb_abs")

    # Most typical pitch of each combo (medoid in velo/movement/location space) for 3D replays.
    z = d[KEY + ["release_speed", "ivb", "hb", "plate_x", "plate_z", "vx0", "vy0", "vz0", "ax", "ay", "az",
                 "release_extension"]].copy()
    med = z.groupby(KEY)[["release_speed", "ivb", "hb", "plate_x", "plate_z"]].transform("median")
    z["dist"] = (((z["release_speed"] - med["release_speed"]) / 2) ** 2 + ((z["ivb"] - med["ivb"]) / 2) ** 2
                 + ((z["hb"] - med["hb"]) / 2) ** 2 + ((z["plate_x"] - med["plate_x"]) / .5) ** 2
                 + ((z["plate_z"] - med["plate_z"]) / .5) ** 2)
    medoid = z.loc[z.groupby(KEY)["dist"].idxmin(), KEY + ["vx0", "vy0", "vz0", "ax", "ay", "az",
                                                          "plate_x", "plate_z", "release_extension"]]
    medoid = medoid.rename(columns={c: f"t_{c}" for c in medoid.columns if c not in KEY})
    a = a.merge(medoid, on=KEY, how="left")

    # Model explanation: mean SHAP per feature (run value per 100 pitches, + helps pitcher).
    shap = pd.read_parquet(INTERIM / "shap_sample.parquet")
    shap[["pitcher", "game_year"]] = shap[["pitcher", "game_year"]].astype(int)
    sm = shap.groupby(KEY)[[f"shap_{f}" for f in FEATURES]].mean() * 100
    a = a.merge(sm.reset_index(), on=KEY, how="left")
    return f32(a)


def build_pitchers(d: pd.DataFrame, arsenal: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby(["pitcher", "game_year"])
    base = g.agg(
        player_name=("player_name", "first"), hand=("p_throws", "first"),
        team=("team", lambda s: s.mode().iat[0]), games=("game_pk", "nunique"),
        arm_angle=("arm_angle", "mean"), ext=("release_extension", "mean"), rel_z=("release_pos_z", "mean"),
    )
    pa = d[d["events"].notna()].groupby(["pitcher", "game_year"])["events"]
    base["pa"] = pa.size()
    base["k_pct"] = 100 * pa.apply(lambda s: s.isin(["strikeout", "strikeout_double_play"]).mean())
    base["bb_pct"] = 100 * pa.apply(lambda s: s.isin(["walk", "intent_walk"]).mean())
    out = base.join(outcome_aggs(g)).reset_index()
    out["name"] = display_name(out["player_name"]).str.strip()
    out["pitches_per_game"] = out["n"] / out["games"]
    out["role"] = np.where(out["pitches_per_game"] >= 50, "SP", "RP")
    fb = arsenal[arsenal["pitch_type"].isin(ph.FASTBALLS)].sort_values("n").groupby(["pitcher", "game_year"]).tail(1)
    out = out.merge(fb[["pitcher", "game_year", "pitch_type", "velo"]].rename(
        columns={"pitch_type": "primary_fb", "velo": "fb_velo"}), on=["pitcher", "game_year"], how="left")
    out["n_pitch_types"] = out.merge(arsenal.groupby(["pitcher", "game_year"]).size().rename("k").reset_index(),
                                     on=["pitcher", "game_year"], how="left")["k"].to_numpy()
    q = out["n"] >= 500
    for col in ("stuff_plus", "whiff_pct", "rv100", "k_pct", "csw_pct", "chase_pct"):
        out[f"{col}_pctl"] = np.nan
        out.loc[q, f"{col}_pctl"] = out[q].groupby("game_year")[col].rank(pct=True) * 100
    return f32(out)


def build_sample(d: pd.DataFrame, arsenal: pd.DataFrame) -> pd.DataFrame:
    keep = arsenal[KEY]
    s = d.merge(keep, on=KEY)
    s = s.assign(r=np.random.default_rng(11).random(len(s)))
    s = s[s.groupby(KEY)["r"].rank(method="first") <= SAMPLE_PER_COMBO]
    res = np.select([s["is_whiff"], s["description"].eq("called_strike"), s["is_bip"], s["is_swing"]],
                    ["whiff", "called", "in_play", "foul"], "ball")
    out = s[KEY + ["release_speed", "ivb", "hb", "plate_x", "plate_z", "zone_height", "stand", "count",
                   "release_side", "release_pos_z", "spin_axis", "release_spin_rate"]].copy()
    out["result"] = res
    for c in ("stand", "count", "result", "pitch_type"):
        out[c] = out[c].astype("category")
    out["pitcher"] = out["pitcher"].astype("int32")
    out["game_year"] = out["game_year"].astype("int16")
    return f32(out).reset_index(drop=True)


def build_tunnels(d: pd.DataFrame) -> pd.DataFrame:
    t = ph.tunnel_pairs(d)
    g = t.groupby(["pitcher", "game_year", "prev_type", "pitch_type"])
    out = g.agg(n=("tunnel_in", "size"), tunnel_in=("tunnel_in", "median"), plate_in=("plate_in", "median"),
                ratio=("break_tunnel_ratio", "median")).reset_index()
    out = out[out["n"] >= 25]
    out["ratio_pctl"] = out.groupby("game_year")["ratio"].rank(pct=True) * 100
    return f32(out)


def build_counts(d: pd.DataFrame, arsenal: pd.DataFrame) -> pd.DataFrame:
    b, s = d["balls"], d["strikes"]
    state = np.select([(b == 0) & (s == 0), s == 2, b > s, s > b], ["first", "two_strike", "behind", "ahead"], "even")
    x = d.assign(state=state).merge(arsenal[KEY], on=KEY)
    c = x.groupby(["pitcher", "game_year", "stand", "state", "pitch_type"]).size().rename("n").reset_index()
    c["share"] = 100 * c["n"] / c.groupby(["pitcher", "game_year", "stand", "state"])["n"].transform("sum")
    c["pitcher"] = c["pitcher"].astype("int32")
    return f32(c)


def build_locations(d: pd.DataFrame, arsenal: pd.DataFrame) -> pd.DataFrame:
    x = d.merge(arsenal[KEY], on=KEY)
    x = x.assign(bx=np.clip(np.floor(x["plate_x"] / (17 / 12 / 3)), -4, 3).astype(int),
                 bz=np.clip(np.floor(x["zone_height"] * 3), -2, 4).astype(int))
    g = x.groupby(KEY + ["stand", "bx", "bz"]).agg(n=("is_whiff", "size"), whiffs=("is_whiff", "sum"),
                                                     swings=("is_swing", "sum"), rv=("delta_run_exp", "sum"))
    g = g.reset_index()
    for c in ("bx", "bz"):
        g[c] = g[c].astype("int8")
    g["pitcher"] = g["pitcher"].astype("int32")
    return f32(g)


def build_monthly(d: pd.DataFrame, arsenal: pd.DataFrame) -> pd.DataFrame:
    x = d.merge(arsenal[KEY], on=KEY)
    x["month"] = x["game_date"].dt.to_period("M").dt.to_timestamp()
    g = x.groupby(KEY + ["month"]).agg(n=("release_speed", "size"), velo=("release_speed", "mean"),
                                       ivb=("ivb", "mean"), hb=("hb", "mean"), spin=("release_spin_rate", "mean"),
                                       stuff_plus=("stuff_plus", "mean")).reset_index()
    return f32(g[g["n"] >= 15])


def build_league(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    g = d.groupby(["game_year", "pitch_type"])
    league = g.agg(n=("release_speed", "size"), velo=("release_speed", "mean"), spin=("release_spin_rate", "mean"),
                   ivb=("ivb", "mean"), hb=("hb", "mean"), vaa=("vaa", "mean"), haa=("haa", "mean"),
                   spin_eff=("spin_eff", "mean"), ssw_deg=("ssw_deg", "mean"), ext=("release_extension", "mean"),
                   arm_angle=("arm_angle", "mean"), flight_time=("flight_time", "mean"),
                   eff_velo=("effective_speed", "mean"))
    league = league.join(outcome_aggs(g).drop(columns=["n"])).reset_index()
    league["usage"] = 100 * league["n"] / league.groupby("game_year")["n"].transform("sum")
    # Movement density: 2-inch bins of HB x IVB per pitch type (for league "clouds").
    dd = d.assign(hx=(np.floor(d["hb"] / 2) * 2 + 1).astype("int16"), vz=(np.floor(d["ivb"] / 2) * 2 + 1).astype("int16"))
    dens = dd.groupby(["game_year", "pitch_type", "hx", "vz"]).size().rename("n").reset_index()
    dens = dens[dens["n"] >= 20]
    return f32(league), f32(dens)


def build_insights(d: pd.DataFrame) -> pd.DataFrame:
    """'Does it matter?' curves: outcome vs. metric in 16 quantile bins, by pitch type."""
    rows = []
    metrics = ["release_speed", "ivb", "hb", "vaa", "vaa_aa", "spin_eff", "ssw_deg", "release_extension",
               "arm_angle", "release_spin_rate", "velo_diff", "ivb_diff", "stuff_plus"]
    for pt in ["FF", "SI", "FC", "SL", "ST", "CU", "CH", "FS"]:
        x = d[d["pitch_type"] == pt]
        for m in metrics:
            v = x[m]
            if v.notna().sum() < 5000:
                continue
            bins = pd.qcut(v, 16, duplicates="drop")
            g = x.groupby(bins, observed=True).agg(
                x=(m, "median"), n=(m, "size"), swings=("is_swing", "sum"), whiffs=("is_whiff", "sum"),
                csw=("is_csw", "sum"), rv=("delta_run_exp", "mean"))
            g["whiff_pct"] = 100 * g["whiffs"] / g["swings"]
            g["csw_pct"] = 100 * g["csw"] / g["n"]
            g["rv100"] = -100 * g["rv"]
            g = g.reset_index(drop=True).assign(pitch_type=pt, metric=m)
            rows.append(g[["pitch_type", "metric", "x", "n", "whiff_pct", "csw_pct", "rv100"]])
    return f32(pd.concat(rows, ignore_index=True))


def build_correlations(arsenal: pd.DataFrame) -> pd.DataFrame:
    """Pitch-level-aggregated correlation of each metric with whiff% and run value (qualified arsenals)."""
    rows = []
    metrics = ["velo", "ivb", "hb", "vaa", "vaa_aa", "spin", "spin_eff", "ssw_deg", "ext", "arm_angle",
               "rel_z", "velo_diff", "ivb_diff", "hb_diff", "stuff_plus"]
    q = arsenal[arsenal["n"] >= 200]
    for pt, g in q.groupby("pitch_type"):
        if len(g) < 40:
            continue
        for m in metrics:
            sub = g[[m, "whiff_pct", "rv100"]].dropna()
            rows.append({"pitch_type": pt, "metric": m, "n_arsenals": len(sub),
                         "r_whiff": sub[m].corr(sub["whiff_pct"]), "r_rv": sub[m].corr(sub["rv100"])})
    return f32(pd.DataFrame(rows))


def main() -> None:
    APP.mkdir(parents=True, exist_ok=True)
    d = pd.read_parquet(INTERIM / "pitches.parquet")
    print(f"pitches: {len(d):,}")
    arsenal = build_arsenal(d)
    tables = {
        "arsenal": arsenal,
        "pitchers": build_pitchers(d, arsenal),
        "sample": build_sample(d, arsenal),
        "tunnels": build_tunnels(d),
        "counts": build_counts(d, arsenal),
        "locations": build_locations(d, arsenal),
        "monthly": build_monthly(d, arsenal),
        "insights": build_insights(d),
        "correlations": build_correlations(arsenal),
    }
    tables["league"], tables["league_density"] = build_league(d)
    for name, t in tables.items():
        p = APP / f"{name}.parquet"
        t.to_parquet(p, index=False, compression="zstd")
        print(f"{name:15s} {len(t):>9,} rows  {p.stat().st_size / 1e6:6.2f} MB")
    meta = {"seasons": sorted(int(y) for y in d["game_year"].unique()), "pitches": int(len(d)),
            "pitchers": int(d["pitcher"].nunique()), "built": pd.Timestamp.now().strftime("%Y-%m-%d"),
            "last_game": str(d["game_date"].max().date()),
            "spin_eff_reference": json.loads((INTERIM / "calibration.json").read_text())["spin_eff_reference"]}
    (APP / "meta.json").write_text(json.dumps(meta, indent=2))
    print(meta)


if __name__ == "__main__":
    main()
