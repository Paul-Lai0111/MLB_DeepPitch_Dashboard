import pandas as pd
import streamlit as st

from deeppitch import charts, components as ui, data
from deeppitch.i18n import L, pitch_name
from deeppitch.theme import PLOT_CONFIG

# Entity colours for pitchers (fixed order, validated categorical set, never cycled).
PITCHER_INKS = ["#C7352B", "#2350A0", "#3C8D3F", "#7B4FA6"]

st.html(f'<div class="mast"><div><h1 class="title">{ui.esc(L("Compare", "比較"))}</h1>'
        f'<p class="lede">{ui.esc(L("Put up to four pitchers on the same page. Pick a pitch type to fly them side by side.", "最多四位投手放在同一頁。選一個球種，讓他們的球並排飛行。"))}</p></div></div>')

labels = data.pitcher_labels()
defaults = [x for x in (data.find_pitcher("Yamamoto"), data.find_pitcher("Skubal"), data.find_pitcher("Skenes")) if x]
c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
with c1:
    chosen = st.multiselect(L("Pitchers", "投手"), list(labels), default=defaults, format_func=labels.get, max_selections=4)
seasons = data.seasons()
with c2:
    yr = st.selectbox(L("Season", "賽季"), seasons[::-1])

if not chosen:
    st.info(L("Pick at least one pitcher to start.", "請至少選一位投手。"))
    st.stop()

ars_all = data.table("arsenal")
ars_all = ars_all[(ars_all["game_year"] == yr) & (ars_all["pitcher"].isin(chosen))]
missing = [labels[c] for c in chosen if c not in set(ars_all["pitcher"])]
if missing:
    st.caption(L("No data that season for: ", "該賽季無資料：") + ", ".join(missing))
chosen = [c for c in chosen if c in set(ars_all["pitcher"])]
names = {c: labels[c].split(" · ")[0] for c in chosen}
ink = {c: PITCHER_INKS[i] for i, c in enumerate(chosen)}

pts = [pt for pt in ["FF", "SI", "FC", "SL", "ST", "CU", "KC", "CH", "FS"] if pt in set(ars_all["pitch_type"])]
if not pts:
    st.stop()
pt = st.segmented_control(L("Pitch type", "球種"), pts, default=pts[0], format_func=pitch_name, key="cmp_pt") or pts[0]

rows = ars_all[ars_all["pitch_type"] == pt].copy()
rows["who"] = rows["pitcher"].map(names)
flights = []
for c in chosen:
    r = rows[rows["pitcher"] == c]
    if r.empty:
        continue
    f = data.flight_payload(r, lambda x: f"{names[c]} · {x['velo']:.0f}")
    for item in f:
        item["color"] = ink[c]
    flights += f
st.markdown(f"## {pitch_name(pt)}")
ui.flight(flights, key="cmp_flight")

ui.ledger(rows.sort_values("stuff_plus", ascending=False), [
    (L("Pitcher", "投手"), "who", lambda r: f'<span class="pt"><span class="dot" style="border-color:{ink[int(r["pitcher"])]}"></span>{ui.esc(r["who"])}</span>'),
    (L("Usage", "使用率"), "u", lambda r: ui.num(r["usage"], 0, "%")),
    (L("Velo", "球速"), "v", lambda r: f"{ui.num(r['velo'])} {ui.diamond(r['velo_pctl'], 16, False)}"),
    (L("Ext.", "延伸"), "e", lambda r: ui.num(r["ext"], 1)),
    (L("Spin", "轉速"), "s", lambda r: ui.num(r["spin"], 0)),
    (L("Eff.", "效率"), "ef", lambda r: ui.num(r["spin_eff"] * 100, 0, "%")),
    ("IVB", "i", lambda r: f"{ui.num(r['ivb'])}″ {ui.diamond(r['ivb_pctl'], 16, False)}"),
    ("HB", "h", lambda r: f"{ui.num(r['hb'])}″"),
    (L("VAA vs loc.", "位置校正 VAA"), "va", lambda r: f"{ui.num(r['vaa_aa'], 2)}°"),
    ("SSW", "ss", lambda r: f"{ui.num(r['ssw_deg'], 0)}°"),
    (L("Whiff", "揮空"), "w", lambda r: f"{ui.num(r['whiff_pct'])}%"),
    ("Stuff+", "st", lambda r: f"<b>{ui.num(r['stuff_plus'], 0)}</b> {ui.diamond(r['stuff_plus_pctl'], 16, False)}"),
])

st.markdown(f"## {L('Full arsenals', '完整球路')}")
sample = data.table("sample")
dens = data.table("league_density")
dens = dens[dens["game_year"] == yr]
cols = st.columns(2, gap="large")
for i, c in enumerate(chosen):
    a = ars_all[ars_all["pitcher"] == c].sort_values("usage", ascending=False)
    smp = sample[(sample["pitcher"] == c) & (sample["game_year"] == yr)]
    with cols[i % 2]:
        st.plotly_chart(charts.movement(smp, a, dens, height=440, title=names[c]), config=PLOT_CONFIG, key=f"cmp_mv_{c}")
ui.footer()
