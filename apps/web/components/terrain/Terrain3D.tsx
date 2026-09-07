"use client";

/* The canvas, the camera and the invalidation rule — and nothing about what the
 * scene SHOWS, which lives in scenes.tsx so a variant cannot change the data.
 *
 * frameloop="demand" is the important line. A demand forecast is not a game:
 * nothing moves unless the scrubber moves or the variant changes, so rendering
 * sixty times a second would burn a laptop battery to display a still image.
 * The scene re-renders when invalidate() is called and at no other time. The
 * single exception is a slow pulse on the key light, and that stops entirely
 * under prefers-reduced-motion — at which point the scene stops rendering too.
 */

import { Canvas, useThree } from "@react-three/fiber";
import { useEffect } from "react";
import { CAMERAS, SCENES, type Variant } from "./scenes";
import type { TerrainResponse } from "@/lib/api";
import { PCFShadowMap } from "three";

export function Terrain3D({
  data,
  variant,
  focusDay,
  reduced,
  onHover,
}: {
  data: TerrainResponse;
  variant: Variant;
  focusDay: number;
  reduced: boolean;
  onHover?: (d: { zone: string; date: string; yhat: number; lo: number; hi: number } | null) => void;
}) {
  const Scene = SCENES[variant] ?? SCENES.terrain;
  const camera = CAMERAS[variant] ?? CAMERAS.terrain;

  return (
    <Canvas
      frameloop={reduced ? "demand" : "always"}
      dpr={[1, 1.75]}
      /* PCFSoft is the default and three has deprecated it — it downgrades to
         PCF and warns on every single render. Asking for PCF outright is the
         same picture without the console noise. */
      shadows={{ type: PCFShadowMap }}
      camera={{ position: camera.position, fov: camera.fov }}
      gl={{ antialias: true, powerPreference: "low-power" }}
      data-testid="terrain-3d"
      style={{ height: "clamp(320px, 52vh, 560px)" }}
    >
      <CameraAim height={camera.look} />
      <Scene data={data} focusDay={focusDay} reduced={reduced} onHover={onHover} />
      <Invalidator dep={`${variant}-${focusDay}-${data.days}`} />
    </Canvas>
  );
}

/** Aim above the ground so the whole spread fits rather than the near edge
 *  filling the frame. */
function CameraAim({ height }: { height: number }) {
  const { camera, invalidate } = useThree();
  useEffect(() => {
    camera.lookAt(0, height, 0);
    camera.updateProjectionMatrix();
    invalidate();
  }, [camera, height, invalidate]);
  return null;
}

function Invalidator({ dep }: { dep: string }) {
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    invalidate();
  }, [dep, invalidate]);
  return null;
}
