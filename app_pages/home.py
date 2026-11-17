import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from deeppitch import charts, components as ui, data
from deeppitch.icons import icon
from deeppitch.i18n import L, pitch_name
from deeppitch.theme import COND, INK, PLOT_CONFIG, RED

meta = data.meta()
rep = data.model_report()
seasons = meta["seasons"]
latest = seasons[-1]

ui.masthead(
    L("Deep<em>Pitch</em>", "Deep<em>Pitch</em>"),
    L("The physics scorebook of every MLB pitch. Watch the ball fly, see the forces that bend it, "
      "and check whether those forces actually win at-bats.",
      "大聯盟每一球的物理計分簿。看球怎麼飛、是什麼力量讓它轉彎，再驗證這些力量是否真的贏得打席。"),
    [(L("seasons", "賽季"), f"{seasons[0]}–{seasons[-1]}"),
     (L("pitches tracked", "追蹤球數"), f"{meta['pitches'] / 1e6:.2f}M"),
     (L("pitchers", "投手"), f"{meta['pitchers']:,}")],
)

# ---- featured arsenal: Yamamoto (the original DeepPitch default), latest season
pid = data.find_pitcher("Yamamoto") or int(data.pitcher_index().iloc[0]["pitcher"])
yrs = data.pitcher_years(pid)
yr = yrs[0]
ars = data.arsenal(pid, yr)
ars = ars[ars["usage"] >= 4].head(5)
prow = data.pitcher_row(pid, yr)

st.html(f'<span class="note">{ui.esc(L(f"{prow["name"]}, {yr}: every pitch in his arsenal, thrown from the same hand.", f"{prow["name"]}，{yr}：他的每一種球路，從同一隻手投出。"))}</span>')
ui.flight(data.flight_payload(ars, lambda r: f"{pitch_name(r['pitch_type'])} {r['velo']:.0f}"), height=540, autoplay=True,
          key="home_flight")
st.markdown(L(
    "**Press Throw at ⅒ speed.** Every pitch leaves the hand on almost the same line. The dashed red mark is the "
    "**commit point**, 175 milliseconds before the plate: the last moment a hitter can still start or stop a swing. "
    "Everything that separates the pitches after that line is movement the hitter has to guess.",
    "**用 ⅒ 速按「投球」。** 每一球幾乎都從同一條線離手。紅色虛線是**出棒決策點**，球到本壘前 175 毫秒，"
    "打者最後還能決定揮或不揮的時刻。過了這條線之後才分開的位移，打者只能用猜的。"))

st.markdown(f"### {L('The flight folio', '飛行圖鑑')}")
st.caption(L("The same pitches at four instants, drawn at the same scale from the catcher's seat. "
             "Bunched at the commit point, split at the plate: that gap is deception.",
             "同一批球在四個瞬間的位置，以同比例從捕手視角繪製。在決策點擠在一起、到本壘才分開，那個落差就是欺騙性。"))
st.plotly_chart(charts.folio(ars), config=PLOT_CONFIG, key="home_folio")

# ---- search
st.markdown(f"## {L('Look up any pitcher', '查詢任何投手')}")
idx = data.pitcher_index()
labels = data.pitcher_labels()
c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
with c1:
    pick = st.selectbox(L("Pitcher", "投手"), list(labels), format_func=labels.get, index=None,
                        placeholder=L(f"Type a name — {len(labels):,} pitchers, {seasons[0]}–{seasons[-1]}",
                                      f"輸入姓名 — 共 {len(labels):,} 位投手，{seasons[0]}–{seasons[-1]}"))
with c2:
    open_btn = st.button(L("Open scorecard", "開啟計分卡"), type="primary", use_container_width=True, disabled=pick is None)
if open_btn and pick is not None:
    st.session_state["pitcher"] = pick
    st.session_state["pitcher_select"] = pick
    st.query_params["id"] = str(pick)
    st.switch_page("app_pages/pitcher.py")

# ---- findings, with the real numbers
corr = data.table("correlations")
ff = corr[corr["pitch_type"] == "FF"].set_index("metric")
league = data.table("league")
usage = league.pivot(index="pitch_type", columns="game_year", values="usage")
ars_all = data.table("arsenal")
si_ssw = ars_all[(ars_all["pitch_type"] == "SI") & (ars_all["n"] >= 300)]["ssw_deg"].median()
val = rep["validity"]

st.markdown(f"## {L('Three things the data says', '數據告訴我們的三件事')}")
cols = st.columns(3, gap="large")


def mini_bars(labels, values, highlight, fmt="{:+.2f}", rng=None):
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker=dict(color=[RED if h else "#8A9089" for h in highlight]),
                           text=[fmt.format(v) for v in values], textposition="outside", cliponaxis=False,
                           textfont=dict(family=COND, size=14, color=INK), hoverinfo="skip"))
    fig.update_layout(height=150, margin=dict(l=4, r=36, t=4, b=4), xaxis=dict(visible=False, range=rng),
                      yaxis=dict(showgrid=False, autorange="reversed", ticks=""), bargap=.35)
    return fig


ssw_by = (ars_all[(ars_all["n"] >= 300) & ars_all["pitch_type"].isin(["SI", "ST", "FC", "FF"])]
          .groupby("pitch_type")["ssw_deg"].median().reindex(["SI", "ST", "FC", "FF"]))
findings = [
    (L("A pitcher's rise alone doesn't predict his whiffs", "投手的平均上竄，單獨預測不了揮空"),
     L(f"Across {int(ff.loc['ivb', 'n_arsenals']):,} pitcher-season four-seamers, average induced vertical break barely relates to whiff rate. "
       "Approach angle does: rise pays off when the ball also arrives flat.",
       f"在 {int(ff.loc['ivb', 'n_arsenals']):,} 組投手賽季的四縫線中，平均 IVB 和揮空率幾乎無關；進壘角度才有關：上竄要搭配平的進壘角才會有效。"),
     mini_bars([L("Approach angle", "進壘角度"), L("Velocity", "球速"), "IVB"],
               [ff.loc["vaa", "r_whiff"], ff.loc["velo", "r_whiff"], ff.loc["ivb", "r_whiff"]], [True, False, False], rng=[-0.1, 0.6]),
     L("correlation with whiff rate, four-seamers", "與揮空率的相關，四縫線"), "app_pages/insights.py"),
    (L("Sinkers move where spin says they can't", "伸卡球往旋轉解釋不了的方向跑"),
     L("Movement points this many degrees away from where the measured spin axis says it should go. "
       "That gap is seam-shifted wake: the seams, not the spin, steer the ball.",
       "實際位移方向和實測轉軸預測的方向差了這麼多度。這個落差就是縫線偏移尾流：是縫線、不是旋轉，在駕駛這顆球。"),
     mini_bars([pitch_name(p) for p in ssw_by.index], ssw_by.abs().tolist(), [p in ("SI", "ST") for p in ssw_by.index],
               fmt="{:.0f}°", rng=[0, 40]),
     L("typical seam-shifted wake, degrees", "典型縫線偏移尾流（度）"), "app_pages/guide.py"),
    (L("Stuff predicts next year better than results", "球質比成績更能預測明年"),
     L(f"How well each number from this season predicts a pitcher's run value next season ({val['pairs']} pitcher pairs). "
       "Physics is stable; results are noisy.",
       f"本季各數字預測投手下一季失分價值的能力（{val['pairs']} 組投手）。物理很穩定，成績很吵。"),
     mini_bars([L("Stuff+", "Stuff+"), L("Whiff rate", "揮空率"), L("Run value", "失分價值")],
               [val["stuff_vs_next_rv100"], val["whiff_rate_vs_next_rv100"], val["rv100_vs_next_rv100"]], [True, False, False],
               rng=[0, 0.6]),
     L("correlation with next season's run value", "與下一季失分價值的相關"), "app_pages/methods.py"),
]
for i, (col, (h, body, fig, cap, page)) in enumerate(zip(cols, findings)):
    with col:
        st.html(f'<div class="finding"><h4>{ui.esc(h)}</h4><p>{ui.esc(body)}</p></div>')
        st.plotly_chart(fig, config=PLOT_CONFIG, key=f"find_{i}")
        st.caption(cap)
        st.page_link(page, label=L("Show me the evidence →", "看證據 →"))

st.markdown(f"## {L('What changed, season to season', '每個賽季的變化')}")
mix = ["ST", "SL", "SI", "FF", "CH", "FC", "CU", "FS"]


def delta_cell(v):
    color = RED if abs(v) >= 1 else INK
    return f'<b style="color:{color}">{v:+.1f}</b>'


rows = pd.DataFrame({"pt": mix})
ui.ledger(rows, [(L("Share of all pitches", "占全部投球"), "pt", lambda r: ui.pitch_chip(r["pt"]), "l")]
          + [(str(y), str(y), (lambda yy: lambda r: f'{usage.loc[r["pt"], yy]:.1f}%')(y)) for y in seasons]
          + [(L(f"Δ since {seasons[0]}", f"相較 {seasons[0]}"), "d",
              lambda r: delta_cell(usage.loc[r["pt"], latest] - usage.loc[r["pt"], seasons[0]]))])
ffv = league[league["pitch_type"] == "FF"].set_index("game_year")["velo"]
ui.note(L(f"Sweepers keep eating the slider's share. Four-seam velo {ffv.loc[seasons[0]]:.1f} → {ffv.loc[latest]:.1f} mph.",
          f"橫掃球持續吃掉滑球的比例。四縫線均速 {ffv.loc[seasons[0]]:.1f} → {ffv.loc[latest]:.1f} mph。"))

st.markdown(f"## {L('Index', '目錄')}")
ui.ledger(pd.DataFrame([
    ("app_pages/pitcher.py", L("Pitchers", "投手"), L("Any pitcher's arsenal, flight, movement, locations, sequencing and model grades", "任何投手的球路、軌跡、位移、進壘位置、配球與模型評分")),
    ("app_pages/compare.py", L("Compare", "比較"), L("Two to four pitchers side by side, same pitch overlaid in flight", "二到四位投手並排比較，同球種飛行軌跡疊圖")),
    ("app_pages/leaders.py", L("Leaders", "排行榜"), L("Rank any pitch type by any metric, with minimums you control", "依任何指標替任何球種排名，門檻自訂")),
    ("app_pages/lab.py", L("Physics Lab", "物理實驗室"), L("Build a pitch from spin, axis and release and watch what it does", "用轉速、轉軸、出手點自己做一顆球，看它怎麼飛")),
    ("app_pages/guide.py", L("Field Guide", "指標圖鑑"), L("Every metric explained in plain language, equations on demand", "每個指標的白話解釋，想看公式再展開")),
    ("app_pages/insights.py", L("Does It Matter?", "真的有用嗎？"), L("Which physical traits actually turn into whiffs and runs saved", "哪些物理特性真的轉化為揮空與失分減少")),
    ("app_pages/methods.py", L("Methods", "方法與模型"), L("Pipeline, physics validation, the Stuff+ model and its limits", "資料管線、物理驗證、Stuff+ 模型與其限制")),
], columns=["page", "name", "what"]).assign(ic=["stuff", "tunnel", "ivb", "forces", "spin", "vaa", "commit"]), [
    ("", "ic", lambda r: icon(r["ic"], 24), "l"),
    (L("Page", "頁面"), "name", lambda r: f'<a href="./{r["page"].split("/")[1][:-3]}" target="_self"><b>{ui.esc(r["name"])}</b></a>', "l"),
    (L("What it answers", "能回答什麼"), "what", lambda r: ui.esc(r["what"]), "l"),
])
ui.footer()
