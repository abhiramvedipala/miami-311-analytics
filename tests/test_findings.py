import duckdb

import write_findings
from ingest import connect


def test_findings_and_readme_block_come_from_the_database(small_db, tmp_path, monkeypatch):
    con = duckdb.connect(str(small_db))
    con.execute(
        """
        CREATE TABLE mart.anomalies AS SELECT DATE '2025-03-03' AS week_start, 'Pothole' AS request_type, 9.0 AS z,
            'A planted note.' AS note
        """
    )
    con.close()
    con = connect()
    f = write_findings.facts(con)
    con.close()
    assert "33101 (MIAMI)" in write_findings.findings_text(f)
    assert "A planted note." in write_findings.findings_text(f)
    table = write_findings.results_table(f)
    assert "| Requests analysed (duplicates excluded) | 1,202 |" in table
    assert write_findings.RESULTS_BLOCK.fullmatch(table)
