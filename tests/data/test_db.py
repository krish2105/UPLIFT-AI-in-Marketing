"""The database layer: migrations run once, and writes replace rather than duplicate."""

from __future__ import annotations

from services.api.core.db import connect, migrate, upsert_many


def test_migrations_apply_once(tmp_path):
    db = tmp_path / "t.db"
    conn = connect(db)
    assert migrate(conn) == [], "a second migrate() should be a no-op"
    names = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}
    assert "0001_weather" in names


def test_upsert_replaces_on_the_primary_key(tmp_path):
    conn = connect(tmp_path / "t.db")
    cols = (
        "zone_code",
        "ts_local",
        "temp_c",
        "apparent_c",
        "humidity",
        "precip_mm",
        "wind_kmh",
        "source",
    )
    upsert_many(
        conn,
        "weather_hourly",
        cols,
        [("DXB-MAR", "2026-09-01T00:00", 30.0, 34.0, 60, 0, 8, "archive")],
    )
    upsert_many(
        conn,
        "weather_hourly",
        cols,
        [("DXB-MAR", "2026-09-01T00:00", 31.5, 35.0, 61, 0, 9, "forecast")],
    )
    rows = list(conn.execute("SELECT temp_c, source FROM weather_hourly"))
    assert len(rows) == 1, "the same zone-hour must not duplicate"
    assert rows[0]["temp_c"] == 31.5, "the later write wins"
    assert rows[0]["source"] == "forecast"
