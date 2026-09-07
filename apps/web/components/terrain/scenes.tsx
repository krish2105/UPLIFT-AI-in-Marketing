"use client";

/* The two projections of the same forecast.
 *
 * TERRAIN answers WHEN: four site lanes running across fifty-six days, so the
 * shape of the season is the thing you see first.
 * MAP answers WHERE: the same four sites at their real coordinates on a
 * stylised coastline, with the horizon collapsed to a scrubbed day.
 *
 * Neither alone answers a promo question, which is why both exist behind one
 * toggle rather than one being chosen.
 *
 * THE CAP IS THE ARGUMENT. Every block wears a translucent cap whose height is
 * that day's 80% prediction interval. A tall block with a tall cap is an
 * uncertain forecast and LOOKS like one. Without it a 3D landscape is the most
 * confident-looking chart there is: extrusion reads as fact, and a reader has
 * no way to tell a well-known Tuesday from a guess.
 */

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { TerrainResponse } from "@/lib/api";

export const LANE_ORDER = ["DXB-MAR", "DXB-DTN", "DXB-MOE", "DXB-DEI"] as const;

/** Read a CSS custom property so the scene follows the theme rather than
 *  carrying its own palette. A 3D view with hardcoded colours is a second
 *  design system that drifts from the first.
 *
 * RESOLVED THROUGH A CANVAS PIXEL, NOT READ AS TEXT.
 * `getComputedStyle(root).getPropertyValue("--sig-forecast")` returns the raw
 * declared text — here `light-dark(oklch(...), oklch(...))` — because a custom
 * property is substituted, not resolved, until it is used. THREE.Color cannot
 * parse that, and it does not throw: setStyle warns and leaves the colour at
 * its default, so every block in the scene rendered WHITE while the fallback
 * sat unused. Painting the value into a 1×1 canvas makes the browser resolve
 * it — light-dark(), oklch(), colour space and all — and the pixel comes back
 * as plain RGB. */
export function tokenColour(name: string, fallback: string): THREE.Color {
  if (typeof window === "undefined") return new THREE.Color(fallback);
  try {
    const probe = document.createElement("span");
    probe.style.color = `var(${name})`;
    probe.style.display = "none";
    document.body.appendChild(probe);
    const resolved = getComputedStyle(probe).color;
    probe.remove();

    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 1;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return new THREE.Color(fallback);
    ctx.fillStyle = resolved || fallback;
    ctx.fillRect(0, 0, 1, 1);
    const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data;
    return new THREE.Color(r / 255, g / 255, b / 255);
  } catch {
    return new THREE.Color(fallback);
  }
}

type SceneProps = {
  data: TerrainResponse;
  focusDay: number;
  reduced: boolean;
  onHover?: (d: { zone: string; date: string; yhat: number; lo: number; hi: number } | null) => void;
};

/* ── terrain ──────────────────────────────────────────────────────────────── */

export function TerrainScene({ data, focusDay, reduced, onHover }: SceneProps) {
  const lanes = LANE_ORDER.map((z) => data.lanes.find((l) => l.zone === z)).filter(Boolean) as TerrainResponse["lanes"];
  const days = data.days;

  const peak = useMemo(
    () => Math.max(...lanes.flatMap((l) => l.days.map((d) => d.hi)), 1),
    [lanes],
  );

  const colours = useMemo(
    () => ({
      block: tokenColour("--sig-forecast", "#4a8fb5"),
      cap: tokenColour("--sig-actual", "#b8d4e0"),
      band: tokenColour("--accent", "#a04ba8"),
      rule: tokenColour("--rule", "#4a5560"),
    }),
    [],
  );

  const W = 30;           // lane length along X, in scene units
  const LANE_GAP = 4.4;   // wide enough that four lanes read as four

  const x = (i: number) => (i / Math.max(days - 1, 1)) * W - W / 2;
  const y = (v: number) => (v / peak) * 5;
  const bw = W / days;

  return (
    <group>
      {/* ground */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
        <planeGeometry args={[W + 5, LANE_GAP * 4 + 2]} />
        <meshStandardMaterial color={colours.rule} opacity={0.10} transparent />
      </mesh>

      {/* the weather ribbon: a heat strip along the ground, in front of the lanes */}
      {data.ribbon.slice(0, days).map((r, i) => {
        const t = Math.min(1, Math.max(0, (r.apparent_c - 24) / 20));
        return (
          <mesh
            key={r.date}
            position={[x(i), 0.005, LANE_GAP * 1.8]}
            rotation={[-Math.PI / 2, 0, 0]}
          >
            <planeGeometry args={[W / days, 1.1]} />
            <meshBasicMaterial color={new THREE.Color().setHSL(0.62 - t * 0.62, 0.62, 0.52)} />
          </mesh>
        );
      })}

      {/* event bands: translucent walls crossing every lane at once, which is
          what makes them bands rather than per-site marks */}
      {data.bands.slice(0, 6).map((b) => {
        const s = data.horizon.indexOf(b.start);
        const e = data.horizon.indexOf(b.end);
        if (s < 0 && e < 0) return null;
        const from = s < 0 ? 0 : s;
        const to = e < 0 ? days - 1 : e;
        const w = Math.max(W / days, ((to - from + 1) / days) * W);
        return (
          <group key={b.event_id}>
            {/* A floor stripe carries the extent, and one thin wall marks where
                the event starts. Ten full-depth translucent boxes compounded
                into a purple wash that hid the data they annotate — a band
                should say "here", not repaint the scene. */}
            <mesh
              position={[(x(from) + x(to)) / 2, 0.012, 0]}
              rotation={[-Math.PI / 2, 0, 0]}
            >
              <planeGeometry args={[w, LANE_GAP * 3.6]} />
              <meshBasicMaterial
                color={colours.band}
                transparent
                opacity={0.10 + b.weight * 0.10}
                depthWrite={false}
              />
            </mesh>
            <mesh position={[x(from) - bw / 2, 2.6, 0]}>
              <boxGeometry args={[0.055, 5.2, LANE_GAP * 3.6]} />
              <meshBasicMaterial color={colours.band} transparent opacity={0.34} depthWrite={false} />
            </mesh>
          </group>
        );
      })}

      {lanes.map((lane, li) => {
        const z = (li - 1.5) * LANE_GAP;
        return (
          <group key={lane.zone} position={[0, 0, z]}>
            {lane.days.slice(0, days).map((d, i) => {
              const h = Math.max(0.02, y(d.yhat));
              const capH = Math.max(0.015, y(d.hi - d.lo));
              const focused = i === focusDay;
              return (
                <group key={d.date} position={[x(i), 0, 0]}>
                  {/* the block: what the model expects */}
                  <mesh
                    position={[0, h / 2, 0]}
                    castShadow
                    onPointerOver={(e) => {
                      e.stopPropagation();
                      onHover?.({ zone: lane.zone, date: d.date, yhat: d.yhat, lo: d.lo, hi: d.hi });
                    }}
                    onPointerOut={() => onHover?.(null)}
                  >
                    <boxGeometry args={[(W / days) * 0.66, h, 2.0]} />
                    <meshStandardMaterial
                      color={colours.block}
                      emissive={colours.block}
                      emissiveIntensity={focused ? 0.55 : 0.12}
                      roughness={0.55}
                    />
                  </mesh>
                  {/* the cap: how sure it is. Sits ON the block, from lo to hi. */}
                  <mesh position={[0, y(d.lo) + capH / 2, 0]}>
                    <boxGeometry args={[(W / days) * 0.7, capH, 2.06]} />
                    <meshStandardMaterial
                      color={colours.cap}
                      transparent
                      opacity={0.17}
                      depthWrite={false}
                    />
                  </mesh>
                </group>
              );
            })}
          </group>
        );
      })}

      <Breathing enabled={!reduced} />
    </group>
  );
}

/* ── map ──────────────────────────────────────────────────────────────────── */

/** A hand-simplified Dubai coastline, from Natural Earth 10m (public domain).
 *  Coarse on purpose: it exists to say "this is Dubai", not to be a chart. */
const COAST: [number, number][] = [
  [54.94, 24.98], [55.00, 25.03], [55.06, 25.07], [55.10, 25.10], [55.14, 25.13],
  [55.18, 25.17], [55.22, 25.20], [55.26, 25.24], [55.29, 25.27], [55.33, 25.30],
  [55.37, 25.33], [55.42, 25.36], [55.48, 25.40],
];

export function MapScene({ data, focusDay, reduced, onHover }: SceneProps) {
  const colours = useMemo(
    () => ({
      block: tokenColour("--sig-forecast", "#4a8fb5"),
      cap: tokenColour("--sig-actual", "#b8d4e0"),
      coast: tokenColour("--rule", "#4a5560"),
    }),
    [],
  );

  const peak = useMemo(
    () => Math.max(...data.lanes.flatMap((l) => l.days.map((d) => d.hi)), 1),
    [data],
  );

  // Real lat/lon, projected flat. Over 30 km the earth's curvature is far below
  // the width of a block, so a plate carrée projection costs nothing here.
  const SCALE = 118;   // Dubai's four sites span ~0.2 degrees; at 46 they were specks
  const cx = 55.23;
  const cy = 25.19;
  const px = (lon: number) => (lon - cx) * SCALE;
  const pz = (lat: number) => -(lat - cy) * SCALE;

  const coastPoints = useMemo(
    () => COAST.map(([lon, lat]) => new THREE.Vector3(px(lon), 0.01, pz(lat))),
    [],
  );

  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
        <planeGeometry args={[42, 30]} />
        <meshStandardMaterial color={colours.coast} opacity={0.08} transparent />
      </mesh>
      {/* The sea side, so the coastline reads as a coast rather than as a
          stray polyline. Dubai's sites sit on a NE–SW strip along the water,
          which is why the four marks are near-collinear — that is the city,
          not a projection error. */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[-3, -0.015, -9]}>
        <planeGeometry args={[46, 16]} />
        <meshBasicMaterial color={colours.block} opacity={0.05} transparent />
      </mesh>

      {/* the coastline */}
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[new Float32Array(coastPoints.flatMap((p) => [p.x, p.y, p.z])), 3]}
          />
        </bufferGeometry>
        <lineBasicMaterial color={colours.coast} linewidth={2} />
      </line>

      {data.lanes.map((lane) => {
        const d = lane.days[Math.min(focusDay, lane.days.length - 1)];
        if (!d) return null;
        const h = Math.max(0.05, (d.yhat / peak) * 6);
        const capH = Math.max(0.03, ((d.hi - d.lo) / peak) * 6);
        // Footprint scales with outdoor share, so the site most exposed to the
        // weather is also the widest mark — the map's own version of the thesis.
        const w = 1.5 + lane.outdoor_share * 1.6;
        return (
          <group key={lane.zone} position={[px(lane.lon), 0, pz(lane.lat)]}>
            <mesh
              position={[0, h / 2, 0]}
              castShadow
              onPointerOver={(e) => {
                e.stopPropagation();
                onHover?.({ zone: lane.zone, date: d.date, yhat: d.yhat, lo: d.lo, hi: d.hi });
              }}
              onPointerOut={() => onHover?.(null)}
            >
              <boxGeometry args={[w, h, w]} />
              <meshStandardMaterial
                color={colours.block}
                emissive={colours.block}
                emissiveIntensity={0.18}
                roughness={0.5}
              />
            </mesh>
            <mesh position={[0, (d.lo / peak) * 6 + capH / 2, 0]}>
              <boxGeometry args={[w * 1.14, capH, w * 1.14]} />
              <meshStandardMaterial color={colours.cap} transparent opacity={0.3} depthWrite={false} />
            </mesh>
          </group>
        );
      })}

      <Breathing enabled={!reduced} />
    </group>
  );
}

/* ── the only thing that animates ─────────────────────────────────────────── */

function Breathing({ enabled }: { enabled: boolean }) {
  const light = useRef<THREE.DirectionalLight>(null);
  /* A slow pulse on the key light, so a still forecast does not read as a
     screenshot. It stops entirely under prefers-reduced-motion, and the canvas
     drops to frameloop="demand" with it, so the scene then renders only when
     something changes.

     THE KEY LIGHT IS DIRECTIONAL, NOT A POINT LIGHT, AND THAT IS A PERFORMANCE
     DECISION. A shadow-casting point light is omnidirectional, so three renders
     its shadow map as a CUBE — six passes, every frame. Measured on the
     scrubbing test that put the 95th-percentile frame at 50 ms while the median
     sat on vsync: a visible stutter on exactly the interaction the tab exists
     for. A directional light is one orthographic pass, and for a scene lit like
     an almanac it is also the right physical model: this is the sun over a
     stretch of coast, not a bulb hanging in a room.

     The shadow camera is sized to the ground plane. Left at its 5-unit default
     the bars at the ends of the horizon simply stop casting, which reads as a
     rendering bug rather than as a lighting choice. */
  useFrame(({ clock }) => {
    if (!enabled || !light.current) return;
    light.current.intensity = 2.6 + Math.sin(clock.elapsedTime * 0.7) * 0.4;
  });
  return (
    <>
      <ambientLight intensity={0.55} />
      <directionalLight
        ref={light}
        position={[9, 16, 10]}
        intensity={2.6}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-left={-26}
        shadow-camera-right={26}
        shadow-camera-top={20}
        shadow-camera-bottom={-20}
        shadow-camera-near={1}
        shadow-camera-far={60}
      />
      {/* Fill, from the opposite side and with no shadow of its own: it exists
          to keep the unlit faces of the blocks from going flat, and a second
          shadow map would double the cost for nothing. */}
      <directionalLight position={[-12, 9, -8]} intensity={0.7} />
    </>
  );
}

export const SCENES = { terrain: TerrainScene, map: MapScene } as const;
export type Variant = keyof typeof SCENES;

export const CAMERAS: Record<Variant, { position: [number, number, number]; fov: number; look: number }> = {
  // High and off to one side: from head-on the four lanes occlude each other
  // and 224 thin blocks read as a single wall.
  terrain: { position: [17, 16, 26], fov: 38, look: 1.6 },
  map: { position: [6, 13, 15], fov: 42, look: 1.0 },
};
