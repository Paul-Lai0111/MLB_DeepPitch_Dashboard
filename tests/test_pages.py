"""Smoke test: every page renders without an exception, in both languages."""
import pytest
from streamlit.testing.v1 import AppTest

PAGES = ["home", "pitcher", "compare", "leaders", "lab", "guide", "insights", "methods"]


@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page, lang):
    at = AppTest.from_file("../app.py", default_timeout=90)
    at.session_state["lang"] = lang
    at.run()
    at.switch_page(f"app_pages/{page}.py").run()
    assert not at.exception, at.exception
