import numpy as np
import pandas as pd
import streamlit as st

from deeppitch import components as ui, data
from deeppitch.i18n import L, pitch_name
from deeppitch.theme import INK, RED, pitch_color

st.html(f'<div class="mast"><div><h1 class="title">{ui.esc(L("Leaders", "排行榜"))}</h1>'
        f'<p class="lede">{ui.esc(L("Rank any pitch type by any physical trait or result. Every metric shows how strongly it relates to whiffs, so you know whether a leaderboard means anything.", "依任何物理特性或成績替任何球種排名。每個指標都附上它和揮空率的關聯強度，讓你知道這個排行榜有沒有意義。"))}</p></div></div>')

METRICS = {
    "stuff_plus": (L("Stuff+", "Stuff+"), False, ".0f", "", L("Model grade of the ball's physics alone. 100 = average, 110 = one standard deviation better.", "只看球本身物理的模型評分。100 = 平均，110 = 好一個標準差。")),
    "velo": (L("Velocity", "球速"), False, ".1f", " mph", L("Average release speed.", "平均出手球速。")),
    "ivb": (L("Induced vertical break", "誘發垂直位移 IVB"), False, ".1f", "″", L("Rise against a spinless path. High for four-seamers, very negative for curveballs.", "相對無旋轉路徑的上竄。四縫線越高越好，曲球則越負越好。")),
    "ivb_low": (L("Most drop (IVB, lowest)", "最大下墜（IVB 最低）"), True, ".1f", "″", L("For curveballs, splitters and sinkers, more drop is the point.", "對曲球、指叉、伸卡來說，下墜越多越好。")),
    "hb_abs": (L("Horizontal break (size)", "水平位移幅度"), False, ".1f", "″", L("Total sideways movement, either direction.", "不分方向的總水平位移。")),
    "vaa_aa": (L("Flattest approach (location-adjusted)", "最平的進壘角（位置校正）"), False, ".2f", "°", L("VAA compared with what's normal at that height in the zone. The fair way to compare approach angle.", "和同一進壘高度的平均 VAA 比較，才是公平的進壘角比較方式。")),
    "spin": (L("Spin rate", "轉速"), False, ".0f", " rpm", L("Total spin, useful and not.", "總轉速，不分有效無效。")),
    "spin_eff": (L("Spin efficiency", "旋轉效率"), False, ".0%", "", L("Share of spin that bends the ball. Gyro spin (bullet spin) bends nothing.", "會讓球轉彎的那部分旋轉比例。陀螺旋轉（子彈旋）不會造成位移。")),
    "ssw_abs": (L("Seam-shifted wake (size)", "縫線偏移尾流幅度"), False, ".0f", "°", L("How far movement points away from the spin axis. Seams steering the ball.", "實際位移偏離轉軸預測的角度。縫線在駕駛這顆球。")),
    "ext": (L("Extension", "延伸距離"), False, ".2f", " ft", L("How far in front of the rubber the ball is released.", "出手點在投手板前多遠。")),
    "whiff_pct": (L("Whiff rate", "揮空率"), False, ".1f", "%", L("Misses per swing.", "每次揮棒的揮空比例。")),
    "chase_pct": (L("Chase rate", "追打率"), False, ".1f", "%", L("Swings at pitches outside the zone.", "好球帶外的出棒比例。")),
    "csw_pct": (L("Called + swinging strikes", "CSW 率"), False, ".1f", "%", L("Called strikes plus whiffs per pitch.", "每球被判好球或揮空的比例。")),
    "rv100": (L("Run value / 100 pitches", "每百球失分價值"), False, "+.2f", "", L("Runs saved per 100 pitches, from Statcast run expectancy. + is good for the pitcher.", "依 Statcast 得分期望值，每百球替投手省下的分數。+ 對投手有利。")),
}

seasons = data.seasons()
c1, c2, c3, c4 = st.columns([1.1, 1.4, 2.2, 1.2], vertical_alignment="bottom")
with c1:
    yr = st.selectbox(L("Season", "賽季"), seasons[::-1])
with c2:
    pts = ["FF", "SI", "FC", "SL", "ST", "CU", "KC", "CH", "FS"]
    pt = st.selectbox(L("Pitch type", "球種"), pts, format_func=pitch_name)
with c3:
    metric = st.selectbox(L("Rank by", "排名依據"), list(METRICS), format_func=lambda m: METRICS[m][0])
with c4:
    min_n = st.number_input(L("Min. pitches", "最少球數"), 50, 1500, 250, step=50)

a = data.table("arsenal")
a = a[(a["game_year"] == yr) & (a["pitch_type"] == pt) & (a["n"] >= min_n)].copy()
a["hb_abs"] = a["hb"].abs()
a["ssw_abs"] = a["ssw_deg"].abs()
a["ivb_low"] = a["ivb"]
p = data.table("pitchers")[["pitcher", "game_year", "name", "team", "hand"]]
a = a.merge(p, on=["pitcher", "game_year"], how="left")

label, asc, fmt, unit, desc = METRICS[metric]
col = metric
top = a.sort_values(col, ascending=asc).head(25).reset_index(drop=True)
top["rank"] = np.arange(1, len(top) + 1)

corr = data.table("correlations")
rkey = {"ivb_low": "ivb", "hb_abs": "hb", "ssw_abs": "ssw_deg"}.get(metric, metric)
rr = corr[(corr["pitch_type"] == pt) & (corr["metric"] == rkey)]
st.markdown(f"### {pitch_name(pt)} · {label} · {yr}")
st.caption(desc + "  " + (L(f"Across {pitch_name(pt).lower()}s with 200+ pitches, this metric's correlation with whiff rate is r = {rr['r_whiff'].iat[0]:+.2f}.",
                             f"在 200 球以上的{pitch_name(pt)}中，這個指標和揮空率的相關係數為 r = {rr['r_whiff'].iat[0]:+.2f}。")
                           if len(rr) and metric not in ("whiff_pct",) else ""))
st.caption(L(f"{len(a):,} qualifying pitchers.", f"共 {len(a):,} 位符合門檻的投手。"))

if top.empty:
    st.info(L("Nobody qualifies. Lower the minimum.", "沒有人符合門檻，請降低最少球數。"))
else:
    vals = top[col].astype(float)
    lo, hi = float(np.nanmin(vals)), float(np.nanmax(vals))
    span = (hi - lo) or 1.0

    def bar(r):
        v = float(r[col])
        w = 10 + 110 * ((v - lo) / span if not asc else (hi - v) / span)
        disp = format(v, fmt) + unit
        return f'<span class="bar" style="width:{w:.0f}px;background:{pitch_color(pt)}"></span><b>{disp}</b>'

    cols = [
        ("#", "rank", lambda r: f'<span class="rk">{r["rank"]}</span>', "l"),
        (L("Pitcher", "投手"), "name", lambda r: f'<a href="./pitcher?id={int(r["pitcher"])}" target="_self">{ui.esc(r["name"])}</a> '
                                                  f'<span class="sub">{ui.esc(r["team"])} · {r["hand"]}HP</span>', "l"),
        (label, col, bar, "l"),
        (L("Pitches", "球數"), "n", lambda r: f'{int(r["n"]):,}'),
        (L("Velo", "球速"), "x_velo", lambda r: ui.num(r["velo"])),
        ("IVB", "x_ivb", lambda r: ui.num(r["ivb"]) + "″"),
        ("HB", "hb", lambda r: ui.num(r["hb"]) + "″"),
        (L("Whiff", "揮空"), "x_w", lambda r: ui.num(r["whiff_pct"]) + "%"),
        ("Stuff+", "x_s", lambda r: f'{ui.num(r["stuff_plus"], 0)} {ui.diamond(r["stuff_plus_pctl"], 16, False)}'),
    ]
    lead = top.iloc[0]
    ui.note(L(f"{lead['name']} leads {len(a):,} qualifiers: {format(float(lead[col]), fmt)}{unit}.",
              f"{lead['name']} 在 {len(a):,} 位符合者中排第一：{format(float(lead[col]), fmt)}{unit}。"))
    drop = {"stuff_plus": "x_s", "velo": "x_velo", "whiff_pct": "x_w", "ivb": "x_ivb", "ivb_low": "x_ivb"}.get(metric)
    ui.ledger(top, [c for c in cols if c[1] != drop])
    st.download_button(L("Download this table (CSV)", "下載此表（CSV）"),
                       top[["rank", "name", "team", "hand", col, "n", "velo", "ivb", "hb", "whiff_pct", "stuff_plus"]].to_csv(index=False),
                       file_name=f"deeppitch_{yr}_{pt}_{metric}.csv", mime="text/csv")

st.markdown(f"## {L('Whole-staff leaders', '投手整體排行')}")
c1, c2 = st.columns([1, 1], gap="large")
pp = data.table("pitchers")
pp = pp[(pp["game_year"] == yr) & (pp["n"] >= 1000)]
for col_, (m, title) in zip((c1, c2), [("stuff_plus", L("Highest Stuff+ (1,000+ pitches)", "最高 Stuff+（1,000 球以上）")),
                                       ("whiff_pct", L("Highest whiff rate (1,000+ pitches)", "最高揮空率（1,000 球以上）"))]):
    with col_:
        st.markdown(f"#### {title}")
        t = pp.sort_values(m, ascending=False).head(10).reset_index(drop=True)
        t["rank"] = np.arange(1, len(t) + 1)
        ui.ledger(t, [
            ("#", "rank", lambda r: f'<span class="rk">{r["rank"]}</span>', "l"),
            (L("Pitcher", "投手"), "name", lambda r: f'<a href="./pitcher?id={int(r["pitcher"])}" target="_self">{ui.esc(r["name"])}</a> <span class="sub">{ui.esc(r["team"])}</span>', "l"),
            ("Stuff+", "s", lambda r: f'<b>{r["stuff_plus"]:.0f}</b>' if m == "stuff_plus" else f'{r["stuff_plus"]:.0f}'),
            (L("Whiff", "揮空"), "w", lambda r: f'<b>{r["whiff_pct"]:.1f}%</b>' if m == "whiff_pct" else f'{r["whiff_pct"]:.1f}%'),
            ("K%", "k", lambda r: f'{r["k_pct"]:.1f}%'),
        ])

st.markdown(f"## {L('Best tunnels in baseball', '全聯盟最佳隧道組合')}")
st.caption(L("Consecutive pitches of different types (25+ pairs). Ranked by how far apart they finish relative to how close they were at the commit point.",
             "同一打席中連續的不同球種（至少 25 組），依「到本壘的分離距離 ÷ 決策點的距離」排名。"))
tun = data.table("tunnels")
tun = tun[(tun["game_year"] == yr) & (tun["n"] >= 25)].merge(p, on=["pitcher", "game_year"], how="left")
tt = tun.sort_values("ratio", ascending=False).head(12).reset_index(drop=True)
tt["rank"] = np.arange(1, len(tt) + 1)
ui.ledger(tt, [
    ("#", "rank", lambda r: f'<span class="rk">{r["rank"]}</span>', "l"),
    (L("Pitcher", "投手"), "name", lambda r: f'<a href="./pitcher?id={int(r["pitcher"])}" target="_self">{ui.esc(r["name"])}</a>', "l"),
    (L("Sequence", "順序"), "seq", lambda r: f"{ui.pitch_chip(r['prev_type'])} → {ui.pitch_chip(r['pitch_type'])}", "l"),
    (L("At commit", "決策點"), "t", lambda r: f"{r['tunnel_in']:.1f}″"),
    (L("At plate", "本壘"), "pl", lambda r: f"{r['plate_in']:.1f}″"),
    (L("Ratio", "分離比"), "ratio", lambda r: f"<b>{r['ratio']:.2f}</b>"),
    (L("Pairs", "次數"), "n", lambda r: f"{int(r['n'])}"),
])
ui.footer()
