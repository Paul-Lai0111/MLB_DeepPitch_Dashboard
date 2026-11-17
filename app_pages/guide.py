import streamlit as st

from deeppitch import charts, components as ui, data
from deeppitch.i18n import L, pitch_name
from deeppitch.icons import icon
from deeppitch.theme import PLOT_CONFIG

st.html(f'<div class="mast"><div><h1 class="title">{ui.esc(L("Field Guide", "指標圖鑑"))}</h1>'
        f'<p class="lede">{ui.esc(L("Every number DeepPitch shows, explained in plain language: what it is, what causes it, what is typical, and whether it actually matters. Equations wait behind each entry for when you want them.", "DeepPitch 的每個數字都用白話說明：它是什麼、成因、常見數值、到底有沒有用。想看公式時再展開。"))}</p></div></div>')

ins = data.table("insights")
corr = data.table("correlations")
lg = data.table("league")
yr = data.seasons()[-1]
lgy = lg[lg["game_year"] == yr].set_index("pitch_type")


def r_of(pt, m):
    x = corr[(corr["pitch_type"] == pt) & (corr["metric"] == m)]
    return f"{x['r_whiff'].iat[0]:+.2f}" if len(x) else "—"


def typical(metric, pts, fmt="{:.1f}", unit=""):
    return " · ".join(f"{pitch_name(p)} {fmt.format(lgy.loc[p, metric])}{unit}" for p in pts if p in lgy.index)


toc = [("ivb", "IVB"), ("hb", L("Horizontal break", "水平位移")), ("vaa", L("Approach angle", "進壘角度")),
       ("spin", L("Spin efficiency", "旋轉效率")), ("ssw", L("Seam-shifted wake", "縫線偏移尾流")),
       ("tunnel", L("Tunneling", "隧道效應")), ("ext", L("Extension & perceived velocity", "延伸與體感球速")),
       ("arm", L("Arm angle", "手臂角度")), ("stuff", "Stuff+"), ("forces", L("The forces, in depth", "力學深入"))]
st.html('<div class="legend-row">' + "".join(f'<span>{icon({"forces": "forces"}.get(k, k if k in ("ivb","hb","vaa","spin","ssw","tunnel","ext","arm","stuff") else "forces"), 20)}'
                                           f'<a href="#{k}" style="color:inherit">{ui.esc(v)}</a></span>' for k, v in toc) + "</div>")


ICON_FOR = {"ivb": "ivb", "hb": "hb", "vaa": "vaa", "spin": "spin", "ssw": "ssw", "tunnel": "tunnel", "ext": "ext",
            "arm": "arm", "stuff": "stuff"}


def entry(anchor, title, rows, chart=None, math=None, caption=None):
    st.html(f'<div class="entry-head" id="{anchor}">{icon(ICON_FOR.get(anchor, "forces"), 40, title)}<h2>{ui.esc(title)}</h2></div>')
    c1, c2 = st.columns([1.15, 1], gap="large")
    with c1:
        ui.facts(rows)
        if math:
            with st.expander(L("Show the math", "看公式")):
                st.markdown(math)
    with c2:
        if chart is not None:
            st.plotly_chart(chart, config=PLOT_CONFIG, key=f"g_{anchor}")
            if caption:
                st.caption(caption)


W = L("Whiff rate, %", "揮空率 %")

entry("ivb", L("IVB · Induced vertical break", "IVB · 誘發垂直位移"), [
    (L("What it is", "是什麼"), L("How many inches a pitch finishes above (or below) where a spinless ball thrown the same way would land. Gravity is taken out, so only spin's effect remains.",
                                "球最後比「同樣出手但不旋轉的球」高（或低）多少吋。重力已扣除，只剩旋轉的效果。")),
    (L("What causes it", "成因"), L("Backspin. Air is dragged faster over the top of the ball, pressure drops there, and the ball is pushed up (the Magnus effect). Topspin does the opposite.",
                                  "倒旋。球上方的氣流被帶得更快、壓力降低，球被往上推（馬格努斯效應）。上旋則相反。")),
    (L("Typical", "常見數值"), typical("ivb", ["FF", "SI", "CH", "CU"], unit="″")),
    (L("Does it matter?", "有用嗎？"), L(f"Pitch by pitch, more rise goes with more whiffs (chart). "
                                       f"But compare pitchers' season averages and IVB alone barely separates fastballs (r = {r_of('FF', 'ivb')} with whiff rate); it pays off combined with a flat approach angle (below).",
                                       f"逐球來看，上竄越多揮空越多（右圖）。"
                                       f"但跨投手比較，平均 IVB 單獨幾乎分不出速球好壞（與揮空率 r = {r_of('FF', 'ivb')}）；要搭配平的進壘角度才有效（見下）。")),
], charts.insight_curve(ins, "ivb", ["FF"], "whiff_pct", "IVB (in)", W, height=300),
    r"""$$\text{IVB} \approx \tfrac12\,a_{M,z}\,t^2 \times 12$$ where $a_{M,z}$ is the vertical spin-induced acceleration (Statcast `az` + $g$) and $t$ the flight time. Statcast reports it as `pfx_z` (feet).""",
    L("Every four-seamer, grouped into 16 equal bins by IVB.", "所有四縫線依 IVB 分成 16 個等量組。"))

entry("hb", L("Horizontal break", "水平位移 HB"), [
    (L("What it is", "是什麼"), L("Sideways movement versus a spinless ball, in inches. DeepPitch flips left-handers so + always means arm side (sinkers, changeups) and − glove side (sliders, sweepers).",
                                "相對無旋轉球的水平位移（吋）。DeepPitch 把左投鏡像，讓 + 永遠代表手臂側（伸卡、變速），− 代表手套側（滑球、橫掃）。")),
    (L("What causes it", "成因"), L("Tilting the spin axis away from 12:00. A 3:00 axis is pure sidespin; seams can add more (see seam-shifted wake).", "轉軸從 12:00 傾斜。3:00 是純側旋；縫線還能額外加碼（見縫線偏移尾流）。")),
    (L("Typical", "常見數值"), typical("hb", ["SI", "CH", "ST", "SL"], unit="″")),
    (L("Does it matter?", "有用嗎？"), L(f"The sweeper is built on it. Sweeper usage moved from {lg[(lg.pitch_type == 'ST') & (lg.game_year == data.seasons()[0])]['usage'].iat[0]:.1f}% to {lgy.loc['ST', 'usage']:.1f}% of all pitches.",
                                       f"橫掃球就是靠它。橫掃球占全部投球的比例從 {lg[(lg.pitch_type == 'ST') & (lg.game_year == data.seasons()[0])]['usage'].iat[0]:.1f}% 增加到 {lgy.loc['ST', 'usage']:.1f}%。")),
], charts.insight_curve(ins, "hb", ["ST", "SL"], "whiff_pct", L("HB (in, arm side +)", "HB（吋，手臂側 +）"), W, height=300))

entry("vaa", L("VAA · Vertical approach angle", "VAA · 垂直進壘角度"), [
    (L("What it is", "是什麼"), L("The angle the ball is falling at as it reaches the plate. −4° is flat, −10° is steep.", "球抵達本壘時下墜的角度。−4° 算平，−10° 算陡。")),
    (L("What causes it", "成因"), L("Mostly where the pitch is thrown (high pitches arrive flatter), then release height, extension, velocity and rise. "
                                  "DeepPitch also reports VAA versus location: how much flatter than normal for that height in the zone.",
                                  "主要取決於投到哪（高球比較平），其次是出手高度、延伸、球速和上竄。DeepPitch 也提供「位置校正 VAA」：比同高度的平均平多少。")),
    (L("Typical", "常見數值"), typical("vaa", ["FF", "SI", "CH", "CU"], unit="°")),
    (L("Does it matter?", "有用嗎？"), L(f"Yes. For four-seamers r = {r_of('FF', 'vaa')} with whiff rate; location-adjusted r = {r_of('FF', 'vaa_aa')}. A flat fastball meets an upward swing at the wrong angle.",
                                       f"有。四縫線 VAA 與揮空率 r = {r_of('FF', 'vaa')}；位置校正後 r = {r_of('FF', 'vaa_aa')}。平的速球會和往上的揮棒軌跡錯開。")),
], charts.insight_curve(ins, "vaa_aa", ["FF"], "whiff_pct", L("VAA vs location (°, + = flatter)", "位置校正 VAA（°，+ 較平）"), W, height=300),
    r"""$$\text{VAA} = \arctan\!\left(\frac{v_z}{|v_y|}\right)_{\text{plate}},\quad v(t) = v_0 + a\,t$$ evaluated at the front of home plate ($y = 17/12$ ft), with $t$ from solving $y(t) = 50 + v_{y0}t + \tfrac12 a_y t^2$.""")

entry("spin", L("Spin efficiency", "旋轉效率"), [
    (L("What it is", "是什麼"), L("The share of total spin that actually bends the ball. 100% = all backspin/sidespin; 0% = pure gyro (bullet) spin.", "總轉速中真正讓球轉彎的比例。100% = 全是倒旋／側旋；0% = 純陀螺（子彈）旋轉。")),
    (L("What causes it", "成因"), L("Finger position and wrist angle at release. Sliders and cutters are thrown with lots of gyro spin on purpose.", "出手時的手指位置與手腕角度。滑球和卡特本來就刻意帶大量陀螺旋轉。")),
    (L("Typical", "常見數值"), typical("spin_eff", ["FF", "SI", "SL", "CU"], "{:.0%}")),
    (L("How we measure it", "怎麼量"), L("From the measured Magnus acceleration per unit of speed × spin, scaled so the 98th-percentile four-seamer = 100%. Rank pitchers within a pitch type, never across types.",
                                        "由實測馬格努斯加速度除以（速度 × 轉速）算出，以第 98 百分位的四縫線為 100%。只在同球種內比較，不跨球種比。")),
], charts.insight_curve(ins, "spin_eff", ["FF", "CU"], "whiff_pct", L("Spin efficiency", "旋轉效率"), W, height=300),
    r"""$$\varepsilon = \frac{a_M}{v\,\omega}\Big/\left(\frac{a_M}{v\,\omega}\right)_{\text{FF, p98}}$$ where $a_M$ is the acceleration perpendicular to the flight after removing gravity and the drag component along the velocity.""")

entry("ssw", L("Seam-shifted wake", "縫線偏移尾流 SSW"), [
    (L("What it is", "是什麼"), L("The angle between where the measured spin says the ball should move and where it actually moved. Zero means pure Magnus.", "實測轉軸預測的位移方向，和實際位移方向的夾角。0 代表純馬格努斯效應。")),
    (L("What causes it", "成因"), L("The seams. When a smooth patch of the ball faces one side, air separates from the ball unevenly and the wake shifts, pushing the ball in a direction spin can't explain.",
                                  "縫線。當球光滑的一面朝向某一側時，氣流在兩側分離的位置不同、尾流偏移，把球推往旋轉解釋不了的方向。")),
    (L("Typical", "常見數值"), typical("ssw_deg", ["SI", "CH", "FS", "ST", "FF"], "{:+.0f}", "°")),
    (L("Does it matter?", "有用嗎？"), L("It's why two sinkers with the same spin can move differently. In the Stuff+ model it is the second most important input after velocity.",
                                       "這是為什麼兩顆轉速一樣的伸卡球會跑得不一樣。在 Stuff+ 模型中，它是僅次於球速的第二重要特徵。")),
], charts.insight_curve(ins, "ssw_deg", ["SI", "CH"], "whiff_pct", L("SSW (°)", "SSW（°）"), W, height=300),
    r"""Movement-inferred axis $\theta_{mov} = \operatorname{atan2}(\text{pfx}_x, -\text{pfx}_z)$; SSW $= \theta_{spin} - \theta_{mov}$ wrapped to $\pm180°$, mirrored for left-handers. Pitches with under 4 inches of total movement are excluded (direction undefined). 30° = one hour on the clock.""")

entry("tunnel", L("Tunneling", "隧道效應"), [
    (L("What it is", "是什麼"), L("How alike two consecutive pitches look at the commit point (175 ms before the plate), compared with how far apart they finish.", "連續兩球在出棒決策點（到本壘前 175 毫秒）看起來有多像，對比最後分得多開。")),
    (L("Why 175 ms", "為何是 175 毫秒"), L("A big-league swing takes about 150 ms. A hitter has to have decided by then; after it, movement is information he can't use.", "大聯盟揮棒約需 150 毫秒，打者必須在這之前做決定；之後的位移是他用不到的資訊。")),
    (L("How we measure it", "怎麼量"), L("Pairs of different pitch types back to back in the same at-bat, in pitch order. Break:tunnel ratio = distance apart at the plate ÷ distance apart at the commit point.",
                                        "同打席中依投球順序連續的兩個不同球種。分離比 = 本壘距離 ÷ 決策點距離。")),
    (L("What we fixed", "修正了什麼"), L("The first DeepPitch double-counted gravity and ignored pitch order. Both are fixed and covered by unit tests.", "第一版 DeepPitch 重複計算了重力、也沒照投球順序。兩者都已修正並有單元測試。")),
])

entry("ext", L("Extension & perceived velocity", "延伸與體感球速"), [
    (L("What it is", "是什麼"), L("Extension is how far in front of the rubber the ball is released. Perceived velocity is how fast the pitch looks given that shorter distance.", "延伸是出手點在投手板前多遠。體感球速是考慮這段縮短的距離後，球「看起來」多快。")),
    (L("Typical", "常見數值"), typical("ext", ["FF"], "{:.1f}", " ft") + " · " + L(f"perceived {lgy.loc['FF', 'eff_velo']:.1f} vs actual {lgy.loc['FF', 'velo']:.1f} mph", f"體感 {lgy.loc['FF', 'eff_velo']:.1f} vs 實際 {lgy.loc['FF', 'velo']:.1f} mph")),
    (L("What we fixed", "修正了什麼"), L("The first version reported 105 mph average perceived velocity. Statcast's own effective speed is used now: about +1 mph per foot of extra extension.",
                                        "第一版算出的平均體感球速是 105 mph。現在改用 Statcast 自己的 effective speed：每多一呎延伸約 +1 mph。")),
])

entry("arm", L("Arm angle", "手臂角度"), [
    (L("What it is", "是什麼"), L("Statcast's measured angle of the throwing arm at release (2024+). 0° is sidearm, 90° straight over the top.", "Statcast 量測的出手瞬間手臂角度（2024 年起）。0° 是側投，90° 是正上方。")),
    (L("Why it matters", "為何重要"), L(f"Lower slots release the ball lower, which flattens the approach angle. Among four-seamers, arm angle vs whiff rate r = {r_of('FF', 'arm_angle')}.",
                                      f"手臂越低、出手點越低，進壘角度就越平。四縫線中手臂角度與揮空率 r = {r_of('FF', 'arm_angle')}。")),
])

entry("stuff", "Stuff+", [
    (L("What it is", "是什麼"), L("A model's estimate of how many runs a pitch saves from its physics alone: velocity, spin, movement, release, and difference from the pitcher's fastball. 100 = average, every 10 points = one standard deviation.",
                                "模型只用球的物理（球速、轉速、位移、出手點、與自己速球的差異）估計這球能省下多少分。100 = 平均，每 10 分 = 一個標準差。")),
    (L("What it ignores", "不看什麼"), L("Location, count, batter and luck, on purpose. That's why it stabilises fast and predicts the future well.", "刻意不看進壘位置、球數、打者與運氣，所以它很快就穩定、也比較能預測未來。")),
])
st.page_link("app_pages/methods.py", label=L("Model details and validation →", "模型細節與驗證 →"))

# ---- the original DeepPitch physics encyclopedia, kept and tightened
st.html(f'<div class="entry-head" id="forces">{icon("forces", 40)}<h2>{ui.esc(L("The forces on a baseball, in depth", "棒球受力深入解析"))}</h2></div>')
c1, c2 = st.columns([1, 1.2], gap="large")
with c1:
    st.image("image/forces_baseball.jpg", caption=L("Forces on a baseball in flight: gravity, drag and Magnus lift.", "飛行中棒球所受的力：重力、阻力與馬格努斯升力。"))
with c2:
    st.markdown(L("""
**The Magnus effect is the foundation of all pitch movement.** A spinning ball drags the air around with it. On the side where the surface moves with the oncoming air the flow speeds up and pressure drops; on the other side it slows and pressure rises. The ball is pushed toward low pressure.

- **Backspin** pushes up against gravity → IVB.
- **Topspin** pushes down → the curveball's extra drop.
- **Sidespin** pushes sideways → horizontal break.
- **Gyro spin** (axis pointing at the plate, like a bullet) pushes nowhere.
""", """
**馬格努斯效應是所有球路位移的基礎。** 旋轉的球會帶動周圍空氣。表面轉動方向與迎面氣流相同的一側，氣流加速、壓力下降；另一側氣流減速、壓力上升。球被推向低壓側。

- **倒旋**向上對抗重力 → IVB。
- **上旋**向下 → 曲球額外的下墜。
- **側旋**向側邊 → 水平位移。
- **陀螺旋轉**（轉軸指向本壘，像子彈）不往任何方向推。
"""))

with st.expander(L("Bernoulli's principle: why faster air means lower pressure", "白努利定律：為什麼氣流越快壓力越低")):
    st.markdown(L(r"""
In a moving fluid, pressure and speed trade off: $P + \tfrac12\rho v^2 = \text{constant}$ along a streamline.
The seams grip the air and drag it around the spinning ball, so one side sees faster flow (lower pressure) and the other slower flow (higher pressure).
The same idea lifts an aircraft wing and pulls two trucks together when they pass on the highway.
Without that pressure difference there is no movement at all: no IVB, no HB.
""", r"""
在流動的流體中，壓力與速度此消彼長：沿流線 $P + \tfrac12\rho v^2 = \text{常數}$。
縫線抓住空氣並帶著它繞球轉，所以一側氣流較快（壓力低）、另一側較慢（壓力高）。
同樣的原理讓飛機機翼產生升力，也讓兩台在高速公路並行的卡車互相靠近。
沒有這個壓力差就沒有任何位移：沒有 IVB，也沒有 HB。
"""))
with st.expander(L("Air density: why Coors Field flattens breaking balls", "空氣密度：為什麼庫爾斯球場的變化球比較不會跑")):
    st.markdown(L("""
Both drag and Magnus force scale with air density. Denver's thin air (roughly 15–20% less dense than at sea level) cuts both: fastballs keep a little more velocity, but every pitch bends less.
DeepPitch's physics uses each pitch's own measured accelerations, so park effects are already inside the numbers rather than assumed.
""", """
阻力與馬格努斯力都和空氣密度成正比。丹佛稀薄的空氣（密度約比海平面低 15–20%）兩者都會減弱：速球掉速少一點，但每一種球都轉得比較少。
DeepPitch 使用每一球自己的實測加速度，所以球場效應已經包含在數字裡，而不是用假設的。
"""))
with st.expander(L("Approach geometry: why a 92 mph fastball can beat a 98", "進壘幾何：為什麼 92 mph 的速球能贏過 98")):
    st.markdown(L("""
The same 18 inches of rise released from a lower arm slot arrives flatter. "Low origin, high destination" makes the ball seem to climb through the zone,
and a hitter's swing, which travels slightly upward, meets it at the wrong angle. More extension shortens the trip, flattening the angle again and raising perceived velocity.
""", """
同樣 18 吋的上竄，從較低的出手點投出，進壘會更平。「低出手、高進壘」讓球看起來像往上穿過好球帶，
而打者略微往上的揮棒軌跡會以錯誤的角度遇到它。更長的延伸縮短飛行距離，讓角度更平、體感球速更高。
"""))
with st.expander(L("The hitter's brain: the commit point", "打者的大腦：出棒決策點")):
    st.markdown(L("""
A hitter has to commit roughly 23–25 feet in front of the plate, about 175 ms before the ball arrives. If two different pitches share the same path through that window,
the brain files them as the same pitch until it's too late. Elite pitchers stack the effects: Magnus force for movement, seam-shifted wake for surprise,
approach angle and tunneling to keep it all hidden until the decision is made.
""", """
打者大約要在本壘前 23–25 呎、球到前約 175 毫秒做出決定。如果兩種不同的球在這段窗口走同一條路，
大腦會把它們當成同一種球，等發現時已經太遲。頂尖投手把效果疊加：用馬格努斯力產生位移、用縫線偏移尾流製造意外、
再用進壘角度與隧道效應把一切藏到打者做完決定為止。
"""))
ui.footer()
