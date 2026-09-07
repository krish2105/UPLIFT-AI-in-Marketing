"use client";

import { useEffect, useState } from "react";
import { StationStrip, type Station as StationView } from "@/components/signatures/StationStrip";
import { api } from "@/lib/api";

/* The strip, fetched on the client.
 *
 * It sits above every page, so server-rendering it would make every route wait
 * on the API — and on a sleeping free instance that is a minute. It renders
 * nothing until it has a real reading rather than showing zeros: a station
 * report with no observation is not a station report.
 */
export function StationBar({ zone = "DXB-MAR" }: { zone?: string }) {
  const [station, setStation] = useState<StationView | null>(null);

  useEffect(() => {
    let live = true;
    api
      .station(zone)
      .then((s) => {
        if (!live || s.temp_c === null) return;
        setStation({
          zone: s.zone,
          tempC: s.temp_c,
          humidity: s.humidity ?? 0,
          windKmh: s.wind_kmh ?? 0,
          hijri: s.hijri,
          index: s.index,
          pi: s.pi,
        });
      })
      .catch(() => {
        /* The API sleeps on the free tier. A missing strip is correct here —
           an invented reading would not be. */
      });
    return () => {
      live = false;
    };
  }, [zone]);

  if (!station) return null;
  return <StationStrip station={station} />;
}
