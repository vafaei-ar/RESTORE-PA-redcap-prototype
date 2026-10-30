"""Run the Streamlit screens in a clean Python interpreter.

Testing from a clean interpreter catches module shadowing. Exercising the Case
Browser also catches Arrow serialization problems that may be hidden by
Streamlit's automatic type-conversion fallback.
"""
from pathlib import Path
import subprocess
import sys
import textwrap


ROOT = Path(__file__).resolve().parents[1]


def test_isolated_streamlit_startup_and_all_pages():
    script = textwrap.dedent(
        """
        import io
        import logging
        from pathlib import Path
        import pyarrow as pa
        from streamlit.testing.v1 import AppTest

        output = io.StringIO()
        logger = logging.getLogger("streamlit.dataframe_util")
        handler = logging.StreamHandler(output)
        logger.addHandler(handler)
        old_level = logger.level
        logger.setLevel(logging.WARNING)

        try:
            path = Path("app/app.py").resolve()
            app = AppTest.from_file(str(path), default_timeout=60).run()
            assert not app.exception, app.exception

            for page in ("Case Browser", "Registry Entry", "Reports",
                         "Workflow", "Data Dictionary", "Dashboard"):
                app.sidebar.radio[0].set_value(page).run()
                assert not app.exception, (page, app.exception)

                if page == "Case Browser":
                    tables = [
                        item.value for item in app.dataframe
                        if {"Field", "Value"}.issubset(item.value.columns)
                    ]
                    assert len(tables) == 1, "EHR detail table missing"
                    details = tables[0]
                    assert details["Value"].map(lambda v: isinstance(v, str)).all()
                    pa.Table.from_pandas(details, preserve_index=False)

                if page == "Registry Entry":
                    assert any("Registry Data Entry" in x.value for x in app.title)

            assert "Serialization of dataframe to Arrow table was unsuccessful" not in output.getvalue(), output.getvalue()
        finally:
            logger.removeHandler(handler)
            logger.setLevel(old_level)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (
        f"Fresh-interpreter Streamlit test failed:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
