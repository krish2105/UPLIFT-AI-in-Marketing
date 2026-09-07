"""The dataset registry: nothing enters the application unlabelled.

WHY A REGISTRY AND NOT A DOCS PAGE
----------------------------------
docs/datasets.md is for a reader. This is for the running system. Every series
UPLIFT holds is one of four very different things, and a chart that does not
say which is quietly dishonest:

  observed   fetched from a provider and not modified. Weather.
  curated    assembled by the project from public listings, because no
             redistributable feed exists. Events.
  simulated  generated. There is no observed counterpart. Footfall.
  sample     a generated extract standing in for an export a pilot would
             provide. Point-of-sale baskets.

A Dataset cannot be constructed without a licence and one of those four labels
— not "should not", cannot: the constructor raises. The registry is then the
single place the API, the Data tab and every generated report read from, so a
new dataset added without provenance fails the test suite rather than appearing
on a chart with nothing attached to it.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class Label(StrEnum):
    OBSERVED = "observed"
    CURATED = "curated"
    SIMULATED = "simulated"
    SAMPLE = "sample"

    @property
    def caveat(self) -> str:
        """The sentence the interface shows beside this data. Held here so the
        wording cannot drift between the API, the web app and the report."""
        return {
            Label.OBSERVED: "Fetched from the source named below and not modified.",
            Label.CURATED: (
                "Assembled by this project from public listings because no "
                "redistributable feed exists. Dates sit inside each series' "
                "established window and are not individually confirmed."
            ),
            Label.SIMULATED: (
                "Generated. There is no observed counterpart — a real pilot would "
                "replace this with an actual footfall or point-of-sale export."
            ),
            Label.SAMPLE: ("A generated extract standing in for the export a pilot would provide."),
        }[self]


class UnlabelledDataset(ValueError):
    """Raised when a dataset is registered without provenance."""


@dataclass(frozen=True)
class Dataset:
    key: str
    table: str
    title: str
    label: Label
    licence: str
    source_name: str
    source_url: str
    #: ISO date the source was last verified by actually fetching it.
    verified: str
    built_by: str
    description: str
    #: Column carrying the row timestamp, used to compute span and freshness.
    time_column: str = ""

    def __post_init__(self) -> None:
        if not self.licence.strip():
            raise UnlabelledDataset(
                f"{self.key}: a dataset without a licence cannot be shown or cited"
            )
        if not isinstance(self.label, Label):
            raise UnlabelledDataset(f"{self.key}: label must be one of {[i.value for i in Label]}")
        if not self.source_url.strip():
            raise UnlabelledDataset(f"{self.key}: no source URL")
        if not self.built_by.strip():
            raise UnlabelledDataset(f"{self.key}: no script recorded as having built it")

    def snapshot(self, conn: sqlite3.Connection) -> dict:
        """Live row count and time span, read from the database itself.

        Read rather than stored, because a stored count is a claim that goes
        stale silently the moment a pipeline runs.
        """
        try:
            rows = conn.execute(f"SELECT COUNT(*) FROM {self.table}").fetchone()[0]
        except sqlite3.OperationalError:
            return {**self.as_dict(), "rows": 0, "span": None, "present": False}

        span = None
        if self.time_column and rows:
            lo, hi = conn.execute(
                f"SELECT MIN({self.time_column}), MAX({self.time_column}) FROM {self.table}"
            ).fetchone()
            span = [lo, hi]
        return {**self.as_dict(), "rows": rows, "span": span, "present": rows > 0}

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "table": self.table,
            "title": self.title,
            "label": self.label.value,
            "caveat": self.label.caveat,
            "licence": self.licence,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "verified": self.verified,
            "built_by": self.built_by,
            "description": self.description,
        }


REGISTRY: tuple[Dataset, ...] = (
    Dataset(
        key="weather_hourly",
        table="weather_hourly",
        title="Hourly weather for the four sites",
        label=Label.OBSERVED,
        licence="CC BY 4.0 — attribution to Open-Meteo required",
        source_name="Open-Meteo historical reanalysis and forecast",
        source_url="https://open-meteo.com/",
        verified="2026-09-07",
        built_by="pipeline/weather.py",
        time_column="ts_local",
        description=(
            "ERA5 reanalysis on roughly an 11 km grid, so the four sites land in "
            "nearby cells about a degree apart. The zones differ in how they "
            "RESPOND to weather, not in what weather they get."
        ),
    ),
    Dataset(
        key="calendar_days",
        table="calendar_days",
        title="UAE public holidays, Ramadan and school breaks",
        label=Label.CURATED,
        licence="Public information; Hijri conversion via hijridate (MIT)",
        source_name="u.ae public holidays, converted with the Umm al-Qura calendar",
        source_url="https://u.ae/en/information-and-services/public-holidays-and-religious-affairs/public-holidays",
        verified="2026-09-07",
        built_by="pipeline/calendar.py",
        time_column="date_local",
        description=(
            "Islamic holidays are determined by moon sighting, so those rows are "
            "calculated and carry one day of uncertainty. School breaks are "
            "approximate windows: KHDA's calendar is not machine-readable."
        ),
    ),
    Dataset(
        key="events",
        table="events",
        title="Dubai events",
        label=Label.CURATED,
        licence=(
            "Curated by this project from public listings; each row links the "
            "organiser's own page. Wikipedia summaries are CC BY-SA 4.0."
        ),
        source_name="Public event listings, enriched from Wikipedia",
        source_url="https://en.wikipedia.org/",
        verified="2026-09-07",
        built_by="pipeline/events.py",
        time_column="start_date",
        description=(
            "visitdubai.com returns 403 to non-browser clients and no "
            "redistributable feed exists. Series, venues and windows are real; "
            "the dates of a given edition sit inside the established window and "
            "are not individually confirmed."
        ),
    ),
    Dataset(
        key="footfall_hourly",
        table="footfall_hourly",
        title="Hourly footfall per site",
        label=Label.SIMULATED,
        licence="Generated by this project; no third-party rights",
        source_name="pipeline/footfall.py, seeded",
        source_url="https://github.com/krish2105/UPLIFT-AI-in-Marketing",
        verified="2026-09-07",
        built_by="pipeline/footfall.py",
        time_column="ts_local",
        description=(
            "No public hourly footfall series exists for a Dubai cafe. This is "
            "generated from the brand kit's seat counts and trading hours, "
            "coupled to the weather, calendar and event tables. The evaluation "
            "against a seasonal-naive baseline is what keeps it honest."
        ),
    ),
    Dataset(
        key="pos_baskets",
        table="pos_baskets",
        title="Point-of-sale basket sample",
        label=Label.SAMPLE,
        licence="Generated by this project; no third-party rights",
        source_name="pipeline/footfall.py, seeded",
        source_url="https://github.com/krish2105/UPLIFT-AI-in-Marketing",
        verified="2026-09-07",
        built_by="pipeline/footfall.py",
        time_column="ts_local",
        description=(
            "A basket-level extract for RFM segmentation, sampled from the "
            "generated transactions with a heterogeneous customer base so the "
            "segmentation has real structure to find."
        ),
    ),
)


def by_key(key: str) -> Dataset:
    for d in REGISTRY:
        if d.key == key:
            return d
    raise KeyError(f"no dataset {key!r}; have {[d.key for d in REGISTRY]}")


def freshness(conn: sqlite3.Connection) -> dict:
    """Everything the Data tab and the report need, in one payload."""
    datasets = [d.snapshot(conn) for d in REGISTRY]
    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "datasets": datasets,
        "totals": {
            "datasets": len(datasets),
            "rows": sum(d["rows"] for d in datasets),
            "by_label": {
                label.value: sum(1 for d in datasets if d["label"] == label.value)
                for label in Label
            },
        },
        # Stated in the payload rather than only in the UI, so any consumer —
        # including a generated report — carries it.
        "standing_note": (
            "Footfall and point-of-sale figures are generated for a fictional "
            "brand and have no observed counterpart. Every row carries its label."
        ),
    }
