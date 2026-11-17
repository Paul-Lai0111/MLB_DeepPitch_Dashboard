import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from deeppitch import charts, components as ui, data
from deeppitch.i18n import L, pitch_name
from deeppitch.theme import BLUE, COND, INK, MUTED, PAPER, PLOT_CONFIG, RED, pitch_color

st.html(f'<div class="mast"><div><h1 class="title">{ui.esc(L("Does it matter?", "真的有用嗎？"))}</h1>'
        f'<p class="lede">{ui.esc(L("Physics is only interesting if it wins at-bats. This page checks every metric against what hitters actually did: whiffs, called strikes, and runs.", "物理只有在能贏得打席時才有意思。這一頁把每個指標拿去對照打者的實際結果：揮空、好球、失分。"))}</p></div></div>')

MET = {"velo": L("Velocity", "球速"), "ivb": "IVB", "hb": "HB", "vaa": "VAA", "vaa_aa": L("VAA vs loc.", "位置校正 VAA"),
       "spin": L("Spin rate", "轉速"), "spin_eff": L("Spin eff.", "旋轉效率"), "ssw_deg": "SSW", "ext": L("Extension", "延伸"),
       "arm_angle": L("Arm angle", "手臂角度"), "rel_z": L("Release ht.", "出手高度"), "velo_diff": L("Velo gap", "球速差"),
       "ivb_diff": L("Rise gap", "垂直差"), "hb_diff": L("Run gap", "水平差"), "stuff_plus": "Stuff+"}
PTS = ["FF", "SI", "FC", "SL", "ST", "CU", "CH", "FS"]

corr = data.table("correlations")
st.markdown(f"## {L('Which traits travel with whiffs', '哪些特性和揮空有關')}")
outcome = st.segmented_control(L("Outcome", "結果"), ["r_whiff", "r_rv"], default="r_whiff", key="ins_out",
                               format_func=lambda k: L("Whiff rate", "揮空率") if k == "r_whiff" else L("Run value", "失分價值")) or "r_whiff"
m = corr.pivot(index="metric", columns="pitch_type", values=outcome).reindex(index=list(MET), columns=PTS)
fig = go.Figure(go.Heatmap(
    z=m.values, x=[pitch_name(p) for p in PTS], y=[MET[k] for k in m.index], zmin=-0.6, zmax=0.6,
    colorscale=[[0, BLUE], [0.5, "#E4E7E0"], [1, RED]], xgap=2, ygap=2,
    text=np.where(np.isfinite(m.values), np.vectorize(lambda v: f"{v:+.2f}")(np.nan_to_num(m.values)), ""),
    texttemplate="%{text}", textfont=dict(family=COND, size=13, color=INK),
    hovertemplate="%{y} · %{x}<br>r = %{z:+.2f}<extra></extra>",
    colorbar=dict(title="r", thickness=10, outlinewidth=0, tickfont=dict(color=MUTED))))
fig.update_layout(height=560, xaxis=dict(side="top", showgrid=False, ticks=""), yaxis=dict(autorange="reversed", showgrid=False, ticks=""),
                  margin=dict(l=8, r=8, t=40, b=8))
st.plotly_chart(fig, config=PLOT_CONFIG, key="ins_heat")
st.caption(L("Each cell: correlation across pitchers' arsenals (200+ pitches of that type, all seasons pooled). "
             "Red = more of the trait goes with more whiffs (or more runs saved); blue = the opposite; gray = no relation.",
             "每格：所有投手該球種（200 球以上、三季合併）之間的相關係數。紅 = 特性越多、揮空（或省下的分）越多；藍 = 相反；灰 = 無關。"))

ff = corr[corr["pitch_type"] == "FF"].set_index("metric")
ui.note(L("Look down the four-seam column: approach angle, not rise, carries the red.", "看四縫線那一欄：帶紅色的是進壘角度，不是上竄。"))
c1, c2, c3 = st.columns(3, gap="large")
with c1:
    st.html(f'<div class="finding"><div class="stat">{ff.loc["vaa", "r_whiff"]:+.2f}</div><h4>{ui.esc(L("Approach angle beats rise", "進壘角度勝過上竄"))}</h4>'
            f'<p>{ui.esc(L(f"For four-seamers, VAA relates to whiffs far more than IVB ({ff.loc['ivb', 'r_whiff']:+.2f}). Rise is an ingredient; the flat angle is the dish.", f"四縫線的 VAA 和揮空的關係遠大於 IVB（{ff.loc['ivb', 'r_whiff']:+.2f}）。上竄只是食材，平的進壘角才是成品。"))}</p></div>')
with c2:
    st.html(f'<div class="finding"><div class="stat">{ff.loc["stuff_plus", "r_rv"]:+.2f}</div><h4>{ui.esc(L("Physics explains part, not all", "物理只解釋了一部分"))}</h4>'
            f'<p>{ui.esc(L("Stuff+ vs. four-seam run value. Location, sequencing and the hitter carry the rest, which is why command matters.", "Stuff+ 與四縫線失分價值的相關。剩下的由進壘位置、配球與打者決定，這也是控球為何重要。"))}</p></div>')
with c3:
    st.html(f'<div class="finding"><div class="stat">{ff.loc["arm_angle", "r_whiff"]:+.2f}</div><h4>{ui.esc(L("Lower slots, more whiffs", "手臂越低，揮空越多"))}</h4>'
            f'<p>{ui.esc(L("Four-seam arm angle vs whiff rate. A lower release flattens the angle the ball arrives at.", "四縫線手臂角度與揮空率。較低的出手點讓球進壘更平。"))}</p></div>')

# ---- explorer
st.markdown(f"## {L('Explore any relationship', '自己探索任何關係')}")
ins = data.table("insights")
labels_x = {"release_speed": L("Velocity (mph)", "球速 (mph)"), "ivb": "IVB (in)", "hb": L("HB (in, arm side +)", "HB（吋，手臂側 +）"),
            "vaa": "VAA (°)", "vaa_aa": L("VAA vs location (°)", "位置校正 VAA (°)"), "spin_eff": L("Spin efficiency", "旋轉效率"),
            "ssw_deg": "SSW (°)", "release_extension": L("Extension (ft)", "延伸 (呎)"), "arm_angle": L("Arm angle (°)", "手臂角度 (°)"),
            "release_spin_rate": L("Spin rate (rpm)", "轉速 (rpm)"), "velo_diff": L("Velo gap vs fastball (mph)", "與速球球速差 (mph)"),
            "ivb_diff": L("Rise gap vs fastball (in)", "與速球垂直差 (吋)"), "stuff_plus": "Stuff+"}
c1, c2, c3 = st.columns([1.3, 1, 2])
with c1:
    xm = st.selectbox(L("Metric", "指標"), list(labels_x), index=list(labels_x).index("vaa_aa"), format_func=labels_x.get)
with c2:
    ym = st.selectbox(L("Outcome", "結果"), ["whiff_pct", "csw_pct", "rv100"],
                      format_func={"whiff_pct": L("Whiff %", "揮空率"), "csw_pct": "CSW %", "rv100": L("Runs saved / 100", "每百球省分")}.get)
with c3:
    pts = st.multiselect(L("Pitch types", "球種"), PTS, default=["FF", "SI"], format_func=pitch_name)
ytitle = {"whiff_pct": L("Whiff rate, %", "揮空率 %"), "csw_pct": "CSW %", "rv100": L("Runs saved per 100 pitches", "每百球省下的分數")}[ym]
st.plotly_chart(charts.insight_curve(ins, xm, pts, ym, labels_x[xm], ytitle, height=420), config=PLOT_CONFIG, key="ins_curve")
st.caption(L("Every pitch of that type, 2024–2026, split into 16 equal-size groups by the metric. Each dot is one group's outcome.",
             "該球種 2024–2026 年所有投球，依指標分成 16 個等量組，每個點是一組的結果。"))

# ---- arm angle map
st.markdown(f"## {L('Arm angle shapes the fastball', '手臂角度塑造速球')}")
a = data.table("arsenal")
yr = data.seasons()[-1]
f = a[(a["pitch_type"] == "FF") & (a["game_year"] == yr) & (a["n"] >= 300)].merge(
    data.table("pitchers")[["pitcher", "game_year", "name"]], on=["pitcher", "game_year"])
fig = go.Figure(go.Scatter(
    x=f["arm_angle"], y=f["ivb"], mode="markers", text=f["name"],
    marker=dict(size=np.clip(f["whiff_pct"] - 8, 4, 30), color=f["vaa_aa"], colorscale=[[0, BLUE], [0.5, "#D9DDD5"], [1, RED]],
                cmid=0, line=dict(width=1, color=PAPER), colorbar=dict(title=L("VAA vs loc.", "位置校正 VAA"), thickness=10, outlinewidth=0)),
    hovertemplate="<b>%{text}</b><br>" + L("Arm angle", "手臂角度") + " %{x:.0f}° · IVB %{y:.1f}″<extra></extra>"))
fig.update_layout(height=480, xaxis=dict(title=L("Arm angle at release (°)", "出手手臂角度 (°)")), yaxis=dict(title=L("Four-seam IVB (in)", "四縫線 IVB (吋)")))
st.plotly_chart(fig, config=PLOT_CONFIG, key="ins_arm")
st.caption(L(f"{yr} four-seamers, 300+ thrown. Dot size = whiff rate; red = flatter than expected for location. Higher slots create more rise, lower slots a flatter angle: two routes to the same result.",
             f"{yr} 年投超過 300 顆的四縫線。點越大揮空率越高；紅色 = 比同位置預期更平。手臂越高上竄越多，越低進壘越平：兩條路通往同一個結果。"))

# ---- bat tracking + trends
c1, c2 = st.columns(2, gap="large")
lg = data.table("league")
with c1:
    st.markdown(f"### {L('How hard hitters swing at each pitch', '打者面對各球種的揮棒速度')}")
    b = lg[lg["game_year"] == yr].set_index("pitch_type").reindex(PTS).reset_index()
    b["label"] = b["pitch_type"].map(pitch_name)
    b = b.sort_values("bat_speed", ascending=False)
    fig = go.Figure(go.Bar(x=b["bat_speed"], y=b["label"], orientation="h",
                           marker=dict(color=[pitch_color(p) for p in b["pitch_type"]]),
                           text=[f"{v:.1f}" for v in b["bat_speed"]], textposition="outside", cliponaxis=False,
                           textfont=dict(family=COND, size=13, color=INK), hovertemplate="%{y}: %{x:.1f} mph<extra></extra>"))
    fig.update_layout(height=340, xaxis=dict(range=[60, 75], title=L("Average bat speed on swings (mph)", "平均揮棒速度 (mph)")),
                      yaxis=dict(autorange="reversed", showgrid=False))
    st.plotly_chart(fig, config=PLOT_CONFIG, key="ins_bat")
    st.caption(L("Statcast bat tracking. Off-speed pitches catch hitters early and slow the swing down.", "Statcast 揮棒追蹤。變速類球路讓打者提早出棒、揮速變慢。"))
with c2:
    st.markdown(f"### {L('The pitch mix is shifting', '球種配置正在改變')}")
    seasons = data.seasons()
    fig = go.Figure()
    for pt in ["FF", "SI", "SL", "ST", "CH", "FC", "CU", "FS"]:
        u = lg[lg["pitch_type"] == pt].sort_values("game_year")
        fig.add_trace(go.Scatter(x=u["game_year"], y=u["usage"], mode="lines+markers+text", name=pitch_name(pt),
                                 line=dict(color=pitch_color(pt), width=2), marker=dict(size=8, line=dict(width=1.5, color=PAPER)),
                                 text=[""] * (len(u) - 1) + [pitch_name(pt)], textposition="middle right",
                                 textfont=dict(size=12, color=INK), hovertemplate=f"{pitch_name(pt)} %{{x}}: %{{y:.1f}}%<extra></extra>"))
    fig.update_layout(height=340, showlegend=False, xaxis=dict(dtick=1, range=[seasons[0] - .2, seasons[-1] + .9], title=None),
                      yaxis=dict(title=L("Share of all pitches, %", "占全部投球 %")), margin=dict(r=90))
    st.plotly_chart(fig, config=PLOT_CONFIG, key="ins_mix")
ui.footer()
