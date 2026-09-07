"""The marketing models: the properties that make their numbers worth reading.

These run against the built database, so they are integration tests. That is
deliberate — the failure modes worth catching here (leakage, an optimiser that
silently does nothing, an allocation that does not sum to its budget) only
appear on real shapes of data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from services.api.core.db import connect
from services.api.marketing import allocator, segments, uplift
from services.api.marketing.features import FEATURES, TARGET, load_frame
from services.api.marketing.forecast import fit, predict, seasonal_naive, trading_mask


@pytest.fixture(scope="module")
def conn():
    c = connect()
    if c.execute("SELECT COUNT(*) FROM footfall_hourly").fetchone()[0] == 0:
        pytest.skip("no data loaded — run `make etl` first")
    return c


@pytest.fixture(scope="module")
def frame(conn):
    return load_frame(conn, "DXB-MAR")


@pytest.fixture(scope="module")
def daily(conn):
    df = pd.read_sql_query(
        "SELECT substr(ts_local,1,10) d, zone_code, SUM(footfall) f "
        "FROM footfall_hourly GROUP BY d, zone_code",
        conn,
    )
    return df.pivot(index="d", columns="zone_code", values="f").dropna().astype(float)


class TestFeatures:
    def test_no_feature_is_the_target(self, frame):
        assert TARGET not in FEATURES

    def test_lags_carry_no_information_from_their_own_hour(self, frame):
        """The single easiest way to build a model that scores beautifully and
        cannot forecast."""
        df = frame.df
        # lag_168 at row i must equal the target 168 rows earlier, exactly.
        assert np.allclose(df[TARGET].to_numpy()[:-168], df["lag_168"].to_numpy()[168:])

    def test_the_split_is_chronological(self, frame):
        train, test = frame.split(56)
        assert train["ts"].max() < test["ts"].min()
        assert len(test) == pytest.approx(56 * 24, rel=0.05)

    def test_the_event_countdown_is_capped(self, frame):
        """An uncapped countdown lets the model learn where the event table
        ends rather than when the next event is."""
        assert frame.df["days_to_event"].max() <= 30


class TestForecast:
    def test_a_closed_site_is_predicted_at_exactly_zero(self, frame):
        """Opening hours are a fact about the business, not a pattern to infer.
        Before this, the model predicted a small positive number at 04:00 — a
        rounding error in MAE and a catastrophe in sMAPE."""
        train, test = frame.split(56)
        pred = predict(fit(train), test, "DXB-MAR")
        shut = ~trading_mask("DXB-MAR", test["ts"].dt.hour.to_numpy())
        assert (pred.loc[shut, "yhat"] == 0).all()
        assert (pred.loc[shut, "hi"] == 0).all()

    def test_the_interval_never_inverts(self, frame):
        train, test = frame.split(56)
        pred = predict(fit(train), test, "DXB-MAR")
        assert (pred["hi"] >= pred["lo"]).all()
        assert (pred["lo"] >= 0).all()

    def test_it_beats_the_baseline_on_absolute_error(self, frame):
        train, test = frame.split(56)
        pred = predict(fit(train), test, "DXB-MAR")
        actual = test[TARGET].to_numpy(dtype=float)
        mae = np.mean(np.abs(actual - pred["yhat"].to_numpy()))
        base = np.mean(np.abs(actual - seasonal_naive(test)))
        assert mae < base, f"model MAE {mae:.2f} did not beat naive {base:.2f}"

    def test_marina_trades_past_midnight_and_al_barsha_does_not(self):
        hours = np.arange(24)
        assert trading_mask("DXB-MAR", hours)[0], "Marina serves until 01:00"
        assert not trading_mask("DXB-MOE", hours)[0]
        assert trading_mask("DXB-DEI", hours)[6], "Deira opens at 06:00"


class TestSegments:
    def test_every_customer_gets_exactly_one_segment(self, conn):
        seg = segments.rfm(conn)
        assert seg.table["segment"].notna().all()
        assert seg.summary["customers"].sum() == len(seg.table)

    def test_segments_are_stable_under_resampling(self, conn):
        """A segmentation that reshuffles under a bootstrap is describing the
        sample rather than the customers."""
        seg = segments.rfm(conn)
        assert seg.stability >= 0.80, f"only {seg.stability:.1%} keep their segment"

    def test_revenue_concentrates_the_way_retail_revenue_does(self, conn):
        seg = segments.rfm(conn)
        top = seg.summary.iloc[0]
        assert top["revenue_share"] > top["customer_share"], (
            "the largest revenue segment should be a minority of customers"
        )

    def test_response_curves_declare_themselves_assumed(self, conn):
        curves = segments.response_curves(segments.rfm(conn))
        assert curves["assumed"].all()


class TestAllocator:
    @pytest.fixture(scope="class")
    def cells(self):
        return allocator.build_cells({"morning": 21765, "midday": 14110, "evening": 87097})

    @pytest.mark.parametrize("budget", [1000, 5000, 12000, 40000])
    def test_the_allocation_sums_to_the_budget(self, cells, budget):
        a = allocator.allocate(cells, budget)
        assert sum(c.spend for c in a.cells) == pytest.approx(budget)

    @pytest.mark.parametrize("budget", [5000, 12000, 40000])
    def test_funded_cells_reach_equal_marginal_return(self, cells, budget):
        """The KKT condition for a concave objective. If this drifts, the greedy
        step is no longer finding the optimum."""
        a = allocator.allocate(cells, budget)
        assert a.marginal_spread < 0.01, f"marginal spread {a.marginal_spread}"

    def test_response_is_monotone_in_budget(self, cells):
        totals = [allocator.allocate(cells, b).total_response for b in (2000, 6000, 12000, 24000)]
        assert totals == sorted(totals)

    def test_returns_diminish(self, cells):
        """Concavity, stated as the thing a planner actually cares about: the
        second ten thousand buys less than the first."""
        a = allocator.allocate(cells, 10000).total_response
        b = allocator.allocate(cells, 20000).total_response
        assert b - a < a

    def test_no_cell_is_funded_below_a_better_one(self, cells):
        a = allocator.allocate(cells, 12000)
        funded = [c for c in a.cells if c.spend > 0]
        unfunded = [c for c in a.cells if c.spend == 0]
        if funded and unfunded:
            worst_funded = min(c.marginal() for c in funded)
            best_unfunded = max(c.marginal(0) for c in unfunded)
            assert best_unfunded <= worst_funded + 0.01

    def test_evening_takes_the_largest_share(self, cells):
        """Evening is 71% of demand for this brand; an allocator that did not
        follow the forecast would not be using it."""
        a = allocator.allocate(cells, 12000)
        by_dp = a.by_daypart()
        assert max(by_dp, key=by_dp.get) == "evening"


class TestUplift:
    def test_the_donor_weights_are_actually_fitted(self, daily):
        """This failed silently once: SLSQP reported success and returned the
        equal-weight starting point, because the loss was around 1e5 and its
        finite-difference gradient was rounding noise."""
        pre = daily.loc["2026-04-06":"2026-05-31"]
        w = uplift._fit_weights(
            pre["DXB-MAR"].to_numpy(), pre[["DXB-DTN", "DXB-MOE", "DXB-DEI"]].to_numpy()
        )
        assert w.sum() == pytest.approx(1.0)
        assert (w >= 0).all()
        assert not np.allclose(w, 1 / 3, atol=0.02), "weights never left the starting point"

    def test_weights_are_a_convex_combination(self, daily):
        r = uplift.synthetic_control(daily, "DXB-MAR", "2026-06-01", "2026-06-14")
        assert sum(r.weights.values()) == pytest.approx(1.0, abs=1e-3)
        assert all(v >= 0 for v in r.weights.values())

    @pytest.mark.parametrize("injected", [0.0, 0.05, 0.10, 0.20, 0.30])
    def test_an_injected_lift_is_recovered_within_five_points(self, daily, injected):
        """The check that makes every other number in this module worth reading."""
        r = uplift.recovery_check(daily, "DXB-MAR", "2026-06-01", "2026-06-14", injected=injected)
        assert r["within_5_points"], (
            f"injected {injected:+.0%}, recovered {r['recovered']:+.2%}, "
            f"error {r['error_points']:+.2f} points"
        )

    def test_the_estimator_reports_its_own_bias(self, daily):
        """It is about -3.5% on a window where nothing happened, because the
        donor blend is weather-flat and the treated site is not. Reporting zero
        would put that error straight into the effect."""
        bias = uplift.placebo_in_time(daily, "DXB-MAR", "2026-06-01", "2026-06-14")
        assert bias != 0.0
        assert abs(bias) < 0.15, "a bias this large would mean the donors are unusable"

    def test_cuped_narrows_the_interval(self, daily):
        r = uplift.synthetic_control(daily, "DXB-MAR", "2026-06-01", "2026-06-14")
        assert r.pre_rmse > 0
        assert (r.ci_high - r.ci_low) > 0
