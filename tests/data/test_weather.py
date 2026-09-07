"""Weather pipeline unit tests.

These never touch the network. The pipeline's own `--verify` mode checks the
loaded data against the provider; what is checked here is the parsing, because
the failure mode that matters is silent: Open-Meteo returns a LIST of blocks in
the order the coordinates were requested, and nothing in the payload says which
block belongs to which site. Mis-pair them and every zone gets another zone's
weather, with no error anywhere.
"""

from __future__ import annotations

import pytest

from pipeline.weather import COLUMNS, _rows

BLOCK = {
    "latitude": 25.2,
    "longitude": 55.3,
    "hourly": {
        "time": ["2026-09-01T00:00", "2026-09-01T01:00"],
        "temperature_2m": [33.1, 32.4],
        "apparent_temperature": [38.0, 37.2],
        "relative_humidity_2m": [62, 65],
        "precipitation": [0.0, 0.0],
        "wind_speed_10m": [11.2, 9.8],
    },
}


def test_rows_are_flattened_in_column_order():
    rows = _rows([BLOCK], ["DXB-DTN"], "archive")
    assert len(rows) == 2
    assert len(rows[0]) == len(COLUMNS)
    row = dict(zip(COLUMNS, rows[0], strict=True))
    assert row["zone_code"] == "DXB-DTN"
    assert row["ts_local"] == "2026-09-01T00:00"
    assert row["temp_c"] == 33.1
    assert row["apparent_c"] == 38.0
    assert row["source"] == "archive"


def test_zone_blocks_are_paired_positionally_and_strictly():
    """The whole correctness of the join rests on this ordering.

    strict=True turns a length mismatch into an exception instead of silently
    dropping the last site — which is the shape this bug would take if a
    coordinate were added to the request and not to the zone list.
    """
    rows = _rows([BLOCK, BLOCK], ["DXB-DTN", "DXB-MAR"], "archive")
    assert {r[0] for r in rows} == {"DXB-DTN", "DXB-MAR"}

    with pytest.raises(ValueError):
        _rows([BLOCK, BLOCK], ["DXB-DTN"], "archive")
    with pytest.raises(ValueError):
        _rows([BLOCK], ["DXB-DTN", "DXB-MAR"], "archive")
