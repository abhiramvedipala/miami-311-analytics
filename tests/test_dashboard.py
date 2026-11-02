from pathlib import Path

import duckdb
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent.parent / "dashboard" / "app.py")


def test_dashboard_renders_every_tab_from_the_mart(small_db):
    con = duckdb.connect(str(small_db))
    con.execute(
        """
        CREATE TABLE mart.anomalies AS SELECT DATE '2025-03-03' AS week_start, 'Pothole' AS request_type, 9.0 AS z,
            600 AS requests, 100.0 AS expected, 'Hurricane' AS event, 'A note' AS note
        """
    )
    con.close()
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    assert app.metric[0].value == "1,202"
    assert app.metric[1].value == "2"
    assert [tab.label for tab in app.tabs] == ["Overview", "Time to close", "Backlog", "Anomalies"]
