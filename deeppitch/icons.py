"""Authored single-stroke icons in the scorebook's ink (graphite + red pencil accent).

Streamlit's HTML sanitizer strips inline <svg>, so icons ship as data-URI <img>.
"""
from __future__ import annotations

import base64

INK = "#26292B"
RED = "#C7352B"
_W = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'


def _svg(body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" {_W} stroke="{INK}" stroke-width="1.8">'
            f'{body}</svg>')


_BALL = '<circle cx="16" cy="16" r="6.5"/><path d="M11.6 11.3c1.6 1.6 1.6 7.8 0 9.4M20.4 11.3c-1.6 1.6-1.6 7.8 0 9.4" stroke-width="1.2"/>'

ICONS = {
    # backspin + lift arrow
    "ivb": _svg(_BALL + f'<path d="M16 7.5V2.5M13.5 5 16 2.5 18.5 5" stroke="{RED}"/>'
                '<path d="M8 23.5a9 9 0 0 1 0-15" stroke-dasharray="1.5 2.2"/>'),
    # sideways push
    "hb": _svg(_BALL + f'<path d="M24.5 16h5M27 13.5l2.5 2.5-2.5 2.5" stroke="{RED}"/>'),
    # ball arriving at an angle onto the plate line
    "vaa": _svg(f'<path d="M3 6c7 2 13 6 19 13" /><path d="M3 27h26"/><path d="M20 27a8 8 0 0 0-3.2-6.2" stroke="{RED}"/>'
                '<circle cx="23.5" cy="21" r="2.6"/>'),
    # spin axis tilted through the ball, partial efficiency arc
    "spin": _svg(_BALL + f'<path d="M7 25 25 7" stroke="{RED}"/><path d="M22.5 22.5a9 9 0 0 1-13.5 1" stroke-dasharray="1.5 2.2"/>'),
    # seams + shifted wake behind the ball
    "ssw": _svg('<circle cx="12" cy="16" r="6.5"/><path d="M8.2 11.5c2.5 2 2.5 7 0 9" stroke-width="1.2"/>'
                f'<path d="M18.5 12.5c4 0 6 1.5 10.5 3.5M18.5 19.5c4 0 6.5-.5 10.5-.5" stroke="{RED}"/>'),
    # two paths share a tunnel then split
    "tunnel": _svg(f'<path d="M3 16h12"/><path d="M15 16c5 0 8-5 14-8" /><path d="M15 16c5 0 8 5 14 8" stroke="{RED}"/>'
                   '<path d="M15 10v12" stroke-dasharray="1.5 2.2"/>'),
    # stride forward: extension
    "ext": _svg(f'<path d="M4 26h24"/><path d="M6 26v-4M6 22h16"/><path d="M19 19l3 3-3 3" stroke="{RED}"/>'
                '<circle cx="25" cy="12" r="3"/>'),
    # arm slot angle
    "arm": _svg(f'<path d="M6 26 18 10"/><path d="M6 26h20"/><path d="M14 26a8 8 0 0 0-2.8-6.2" stroke="{RED}"/>'
                '<circle cx="20" cy="7.5" r="2.6"/>'),
    # base-path diamond
    "stuff": _svg(f'<path d="M16 4 28 16 16 28 4 16Z"/><path d="M16 28 28 16 16 4" stroke="{RED}" stroke-width="2.4"/>'),
    # gravity, drag, Magnus around one ball
    "forces": _svg(_BALL + f'<path d="M16 22.5v6M13.5 26l2.5 2.5 2.5-2.5"/><path d="M9.5 16h-6M6 13.5 3.5 16 6 18.5"/>'
                   f'<path d="M16 9.5v-6M13.5 6 16 3.5 18.5 6" stroke="{RED}"/>'),
    # clock face for the commit point
    "commit": _svg(f'<circle cx="16" cy="17" r="11"/><path d="M16 17V10M16 17l5 3" stroke="{RED}"/><path d="M13 3h6"/>'),
}


def icon(name: str, size: int = 28, title: str = "") -> str:
    data = base64.b64encode(ICONS[name].encode()).decode()
    return (f'<img src="data:image/svg+xml;base64,{data}" width="{size}" height="{size}" alt="{title}" '
            f'title="{title}" style="vertical-align:middle;flex:none">')
