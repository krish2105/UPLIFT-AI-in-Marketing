# Data sources

Every source UPLIFT can read, with the URL, the date it was last verified **by
running it**, and its licence. Where a source turned out to be unusable, the
fallback actually in use is named here and the reason is given — the failures
are on this page as prominently as the successes, because which sources refused
is part of what shaped the design.

**Standing rule:** only free, licensed sources. Nothing behind a paywall, a
request form or a signup. Where a licence requires attribution, UPLIFT complies
rather than working around it.

**Everything below was verified on 2026-09-07 by fetching it**, not by reading
documentation. The pipelines re-check their own output on every run and write to
`docs/results/`; the Data tab reads the same registry
(`services/api/data/registry.py`), so a dataset cannot appear in the application
without the provenance on this page.

## The four labels

A chart that does not say which of these it is showing is quietly dishonest, so
the label is a database column and a constructor invariant, not a footnote.

| Label | Means |
|---|---|
| `observed` | Fetched from the named source and not modified. |
| `curated` | Assembled by this project from public listings because no redistributable feed exists. |
| `simulated` | Generated. There is no observed counterpart. |
| `sample` | A generated extract standing in for an export a pilot would provide. |

---

## Weather — `observed`

| | |
|---|---|
| Source | Open-Meteo historical reanalysis and forecast |
| Endpoints | `archive-api.open-meteo.com/v1/archive`, `api.open-meteo.com/v1/forecast` |
| Licence | **CC BY 4.0**, attribution required. No key, no signup. |
| Verified | 2026-09-07 — HTTP 200, hourly arrays for all four sites in one call |
| Loaded | 72,192 rows, 18,048 per site, 2024-09-01 → 2026-09-22 |
| Rebuild | `uv run python -m pipeline.weather --verify` → [`A4-weather-etl.json`](results/A4-weather-etl.json) |

**The caveat that matters.** The archive is ERA5 reanalysis on roughly an 11 km
grid. Dubai is small, so the four sites do not each get their own station — they
land in nearby grid cells about a degree apart, and the pipeline measures and
stores that snap. The zones differ mainly in how they **respond** to weather,
not in what weather they get: Marina Walk is 46 of 86 seats outdoors and Al
Barsha is fully enclosed.

---

## Calendar — `curated`

| | |
|---|---|
| Rule set | [u.ae public holidays](https://u.ae/en/information-and-services/public-holidays-and-religious-affairs/public-holidays) |
| Conversion | Umm al-Qura tabular calendar via `hijridate` (MIT) |
| Licence | Public government information; converter is MIT |
| Verified | 2026-09-07 — page fetched and the rule set read off it |
| Loaded | 1,161 days, 2024-08-08 → 2027-10-12 |
| Rebuild | `uv run python -m pipeline.calendar --verify` → [`A5-calendar.json`](results/A5-calendar.json) |

The rule set as published: Eid al-Fitr 1–3 Shawwal, Arafah 9 Dhu al-Hijjah, Eid
al-Adha 10–12 Dhu al-Hijjah, Islamic New Year 1 Muharram, the Prophet's birthday
12 Rabi' al-Awwal, New Year 1 January, National Day 2–3 December.
**Commemoration Day is widely repeated elsewhere and is not in that list**, so
it is not in this dataset either.

The computed dates reproduce all four 2025 UAE observances — Ramadan day 1 on
1 March, Eid al-Fitr 30 March, Arafah 5 June, Eid al-Adha 6 June. That is
evidence, not proof: u.ae states that Islamic holidays are determined by moon
sighting, so every Islamic row carries `date_uncertainty_days = 1` and
`confidence = 'calculated'`.

### ⚠ Nager.Date — NOT USABLE

`https://date.nager.at/api/v3/PublicHolidays/2025/AE` returns **HTTP 204 No
Content**: the AE calendar is not in that dataset. Checked 2026-09-07.
**Fallback in use:** the Hijri conversion above, calibrated against the four
2025 observances.

### ⚠ School calendar — approximate, and says so

KHDA's academic-calendar page 301-redirects to `web.khda.gov.ae`, whose
certificate chain does not verify; the Ministry of Education site does not
publish the calendar machine-readably; and the u.ae path for it returns 404. All
three checked 2026-09-07.

**Fallback in use:** three approximate windows — the summer exodus, the winter
break and the spring break — carried in a separate
`school_break_confidence = 'approximate'` column. These are broad and stable
enough that a week either way does not move the demand signal. A pilot would
replace them with the school's actual calendar.

---

## Events — `curated`

| | |
|---|---|
| Source | Public event listings; each row links the organiser's own page |
| Enrichment | Wikipedia REST API — **CC BY-SA 4.0**, attributed |
| Licence | Curated by this project; Wikipedia summaries CC BY-SA 4.0 |
| Verified | 2026-09-07 |
| Loaded | 245 instances across 55 series, 48 carrying a Wikipedia summary |
| Rebuild | `uv run python -m pipeline.events --verify` → [`A6-events.json`](results/A6-events.json) |

**What is real and what is derived.** Real: the series, its venue, its
coordinates, its category, and the calendar window it has occupied for years.
Derived: the exact dates of a given edition, placed inside that window and
carrying `date_confidence = 'annual_window'`. No row claims a verified date, and
a pipeline check fails if one ever does. Ramadan and Eid events take their dates
from the calendar pipeline instead and inherit its moon-sighting caveat.

Wikipedia's REST API returns **403** to a default user agent and **429** to a
fast loop, both observed. Requests carry a descriptive agent per the Wikimedia
user-agent policy, are throttled to roughly one a second, and are cached.

### ⚠ Visit Dubai — NOT USABLE

`https://www.visitdubai.com/en/whats-on` returns **HTTP 403** to every
non-browser client; the CDN blocks on user agent rather than on `robots.txt`,
which permits the path. Checked 2026-09-07. There is no public Dubai events feed
with a licence permitting redistribution.

**Fallback in use:** the curated set above — exactly the fallback the master
plan named in advance.

### ⚠ Open-data portals — NOT USABLE

`dubaipulse.gov.ae` and `opendata.gov.ae` do not resolve from this network;
`uaelegislation.gov.ae` returns **403**. `bayanat.ae` returns 200 and is
recorded as a secondary source, but carries no events feed this project needs.

---

## Footfall — `simulated`

| | |
|---|---|
| Source | `pipeline/footfall.py`, seed 20260907 |
| Licence | Generated by this project; no third-party rights |
| Loaded | 72,192 rows, four sites, 2024-09-01 → 2026-09-22 |
| Rebuild | `uv run python -m pipeline.footfall --verify` → [`A7-footfall.json`](results/A7-footfall.json) |

**No public hourly footfall series exists for any Dubai café.** This is
generated, and that is stated on every row, in every API response and on every
chart. `FootfallRecord` cannot be constructed without `simulated=True`; the
database column is `NOT NULL CHECK (simulated = 1)`.

The generator is coupled to the other three datasets — weather against each
site's outdoor seat share, the calendar's Ramadan and holiday flags, and event
pull decayed by distance. The elasticities are **derived from the brand kit's
seat counts**, not written into the generator, so the measured result that
Marina Walk is 2.4× more temperature-sensitive than Al Barsha is emergent rather
than assumed.

What is *not* invented is the evaluation: Phase B scores the forecaster against
a seasonal-naive baseline on held-out data, and a model that cannot beat it is
not used.

A real pilot replaces this dataset with an actual footfall or point-of-sale
export. Nothing else in the system changes.

---

## Point-of-sale baskets — `sample`

| | |
|---|---|
| Source | `pipeline/footfall.py`, seed 20260907 |
| Licence | Generated by this project; no third-party rights |
| Loaded | 8,737 baskets over ~1,850 customers, 12 months |
| File | `data/pos_sample.csv` |

A basket-level extract for RFM segmentation, sampled from the generated
transactions at 0.8% with a heterogeneous customer base, so the segmentation has
real structure to find rather than a single Poisson blob.

---

## Compliance corpus — `observed`, ingested in Phase C

The documents the Compliance agent cites. Each was verified reachable on
2026-09-07. The *landing pages* answer 200. The **clause text does not**, and
that distinction is the whole of what `clause_verified` records.

Three of eleven rules cite a clause that has been read. The other eight cite a
section by title, and say so. Closing the gap needs the standard's own text, and
the standard's own text is not retrievable from a script: the Codex PDFs sit
behind `fao.org/fao-who-codexalimentarius/sh-proxy/`, which returns **HTTP 403**
to curl with and without a browser user-agent (retried 2026-09-07), and the
direct `input/download/standards/` path returns **404**. It is the same wall
Visit Dubai puts up, and it has the same honest answer: name it, and do not
pretend past it.

So the eight stay `clause_verified: false`, the generated brand PDF prints
"clause unverified" beside each, and the Compliance tab shows the section title
rather than a quotation. What is NOT done is the tempting thing — writing
plausible clause text from memory of the standard, which would produce a
citation that looks verified, reads correctly, and is unsourced. A rule that
cites a section it has genuinely located is worth more than a quotation nobody
can trace.

**What would close it:** a human opening each PDF in a browser and pasting the
clause into `data/brand/sidra.yaml`, then flipping the flag. The schema, the PDF
generator, the API response and the UI already carry the verified case — three
rules use it today, so the path is exercised rather than theoretical.

| Document | Publisher | Verified |
|---|---|---|
| **CXG 23-1997** Guidelines for Use of Nutrition and Health Claims (rev. 2013) | FAO/WHO Codex Alimentarius | 2026-09-07 — 200 |
| **CXG 2-1985** Guidelines on Nutrition Labelling (rev. 2024) | FAO/WHO Codex Alimentarius | 2026-09-07 — 200 |
| Consumer protection guidance | [UAE Ministry of Economy and Tourism](https://www.moec.gov.ae/en/consumer-protection) | 2026-09-07 — 200 |
| Food safety and labelling guidance | [Dubai Municipality](https://www.dm.gov.ae/) | 2026-09-07 — 200 |
| Media and advertising guidance | [UAE Media Office](https://www.mediaoffice.ae/en) | 2026-09-07 — 200 |
| SIDRA brand guidelines | This project (fictional brand) | generated from `data/brand/sidra.yaml` |

`uaemediacouncil.gov.ae` does not resolve from this network and is not used.
EUR-Lex Regulation 1924/2006 and the UK CAP food rules are reachable and are
recorded as comparators, attributed, rather than as UAE authority.
