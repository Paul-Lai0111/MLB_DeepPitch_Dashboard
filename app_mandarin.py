"""Compatibility entry point for the original deployment (its main file is still app_mandarin.py).

DeepPitch opens in English; visitors switch to Traditional Chinese with the 中文 toggle or ?lang=zh.
"""
import runpy

runpy.run_path("app.py", run_name="__main__")
