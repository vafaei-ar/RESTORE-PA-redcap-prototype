"""Launch Streamlit in a fresh Python interpreter.

The usual pytest process may import the registry package before the UI,
masking the script/module naming collision in a real Streamlit launch.
This test deliberately avoids importing project modules in its parent process.
"""
from pathlib import Path
import subprocess
import sys
import textwrap


ROOT = Path(__file__).resolve().parents[1]


def test_isolated_streamlit_startup_and_registry_entry():
    script = textwrap.dedent(
        """
        from pathlib import Path
        from streamlit.testing.v1 import AppTest

        path = Path("app/app.py").resolve()
        app = AppTest.from_file(str(path), default_timeout=60).run()
        assert not app.exception, app.exception

        app.sidebar.radio[0].set_value("Registry Entry").run()
        assert not app.exception, app.exception
        assert any("Registry Data Entry" in title.value for title in app.title)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=100,
        check=False,
    )
    assert result.returncode == 0, (
        f"Fresh-interpreter Streamlit test failed:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
