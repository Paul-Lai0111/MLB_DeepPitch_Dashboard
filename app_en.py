"""Compatibility entry point for the original deployment: opens DeepPitch in English."""
import runpy

runpy.run_path("app.py", run_name="__main__")
