"""Two-language copy. English is the default; ?lang=zh switches to Traditional Chinese."""
from __future__ import annotations

import streamlit as st

PITCH_NAMES = {
    "FF": ("Four-seam fastball", "四縫線速球"), "SI": ("Sinker", "伸卡球"), "FC": ("Cutter", "卡特球"),
    "SL": ("Slider", "滑球"), "ST": ("Sweeper", "橫掃球"), "SV": ("Slurve", "滑曲球"),
    "CU": ("Curveball", "曲球"), "KC": ("Knuckle curve", "彈指曲球"), "CH": ("Changeup", "變速球"),
    "FS": ("Splitter", "指叉球"), "FO": ("Forkball", "叉球"), "KN": ("Knuckleball", "蝴蝶球"),
}


def lang() -> str:
    if "lang" not in st.session_state:
        st.session_state["lang"] = "zh" if st.query_params.get("lang") == "zh" else "en"
    return st.session_state["lang"]


def L(en: str, zh: str) -> str:
    """Pick the string for the active language."""
    return zh if lang() == "zh" else en


def pitch_name(pt: str) -> str:
    en, zh = PITCH_NAMES.get(pt, (pt, pt))
    return zh if lang() == "zh" else en


def language_switch() -> None:
    cur = lang()
    choice = st.segmented_control("Language", ["EN", "中文"], default="中文" if cur == "zh" else "EN",
                                  label_visibility="collapsed", key="lang_switch")
    new = "zh" if choice == "中文" else "en"
    if choice and new != cur:
        st.session_state["lang"] = new
        if new == "zh":
            st.query_params["lang"] = "zh"
        elif "lang" in st.query_params:
            del st.query_params["lang"]
        st.rerun()
