import numpy as np
import pandas as pd
import streamlit as st

from deeppitch import charts, components as ui, data
from deeppitch.i18n import L, pitch_name
from deeppitch.theme import PLOT_CONFIG
from deeppitch.features import FEATURE_LABELS

idx = data.pitcher_index()
labels = data.pitcher_labels()
ids = list(labels)

qp = st.query_params.get("id")
if qp and qp.isdigit() and int(qp) in labels:
    if st.session_state.get("pitcher_select") != int(qp):
        st.session_state["pitcher_select"] = int(qp)
elif "pitcher_select" not in st.session_state:
    st.session_state["pitcher_select"] = st.session_state.get("pitcher") or data.find_pitcher("Yamamoto")


def _sync():
    st.query_params["id"] = str(st.session_state["pitcher_select"])


c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
with c1:
    pid = st.selectbox(L("Pitcher", "投手"), ids, format_func=labels.get, key="pitcher_select", on_change=_sync)
st.session_state["pitcher"] = pid
yrs = data.pitcher_years(pid)
with c2:
    yr = st.segmented_control(L("Season", "賽季"), yrs, default=yrs[0], key=f"yr_{pid}") or yrs[0]

p = data.pitcher_row(pid, yr)
ars = data.arsenal(pid, yr)
if p is None or ars.empty:
    st.warning(L("Not enough tracked pitches for this pitcher in that season.", "這位投手在該賽季的追蹤球數不足。"))
    st.stop()

name = p["name"]
st.html(f'<div class="mast" style="grid-template-columns:1fr auto"><div><h1 class="title">{ui.esc(name)}</h1>'
        f'<p class="lede">{ui.esc(p["team"])} · {ui.esc(L("Right-handed", "右投") if p["hand"] == "R" else L("Left-handed", "左投"))} · '
        f'{ui.esc(L("Starter", "先發") if p["role"] == "SP" else L("Reliever", "後援"))} · {yr} · '
        f'<a href="https://www.mlb.com/player/{pid}" target="_blank">{ui.esc(L("MLB profile", "MLB 球員頁"))}</a> · '
        f'<a href="https://baseballsavant.mlb.com/savant-player/{pid}" target="_blank">Baseball Savant</a></p></div></div>')

ui.line([
    (L("Pitches", "投球數"), f"{int(p['n']):,}", None),
    ("Stuff+", f"{p['stuff_plus']:.0f}", L(f"{p['stuff_plus_pctl']:.0f} pct", f"第 {p['stuff_plus_pctl']:.0f} 百分位") if pd.notna(p["stuff_plus_pctl"]) else None),
    (L("Whiff", "揮空率"), f"{p['whiff_pct']:.1f}%", None),
    ("K%", f"{p['k_pct']:.1f}%", None),
    ("BB%", f"{p['bb_pct']:.1f}%", None),
    (L("Run value", "失分價值"), f"{p['rv100']:+.2f}", L("/100", "/百球")),
    (L("Arm angle", "手臂角度"), f"{p['arm_angle']:.0f}°", None),
    (L("Extension", "延伸"), f"{p['ext']:.1f}", "ft"),
], circled=1)
best = ars[ars["n"] >= 100].sort_values("stuff_plus", ascending=False)
if len(best):
    b0 = best.iloc[0]
    ui.note(L(f"Best pitch by the model: the {pitch_name(b0['pitch_type']).lower()}, Stuff+ {b0['stuff_plus']:.0f}"
              f"{f', {b0.whiff_pct:.0f}% whiffs' if pd.notna(b0.whiff_pct) else ''}.",
              f"模型眼中最好的球：{pitch_name(b0['pitch_type'])}，Stuff+ {b0['stuff_plus']:.0f}"
              f"{f'，揮空率 {b0.whiff_pct:.0f}%' if pd.notna(b0.whiff_pct) else ''}。"))

# ---- arsenal ledger
st.markdown(f"## {L('Arsenal', '球路組成')}")
st.html(ui.diamond_legend())
ui.ledger(ars, [
    (L("Pitch", "球種"), "pt", lambda r: ui.pitch_chip(r["pitch_type"], f"{r['usage']:.0f}%")),
    (L("Velo", "球速"), "velo", lambda r: f"{ui.num(r['velo'])} {ui.diamond(r['velo_pctl'], 16, False)}"),
    (L("Spin", "轉速"), "spin", lambda r: ui.num(r["spin"], 0)),
    (L("Eff.", "旋轉效率"), "spin_eff", lambda r: ui.num(r["spin_eff"] * 100, 0, "%")),
    (L("Axis", "轉軸"), "axis", lambda r: r["axis_clock"]),
    ("IVB", "ivb", lambda r: f"{ui.num(r['ivb'])}″ {ui.diamond(r['ivb_pctl'], 16, False)}"),
    ("HB", "hb", lambda r: f"{ui.num(r['hb'])}″ {ui.diamond(r['hb_pctl'], 16, False)}"),
    ("VAA", "vaa", lambda r: f"{ui.num(r['vaa'])}°"),
    (L("VAA vs loc.", "位置校正 VAA"), "vaa_aa", lambda r: f"{ui.num(r['vaa_aa'], 2)}° {ui.diamond(r['vaa_aa_pctl'], 16, False)}"),
    ("SSW", "ssw", lambda r: f"{ui.num(r['ssw_deg'], 0)}°"),
    (L("Whiff", "揮空"), "whiff", lambda r: f"{ui.num(r['whiff_pct'])}%"),
    (L("Chase", "追打"), "chase", lambda r: f"{ui.num(r['chase_pct'])}%"),
    ("Stuff+", "stuff", lambda r: f"<b>{ui.num(r['stuff_plus'], 0)}</b> {ui.diamond(r['stuff_plus_pctl'], 18, False)}"),
])
st.caption(L("IVB and HB in inches (HB: + = arm side). VAA vs loc. = approach angle relative to what's normal for the pitch's height in the zone; "
             "positive = flatter than expected. SSW = angle between spin-predicted and actual movement. Diamonds rank within the same pitch type and season.",
             "IVB、HB 單位為吋（HB：+ 為手臂側）。位置校正 VAA = 相對於同進壘高度的一般角度，正值代表比預期更平。"
             "SSW = 旋轉預測方向與實際位移方向的夾角。菱形為同球種同賽季內的排名。"))

# ---- flight
st.markdown(f"## {L('Flight', '飛行軌跡')}")
show = ars[ars["usage"] >= 3]
ui.flight(data.flight_payload(show, lambda r: f"{pitch_name(r['pitch_type'])} {r['velo']:.0f}"), height=540, key="p_flight")
st.plotly_chart(charts.folio(show), config=PLOT_CONFIG, key="p_folio")
st.caption(L("Each pitch's most typical delivery that season. Folio plates share one scale: overlap at the commit point is the tunnel.",
             "每種球路當季最典型的一球。四張圖同比例：在決策點重疊的部分就是隧道。"))

# ---- movement
st.markdown(f"## {L('Movement', '位移')}")
sample = data.table("sample")
smp = sample[(sample["pitcher"] == pid) & (sample["game_year"] == yr)]
dens = data.table("league_density")
dens = dens[dens["game_year"] == yr].copy()
c1, c2 = st.columns([3, 2], gap="large")
with c1:
    st.plotly_chart(charts.movement(smp, ars, dens, height=560), config=PLOT_CONFIG, key="p_move")
with c2:
    lg = data.table("league").query("game_year == @yr").set_index("pitch_type")
    st.markdown(f"#### {L('Against the league', '和聯盟比')}")
    rows = []
    for _, r in ars.iterrows():
        if r["pitch_type"] not in lg.index:
            continue
        l = lg.loc[r["pitch_type"]]
        rows.append(dict(pt=r["pitch_type"], dv=r["velo"] - l["velo"], di=r["ivb"] - l["ivb"], dh=r["hb"] - l["hb"],
                         dw=r["whiff_pct"] - l["whiff_pct"]))
    ui.ledger(pd.DataFrame(rows), [
        (L("Pitch", "球種"), "pt", lambda r: ui.pitch_chip(r["pt"])),
        (L("Velo", "球速"), "dv", lambda r: f"{r['dv']:+.1f}"),
        ("IVB", "di", lambda r: f"{r['di']:+.1f}″"),
        ("HB", "dh", lambda r: f"{r['dh']:+.1f}″"),
        (L("Whiff", "揮空"), "dw", lambda r: f'<span class="{"hi" if r["dw"] > 5 else ""}">{r["dw"]:+.1f}</span>'),
    ])
    st.caption(L("Difference from the league average for the same pitch type. The faint squares behind the chart are where the league throws each pitch.",
                 "與同球種聯盟平均的差距。圖表背後淡色方塊是全聯盟該球種的分布。"))

# ---- the rest, in tabs to keep the page scannable
t1, t2, t3, t4 = st.tabs([L("Locations", "進壘位置"), L("Sequencing & tunnels", "配球與隧道"),
                          L("Why the model grades it", "模型為何這樣評分"), L("Season trend", "賽季趨勢")])
with t1:
    stand = st.segmented_control(L("Batter", "打者"), ["R", "L"], default="R", key="stand",
                                 format_func=lambda s: L("vs right-handed hitters", "對右打") if s == "R" else L("vs left-handed hitters", "對左打")) or "R"
    loc = data.table("locations")
    loc = loc[(loc["pitcher"] == pid) & (loc["game_year"] == yr)]
    pts = [pt for pt in ars["pitch_type"] if loc[(loc["pitch_type"] == pt) & (loc["stand"] == stand)]["n"].sum() >= 20][:6]
    if pts:
        st.plotly_chart(charts.location_grid(loc, pts, stand, height=330), config=PLOT_CONFIG, key="p_loc")
        st.caption(L("Catcher's view. Darker = larger share of that pitch. The bold box is the strike zone, scaled to each hitter's height; hover for whiff rate.",
                     "捕手視角。顏色越深 = 該球種越常投到那裡。粗框為好球帶（依打者身高標準化），滑過可看揮空率。"))
    else:
        st.info(L("Too few pitches to that side.", "對這一側的投球太少。"))
with t2:
    cnt = data.table("counts")
    cnt = cnt[(cnt["pitcher"] == pid) & (cnt["game_year"] == yr)]
    s2 = st.segmented_control(L("Batter", "打者"), ["R", "L"], default="R", key="stand2",
                              format_func=lambda s: L("vs RHH", "對右打") if s == "R" else L("vs LHH", "對左打")) or "R"
    st.plotly_chart(charts.count_usage(cnt[cnt["stand"] == s2], list(ars["pitch_type"])), config=PLOT_CONFIG, key="p_counts")
    tun = data.table("tunnels")
    tun = tun[(tun["pitcher"] == pid) & (tun["game_year"] == yr)].sort_values("ratio", ascending=False)
    if len(tun):
        st.markdown(f"#### {L('Best tunnels', '最佳隧道組合')}")
        ui.ledger(tun.head(8), [
            (L("Sequence", "順序"), "seq", lambda r: f"{ui.pitch_chip(r['prev_type'])} → {ui.pitch_chip(r['pitch_type'])}"),
            (L("Pairs", "次數"), "n", lambda r: f"{int(r['n'])}"),
            (L("Apart at commit", "決策點距離"), "t", lambda r: f"{r['tunnel_in']:.1f}″"),
            (L("Apart at plate", "本壘距離"), "p", lambda r: f"{r['plate_in']:.1f}″"),
            (L("Break : tunnel", "分離比"), "ratio", lambda r: f"<b>{r['ratio']:.2f}</b>"),
            (L("Rank", "排名"), "pc", lambda r: ui.diamond(r["ratio_pctl"], 16)),
        ])
        st.caption(L("Back-to-back pitches of different types in the same at-bat. A high break-to-tunnel ratio means the two looked alike "
                     "when the hitter had to decide and ended up far apart.",
                     "同一打席中連續兩球不同球種。分離比高 = 打者決策時兩球看起來很像，最後卻相距很遠。"))
with t3:
    pick = st.segmented_control(L("Pitch", "球種"), list(ars["pitch_type"]), default=ars["pitch_type"].iloc[0],
                                format_func=pitch_name, key="shap_pt") or ars["pitch_type"].iloc[0]
    r = ars[ars["pitch_type"] == pick].iloc[0]
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.plotly_chart(charts.shap_bars(r, {k: L(*v) for k, v in FEATURE_LABELS.items()}), config=PLOT_CONFIG, key="p_shap")
    with c2:
        st.html(f'<div class="stat">{r["stuff_plus"]:.0f} <small>Stuff+</small></div>')
        st.markdown(L("Bars show how much each physical trait moves this pitch's expected run value compared with an average pitch, "
                      "according to the model (SHAP values). Red helps the pitcher.",
                      "長條顯示每項物理特性讓這種球的預期失分價值相對一般球改變多少（模型的 SHAP 值）。紅色代表對投手有利。"))
        st.page_link("app_pages/methods.py", label=L("How Stuff+ is built →", "Stuff+ 怎麼建的 →"))
with t4:
    mon = data.table("monthly")
    mon = mon[(mon["pitcher"] == pid) & (mon["game_year"] == yr)]
    metric = st.segmented_control(L("Metric", "指標"), ["velo", "ivb", "hb", "spin", "stuff_plus"], default="velo", key="mon_m",
                                  format_func={"velo": L("Velocity", "球速"), "ivb": "IVB", "hb": "HB", "spin": L("Spin", "轉速"),
                                               "stuff_plus": "Stuff+"}.get) or "velo"
    if len(mon):
        st.plotly_chart(charts.monthly(mon, metric, metric.upper() if metric != "stuff_plus" else "Stuff+"), config=PLOT_CONFIG, key="p_mon")

ui.footer()
