"""App-level smoke checks for the Streamlit registry entry screen."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app" / "app.py"


def test_dashboard_and_registry_entry_render_without_exceptions():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception, at.exception

    at.sidebar.radio[0].set_value("Registry Entry").run()
    assert not at.exception, at.exception
    assert any("Registry Data Entry" in x.value for x in at.title)
