"use client";

/* The design comparison.
 *
 * Three complete directions, both registers, at phone and desktop width, all
 * rendering the SAME components through the SAME stylesheet — so what differs
 * on screen is the token system and nothing else. This page exists to be
 * decided from and then deleted: once a direction is chosen, the other two
 * token files go, and this route goes with them.
 */

import { useState } from "react";
import { Specimen, DIRECTIONS, type Direction } from "@/components/kit/Specimen";
// All three directions are loaded here and only here. Once one is chosen,
// the other two files and this route go together.
import "@/styles/tokens.almanac.css";
import "@/styles/tokens.souk.css";
import "@/styles/tokens.daypart.css";
import "@/styles/kit.css";

type Register = "dark" | "light";
type Width = "phone" | "full";

const ORDER: Direction[] = ["almanac", "souk", "daypart"];

export default function DesignPage() {
  const [direction, setDirection] = useState<Direction>("almanac");
  const [register, setRegister] = useState<Register>("dark");
  const [width, setWidth] = useState<Width>("full");
  const [side, setSide] = useState(false);

  const shown = side ? ORDER : [direction];

  return (
    <div style={{ minHeight: "100dvh", background: "#111", color: "#eee", fontFamily: "ui-sans-serif, system-ui" }}>
      {/* The control bar is deliberately outside every direction's token scope
          and styled in plain neutrals, so it cannot flatter or fight whichever
          direction is on screen. */}
      <header
        style={{
          position: "sticky", top: 0, zIndex: 10, display: "flex", flexWrap: "wrap",
          gap: "1.2rem", alignItems: "center", padding: "0.8rem 1.2rem",
          background: "#0b0b0c", borderBottom: "1px solid #2a2a2c", fontSize: "0.82rem",
        }}
      >
        <strong style={{ letterSpacing: "0.04em" }}>MAWSIM · design directions</strong>

        <Group label="Direction">
          {ORDER.map((d) => (
            <Pill key={d} on={!side && direction === d} onClick={() => { setSide(false); setDirection(d); }}>
              {DIRECTIONS[d].name}
            </Pill>
          ))}
          <Pill on={side} onClick={() => setSide(true)}>All three</Pill>
        </Group>

        <Group label="Register">
          <Pill on={register === "dark"} onClick={() => setRegister("dark")}>Night</Pill>
          <Pill on={register === "light"} onClick={() => setRegister("light")}>Day</Pill>
        </Group>

        <Group label="Width">
          <Pill on={width === "phone"} onClick={() => setWidth("phone")}>360px</Pill>
          <Pill on={width === "full"} onClick={() => setWidth("full")}>Full</Pill>
        </Group>

        <span style={{ color: "#8a8a8f", marginInlineStart: "auto" }}>
          Every value on screen is invented for this page. Nothing here is a result.
        </span>
      </header>

      <div
        style={{
          display: "grid", gap: "1.5rem", padding: "1.5rem",
          gridTemplateColumns: side ? "repeat(auto-fit, minmax(min(100%, 24rem), 1fr))" : "1fr",
        }}
      >
        {shown.map((d) => (
          <section key={d} style={{ minWidth: 0 }}>
            <h2 style={{ font: "500 0.78rem/1 ui-monospace, monospace", letterSpacing: "0.16em",
                         textTransform: "uppercase", color: "#8a8a8f", margin: "0 0 0.6rem" }}>
              {DIRECTIONS[d].name}
            </h2>
            <div
              data-direction={d}
              data-register={register}
              style={{
                width: width === "phone" ? 360 : "100%",
                maxWidth: "100%",
                margin: width === "phone" && !side ? "0 auto" : undefined,
                border: "1px solid #2a2a2c",
                borderRadius: 8,
                overflow: "hidden",
                containerType: "inline-size",
              }}
            >
              <Specimen direction={d} />
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
      <span style={{ color: "#6e6e73", fontSize: "0.68rem", letterSpacing: "0.14em", textTransform: "uppercase" }}>
        {label}
      </span>
      {children}
    </div>
  );
}

function Pill({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      style={{
        font: "inherit", fontSize: "0.78rem", padding: "0.3rem 0.7rem", borderRadius: 5,
        cursor: "pointer", border: `1px solid ${on ? "#f2f2f4" : "#3a3a3e"}`,
        background: on ? "#f2f2f4" : "transparent", color: on ? "#111" : "#c9c9cf",
      }}
    >
      {children}
    </button>
  );
}
