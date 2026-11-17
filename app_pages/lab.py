import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from deeppitch import charts, components as ui, data
from deeppitch.i18n import L, pitch_name
from deeppitch.sim import simulate
from deeppitch.theme import INK, PLOT_CONFIG, RED, pitch_color

st.html(f'<div class="mast"><div><h1 class="title">{ui.esc(L("Physics Lab", "物理實驗室"))}</h1>'
        f'<p class="lede">{ui.esc(L("Build a pitch from the things a pitcher controls: speed, spin, the tilt of the spin, and where he lets go. The lab flies it with the same force model DeepPitch uses to read two million real pitches.", "用投手能控制的東西做一顆球：球速、轉速、轉軸傾角、出手點。實驗室用 DeepPitch 解讀兩百萬顆真實投球的同一套力學模型讓它飛。"))}</p></div></div>')

# (velo, spin, efficiency, tilt hours, release height, extension, target height, pitch type for comparison)
PRESETS = {
    "ride": (L("Riding 4-seam", "上竄四縫線"), 96, 2450, 95, 1.0, 5.8, 6.8, 3.2, "FF"),
    "sink": (L("Heavy sinker", "重伸卡"), 94, 2200, 90, 2.25, 5.6, 6.5, 2.0, "SI"),
    "sweep": (L("Sweeper", "橫掃球"), 83, 2600, 50, 9.5, 5.7, 6.3, 2.3, "ST"),
    "curve": (L("Big curve", "大曲球"), 79, 2700, 65, 7.0, 5.9, 6.2, 1.8, "CU"),
    "split": (L("Splitter", "指叉球"), 87, 1300, 85, 2.0, 5.8, 6.6, 1.6, "FS"),
    "gyro": (L("Gyro slider", "陀螺滑球"), 88, 2500, 20, 8.5, 5.8, 6.4, 2.0, "SL"),
}


def load(key):
    _, v, s, e, tilt, rz, ext, tz, _pt = PRESETS[key]
    st.session_state.update(lab_velo=v, lab_spin=s, lab_eff=e, lab_tilt=tilt, lab_relz=rz, lab_ext=ext, lab_tz=tz, lab_pt=_pt)


if "lab_velo" not in st.session_state:
    load("ride")

st.markdown(f"#### {L('Start from a classic', '從經典球路開始')}")
cols = st.columns(len(PRESETS))
for c, (k, p) in zip(cols, PRESETS.items()):
    c.button(p[0], key=f"preset_{k}", on_click=load, args=(k,), use_container_width=True)

left, right = st.columns([1, 2.6], gap="large")
with left:
    hand = st.segmented_control(L("Throws", "投球手"), ["R", "L"], default="R", key="lab_hand",
                                format_func=lambda h: L("Right", "右投") if h == "R" else L("Left", "左投")) or "R"
    velo = st.slider(L("Velocity (mph)", "球速 (mph)"), 65, 103, key="lab_velo")
    spin = st.slider(L("Spin rate (rpm)", "轉速 (rpm)"), 500, 3400, step=25, key="lab_spin")
    eff = st.slider(L("Spin efficiency (%)", "旋轉效率 (%)"), 0, 100, key="lab_eff",
                    help=L("How much of the spin is 'sidespin/backspin' that bends the ball. The rest is gyro (bullet) spin, which bends nothing.",
                           "有多少旋轉是能讓球轉彎的側旋／倒旋。其餘是陀螺（子彈）旋轉，不會造成位移。"))
    tilt = st.slider(L("Spin tilt (clock, 12:00 = pure backspin)", "轉軸傾角（時鐘，12:00 = 純倒旋）"), 0.0, 12.0, step=0.25, key="lab_tilt",
                     format="%.2f h", help=L("Right-hander's view: 1:00 is a typical four-seamer, 2:00–2:30 a sinker, 6:00 pure topspin, 9:00 pure glove-side spin.",
                                            "右投視角：1:00 是典型四縫線，2:00–2:30 是伸卡，6:00 是純上旋，9:00 是純手套側旋轉。"))
    relz = st.slider(L("Release height (ft)", "出手高度 (呎)"), 4.0, 7.2, step=0.1, key="lab_relz")
    ext = st.slider(L("Extension (ft)", "延伸距離 (呎)"), 5.0, 7.8, step=0.1, key="lab_ext")
    tz = st.slider(L("Target height at the plate (ft)", "本壘目標高度 (呎)"), 1.0, 4.0, step=0.1, key="lab_tz")

tilt_eff = tilt if hand == "R" else (12 - tilt) % 12
rel_x = -1.9 if hand == "R" else 1.9
ref = data.meta()["spin_eff_reference"]
sim = simulate(velo, spin, eff / 100, tilt_eff, relz, rel_x, ext, 0.0, tz, ref, hand)
ghost_note = L("dashed = same throw with no spin", "虛線 = 同樣出手但沒有旋轉")

with right:
    tr = sim["traj"]
    payload = [{"label": L("Your pitch", "你的球"), "color": RED,
                "pts": tr[["t", "x", "y", "z"]].round(4).to_numpy().tolist(),
                "ghost": tr[["x_nospin", "z_nospin"]].round(4).to_numpy().tolist()}]
    ui.flight(payload, key="lab_flight")
    ui.line([
        ("IVB", f"{sim['ivb']:+.1f}", L("in", "吋")),
        ("HB", f"{sim['hb']:+.1f}", L("in", "吋")),
        ("VAA", f"{sim['vaa']:.1f}°", None),
        (L("Flight", "飛行"), f"{sim['flight_ms']:.0f}", "ms"),
        (L("Useful spin", "有效轉速"), f"{sim['useful_spin']:.0f}", "rpm"),
        (L("Magnus force", "馬格努斯力"), f"{sim['magnus_g']:.2f}", L("× gravity", "× 重力")),
    ])

lift = sim["lift_saved_in"]
if lift > 3:
    msg = L(f"Spin holds this pitch up {lift:.0f} inches compared with the same throw with no spin. That missing drop is what hitters call 'rise'.",
            f"和沒有旋轉的同一球相比，旋轉讓這球少掉了 {lift:.0f} 吋。這段「沒掉下來」的距離，就是打者說的「上竄」。")
elif lift < -3:
    msg = L(f"Topspin drives this pitch {abs(lift):.0f} inches below where gravity alone would take it.",
            f"上旋讓這球比純重力多掉了 {abs(lift):.0f} 吋。")
else:
    msg = L("Almost no vertical help from spin: this pitch falls almost exactly as gravity says, the signature of gyro spin or a splitter.",
            "旋轉幾乎沒有提供垂直方向的力：球幾乎完全照重力落下，這是陀螺旋轉或指叉球的特徵。")
ui.note(msg)
st.caption(ghost_note)

# ---- where it would sit among real pitches
st.markdown(f"## {L('Where your pitch lands among real ones', '你的球在真實投球中的位置')}")
yr = data.seasons()[-1]
dens = data.table("league_density")
dens = dens[dens["game_year"] == yr]
fig = go.Figure()
for pt in ["FF", "SI", "FC", "SL", "ST", "CU", "CH", "FS"]:
    g = dens[(dens["pitch_type"] == pt)]
    g = g[g["n"] >= g["n"].quantile(0.5)]
    fig.add_trace(go.Scatter(x=g["hx"], y=g["vz"], mode="markers", name=pitch_name(pt), hoverinfo="name",
                             marker=dict(symbol="square", size=10, color=pitch_color(pt), opacity=.22, line=dict(width=0))))
fig.add_trace(go.Scatter(x=[sim["hb"]], y=[sim["ivb"]], mode="markers+text", text=[L("your pitch", "你的球")],
                         textposition="top center", textfont=dict(color=INK, size=14), showlegend=False,
                         marker=dict(size=20, color="#fff", line=dict(width=3.5, color=RED))))
fig.update_layout(height=520, xaxis=dict(range=[-26, 26], title=L("Horizontal break, in (arm side +)", "水平位移（吋，手臂側 +）"),
                                         scaleanchor="y", dtick=5),
                  yaxis=dict(range=[-26, 26], title=L("Induced vertical break, in", "誘發垂直位移（吋）"), dtick=5))
st.plotly_chart(fig, config=PLOT_CONFIG, key="lab_cloud")
st.caption(L(f"Shaded squares: where each pitch type was thrown across MLB in {yr}.", f"色塊：{yr} 年全聯盟各球種的位移分布。"))

with st.expander(L("The physics under the hood", "背後的物理")):
    st.markdown(L(
        r"""
Three forces act on the ball, and the lab holds each constant through the flight, exactly as Statcast's trajectory fit does:

- **Gravity** pulls down at $g = 32.2\ \text{ft/s}^2$.
- **Drag** slows the ball along its path: $a_{drag} = k_D\,v^2$, with $k_D$ chosen so a 95 mph pitch loses about 8 mph by the plate.
- **Magnus lift** pushes perpendicular to the path: $a_M = c\,v\,\omega\,\varepsilon$, where $\omega$ is spin rate and $\varepsilon$ spin efficiency.
  The constant $c$ is measured from two million 2024–2026 pitches, so the lab and the database speak the same physics.

The spin tilt points the Magnus force: $a_x = a_M\sin\theta$, $a_z = -a_M\cos\theta$ with Statcast's axis angle $\theta$ (180° = backspin).
Release velocity is solved so the ball arrives at your target height, then the path is integrated to the front of home plate.
""",
        r"""
球在飛行中受三種力，實驗室讓它們在整段飛行中保持固定，和 Statcast 的軌跡擬合方式一樣：

- **重力**向下：$g = 32.2\ \text{ft/s}^2$。
- **空氣阻力**沿飛行方向減速：$a_{drag} = k_D\,v^2$，$k_D$ 讓 95 mph 的球到本壘約掉 8 mph。
- **馬格努斯力**垂直於飛行方向：$a_M = c\,v\,\omega\,\varepsilon$，$\omega$ 是轉速、$\varepsilon$ 是旋轉效率。
  常數 $c$ 由 2024–2026 年兩百萬顆投球量測而來，所以實驗室和資料庫用的是同一套物理。

轉軸傾角決定馬格努斯力的方向：$a_x = a_M\sin\theta$、$a_z = -a_M\cos\theta$（Statcast 轉軸角 $\theta$，180° = 倒旋）。
程式先解出讓球抵達目標高度的出手速度，再積分到本壘前緣。
"""))
ui.footer()
