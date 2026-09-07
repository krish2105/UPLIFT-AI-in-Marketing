"""The generated footfall series, and the label it cannot be built without.

The generator reads the database, so the heavy end-to-end properties — the
zone elasticity ordering, the Ramadan inversion — are checked by the pipeline's
own `--verify`, which writes docs/results/A7-footfall.json. What is checked here
is what can be checked in isolation: the label invariant, the daypart shapes,
and the weather response as a pure function of outdoor share.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.footfall import (
    COMFORT_APPARENT_C,
    DAYPART_PROFILE,
    daypart_of,
    opening_mask,
    ramadan_factor,
    shape_for,
    weather_factor,
)
from services.api.brand import load_brand
from services.api.simulated import BasketRecord, FootfallRecord, NotLabelledError


class TestTheLabelCannotBeDropped:
    """`simulated` is a constructor invariant, not a convention.

    There is no public hourly footfall series for a Dubai cafe. Inventing one
    is defensible; letting a number out of this module without saying so is not.
    """

    def test_a_record_is_simulated_by_default(self):
        assert FootfallRecord("DXB-MAR", "2026-09-07T19:00", 180, 64).simulated is True

    def test_declaring_a_record_observed_raises(self):
        with pytest.raises(NotLabelledError):
            FootfallRecord("DXB-MAR", "2026-09-07T19:00", 180, 64, simulated=False)

    def test_a_basket_cannot_claim_to_come_from_a_till(self):
        with pytest.raises(NotLabelledError):
            BasketRecord(
                "B1", "C1", "DXB-MAR", "2026-09-07T19:00", 2, 48.0, "evening", sample=False
            )

    def test_the_row_written_to_the_database_carries_the_flag(self):
        assert FootfallRecord("DXB-MAR", "2026-09-07T19:00", 180, 64).as_row()[-1] == 1

    def test_more_transactions_than_visitors_is_rejected(self):
        """A conversion rate above 1.0 is a modelling error, not a rounding one."""
        with pytest.raises(ValueError, match="conversion"):
            FootfallRecord("DXB-MAR", "2026-09-07T19:00", 10, 64)


class TestDaypartShape:
    def test_every_zone_peaks_at_one(self):
        for code in DAYPART_PROFILE:
            assert shape_for(code).max() == pytest.approx(1.0)

    def test_the_day_is_bimodal_for_every_zone(self):
        """A commuter peak and an evening peak with a trough between them. A
        unimodal shape would make the daypart allocator meaningless."""
        for code in DAYPART_PROFILE:
            s = shape_for(code)
            morning = s[6:11].max()
            midday = s[12:16].min()
            evening = s[17:23].max()
            assert midday < morning and midday < evening, f"{code} is not bimodal"

    def test_deira_wakes_earliest_and_marina_latest(self):
        """The brand kit says Deira runs on the early market trade and Marina
        lives after dark. The shapes have to agree with the brand document."""
        peak = {code: int(np.argmax(shape_for(code))) for code in DAYPART_PROFILE}
        assert peak["DXB-DEI"] < peak["DXB-MAR"]
        assert int(np.argmax(shape_for("DXB-DEI")[:12])) < 10

    def test_dayparts_partition_trading_hours(self):
        assert daypart_of(8) == "morning"
        assert daypart_of(13) == "midday"
        assert daypart_of(20) == "evening"
        assert daypart_of(3) == "closed"

    def test_the_boundaries_follow_sidra_trading_hours(self):
        """Deira opens at 06:00 and Marina serves until 01:00. Boundaries set to
        a tidy 07:00-midnight labelled 155 real Deira baskets "closed" and
        discarded Marina's last hour."""
        assert daypart_of(6) == "morning", "Deira opens at 06:00"
        assert daypart_of(0) == "evening", "Marina trades until 01:00"
        assert daypart_of(1) == "evening"
        assert daypart_of(2) == "closed", "and is shut by 02:00"


class TestOpeningHours:
    def test_a_closed_hour_generates_nothing(self):
        """A Gaussian lobe has no natural zero, so without the mask a shut cafe
        still traded a trickle at 04:00 — which reached the POS sample."""
        shape = shape_for("DXB-MOE", "08:00", "23:00")
        assert shape[4] == 0.0
        assert shape[7] == 0.0
        assert shape[19] > 0.0

    def test_a_window_that_wraps_midnight_is_handled(self):
        """Marina Walk closes at 01:00."""
        mask = opening_mask("07:30", "01:00")
        assert mask[0] == 1.0, "00:00 is still trading"
        assert mask[2] == 0.0
        assert mask[8] == 1.0

    def test_every_zone_in_the_brand_kit_produces_a_valid_shape(self):
        for z in load_brand().zones:
            shape = shape_for(z.code, z.opens, z.closes)
            assert shape.max() == pytest.approx(1.0)
            assert (shape >= 0).all()


class TestWeatherResponse:
    """The elasticity is derived from the brand kit's seat counts, so these
    tests assert the emergent behaviour rather than a constant in the source."""

    HOT_EVENING = np.array([21])
    hot = np.array([COMFORT_APPARENT_C + 12])
    mild = np.array([COMFORT_APPARENT_C - 6])
    dry = np.array([0.0])

    def test_an_enclosed_site_barely_moves(self):
        f = weather_factor(self.hot, self.dry, outdoor_share=0.0, hours=self.HOT_EVENING)
        assert 0.93 < f[0] < 1.01, f[0]

    def test_a_terrace_empties_in_the_heat(self):
        f = weather_factor(self.hot, self.dry, outdoor_share=0.53, hours=self.HOT_EVENING)
        assert f[0] < 0.90, f[0]

    def test_a_terrace_fills_when_it_cools(self):
        f = weather_factor(self.mild, self.dry, outdoor_share=0.53, hours=self.HOT_EVENING)
        assert f[0] > 1.03, f[0]

    def test_the_response_is_monotone_in_outdoor_share(self):
        heat = [
            weather_factor(self.hot, self.dry, s, self.HOT_EVENING)[0]
            for s in (0.0, 0.25, 0.5, 0.75)
        ]
        assert heat == sorted(heat, reverse=True), heat

    def test_rain_closes_a_terrace(self):
        wet = weather_factor(self.mild, np.array([3.0]), 0.53, self.HOT_EVENING)[0]
        dry = weather_factor(self.mild, self.dry, 0.53, self.HOT_EVENING)[0]
        assert wet < dry * 0.75

    def test_the_brand_kit_drives_the_ordering(self):
        """If the seat counts change, the elasticity ordering follows. This is
        the property that makes the per-zone forecast argument non-circular."""
        brand = load_brand()
        shares = {z.code: z.outdoor_share for z in brand.zones}
        assert shares["DXB-MAR"] > shares["DXB-DEI"] > shares["DXB-MOE"]
        assert shares["DXB-MOE"] == 0.0


class TestRamadan:
    hours = np.arange(24)
    on = np.ones(24, dtype=bool)
    off = np.zeros(24, dtype=bool)

    def test_ramadan_inverts_the_day_rather_than_scaling_it(self):
        """A single multiplier would average a daytime collapse and an evening
        surge into approximately nothing, which is the mistake a naive holiday
        flag makes."""
        f = ramadan_factor(self.hours, self.on, intensity=1.0)
        assert f[12] < 0.5, "daytime should collapse"
        assert f[20] > 1.5, "after iftar should surge"

    def test_a_non_ramadan_day_is_untouched(self):
        assert np.allclose(ramadan_factor(self.hours, self.off, 1.0), 1.0)

    def test_intensity_scales_both_directions(self):
        weak = ramadan_factor(self.hours, self.on, 0.5)
        strong = ramadan_factor(self.hours, self.on, 1.0)
        assert strong[12] < weak[12], "a stronger collapse in the day"
        assert strong[20] > weak[20], "a stronger surge at night"
