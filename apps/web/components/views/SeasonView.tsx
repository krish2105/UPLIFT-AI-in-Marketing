"use client";

/* The season, in three dimensions or two.
 *
 * PROGRESSIVE ENHANCEMENT IS NOT OPTIONAL HERE. The page renders the SVG first
 * and swaps in WebGL only after a successful capability check on the client. A
 * reader without WebGL — an old browser, a locked-down machine, a crawler —
 * gets the same four lanes, the same intervals and the same event bands, not an
 * empty box. The toggle then offers three views rather than two, and "Flat" is
 * a legitimate choice rather than a fallback badge.
 */

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { StatTile, fmt } from "@/components/charts/Chart";
import { TerrainSVG } from "@/components/terrain/TerrainSVG";
import type { TerrainResponse } from "@/lib/api";

/* Loaded on the client only, and only when asked for: three.js is ~600 KB and a
   reader who never opens the 3D view should never download it. */
const Terrain3D = dynamic(() => import("@/components/terrain/Terrain3D").then((m) => m.Terrain3D), {
  ssr: false,
  loading: () => (
    <div className="scaffold" style={{ display: "grid", placeItems: "center", minHeight: 320 }}>
      <span className="faint num">loading the scene</span>
    </div>
  ),
});

type View = "terrain" | "map" | "flat";

function webglAvailable(): boolean {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") ?? c.getContext("webgl"));
  } catch {
    return false;
  }
}

export function SeasonView({ data }: { data: TerrainResponse }) {
  const [view, setView] = useState<View>("flat");
  const [webgl, setWebgl] = useState(false);
  const [reduced, setReduced] = useState(false);
  const [focusDay, setFocusDay] = useState(0);
  const [hover, setHover] = useState<{ zone: string; date: string; yhat: number; lo: number; hi: number } | null>(null);

  useEffect(() => {
    const ok = webglAvailable();
    setWebgl(ok);
    if (ok) setView("terrain");
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const day = data.horizon[focusDay] ?? data.horizon[0];
  const marina = data.lanes.find((l) => l.zone === "DXB-MAR");
  const today = marina?.days[focusDay];
  const bandsToday = data.bands.filter((b) => b.start <= day && b.end >= day);
  const calToday = data.calendar.find((c) => c.date === day);
  const ribbonToday = data.ribbon.find((r) => r.date === day);

  const widest = data.lanes
    .flatMap((l) => l.days.map((d) => ({ zone: l.zone, date: d.date, w: d.hi - d.lo, y: d.yhat })))
    .sort((a, b) => b.w / b.y - a.w / a.y)[0];

  return (
    <div className="stack-l">
      <div className="cards">
        <StatTile label="Horizon" value={`${data.days} days`} detail={`${data.horizon[0]} → ${data.horizon[data.horizon.length - 1]}`} />
        <StatTile label={`Marina Walk on ${day?.slice(5)}`} value={today ? fmt(Math.round(today.yhat)) : "—"} detail={today ? `${Math.round(today.lo)}–${Math.round(today.hi)} at 80%` : ""} />
        <StatTile label="Events in the horizon" value={String(data.bands.length)} detail="curated, crossing every site" token="--accent" />
        <StatTile label="Least certain day" value={widest ? widest.date.slice(5) : "—"} detail={widest ? `${widest.zone} · ±${Math.round(widest.w / 2)}` : ""} token="--heat-4" />
      </div>

      <div className="row" style={{ justifyContent: "space-between" }}>
        <div role="group" aria-label="View" className="row" style={{ gap: "0.25rem" }}>
          <button type="button" className="btn" aria-pressed={view === "terrain"} disabled={!webgl}
                  onClick={() => setView("terrain")} title={webgl ? "" : "WebGL is not available here"}>
            Terrain
          </button>
          <button type="button" className="btn" aria-pressed={view === "map"} disabled={!webgl}
                  onClick={() => setView("map")} title={webgl ? "" : "WebGL is not available here"}>
            Map
          </button>
          <button type="button" className="btn" aria-pressed={view === "flat"} onClick={() => setView("flat")}>
            Flat
          </button>
        </div>
        <div className="row">
          {!webgl && <span className="chip chip-label">no WebGL here</span>}
          {reduced && <span className="chip chip-label">reduced motion</span>}
          <span className="chip chip-label">simulated</span>
        </div>
      </div>

      <p className="note">
        The terrain answers <em>when</em> — four site lanes across {data.days} days, so the shape
        of the season is what you see first. The map answers <em>where</em>, with the horizon
        collapsed to one scrubbed day and each site&rsquo;s footprint scaled by its outdoor share.
        Neither alone answers a promo question.
      </p>

      <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", overflow: "hidden", background: "var(--bg-inset)" }}>
        {view === "flat" || !webgl ? (
          <div style={{ padding: "0.9rem" }}>
            <TerrainSVG data={data} focusDay={focusDay} />
          </div>
        ) : (
          <Terrain3D data={data} variant={view} focusDay={focusDay} reduced={reduced} onHover={setHover} />
        )}
      </div>

      <label className="stack" style={{ gap: "0.4rem" }}>
        <span className="eyebrow" style={{ margin: 0 }}>
          Day {focusDay + 1} of {data.days} · {day}
          {ribbonToday ? ` · ${ribbonToday.apparent_c}°C evening` : ""}
        </span>
        <input
          type="range"
          min={0}
          max={Math.max(0, data.days - 1)}
          value={focusDay}
          onChange={(e) => setFocusDay(Number(e.target.value))}
          aria-label="Day in the horizon"
          style={{ width: "100%", accentColor: "var(--accent)" }}
        />
      </label>

      {(hover || bandsToday.length > 0 || calToday) && (
        <div className="card stack" style={{ gap: "0.4rem" }}>
          {hover && (
            <div className="row">
              <span className="code">{hover.zone}</span>
              <span className="faint num">{hover.date}</span>
              <span className="num">{Math.round(hover.yhat)}</span>
              <span className="faint num">({Math.round(hover.lo)}–{Math.round(hover.hi)})</span>
            </div>
          )}
          {bandsToday.map((b) => (
            <div key={b.event_id} className="row">
              <span className="chip chip-accent">{b.category}</span>
              <span>{b.title}</span>
              <span className="faint num">{b.venue}</span>
              <span className="chip chip-label">curated</span>
            </div>
          ))}
          {calToday && (
            <div className="row">
              {calToday.holiday && <span className="chip">{calToday.holiday}</span>}
              {calToday.ramadan && <span className="chip">Ramadan</span>}
              {calToday.school_break && <span className="chip">school break</span>}
            </div>
          )}
        </div>
      )}

      <section className="stack">
        <h2 className="h3">Why every block wears a cap</h2>
        <p className="note ltr">{data.note}</p>
        <p className="note">
          Extrusion reads as fact. A 3D landscape is the most confident-looking chart there is,
          and without the cap a reader has no way to tell a well-known Tuesday from a guess. The
          cap runs from the low bound to the high one, so an uncertain day is visibly taller in
          its uncertainty than in its estimate.
        </p>
        <div className="cards">
          <StatTile label="Ribbon" value="Assumed" detail="the weather the forecast used, not the observation table" />
          <StatTile label="Bands" value={String(data.bands.length)} detail="cross every lane, because an event is not per-site" token="--accent" />
          <StatTile label="Frame loop" value={reduced ? "demand" : "always"} detail="a still image unless something asks for a frame" />
          <StatTile label="Without WebGL" value="Same data" detail="four lanes, intervals and bands, in SVG" token="--pass-text" />
        </div>
      </section>
    </div>
  );
}
