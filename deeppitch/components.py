"""Reusable scorebook pieces rendered as HTML."""
from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from deeppitch.i18n import L, pitch_name
from deeppitch.theme import INK, RED, RULE, pitch_color

WEB = Path(__file__).resolve().parent / "web"
FONT_LINK = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
             '<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700'
             '&family=Barlow+Condensed:wght@600;700&display=swap" rel="stylesheet">')


def esc(s) -> str:
    return html.escape(str(s))


# ---------------------------------------------------------------------------
# The diamond: a percentile drawn the way a scorer marks a runner's progress.
# 1st base = 25th pct, 2nd = 50th, 3rd = 75th, home (filled) = 90th+.
# ---------------------------------------------------------------------------

def diamond(pctl: float | None, size: int = 22, show_num: bool = True) -> str:
    """CSS diamond (st.html strips inline SVG). Legs light up base by base: 1st, 2nd, 3rd, home."""
    if pctl is None or not np.isfinite(pctl):
        return f'<span class="sub" title="{esc(L("Not enough pitches", "樣本不足"))}">—</span>'
    p = float(pctl)
    reached = sum(p >= t for t in (25, 50, 75, 90))
    side = round(size * 0.62)
    on, off = (RED if reached == 4 else INK), "rgba(38,41,43,.28)"
    # rotated square: right edge = home→1st, top = 1st→2nd, left = 2nd→3rd, bottom = 3rd→home
    edges = [on if reached >= k else off for k in (1, 2, 3, 4)]
    widths = [2 if reached >= k else 1 for k in (1, 2, 3, 4)]
    style = (f"display:inline-block;width:{side}px;height:{side}px;transform:rotate(45deg);margin:0 {size * 0.2:.0f}px;"
             f"border-style:solid;border-right:{widths[0]}px solid {edges[0]};border-top:{widths[1]}px solid {edges[1]};"
             f"border-left:{widths[2]}px solid {edges[2]};border-bottom:{widths[3]}px solid {edges[3]};"
             f"background:{RED if reached == 4 else 'transparent'};vertical-align:middle;box-sizing:border-box")
    title = L(f"{p:.0f}th percentile among this pitch type", f"同球種第 {p:.0f} 百分位")
    num_html = f'<span class="sub">{p:.0f}</span>' if show_num else ""
    return (f'<span title="{esc(title)}" style="display:inline-flex;align-items:center;gap:4px">'
            f'<span style="{style}"></span>{num_html}</span>')


def diamond_legend() -> str:
    items = [(30, L("25th+", "25+")), (55, L("50th+", "50+")), (80, L("75th+", "75+")), (95, L("90th+", "90+"))]
    cells = "".join(f'<span>{diamond(v, 18, show_num=False)}{esc(t)}</span>' for v, t in items)
    return (f'<div class="legend-row"><span>{esc(L("Percentile, scored like a runner on the bases:", "百分位，像計分簿記壘包："))}'
            f'</span>{cells}</div>')


def pitch_chip(pt: str, sub: str | None = None) -> str:
    col = pitch_color(pt)
    extra = f' <span class="sub">{esc(sub)}</span>' if sub else ""
    return f'<span class="pt"><span class="dot" style="border-color:{col}"></span>{esc(pitch_name(pt))}{extra}</span>'


def ledger(df: pd.DataFrame, columns: list[tuple], height: int | None = None) -> None:
    """Render rows as a ruled scorebook ledger. columns = [(header, key, formatter(row)->html[, "l"])]; "l" left-aligns."""
    cols = [(c[0], c[1], c[2], c[3] if len(c) > 3 else "") for c in columns]
    head = "".join(f'<th class="{a}">{esc(h)}</th>' for h, _, _, a in cols)
    body = []
    for _, r in df.iterrows():
        body.append("<tr>" + "".join(f'<td class="{a}">{fmt(r)}</td>' for _, _, fmt, a in cols) + "</tr>")
    style = f' style="max-height:{height}px;overflow-y:auto"' if height else ""
    st.html(f'<div class="ledger-wrap"{style}><table class="ledger"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def num(v, d=1, suffix="") -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)) or pd.isna(v):
        return '<span class="sub">—</span>'
    return f"{v:,.{d}f}{suffix}"


def note(text: str, ink: bool = False) -> None:
    st.html(f'<span class="note{" ink" if ink else ""}">{esc(text)}</span>')


def masthead(title_html: str, lede: str, meta_items: list[tuple[str, str]]) -> None:
    meta = "".join(f"<div><b>{esc(v)}</b>{esc(k)}</div>" for k, v in meta_items)
    st.html(f'<div class="mast"><div><h1 class="title">{title_html}</h1><p class="lede">{esc(lede)}</p></div>'
            f'<div class="meta">{meta}</div></div>')


def line(items: list[tuple], circled: int | None = None) -> None:
    """A scorebook header row. `circled` = index of the stat the scorer ringed in red pencil."""
    cells = "".join(f'<div><div class="k">{esc(it[0])}</div><div class="v{" circled" if i == circled else ""}">{esc(it[1])}'
                    f'{f"<small>{esc(it[2])}</small>" if it[2] else ""}</div></div>' for i, it in enumerate(items))
    st.html(f'<div class="line">{cells}</div>')


def facts(rows: list[tuple[str, str]]) -> None:
    st.html('<div class="facts">' + "".join(f'<div class="k">{esc(k)}</div><div>{v}</div>' for k, v in rows) + "</div>")


def flight(pitches: list[dict], height: int = 520, autoplay: bool = False, zone=None, key: str = "flight") -> None:
    """Animated pencil-on-scorebook flight: side view + catcher's view, commit point marked."""
    if not pitches:
        st.info(L("No trajectory available for this selection.", "這個選擇沒有可用的軌跡。"))
        return
    payload = {
        "pitches": pitches, "decision": 0.175, "canvasH": 440, "autoplay": autoplay, "zone": zone or {"top": 3.4, "bot": 1.6},
        "labels": {"throw": L("Throw", "投球"), "ghost": L("No-spin path", "無旋轉路徑"),
                   "side": L("Side view · rubber to plate", "側視圖 · 投手板到本壘"),
                   "catcher": L("Catcher's view", "捕手視角"), "commit": L("Commit point", "出棒決策點"),
                   "plate": L("plate", "本壘")},
    }
    src = (WEB / "flight.html").read_text().replace("__DATA__", json.dumps(payload))
    components.html(FONT_LINK + src, height=575, scrolling=False)


def footer() -> None:
    from deeppitch.data import meta
    m = meta()
    st.html(
        f'<div class="foot"><span>DeepPitch · {esc(L("Built by", "作者"))} Paul Lai (Hong-Min Lai), M.S. Data Science, UC San Diego</span>'
        f'<span>{esc(L("Data", "資料"))}: MLB Statcast via Baseball Savant · {esc(L("through", "截至"))} {esc(m["last_game"])}</span>'
        f'<a href="https://github.com/Paul-Lai0111/2024MLB_DeepPitch_Dashboard" target="_blank">GitHub</a>'
        f'<a href="https://www.linkedin.com/in/paullai0111/" target="_blank">LinkedIn</a>'
        f'<span>{esc(L("Not affiliated with MLB.", "與 MLB 無隸屬關係。"))}</span></div>')
