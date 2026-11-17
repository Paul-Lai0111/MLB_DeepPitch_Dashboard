"""Stage 3: DeepPitch Stuff+ — how much a pitch's physics alone is worth.

A LightGBM model learns expected run value (Statcast `delta_run_exp`, from
the pitcher's side: lower = better for the pitcher) using ONLY what the ball
does: velocity, spin, movement, release, and how it differs from the
pitcher's fastball. Location, count and batter quality are left out on
purpose, so the score isolates "stuff".

Validation is leave-one-season-out: each season is scored by a model trained\non the other seasons, so every number in the app is out-of-sample.

python -m pipeline.model
Reads/writes data/interim/pitches.parquet (adds stuff_pred, stuff_plus),
writes data/interim/shap_sample.parquet and data/app/model_report.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

INTERIM = Path("data/interim/pitches.parquet")
APP = Path("data/app")

from deeppitch.features import FEATURES, FEATURE_LABELS as _LABELS

FEATURE_LABELS = {k: v[0] for k, v in _LABELS.items()}
PITCH_CODES = {p: i for i, p in enumerate(["FF", "SI", "FC", "SL", "ST", "SV", "CU", "KC", "CH", "FS", "FO", "KN"])}

ROUNDS = 250
PARAMS = dict(objective="regression", learning_rate=0.06, num_leaves=31, min_data_in_leaf=800,
              feature_fraction=0.85, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0, verbose=-1)


def design(d: pd.DataFrame) -> pd.DataFrame:
    X = d.reindex(columns=FEATURES).copy()
    X["pitch_type_code"] = d["pitch_type"].map(PITCH_CODES).fillna(-1).astype(int)
    X["same_hand"] = (d["p_throws"] == d["stand"]).astype(int)
    return X.astype("float32")


def scale_to_plus(d: pd.DataFrame, pred: np.ndarray) -> np.ndarray:
    """100 = league average for that season; 10 points = 1 SD across pitcher arsenals."""
    plus = np.full(len(d), np.nan)
    for yr, idx in d.groupby("game_year").indices.items():
        p = pred[idx]
        mu = p.mean()
        tmp = pd.DataFrame({"pid": d["pitcher"].values[idx], "pt": d["pitch_type"].values[idx], "p": p})
        agg = tmp.groupby(["pid", "pt"])["p"].agg(["mean", "size"])
        sd = agg.loc[agg["size"] >= 100, "mean"].std()
        plus[idx] = 100 - (p - mu) / sd * 10   # lower run value = better = higher Stuff+
    return plus


def pitcher_level_validity(d: pd.DataFrame) -> dict:
    """Does Stuff+ in season N predict run value in season N+1 better than raw velocity?"""
    g = (d.groupby(["pitcher", "game_year"])
           .agg(n=("stuff_plus", "size"), stuff=("stuff_plus", "mean"),
                rv100=("delta_run_exp", lambda s: -100 * s.mean()),
                whiff=("is_whiff", "sum"), swings=("is_swing", "sum"),
                velo=("release_speed", "max"))
           .reset_index())
    g = g[g["n"] >= 500]
    g["whiff_rate"] = g["whiff"] / g["swings"]
    nxt = g.copy()
    nxt["game_year"] -= 1
    m = g.merge(nxt, on=["pitcher", "game_year"], suffixes=("", "_next"))
    out = {"pairs": int(len(m))}
    if len(m) > 30:
        for col in ("stuff", "rv100", "velo", "whiff_rate"):
            out[f"{col}_vs_next_rv100"] = round(float(m[col].corr(m["rv100_next"])), 3)
            out[f"{col}_vs_next_whiff"] = round(float(m[col].corr(m["whiff_rate_next"])), 3)
        out["stuff_year_to_year"] = round(float(m["stuff"].corr(m["stuff_next"])), 3)
        out["rv100_year_to_year"] = round(float(m["rv100"].corr(m["rv100_next"])), 3)
    same = g[["stuff", "rv100", "whiff_rate"]].corr()
    out["same_season_stuff_vs_rv100"] = round(float(same.loc["stuff", "rv100"]), 3)
    out["same_season_stuff_vs_whiff"] = round(float(same.loc["stuff", "whiff_rate"]), 3)
    return out


def main() -> None:
    APP.mkdir(parents=True, exist_ok=True)
    full = pd.read_parquet(INTERIM)
    full = full.drop(columns=[c for c in full.columns if c.startswith("shap_") or c.startswith("stuff_")])
    d = full[full["delta_run_exp"].notna()].reset_index(drop=True)
    X, y = design(d), d["delta_run_exp"].astype("float32").values
    years = sorted(d["game_year"].unique())
    report: dict = {"features": [FEATURE_LABELS[f] for f in FEATURES], "seasons": [int(v) for v in years],
                    "folds": []}

    # Leave-one-season-out: every season is scored by a model that never saw it.
    pred = np.full(len(d), np.nan)
    sample_idx, shap_rows = [], []
    rng = np.random.default_rng(7)
    for yr in years:
        te = (d["game_year"] == yr).values
        tr = ~te if len(years) > 1 else te
        m = lgb.train(PARAMS, lgb.Dataset(X[tr], y[tr]), num_boost_round=ROUNDS)
        pred[te] = m.predict(X[te])
        base = np.mean((y[te] - y[tr].mean()) ** 2)
        report["folds"].append({
            "test_season": int(yr), "train_seasons": [int(v) for v in years if v != yr] or [int(yr)],
            "mse_reduction_pct": round(float(100 * (1 - np.mean((y[te] - pred[te]) ** 2) / base)), 3),
            "pitch_level_corr": round(float(np.corrcoef(pred[te], y[te])[0, 1]), 4),
        })
        # SHAP on up to 40 pitches per pitcher x pitch type (enough for stable means, cheap to compute).
        sub = d.loc[te, ["pitcher", "pitch_type"]].assign(r=rng.random(te.sum()))
        sub["k"] = sub.groupby(["pitcher", "pitch_type"])["r"].rank(method="first")
        idx = sub.index[sub["k"] <= 40].to_numpy()
        contrib = m.predict(X.iloc[idx], pred_contrib=True)[:, :-1]
        sample_idx.append(idx)
        shap_rows.append(-contrib)  # + = helps the pitcher
        print(report["folds"][-1], flush=True)

    d["stuff_pred"] = pred
    d["stuff_plus"] = scale_to_plus(d, pred)
    idx = np.concatenate(sample_idx)
    shap = pd.DataFrame(np.vstack(shap_rows), columns=[f"shap_{f}" for f in FEATURES])
    shap[["pitcher", "game_year", "pitch_type"]] = d.loc[idx, ["pitcher", "game_year", "pitch_type"]].to_numpy()
    shap.to_parquet(Path("data/interim/shap_sample.parquet"), index=False)
    imp = shap[[f"shap_{f}" for f in FEATURES]].abs().mean()
    report["importance"] = sorted(
        [{"feature": FEATURE_LABELS[f], "key": f, "mean_abs_shap": float(imp[f"shap_{f}"])} for f in FEATURES],
        key=lambda r: -r["mean_abs_shap"])
    report["validity"] = pitcher_level_validity(d)

    keys = ["game_pk", "at_bat_number", "pitch_number"]
    full.merge(d[keys + ["stuff_pred", "stuff_plus"]], on=keys, how="left").to_parquet(INTERIM, index=False)
    (APP / "model_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("folds", "validity")}, indent=2))
    print("top features:", [r["feature"] for r in report["importance"][:6]])


if __name__ == "__main__":
    main()
