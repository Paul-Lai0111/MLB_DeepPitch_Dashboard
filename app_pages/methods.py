import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from deeppitch import components as ui, data
from deeppitch.features import FEATURE_LABELS
from deeppitch.i18n import L, pitch_name
from deeppitch.theme import COND, INK, MUTED, PLOT_CONFIG, RED

meta = data.meta()
rep = data.model_report()
val = rep["validity"]

st.html(f'<div class="mast"><div><h1 class="title">{ui.esc(L("Methods", "方法與模型"))}</h1>'
        f'<p class="lede">{ui.esc(L("How the numbers are made, how they were checked, and where they stop being trustworthy.", "這些數字怎麼來、怎麼驗證，以及在哪裡開始不可靠。"))}</p></div></div>')

ui.line([(L("Pitches", "投球"), f"{meta['pitches']:,}", None), (L("Pitchers", "投手"), f"{meta['pitchers']:,}", None),
         (L("Seasons", "賽季"), f"{meta['seasons'][0]}–{meta['seasons'][-1]}", None), (L("Last game", "最後一場"), meta["last_game"], None),
         (L("Unit tests", "單元測試"), "9", L("physics", "物理"))])

st.markdown(f"## {L('Pipeline', '資料管線')}")
st.graphviz_chart(f"""
digraph G {{
  rankdir=LR; bgcolor="transparent"; nodesep=0.35; ranksep=0.45;
  node [shape=box, style="rounded", color="#26292B", fontname="Barlow", fontsize=12, fontcolor="#26292B", penwidth=1.2];
  edge [color="#2E6A4E", penwidth=1.3, arrowsize=0.7];
  a [label="Baseball Savant\\n(pybaseball, 6-day chunks)"];
  b [label="fetch.py\\nraw parquet per season"];
  c [label="features.py\\nclean · physics engine\\nlocation-adjusted VAA"];
  d [label="model.py\\nLightGBM Stuff+\\nleave-one-season-out\\nSHAP"];
  e [label="aggregate.py\\ncompact parquet tables\\n(~17 MB)"];
  f [label="Streamlit app\\nscorebook UI", color="#C7352B", fontcolor="#C7352B"];
  a -> b -> c -> d -> e -> f;
}}""", use_container_width=True)
st.markdown(L("""
1. **Fetch.** Every pitch from Baseball Savant in six-day windows, retried on failure. Spring training, exhibitions and the All-Star Game are dropped.
2. **Clean.** Pitch-outs, intentional balls and position players' generic "fastballs" removed; pitches without full tracking (trajectory, spin axis, extension) dropped; duplicates removed on `game_pk, at_bat_number, pitch_number`.
3. **Physics.** Each pitch's trajectory is reconstructed from Statcast's 9-parameter fit, anchored at the measured plate location. From it: approach angles at the front of the plate, flight time, Magnus acceleration, spin efficiency, seam-shifted wake, positions at the commit point.
4. **Model.** Stuff+ (below).
5. **Aggregate.** Per pitcher × season × pitch type: averages, percentiles within the pitch type, a 60-pitch sample for plots, the most typical pitch for the flight animation, location grids, count usage, tunnel pairs, monthly trends.
""", """
1. **擷取。** 以每 6 天為一段從 Baseball Savant 抓取每一球，失敗會重試。排除春訓、熱身賽與明星賽。
2. **清理。** 移除故意四壞、Pitchout、野手投球的通用「速球」；缺少完整追蹤（軌跡、轉軸、延伸）的球剔除；以 `game_pk, at_bat_number, pitch_number` 去重。
3. **物理。** 由 Statcast 的 9 參數擬合重建每一球的軌跡，並以實測進壘位置定錨。算出：本壘前緣的進壘角度、飛行時間、馬格努斯加速度、旋轉效率、縫線偏移尾流、決策點位置。
4. **模型。** Stuff+（見下）。
5. **彙整。** 每位投手 × 賽季 × 球種：平均值、同球種百分位、60 球繪圖樣本、動畫用的最典型一球、進壘網格、球數配球、隧道組合、月趨勢。
"""))

st.markdown(f"## {L('Physics checked against public benchmarks', '物理數值與公開基準比對')}")
lg = data.table("league")
y = meta["seasons"][-1]
b = lg[lg["game_year"] == y].set_index("pitch_type")
ui.ledger(pd.DataFrame([
    ("FF", "IVB", f"{b.loc['FF', 'ivb']:.1f}″", "15–17″"),
    ("FF", "VAA", f"{b.loc['FF', 'vaa']:.1f}°", L("about −4.5° to −5°", "約 −4.5° 至 −5°")),
    ("SI", "HB", f"{b.loc['SI', 'hb']:.1f}″", "14–16″"),
    ("ST", "HB", f"{b.loc['ST', 'hb']:.1f}″", L("−13 to −15″", "−13 至 −15″")),
    ("CU", "IVB", f"{b.loc['CU', 'ivb']:.1f}″", L("−9 to −11″", "−9 至 −11″")),
    ("FF", L("Flight time", "飛行時間"), f"{b.loc['FF', 'flight_time'] * 1000:.0f} ms", "≈400 ms"),
    ("FF", L("Perceived velo", "體感球速"), f"{b.loc['FF', 'eff_velo']:.1f} mph", L(f"release {b.loc['FF', 'velo']:.1f} mph", f"出手 {b.loc['FF', 'velo']:.1f} mph")),
], columns=["pt", "m", "ours", "ref"]), [
    (L("Pitch", "球種"), "pt", lambda r: ui.pitch_chip(r["pt"])),
    (L("Metric", "指標"), "m", lambda r: ui.esc(r["m"])),
    (f"DeepPitch {y}", "ours", lambda r: f"<b>{r['ours']}</b>"),
    (L("Typical published range", "常見公開數值範圍"), "ref", lambda r: ui.esc(r["ref"])),
])
st.markdown(f"#### {L('Corrections from DeepPitch v1', '相較第一版的修正')}")
st.markdown(L("""
- **Perceived velocity** used `v × 60.5 / (60.5 − extension)`, giving a 105 mph league average. Replaced by Statcast's measured effective speed.
- **Seam-shifted wake** was the distance between observed movement and a spin-rate model, which mostly measured gyro spin (sliders scored highest). Now it is the angle between the measured spin axis and the movement direction, the way the research community defines it.
- **Tunneling** subtracted gravity from an acceleration that already contained it, started the ball at the wrong point, and paired pitches in arbitrary order. Now: correct kinematics, real pitch order, different pitch types only, measured at the commit point and at the plate.
- **Spin efficiency** was averaged across all pitch types, which ranked fastball-heavy relievers first by construction. Now ranked within pitch type only.
- **Horizontal break** is mirrored for left-handers so arsenals compare on one scale.
""", """
- **體感球速**原本用 `v × 60.5 / (60.5 − 延伸)`，算出聯盟平均 105 mph。改用 Statcast 實測的 effective speed。
- **縫線偏移尾流**原本是實際位移與轉速模型的距離，主要量到的是陀螺旋轉（滑球分數最高）。現在改為實測轉軸與位移方向的夾角，與研究社群的定義一致。
- **隧道效應**原本對已含重力的加速度又減一次重力、起點錯誤、配對順序隨機。現在：正確運動學、真實投球順序、只配對不同球種，在決策點與本壘各量一次。
- **旋轉效率**原本跨所有球種平均，結構上就讓速球型後援排第一。現在只在同球種內排名。
- **水平位移**對左投做鏡像，讓所有球路在同一尺度上比較。
"""))

st.markdown(f"## {L('The Stuff+ model', 'Stuff+ 模型')}")
c1, c2 = st.columns([1.1, 1], gap="large")
with c1:
    st.markdown(L(f"""
**Target.** Statcast `delta_run_exp`: the change in expected runs caused by each pitch, sign-flipped so higher is better for the pitcher.

**Inputs.** Only what the ball does: {", ".join(v[0].lower() for v in FEATURE_LABELS.values())}. No location, count or batter, so the grade is about stuff, not command or luck.

**Learner.** LightGBM gradient-boosted trees (31 leaves, 250 rounds, ≥800 pitches per leaf to avoid memorising pitchers).

**Validation.** Leave-one-season-out: each season is graded by a model that never saw it. Every Stuff+ in the app is out-of-sample.

**Scale.** 100 = league average that season; 10 points = one standard deviation across pitcher arsenals.

**Explanations.** Tree SHAP values on a stratified sample (up to 40 pitches per pitcher × pitch type) show which traits drive each grade.
""", f"""
**目標。** Statcast `delta_run_exp`：每一球造成的預期得分變化，正負號反轉讓越高對投手越好。

**輸入。** 只有球本身的表現：{", ".join(v[1] for v in FEATURE_LABELS.values())}。不含進壘位置、球數與打者，所以評的是球質，不是控球或運氣。

**模型。** LightGBM 梯度提升樹（31 葉、250 輪、每葉至少 800 球，避免記住個別投手）。

**驗證。** 留一季交叉驗證：每一季都由「沒看過該季」的模型評分。網站上每個 Stuff+ 都是樣本外的。

**尺度。** 100 = 當季聯盟平均；10 分 = 投手球路之間的一個標準差。

**解釋。** 對分層抽樣（每位投手 × 球種最多 40 球）計算 Tree SHAP 值，說明每個評分由哪些特性驅動。
"""))
with c2:
    imp = pd.DataFrame(rep["importance"])
    imp["label"] = imp["key"].map(lambda k: L(*FEATURE_LABELS[k]))
    imp = imp.sort_values("mean_abs_shap")
    fig = go.Figure(go.Bar(x=imp["mean_abs_shap"] * 100, y=imp["label"], orientation="h", marker=dict(color=INK),
                           hovertemplate="%{y}: %{x:.3f}<extra></extra>"))
    fig.update_layout(height=430, title=L("What the model listens to", "模型在聽什麼"),
                      xaxis=dict(title=L("Mean |SHAP|, runs per 100 pitches", "平均 |SHAP|（每百球分數）")), yaxis=dict(showgrid=False))
    st.plotly_chart(fig, config=PLOT_CONFIG, key="m_imp")

st.markdown(f"### {L('Does it predict the future?', '它能預測未來嗎？')}")
c1, c2 = st.columns([1.2, 1], gap="large")
with c1:
    rows = [(L("Stuff+ this season", "本季 Stuff+"), val["stuff_vs_next_rv100"], True),
            (L("Run value this season", "本季失分價值"), val["rv100_vs_next_rv100"], False),
            (L("Whiff rate this season", "本季揮空率"), val["whiff_rate_vs_next_rv100"], False),
            (L("Max fastball velocity", "最快球速"), val["velo_vs_next_rv100"], False)]
    fig = go.Figure(go.Bar(x=[r[1] for r in rows][::-1], y=[r[0] for r in rows][::-1], orientation="h",
                           marker=dict(color=[RED if r[2] else "#8A9089" for r in rows][::-1]),
                           text=[f"{r[1]:.2f}" for r in rows][::-1], textposition="outside", cliponaxis=False,
                           textfont=dict(family=COND, size=14, color=INK), hovertemplate="%{y}: r = %{x:.2f}<extra></extra>"))
    fig.update_layout(height=280, xaxis=dict(range=[0, 0.6], title=L("Correlation with NEXT season's run value", "與「下一季」失分價值的相關")),
                      yaxis=dict(showgrid=False), margin=dict(r=40))
    st.plotly_chart(fig, config=PLOT_CONFIG, key="m_valid")
with c2:
    st.markdown(L(f"""
Pitchers with 500+ pitches in back-to-back seasons ({val['pairs']} pairs).
Stuff+ is **{val['stuff_year_to_year']:.2f}** correlated with itself year to year, while run value manages only **{val['rv100_year_to_year']:.2f}**: results are noisy, physics is stable.
That stability is why it forecasts next season better than last season's results do.
""", f"""
連續兩季皆投 500 球以上的投手（{val['pairs']} 組）。
Stuff+ 的年對年相關為 **{val['stuff_year_to_year']:.2f}**，失分價值只有 **{val['rv100_year_to_year']:.2f}**：成績很吵，物理很穩。
正因為穩定，它預測下一季比上一季的成績本身還準。
"""))

folds = pd.DataFrame(rep["folds"])
ui.ledger(folds, [
    (L("Held-out season", "測試賽季"), "test_season", lambda r: f"<b>{int(r['test_season'])}</b>"),
    (L("Trained on", "訓練賽季"), "train", lambda r: ", ".join(str(x) for x in r["train_seasons"])),
    (L("Pitch-level r", "逐球相關"), "c", lambda r: f"{r['pitch_level_corr']:.3f}"),
    (L("MSE reduction", "MSE 降低"), "m", lambda r: f"{r['mse_reduction_pct']:.3f}%"),
])
st.caption(L("Pitch-level numbers are tiny by nature: one pitch's run value is mostly noise (a foul ball, a bloop single). Signal appears once pitches are averaged, as the pitcher-level results above show.",
             "逐球的數字天生就很小：單一球的失分價值大多是雜訊（一顆界外、一支德州安打）。把球平均起來後訊號才會出現，如上方投手層級的結果。"))

st.markdown(f"## {L('Limits', '限制')}")
st.markdown(L("""
- Constant-acceleration trajectories (Statcast's own fit) smooth over late movement inside the last few feet.
- Spin efficiency is calibrated to elite four-seamers = 100%; absolute values are an estimate, rankings within a pitch type are the reliable part.
- Seam-shifted wake angles need real movement to be defined; pitches with under 4 inches of total break are excluded.
- Stuff+ ignores command. A pitcher with great stuff and poor location will look better here than on the scoreboard.
- Postseason pitches are included in each season.
""", """
- 等加速度軌跡（Statcast 自己的擬合方式）會把最後幾呎的晚期位移平滑掉。
- 旋轉效率以頂尖四縫線 = 100% 校準；絕對值是估計，同球種內的排名才是可靠的部分。
- 縫線偏移尾流的角度需要足夠位移才有定義；總位移小於 4 吋的球被排除。
- Stuff+ 不看控球。球質很好但位置很差的投手，在這裡會比在比分板上好看。
- 各賽季包含季後賽投球。
"""))

st.markdown(f"## {L('About the author', '關於作者')}")
st.markdown(L("""
**Paul Lai (Hong-Min Lai)** · M.S. in Data Science, University of California, San Diego

DeepPitch is a personal project: data engineering, physics modelling, machine learning and interface design, built end to end.
[paul262935@gmail.com](mailto:paul262935@gmail.com) · [LinkedIn](https://www.linkedin.com/in/paullai0111/) · [GitHub repository](https://github.com/Paul-Lai0111/2024MLB_DeepPitch_Dashboard)

**Stack:** Python · pandas · NumPy · PyArrow · LightGBM (TreeSHAP) · Plotly · Streamlit · pybaseball · pytest.
""", """
**Paul Lai (Hong-Min Lai)** · 加州大學聖地牙哥分校（UCSD）資料科學碩士

DeepPitch 是個人專案：資料工程、物理建模、機器學習與介面設計，從頭到尾獨立完成。
[paul262935@gmail.com](mailto:paul262935@gmail.com) · [LinkedIn](https://www.linkedin.com/in/paullai0111/) · [GitHub](https://github.com/Paul-Lai0111/2024MLB_DeepPitch_Dashboard)

**技術：** Python · pandas · NumPy · PyArrow · LightGBM (TreeSHAP) · Plotly · Streamlit · pybaseball · pytest。
"""))
ui.footer()
