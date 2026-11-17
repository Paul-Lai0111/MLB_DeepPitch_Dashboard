"""Visual system: the scorebook. Green-ruled ledger stock, graphite, red grease
pencil for what matters, blue ballpoint for links and selection."""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

PAPER = "#F3F5EF"
PAPER_2 = "#E6EADF"
RULE = "#2E6A4E"
RULE_SOFT = "rgba(46,106,78,0.16)"
INK = "#26292B"
MUTED = "#5C625E"
RED = "#C7352B"
BLUE = "#2350A0"
FONT = 'Barlow, "Noto Sans TC", system-ui, sans-serif'
COND = '"Barlow Condensed", "Noto Sans TC", system-ui, sans-serif'
HAND = 'Caveat, "Noto Sans TC", cursive'

# Validated (dataviz validator, light, surface #F3F5EF): all six checks pass.
PITCH_COLORS = {
    "FF": "#C7352B", "SL": "#7B4FA6", "SI": "#C9771A", "CU": "#2350A0",
    "CH": "#3C8D3F", "ST": "#C2589A", "FC": "#9A5A1F", "FS": "#00908C",
    # rare types borrow their family's ink; shapes keep them distinct
    "KC": "#2350A0", "SV": "#C2589A", "FO": "#00908C", "KN": "#5C625E",
}
PITCH_ORDER = ["FF", "SI", "FC", "SL", "ST", "SV", "CU", "KC", "CH", "FS", "FO", "KN"]
PITCH_SYMBOL = {"KC": "diamond", "SV": "diamond", "FO": "diamond", "KN": "x"}


def pitch_color(pt: str) -> str:
    return PITCH_COLORS.get(pt, MUTED)


def _template() -> go.layout.Template:
    t = go.layout.Template()
    t.layout = go.Layout(
        font=dict(family=FONT, size=13, color=INK),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=list(PITCH_COLORS.values())[:8],
        margin=dict(l=8, r=8, t=36, b=8),
        title=dict(font=dict(family=COND, size=17, color=INK), x=0, xanchor="left", y=0.98),
        xaxis=dict(gridcolor=RULE_SOFT, zerolinecolor="rgba(38,41,43,0.45)", zerolinewidth=1,
                   linecolor=INK, linewidth=1, ticks="outside", tickcolor=INK, ticklen=4,
                   title=dict(font=dict(size=12, color=MUTED)), tickfont=dict(size=12, color=MUTED)),
        yaxis=dict(gridcolor=RULE_SOFT, zerolinecolor="rgba(38,41,43,0.45)", zerolinewidth=1,
                   linecolor=INK, linewidth=1, ticks="outside", tickcolor=INK, ticklen=4,
                   title=dict(font=dict(size=12, color=MUTED)), tickfont=dict(size=12, color=MUTED)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                    font=dict(size=12), bgcolor="rgba(0,0,0,0)", itemclick="toggleothers"),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=INK, font=dict(family=FONT, size=13, color=INK)),
        hovermode="closest",
    )
    return t


pio.templates["scorebook"] = _template()
pio.templates.default = "scorebook"

PLOT_CONFIG = {"displayModeBar": False, "displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
               "toImageButtonOptions": {"format": "png", "scale": 2}}

CSS = f"""
<style>
@import url("https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Noto+Sans+TC:wght@400;500;700&display=swap");
:root {{ --paper:{PAPER}; --paper2:{PAPER_2}; --rule:{RULE}; --ink:{INK}; --muted:{MUTED}; --red:{RED}; --blue:{BLUE}; }}
html, body, [class*="st-"] {{ font-feature-settings: "tnum" 1, "lnum" 1; }}
.stApp {{ background: var(--paper); }}
.block-container {{ padding-top: 4.4rem; padding-bottom: 4rem; max-width: 1280px; }}
h1, h2, h3, h4 {{ letter-spacing: 0.005em; text-wrap: balance; }}
h1 {{ font-size: 2.9rem !important; line-height: 1.02 !important; }}
h2 {{ font-size: 1.85rem !important; margin-top: 1.6rem !important; }}
h3 {{ font-size: 1.3rem !important; }}
p, li {{ max-width: 72ch; }}

/* top navigation: a scorebook spine */
header[data-testid="stHeader"] {{ background: var(--paper); border-bottom: 2px solid var(--rule); }}
header [data-testid="stTopNavLinkContainer"] a span,
header [data-testid="stNavLink"] span {{ font-family: {COND}; font-weight: 600; font-size: 1.02rem; letter-spacing: .04em; text-transform: uppercase; }}
header [aria-current="page"] span {{ color: var(--blue) !important; }}

/* ledger tables */
.ledger {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; }}
.ledger th {{ font-family: {COND}; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; font-size: .8rem;
  color: var(--rule); text-align: right; padding: 6px 10px; border-bottom: 2px solid var(--rule); white-space: nowrap; }}
.ledger th:first-child, .ledger td:first-child {{ text-align: left; }}
.ledger td {{ padding: 7px 10px; border-bottom: 1px solid rgba(46,106,78,.22); text-align: right; white-space: nowrap; }}
.ledger td + td, .ledger th + th {{ border-left: 1px solid rgba(46,106,78,.18); }}
.ledger tr:hover td {{ background: rgba(35,80,160,.05); }}
.ledger .pt {{ display:inline-flex; align-items:center; gap:8px; font-weight:600; }}
.ledger .dot {{ width:11px; height:11px; border-radius:50%; border:2px solid; background:#fff; flex:none; }}
.ledger .sub {{ color: var(--muted); font-weight: 400; font-size: .85rem; }}
.ledger .hi {{ color: var(--red); font-weight: 700; }}
.ledger a {{ color: var(--ink); text-decoration: none; border-bottom: 1px solid rgba(35,80,160,.4); }}
.ledger a:hover {{ color: var(--blue); }}
.ledger-wrap {{ overflow-x: auto; border-top: 1px solid var(--rule); }}
.ledger td:first-child, .ledger th:first-child {{ position: sticky; left: 0; background: var(--paper); z-index: 1; box-shadow: 1px 0 0 rgba(46,106,78,.25); }}
.line .v.circled {{ display:inline-block; padding: 0 10px; margin-left: -10px; border: 2px solid var(--red); border-radius: 50% 46% 52% 44%; transform: rotate(-2deg); }}
.entry-head {{ display:flex; align-items:center; gap: 12px; margin: 2.2rem 0 .6rem; }}
.entry-head h2 {{ margin: 0 !important; font-family: {COND}; font-weight: 700; font-size: 1.85rem; }}
.slope td {{ font-variant-numeric: tabular-nums; }}
.ledger td.l, .ledger th.l {{ text-align: left; white-space: normal; }}
[data-testid="stMetricValue"] {{ font-family: {COND}; font-weight: 700; }}
[data-testid="stMetricLabel"] p {{ font-family: {COND}; text-transform: uppercase; letter-spacing: .05em; color: var(--rule); }}
.ledger .rk {{ color: var(--muted); width: 2.5rem; }}
.ledger .bar {{ display:inline-block; height:8px; background: var(--ink); border-radius: 0 4px 4px 0; vertical-align: middle; margin-right: 8px; }}

/* scorer's pencil notes */
.note {{ font-family: {HAND}; font-size: 1.45rem; line-height: 1.15; color: var(--red); transform: rotate(-1.2deg);
  display: inline-block; margin: .2rem 0 .6rem; }}
.note.ink {{ color: var(--blue); }}

/* masthead */
.mast {{ display:grid; grid-template-columns: 1fr auto; gap: 8px 32px; align-items: end; padding: 10px 0 14px;
  border-bottom: 1px solid var(--rule); margin-bottom: 18px; }}
.mast .title {{ font-family: {COND}; font-weight: 700; font-size: clamp(2.4rem, 5.2vw, 4.4rem); line-height: .95; letter-spacing: .005em; margin: 0; color: var(--ink); }}
.mast .title em {{ font-style: normal; color: var(--red); }}
.mast .lede {{ font-size: 1.12rem; color: var(--ink); max-width: 60ch; margin: 10px 0 0; }}
.mast .meta {{ font-family: {COND}; text-transform: uppercase; letter-spacing: .06em; font-size: .9rem; color: var(--muted); text-align: right; line-height: 1.5; }}
.mast .meta b {{ color: var(--ink); font-size: 1.35rem; display:block; letter-spacing: .02em; }}
@media (max-width: 720px) {{ .mast {{ grid-template-columns: 1fr; }} .mast .meta {{ text-align:left; display:flex; gap: 18px; }} }}

/* the pitcher line: a scorebook header row */
.line {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(96px, 1fr)); border-top: 2px solid var(--rule); border-bottom: 1px solid var(--rule); margin: 6px 0 18px; }}
.line > div {{ padding: 9px 12px 10px; border-left: 1px solid rgba(46,106,78,.25); }}
.line > div:first-child {{ border-left: 0; }}
.line .k {{ font-family: {COND}; text-transform: uppercase; letter-spacing: .06em; font-size: .78rem; color: var(--rule); }}
.line .v {{ font-family: {COND}; font-weight: 700; font-size: 1.5rem; line-height: 1.1; }}
.line .v small {{ font-size: .95rem; color: var(--muted); font-weight: 500; margin-left: 4px; }}

/* fact rows for the field guide */
.facts {{ display:grid; grid-template-columns: 9.5rem 1fr; border-top: 1px solid var(--rule); }}
.facts > div {{ padding: 8px 0; border-bottom: 1px solid rgba(46,106,78,.2); }}
.facts .k {{ font-family: {COND}; text-transform: uppercase; letter-spacing: .06em; font-size: .85rem; color: var(--rule); padding-right: 12px; }}
@media (max-width: 640px) {{ .facts {{ grid-template-columns: 1fr; }} .facts .k {{ border-bottom: 0; padding-bottom: 0; }} }}

.legend-row {{ display:flex; flex-wrap:wrap; gap: 6px 18px; font-size: .9rem; color: var(--muted); align-items:center; }}
.legend-row span {{ display:inline-flex; align-items:center; gap:6px; }}
.caption {{ color: var(--muted); font-size: .9rem; max-width: 72ch; }}
.stat {{ font-family: {COND}; font-weight: 700; font-size: 2.6rem; line-height: 1; color: var(--ink); }}
.stat small {{ font-size: 1rem; color: var(--muted); font-weight: 500; }}
.finding {{ border-top: 2px solid var(--ink); padding-top: 10px; }}
.finding h4 {{ margin: 6px 0 6px !important; font-size: 1.25rem !important; }}
.finding p {{ color: var(--ink); font-size: .98rem; }}

div[data-testid="stSegmentedControl"] button p {{ font-family: {COND}; font-weight: 600; letter-spacing: .03em; }}
div[data-testid="stExpander"] details {{ border-radius: 2px; border-color: rgba(46,106,78,.35); background: rgba(255,255,255,.35); }}
div[data-testid="stExpander"] summary p {{ font-family: {COND}; font-weight: 600; font-size: 1.05rem; letter-spacing: .02em; }}
.stTabs [data-baseweb="tab"] p {{ font-family: {COND}; font-weight: 600; font-size: 1.05rem; letter-spacing: .03em; }}
.stTabs [aria-selected="true"] p {{ color: var(--blue); }}
footer {{ visibility: hidden; }}
.foot {{ margin-top: 3rem; padding-top: 12px; border-top: 2px solid var(--rule); color: var(--muted); font-size: .88rem; display:flex; flex-wrap:wrap; gap: 6px 22px; }}
.foot a {{ color: var(--muted); }}
</style>
"""


def inject() -> None:
    st.html(CSS)
