"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

/* Three states, not two.
 *
 * A two-state toggle silently overrides the reader's operating system, and
 * once overridden there is no way back to following it. So System is a real
 * option and it is the default.
 *
 * DAYPART names its registers Day and Night rather than Light and Dark,
 * because in this direction the register is not a brightness preference — it
 * is which half of the cafe's day you are looking at.
 */

const OPTIONS = [
  { value: "system", label: "Auto", hint: "Follow the system setting" },
  { value: "light", label: "Day", hint: "The bleached midday register" },
  { value: "dark", label: "Night", hint: "The petrol-blue evening register" },
] as const;

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  // The server cannot know the reader's system preference, so rendering the
  // pressed state before hydration would produce a wrong highlight that then
  // jumps. Render the control disabled-looking until mounted instead.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <div
      role="group"
      aria-label="Colour register"
      style={{ display: "inline-flex", gap: "0.25rem", alignItems: "center" }}
    >
      {OPTIONS.map((o) => (
        <button
          key={o.value}
          type="button"
          className="btn"
          aria-pressed={mounted ? theme === o.value : false}
          title={o.hint}
          onClick={() => setTheme(o.value)}
          style={{ padding: "0.28rem 0.6rem", fontSize: "0.72rem" }}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
