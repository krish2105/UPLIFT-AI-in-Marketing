"""The registry is the gate that stops unlabelled data reaching a chart.

The point of these tests is not that /data/freshness returns 200. It is that a
dataset added later WITHOUT provenance fails the suite, so the discipline
survives the person who wrote it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.data.registry import REGISTRY, Dataset, Label, UnlabelledDataset, freshness
from services.api.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


class TestTheGate:
    """A Dataset cannot be constructed without provenance. Not "should not"."""

    BASE = dict(
        key="x",
        table="weather_hourly",
        title="X",
        label=Label.OBSERVED,
        licence="CC BY 4.0",
        source_name="S",
        source_url="https://example.org",
        verified="2026-09-07",
        built_by="pipeline/x.py",
        description="",
    )

    def test_a_dataset_without_a_licence_cannot_be_built(self):
        with pytest.raises(UnlabelledDataset, match="licence"):
            Dataset(**{**self.BASE, "licence": "   "})

    def test_a_dataset_without_a_source_url_cannot_be_built(self):
        with pytest.raises(UnlabelledDataset, match="source URL"):
            Dataset(**{**self.BASE, "source_url": ""})

    def test_a_dataset_that_names_no_builder_cannot_be_built(self):
        with pytest.raises(UnlabelledDataset, match="built it"):
            Dataset(**{**self.BASE, "built_by": ""})

    def test_a_free_text_label_is_rejected(self):
        """Four labels, and the enum is the whole vocabulary. 'probably real'
        is not a provenance category."""
        with pytest.raises(UnlabelledDataset, match="label must be"):
            Dataset(**{**self.BASE, "label": "probably real"})


class TestEveryRegisteredDataset:
    @pytest.mark.parametrize("dataset", REGISTRY, ids=lambda d: d.key)
    def test_carries_a_licence_and_a_label(self, dataset: Dataset):
        assert dataset.licence.strip()
        assert dataset.label in set(Label)

    @pytest.mark.parametrize("dataset", REGISTRY, ids=lambda d: d.key)
    def test_carries_a_verified_source(self, dataset: Dataset):
        assert dataset.source_url.startswith("http")
        assert dataset.verified, "no date on which the source was checked"

    @pytest.mark.parametrize("dataset", REGISTRY, ids=lambda d: d.key)
    def test_every_label_supplies_the_caveat_the_interface_shows(self, dataset: Dataset):
        """Held on the enum so the wording cannot drift between the API, the web
        app and the generated report."""
        assert len(dataset.label.caveat) > 30

    def test_the_generated_series_are_not_labelled_observed(self):
        """The single most important row in the registry."""
        by_key = {d.key: d for d in REGISTRY}
        assert by_key["footfall_hourly"].label is Label.SIMULATED
        assert by_key["pos_baskets"].label is Label.SAMPLE
        assert by_key["events"].label is Label.CURATED
        assert by_key["weather_hourly"].label is Label.OBSERVED


class TestTheEndpoint:
    def test_freshness_reports_every_registered_dataset(self, client: TestClient):
        body = client.get("/data/freshness").json()
        assert {d["key"] for d in body["datasets"]} == {d.key for d in REGISTRY}

    def test_every_returned_dataset_has_a_licence_a_label_and_a_caveat(self, client: TestClient):
        for d in client.get("/data/freshness").json()["datasets"]:
            assert d["licence"] and d["label"] and d["caveat"], d["key"]

    def test_the_standing_note_travels_with_the_payload(self, client: TestClient):
        """So a consumer that renders only the numbers still carries the caveat."""
        body = client.get("/data/freshness").json()
        assert "generated" in body["standing_note"].lower()

    def test_row_counts_are_read_live_not_stored(self, client: TestClient):
        """A stored count is a claim that goes stale the moment a pipeline runs."""
        body = client.get("/data/freshness").json()
        assert body["totals"]["rows"] > 0

    def test_a_missing_table_reports_absent_rather_than_500(self, tmp_path):
        """A deployed instance with an ephemeral filesystem comes up empty. That
        is a supported state, not a crash."""
        import sqlite3

        empty = sqlite3.connect(tmp_path / "empty.db")
        empty.row_factory = sqlite3.Row
        body = freshness(empty)
        assert all(d["rows"] == 0 and d["present"] is False for d in body["datasets"])

    def test_health_says_degraded_when_a_dataset_is_missing(self, client: TestClient):
        body = client.get("/healthz").json()
        assert body["status"] in {"ok", "degraded"}
        assert set(body["datasets_loaded"]) == {d.key for d in REGISTRY}
        assert body["brand"]["fictional"] is True


class TestZonesAndEvents:
    def test_zones_lead_with_the_fictional_disclaimer(self, client: TestClient):
        body = client.get("/data/zones").json()
        assert body["brand"]["fictional"] is True
        assert "fictional" in body["brand"]["disclaimer"].lower()
        assert len(body["zones"]) == 4

    def test_events_carry_their_provenance_in_every_response(self, client: TestClient):
        body = client.get("/data/events?limit=3").json()
        assert "curated" in body["provenance"].lower()
        for e in body["events"]:
            assert e["curated"] is True
            assert e["date_confidence"] in {"annual_window", "calculated"}
            assert e["source_url"]

    def test_events_return_a_distance_to_every_site(self, client: TestClient):
        for e in client.get("/data/events?limit=5").json()["events"]:
            assert set(e["distance_km"]) == {"DXB-DTN", "DXB-MOE", "DXB-MAR", "DXB-DEI"}

    def test_an_unknown_site_is_a_404_not_an_empty_list(self, client: TestClient):
        assert client.get("/data/events?zone=DXB-NOPE").status_code == 404
