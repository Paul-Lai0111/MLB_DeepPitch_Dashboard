"""Plotly figures in the scorebook template."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from deeppitch import physics as ph
from deeppitch.i18n import L, pitch_name
from deeppitch.theme import COND, INK, MUTED, PAPER, RED, RULE, RULE_SOFT, PITCH_SYMBOL, pitch_color

ZONE_HALF = 17 / 24


def _zone_shapes(fig, row=None, col=None, top=3.4, bot=1.6):
    kw = dict(row=row, col=col) if row else {}
    fig.add_shape(type="rect", x0=-ZONE_HALF, x1=ZONE_HALF, y0=bot, y1=top,
                  line=dict(color=INK, width=1.4), fillcolor="rgba(0,0,0,0)", layer="below", **kw)
    for i in (1, 2):
        x = -ZONE_HALF + i * 2 * ZONE_HALF / 3
        z = bot + i * (top - bot) / 3
        fig.add_shape(type="line", x0=x, x1=x, y0=bot, y1=top, line=dict(color="rgba(38,41,43,.25)", width=.7), **kw)
        fig.add_shape(type="line", x0=-ZONE_HALF, x1=ZONE_HALF, y0=z, y1=z, line=dict(color="rgba(38,41,43,.25)", width=.7), **kw)


def movement(sample: pd.DataFrame, arsenal: pd.DataFrame, density: pd.DataFrame | None = None,
             height: int = 560, title: str | None = None, group_col: str | None = None) -> go.Figure:
    """HB (arm side +) x IVB. League clouds behind, individual pitches, arsenal averages labelled."""
    fig = go.Figure()
    if density is not None and len(density):
        for pt, g in density.groupby("pitch_type", observed=True):
            if pt not in arsenal["pitch_type"].values:
                continue
            g = g[g["n"] >= g["n"].quantile(0.55)]
            fig.add_trace(go.Scatter(x=g["hx"], y=g["vz"], mode="markers", hoverinfo="skip", showlegend=False,
                                     marker=dict(symbol="square", size=11, color=pitch_color(pt), opacity=0.07,
                                                 line=dict(width=0))))
    for pt in arsenal["pitch_type"]:
        s = sample[sample["pitch_type"] == pt]
        name = pitch_name(pt)
        fig.add_trace(go.Scatter(
            x=s["hb"], y=s["ivb"], mode="markers", name=name, legendgroup=pt,
            marker=dict(size=8, color=pitch_color(pt), opacity=.55, symbol=PITCH_SYMBOL.get(pt, "circle"),
                        line=dict(width=1, color=PAPER)),
            customdata=np.c_[s["release_speed"], s["result"].astype(str)],
            hovertemplate=f"<b>{name}</b><br>%{{customdata[0]:.1f}} mph<br>IVB %{{y:.1f}} in · HB %{{x:.1f}} in"
                          "<br>%{customdata[1]}<extra></extra>"))
    a = arsenal
    fig.add_trace(go.Scatter(
        x=a["hb"], y=a["ivb"], mode="markers+text", showlegend=False,
        text=[f"{pitch_name(p)} · {v:.0f}" for p, v in zip(a["pitch_type"], a["velo"])],
        textposition="top center", textfont=dict(family=COND, size=13, color=INK),
        marker=dict(size=17, color=[pitch_color(p) for p in a["pitch_type"]], line=dict(width=2.5, color=INK)),
        hovertemplate="%{text}<br>IVB %{y:.1f} in · HB %{x:.1f} in<extra>" + L("average", "平均") + "</extra>"))
    lim = 26
    fig.add_annotation(x=lim - 1, y=-lim + 1.5, text=L("arm side →", "手臂側 →"), showarrow=False, xanchor="right",
                       font=dict(color=MUTED, size=12))
    fig.add_annotation(x=-lim + 1, y=-lim + 1.5, text=L("← glove side", "← 手套側"), showarrow=False, xanchor="left",
                       font=dict(color=MUTED, size=12))
    fig.add_annotation(x=-lim + 1, y=lim - 1, text=L("rises more than gravity alone ↑", "比純重力少掉 ↑"),
                       showarrow=False, xanchor="left", font=dict(color=MUTED, size=12))
    fig.update_layout(height=height, title=title,
                      xaxis=dict(range=[-lim, lim], title=L("Horizontal break, in (arm side +)", "水平位移（吋，手臂側為 +）"),
                                 dtick=5, scaleanchor="y", scaleratio=1),
                      yaxis=dict(range=[-lim, lim], title=L("Induced vertical break, in", "誘發垂直位移 IVB（吋）"), dtick=5),
                      legend=dict(y=1.02))
    return fig


def folio(arsenal: pd.DataFrame, height: int = 330) -> go.Figure:
    """Flight Folio: every pitch of an arsenal at four instants, same scale, catcher's view.

    Plates: release · halfway · commit point (175 ms before the plate) · plate.
    Where dots overlap at the commit plate and split at the plate, the hitter is fooled.
    """
    labels = [L("Release", "出手"), L("Halfway", "飛行一半"), L("Commit point", "出棒決策點"), L("Plate", "本壘")]
    fig = make_subplots(rows=1, cols=4, shared_yaxes=True, horizontal_spacing=0.025, subplot_titles=labels)
    for _, r in arsenal.iterrows():
        if pd.isna(r.get("t_vy0")):
            continue
        tr = ph.trajectory({k[2:]: r[k] for k in r.index if k.startswith("t_")}, n=400)
        tp = tr["t"].iloc[-1]
        instants = [0.0, tp / 2, tp - ph.DECISION_TIME, tp]
        for c, tt in enumerate(instants, start=1):
            i = int(np.argmin(np.abs(tr["t"] - tt)))
            if i > 0:  # pencil trail: the path drawn so far, seen from the catcher's seat
                fig.add_trace(go.Scatter(x=tr["x"].iloc[: i + 1], y=tr["z"].iloc[: i + 1], mode="lines", showlegend=False,
                                         hoverinfo="skip", line=dict(color=pitch_color(r["pitch_type"]), width=1.6),
                                         opacity=.55, legendgroup=r["pitch_type"]), row=1, col=c)
            fig.add_trace(go.Scatter(
                x=[tr["x"].iloc[i]], y=[tr["z"].iloc[i]], mode="markers", showlegend=(c == 1),
                name=pitch_name(r["pitch_type"]), legendgroup=r["pitch_type"],
                marker=dict(size=15, color=pitch_color(r["pitch_type"]), opacity=.85, line=dict(width=1.5, color=INK)),
                hovertemplate=f"<b>{pitch_name(r['pitch_type'])}</b><br>{labels[c - 1]} · "
                              f"{tr['y'].iloc[i]:.1f} ft · {tt * 1000:.0f} ms<extra></extra>"), row=1, col=c)
    for c in range(1, 5):
        _zone_shapes(fig, 1, c)
        fig.update_xaxes(range=[-2.6, 2.6], showgrid=False, zeroline=False, showticklabels=False, ticks="", row=1, col=c)
    fig.update_yaxes(range=[0.4, 7.2], showgrid=True, gridcolor=RULE_SOFT, linecolor=RULE_SOFT, title=L("Height, ft", "高度（呎）"), row=1, col=1)
    for c in range(2, 5):
        fig.update_yaxes(showgrid=True, gridcolor=RULE_SOFT, linecolor=RULE_SOFT, row=1, col=c)
    fig.update_yaxes(showticklabels=False, ticks="", row=1, col=2)
    fig.update_yaxes(showticklabels=False, ticks="", row=1, col=3)
    fig.update_yaxes(showticklabels=False, ticks="", row=1, col=4)
    for a in fig.layout.annotations:
        a.font = dict(family=COND, size=14, color=RED if a.text == labels[2] else INK)
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=70, b=8), legend=dict(y=1.22))
    return fig


def location_grid(loc: pd.DataFrame, pitch_types: list[str], stand: str, height: int = 260) -> go.Figure:
    """Where each pitch is thrown (share of that pitch's locations), catcher's view, 3x3 zone + chase ring."""
    n = len(pitch_types)
    ncol = min(n, 3)
    nrow = int(np.ceil(n / ncol))
    fig = make_subplots(rows=nrow, cols=ncol, horizontal_spacing=0.03, vertical_spacing=0.1,
                        subplot_titles=[pitch_name(p) for p in pitch_types])
    w = 17 / 36
    for k, pt in enumerate(pitch_types):
        rr, c = k // ncol + 1, k % ncol + 1
        g = loc[(loc["pitch_type"] == pt) & (loc["stand"] == stand)]
        if g.empty:
            continue
        tot = g["n"].sum()
        grid = np.zeros((7, 8))
        hov = np.empty((7, 8), dtype=object)
        hov[:] = ""
        for _, r in g.iterrows():
            i, j = int(r["bz"]) + 2, int(r["bx"]) + 4
            grid[i, j] += r["n"] / tot * 100
            wh = r["whiffs"] / r["swings"] * 100 if r["swings"] > 0 else np.nan
            hov[i, j] = f"{r['n'] / tot * 100:.1f}% · {L('whiff', '揮空')} {wh:.0f}%" if np.isfinite(wh) else f"{r['n'] / tot * 100:.1f}%"
        xs = (np.arange(-4, 4) + .5) * w
        zs = (np.arange(-2, 5) + .5) / 3
        fig.add_trace(go.Heatmap(z=grid, x=xs, y=zs, text=hov, hovertemplate="%{text}<extra></extra>",
                                 colorscale=[[0, "rgba(243,245,239,0)"], [0.06, "#E3E6DE"], [1, pitch_color(pt)]],
                                 showscale=False, xgap=2, ygap=2, zmin=0, zmax=max(8, grid.max())), row=rr, col=c)
        fig.add_shape(type="rect", x0=-ZONE_HALF, x1=ZONE_HALF, y0=0, y1=1, line=dict(color=INK, width=1.6), row=rr, col=c)
        fig.update_xaxes(range=[-4 * w, 4 * w], showgrid=False, zeroline=False, showticklabels=False, ticks="", row=rr, col=c)
        fig.update_yaxes(range=[-2 / 3, 5 / 3], showgrid=False, zeroline=False, showticklabels=False, ticks="", row=rr, col=c)
    for a in fig.layout.annotations:
        a.font = dict(family=COND, size=14, color=INK)
    fig.update_layout(height=height * nrow, margin=dict(l=4, r=4, t=34, b=4))
    return fig


def count_usage(counts: pd.DataFrame, order: list[str], height: int = 300) -> go.Figure:
    states = [("first", L("First pitch", "第一球")), ("ahead", L("Pitcher ahead", "投手領先")),
              ("even", L("Even", "平手")), ("behind", L("Pitcher behind", "投手落後")), ("two_strike", L("Two strikes", "兩好球"))]
    fig = go.Figure()
    for pt in order:
        xs, ys = [], []
        for key, lab in states:
            g = counts[(counts["state"] == key)]
            tot = g["n"].sum()
            xs.append(g.loc[g["pitch_type"] == pt, "n"].sum() / tot * 100 if tot else 0)
            ys.append(lab)
        fig.add_trace(go.Bar(x=xs, y=ys, orientation="h", name=pitch_name(pt), marker=dict(color=pitch_color(pt),
                             line=dict(color=PAPER, width=2)),
                             hovertemplate=f"<b>{pitch_name(pt)}</b> · %{{x:.0f}}%<extra>%{{y}}</extra>"))
    fig.update_layout(barmode="stack", height=height, margin=dict(l=110, r=8, t=36, b=8),
                      xaxis=dict(range=[0, 100], ticksuffix="%", title=None),
                      yaxis=dict(autorange="reversed", title=None, showgrid=False), bargap=0.35)
    return fig


def monthly(m: pd.DataFrame, metric: str, ytitle: str, height: int = 300) -> go.Figure:
    fig = go.Figure()
    for pt, g in m.groupby("pitch_type", observed=True):
        g = g.sort_values("month")
        fig.add_trace(go.Scatter(x=g["month"], y=g[metric], mode="lines+markers", name=pitch_name(pt),
                                 line=dict(color=pitch_color(pt), width=2), marker=dict(size=8, line=dict(width=1.5, color=PAPER)),
                                 hovertemplate=f"<b>{pitch_name(pt)}</b> %{{x|%b %Y}} · %{{y:.1f}}<extra></extra>"))
    fig.update_layout(height=height, yaxis=dict(title=ytitle), xaxis=dict(title=None, dtick="M1", tickformat="%b"))
    return fig


def shap_bars(row: pd.Series, labels: dict, top: int = 7, height: int = 300) -> go.Figure:
    cols = [c for c in row.index if c.startswith("shap_") and pd.notna(row[c])]
    s = pd.Series({labels.get(c[5:], c[5:]): float(row[c]) for c in cols})
    s = s.reindex(s.abs().sort_values(ascending=False).index)[:top][::-1]
    fig = go.Figure(go.Bar(
        x=s.values, y=s.index, orientation="h",
        marker=dict(color=[RED if v > 0 else "#8A9089" for v in s.values], line=dict(width=0)),
        hovertemplate="%{y}: %{x:+.2f} " + L("runs / 100 pitches", "分 / 每百球") + "<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=12, b=8),
                      xaxis=dict(title=L("Run value per 100 pitches vs. average (+ helps pitcher)", "相對平均的每百球失分價值（+ 對投手有利）"),
                                 zeroline=False), yaxis=dict(showgrid=False))
    return fig


def insight_curve(ins: pd.DataFrame, metric: str, pitch_types: list[str], y: str, xtitle: str, ytitle: str,
                  height: int = 340) -> go.Figure:
    fig = go.Figure()
    for pt in pitch_types:
        g = ins[(ins["metric"] == metric) & (ins["pitch_type"] == pt)].sort_values("x")
        if g.empty:
            continue
        fig.add_trace(go.Scatter(x=g["x"], y=g[y], mode="lines+markers", name=pitch_name(pt),
                                 line=dict(color=pitch_color(pt), width=2), marker=dict(size=8, line=dict(width=1.5, color=PAPER)),
                                 customdata=g["n"], hovertemplate=f"<b>{pitch_name(pt)}</b><br>{xtitle}: %{{x:.2f}}"
                                 f"<br>{ytitle}: %{{y:.1f}}<br>n = %{{customdata:,}}<extra></extra>"))
    fig.update_layout(height=height, xaxis=dict(title=xtitle), yaxis=dict(title=ytitle))
    return fig


def bar_rank(df: pd.DataFrame, value: str, label: str, color: str, fmt: str = ".1f", height: int | None = None) -> go.Figure:
    d = df[::-1]
    fig = go.Figure(go.Bar(x=d[value], y=d[label], orientation="h", marker=dict(color=color, line=dict(width=0)),
                           text=[format(v, fmt) for v in d[value]], textposition="outside", cliponaxis=False,
                           textfont=dict(family=COND, size=13, color=INK),
                           hovertemplate="%{y}: %{x:" + fmt + "}<extra></extra>"))
    fig.update_layout(height=height or 28 * len(d) + 40, margin=dict(l=8, r=40, t=8, b=8),
                      xaxis=dict(showgrid=True, title=None), yaxis=dict(showgrid=False, title=None))
    return fig
