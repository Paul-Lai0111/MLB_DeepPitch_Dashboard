"""DeepPitch — the physics scorebook of every MLB pitch.

Run locally:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="DeepPitch · MLB pitch physics", page_icon="image/icon.png", layout="wide",
                   initial_sidebar_state="collapsed")

from deeppitch import theme  # noqa: E402  (registers the plotly template)
from deeppitch.i18n import L, lang, language_switch  # noqa: E402

theme.inject()
lang()
_, right = st.columns([5, 1])
with right:
    language_switch()

pages = [
    st.Page("app_pages/home.py", title=L("The Book", "總覽"), default=True),
    st.Page("app_pages/pitcher.py", title=L("Pitchers", "投手"), url_path="pitcher"),
    st.Page("app_pages/compare.py", title=L("Compare", "比較"), url_path="compare"),
    st.Page("app_pages/leaders.py", title=L("Leaders", "排行榜"), url_path="leaders"),
    st.Page("app_pages/lab.py", title=L("Physics Lab", "物理實驗室"), url_path="lab"),
    st.Page("app_pages/guide.py", title=L("Field Guide", "指標圖鑑"), url_path="guide"),
    st.Page("app_pages/insights.py", title=L("Does It Matter?", "真的有用嗎？"), url_path="insights"),
    st.Page("app_pages/methods.py", title=L("Methods", "方法與模型"), url_path="methods"),
]
nav = st.navigation(pages, position="top")
nav.run()
