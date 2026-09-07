"""Events pipeline: the pure expansion logic, with no network and no database.

The three things that would silently corrupt every event feature are the
year-wrapping window, the month segmentation, and the distance calculation —
none of which raise when they are wrong, they just produce plausible numbers.
"""

from __future__ import annotations

from datetime import date

import pytest

from pipeline.events import (
    MAX_SEGMENT_DAYS,
    CoordinateError,
    _contiguous,
    _segments,
    _window_instances,
    assert_in_uae,
    haversine_km,
)


class TestDistance:
    def test_a_zone_is_zero_from_itself(self):
        assert haversine_km(25.0805, 55.1403, 25.0805, 55.1403) == 0.0

    def test_marina_to_deira_is_about_twenty_five_km(self):
        """The two extremes of the estate. A flat-earth approximation or a
        swapped lat/lon both still return a number; only the magnitude tells
        you which one you got."""
        d = haversine_km(25.0805, 55.1403, 25.2653, 55.3218)
        assert 24 < d < 30, d

    def test_a_transposition_is_NOT_detectable_from_the_distance(self):
        """The reason the bounding-box guard exists.

        Dubai sits near 25N 55E, so swapping latitude and longitude yields
        another plausible pair. The distance between two swapped Dubai points is
        23.3 km against a correct 27.5 km — comfortably inside any range check
        anyone would write. This test pins that fact so nobody later replaces
        the bounding box with a cheaper-looking sanity check on the magnitude.
        """
        correct = haversine_km(25.0805, 55.1403, 25.2653, 55.3218)
        swapped = haversine_km(55.1403, 25.0805, 55.3218, 25.2653)
        assert abs(correct - swapped) < 5, (
            "if this now differs a lot, the coordinates changed — but do not "
            "conclude that magnitude is a sufficient guard"
        )


class TestCoordinateGuard:
    def test_the_four_zones_and_a_far_venue_all_pass(self):
        assert_in_uae("marina", 25.0805, 55.1403)
        assert_in_uae("hatta", 24.7980, 56.1180)

    def test_a_transposed_coordinate_is_rejected(self):
        """What the distance check could not see, the bounding box catches."""
        with pytest.raises(CoordinateError, match="transposed"):
            assert_in_uae("marina", 55.1403, 25.0805)

    def test_a_venue_in_another_country_is_rejected(self):
        with pytest.raises(CoordinateError):
            assert_in_uae("london", 51.5074, -0.1278)


class TestWindowExpansion:
    START, END = date(2024, 9, 1), date(2026, 12, 31)

    def test_a_simple_window_yields_one_instance_per_year(self):
        got = _window_instances([[10, 13], [10, 17]], self.START, self.END)
        assert [s.year for s, _ in got] == [2024, 2025, 2026]
        assert all(e.month == 10 and (e - s).days == 4 for s, e in got)

    def test_a_wrapping_window_ends_in_the_following_year(self):
        """Global Village opens in October and closes in April. Read naively
        this is a negative-length event."""
        got = _window_instances([[10, 16], [4, 30]], self.START, self.END)
        for s, e in got:
            assert e > s, f"{s} to {e} runs backwards"
            assert e.year == s.year + 1

    def test_the_29th_of_february_is_skipped_in_a_common_year(self):
        got = _window_instances([[2, 29], [2, 29]], date(2023, 1, 1), date(2026, 1, 1))
        assert [s.year for s, _ in got] == [2024], "only the leap year has the date"


class TestSegmentation:
    def test_a_short_run_passes_through_whole(self):
        assert _segments(date(2025, 10, 13), date(2025, 10, 17)) == [
            (date(2025, 10, 13), date(2025, 10, 17))
        ]

    def test_a_long_season_is_split_at_calendar_month_boundaries(self):
        """A 197-day 'Global Village season' row would be on for more than half
        the series and carry no information as a feature."""
        segs = _segments(date(2025, 10, 16), date(2026, 4, 30))
        assert len(segs) == 7
        assert segs[0] == (date(2025, 10, 16), date(2025, 10, 31))
        assert segs[1] == (date(2025, 11, 1), date(2025, 11, 30))
        assert segs[-1] == (date(2026, 4, 1), date(2026, 4, 30))

    def test_segments_are_contiguous_and_cover_the_whole_run(self):
        start, end = date(2025, 10, 16), date(2026, 4, 30)
        segs = _segments(start, end)
        assert segs[0][0] == start and segs[-1][1] == end
        for a, b in zip(segs, segs[1:], strict=False):
            assert (b[0] - a[1]).days == 1, "a gap or an overlap between segments"

    def test_no_segment_exceeds_the_cap(self):
        for a, b in _segments(date(2025, 10, 16), date(2026, 4, 30)):
            assert (b - a).days + 1 <= MAX_SEGMENT_DAYS


class TestContiguousRuns:
    def test_consecutive_days_collapse_into_one_run(self):
        days = [date(2026, 3, 20), date(2026, 3, 21), date(2026, 3, 22)]
        assert _contiguous(days) == [(date(2026, 3, 20), date(2026, 3, 22))]

    def test_a_gap_starts_a_new_run(self):
        days = [date(2026, 3, 20), date(2026, 3, 21), date(2026, 5, 27)]
        assert _contiguous(days) == [
            (date(2026, 3, 20), date(2026, 3, 21)),
            (date(2026, 5, 27), date(2026, 5, 27)),
        ]

    def test_an_empty_list_is_no_runs(self):
        assert _contiguous([]) == []
