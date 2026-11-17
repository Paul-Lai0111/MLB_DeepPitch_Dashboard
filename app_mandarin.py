"""Compatibility entry point for the original deployment: opens DeepPitch in Traditional Chinese."""
import runpy

import streamlit as st

st.session_state.setdefault("lang", "zh")
runpy.run_path("app.py", run_name="__main__")
