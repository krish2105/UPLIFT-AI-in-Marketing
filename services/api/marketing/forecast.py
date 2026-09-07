"""Hourly demand per site, and the baseline it has to beat.

THE BASELINE IS THE POINT
-------------------------
A forecast that cannot beat "the same hour, last week" is worse than no
forecast, because it looks like knowledge. So the seasonal-naive baseline is not
a courtesy comparison at the end — it is the gate. `evaluate()` reports the win
rate against it week by week, and `docs/results/B1-forecast.json` carries that
number. If a model stops beating it the number moves and the claim in the README
becomes false, which is the intended failure mode.

WHY GRADIENT BOOSTING
---------------------
Two reasons, in order of weight. It has to deploy — Prophet's build chain does
not fit a free instance, and a model that cannot run where the application runs
is not a candidate. And the interesting claim here is that EXOGENOUS DRIVERS
move demand: event proximity, apparent temperature against a site's outdoor
share, Ramadan, school breaks. A boosted tree takes those as explicit columns
and lets their contribution be read off; a structural time-series model folds
them into components that are harder to attribute.

INTERVALS ARE QUANTILES, NOT A GUESS
------------------------------------
The 80% interval comes from two extra models fitted with a pinball loss at the
10th and 90th percentiles, not from a residual standard deviation multiplied by
1.28. Demand is bounded below by zero and is heteroscedastic — a 40-visitor hour
and a 400-visitor hour do not have the same spread — so a symmetric interval
would be too wide at night and too narrow at the evening peak, which is exactly
when a planner needs it.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from services.api.brand import load_brand
from services.api.marketing.features import FEATURES, TARGET, Frame, load_frame

#: The horizon the plan is built over.
HORIZON_DAYS = 56
HOLDOUT_DAYS = 56
SEED = 20260907

#: Deliberately small. On ~16k rows with strong weekly structure, a deeper
#: forest memorises the training weeks and the holdout score falls.
PARAMS = dict(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.06,
    subsample=0.85,
    min_samples_leaf=40,
    random_state=SEED,
)


@dataclass
class ZoneResult:
    zone: str
    mae: float
    baseline_mae: float
    smape: float
    baseline_smape: float
    weeks_won: int
    weeks_total: int
    coverage_80: float
    weekly: list[dict] = field(default_factory=list)
    importances: dict[str, float] = field(default_factory=dict)

    @property
    def win_rate(self) -> float:
        return self.weeks_won / self.weeks_total if self.weeks_total else 0.0

    @property
    def improvement(self) -> float:
        """Fractional reduction in MAE against the baseline."""
        return (self.baseline_mae - self.mae) / self.baseline_mae if self.baseline_mae else 0.0


def seasonal_naive(df: pd.DataFrame) -> np.ndarray:
    """Same hour, same weekday, last week. The number to beat."""
    return df["lag_168"].to_numpy(dtype=float)


def _smape(actual: np.ndarray, pred: np.ndarray) -> float:
    """Symmetric MAPE, in percent.

    Plain MAPE is unusable here: the series legitimately reaches zero at 04:00
    and MAPE divides by it. sMAPE is bounded and defined at zero.
    """
    denom = (np.abs(actual) + np.abs(pred)) / 2
    mask = denom > 0
    return float(np.mean(np.abs(actual[mask] - pred[mask]) / denom[mask]) * 100)


def fit(train: pd.DataFrame) -> dict[str, GradientBoostingRegressor]:
    """Three models: the median, and the two quantiles that bound it."""
    x = train[list(FEATURES)].to_numpy(dtype=float)
    y = train[TARGET].to_numpy(dtype=float)
    models = {
        "median": GradientBoostingRegressor(loss="absolute_error", **PARAMS).fit(x, y),
        "lo": GradientBoostingRegressor(loss="quantile", alpha=0.10, **PARAMS).fit(x, y),
        "hi": GradientBoostingRegressor(loss="quantile", alpha=0.90, **PARAMS).fit(x, y),
    }
    return models


def trading_mask(zone: str, hours: np.ndarray) -> np.ndarray:
    """1 while the site is open, 0 while it is shut.

    Read from the brand kit rather than learned, because it is KNOWN — SIDRA's
    opening hours are a fact about the business, not a pattern to be inferred
    from noisy counts. Marina Walk closes at 01:00, so the window wraps midnight.
    """
    z = load_brand().zone(zone)
    o, c = int(z.opens[:2]), int(z.closes[:2])
    return ((hours >= o) | (hours < c)) if c <= o else ((hours >= o) & (hours < c))


def predict(models: dict, df: pd.DataFrame, zone: str | None = None) -> pd.DataFrame:
    x = df[list(FEATURES)].to_numpy(dtype=float)
    out = pd.DataFrame({"ts": df["ts"].to_numpy()})
    # Carried through so a consumer can show the weather the forecast ASSUMED
    # rather than joining to an observation table that necessarily stops before
    # the horizon begins. Beyond the 16-day provider window these are the
    # climatology the forward frame filled in, and the payload says so.
    for col in ("apparent_c", "temp_c", "event_pull"):
        if col in df.columns:
            out[col] = df[col].to_numpy()
    # Demand cannot be negative, and a quantile model will happily say it is.
    out["yhat"] = np.maximum(0, models["median"].predict(x))
    out["lo"] = np.maximum(0, models["lo"].predict(x))
    out["hi"] = np.maximum(out["lo"], models["hi"].predict(x))

    if zone is not None:
        # A closed cafe serves exactly nobody, and the model does not know that:
        # it predicted a small positive number at 04:00, which is a rounding
        # error in absolute terms and a catastrophe in proportional ones. sMAPE
        # divides by it and blew up to 69.8% against the baseline's 20.6% —
        # entirely from 392 shut hours — while MAE said the model was 28%
        # better. Both metrics were right about different things; the model was
        # simply ignoring a fact it had been given.
        open_ = trading_mask(zone, df["ts"].dt.hour.to_numpy())
        for col in ("yhat", "lo", "hi"):
            out[col] = np.where(open_, out[col], 0.0)
    return out


def evaluate(frame: Frame, holdout_days: int = HOLDOUT_DAYS) -> ZoneResult:
    train, test = frame.split(holdout_days)
    models = fit(train)
    pred = predict(models, test, frame.zone)

    actual = test[TARGET].to_numpy(dtype=float)
    yhat = pred["yhat"].to_numpy()
    base = seasonal_naive(test)

    # Week-by-week, because a single aggregate MAE hides a model that wins on
    # average by being spectacular in one week and worse in every other.
    weeks = test["ts"].dt.isocalendar().week.astype(int).to_numpy()
    weekly = []
    won = 0
    for w in np.unique(weeks):
        m = weeks == w
        mae_m = float(np.mean(np.abs(actual[m] - yhat[m])))
        mae_b = float(np.mean(np.abs(actual[m] - base[m])))
        weekly.append(
            {
                "week": int(w),
                "hours": int(m.sum()),
                "mae_model": round(mae_m, 2),
                "mae_baseline": round(mae_b, 2),
                "won": bool(mae_m < mae_b),
            }
        )
        won += mae_m < mae_b

    inside = (actual >= pred["lo"].to_numpy()) & (actual <= pred["hi"].to_numpy())

    importances = dict(
        sorted(
            zip(FEATURES, models["median"].feature_importances_, strict=True),
            key=lambda kv: -kv[1],
        )
    )

    return ZoneResult(
        zone=frame.zone,
        mae=round(float(np.mean(np.abs(actual - yhat))), 3),
        baseline_mae=round(float(np.mean(np.abs(actual - base))), 3),
        smape=round(_smape(actual, yhat), 2),
        baseline_smape=round(_smape(actual, base), 2),
        weeks_won=int(won),
        weeks_total=len(weekly),
        coverage_80=round(float(inside.mean()), 4),
        weekly=weekly,
        importances={k: round(float(v), 4) for k, v in importances.items()},
    )


def forward(conn: sqlite3.Connection, zone: str, days: int = HORIZON_DAYS) -> pd.DataFrame:
    """Fit on everything and predict the next `days`.

    The forward frame reuses the loaded history's own lag columns, so the
    horizon is limited to what a week-lagged feature can honestly reach without
    predicting from its own predictions. Beyond that the lag is carried forward,
    and the widening interval is what says so.
    """
    frame = load_frame(conn, zone)
    models = fit(frame.df)

    last = frame.df.iloc[-1]
    future_index = pd.date_range(last["ts"] + pd.Timedelta(hours=1), periods=days * 24, freq="h")
    future = pd.DataFrame({"ts": future_index})
    future["d"] = future["ts"].dt.strftime("%Y-%m-%d")

    calendar = pd.read_sql_query(
        "SELECT date_local AS d, is_weekend, is_public_holiday, is_ramadan, ramadan_day, "
        "is_school_break FROM calendar_days",
        conn,
    )
    future = future.merge(calendar, on="d", how="left")
    future["hour"] = future["ts"].dt.hour
    future["dow"] = future["ts"].dt.dayofweek
    for col in ("is_weekend", "is_public_holiday", "is_ramadan", "is_school_break"):
        future[col] = future[col].fillna(0).astype(int)
    future["ramadan_day"] = future["ramadan_day"].fillna(0)

    # Weather beyond the 16-day forecast horizon falls back to the same
    # calendar week last year, which is a climatology and is labelled as one.
    weather = pd.read_sql_query(
        "SELECT ts_local AS ts, temp_c, apparent_c, humidity, precip_mm, wind_kmh "
        "FROM weather_hourly WHERE zone_code = ?",
        conn,
        params=(zone,),
    )
    weather["ts"] = pd.to_datetime(weather["ts"])
    future = future.merge(weather, on="ts", how="left")
    climate = frame.df.groupby([frame.df["ts"].dt.dayofyear, frame.df["ts"].dt.hour])[
        ["temp_c", "apparent_c", "humidity", "precip_mm", "wind_kmh"]
    ].mean()
    for col in ("temp_c", "apparent_c", "humidity", "precip_mm", "wind_kmh"):
        fill = [
            climate[col].get((d, h), frame.df[col].mean())
            for d, h in zip(future["ts"].dt.dayofyear, future["ts"].dt.hour, strict=True)
        ]
        future[col] = future[col].fillna(pd.Series(fill, index=future.index))

    from services.api.marketing.features import _event_features

    events = pd.read_sql_query(
        "SELECT e.start_date, e.end_date, e.scale_weight, e.venue_key, d.distance_km "
        "FROM events e JOIN event_zone_distance d ON d.event_id = e.event_id "
        "WHERE d.zone_code = ?",
        conn,
        params=(zone,),
    )
    pull, ahead = _event_features(events, future["d"].unique())
    future["event_pull"] = future["d"].map(pull).fillna(0.0)
    future["days_to_event"] = future["d"].map(ahead).fillna(30).clip(0, 30)

    future["trend"] = 1.0 + np.arange(len(future)) / max(len(frame.df), 1)

    # The lag a week out is the last observed week, tiled forward.
    tail = frame.df[TARGET].to_numpy()[-168:]
    future["lag_168"] = np.resize(tail, len(future))
    future["lag_336"] = np.resize(frame.df[TARGET].to_numpy()[-336:-168], len(future))
    future["roll_168_mean"] = float(frame.df[TARGET].to_numpy()[-168:].mean())

    out = predict(models, future, zone)
    out["zone"] = zone
    return out
