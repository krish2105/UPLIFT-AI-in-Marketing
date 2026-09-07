/* Parse tokens.css into two registers.
 *
 * Every token is declared once as light-dark(LIGHT, DARK) — see the header of
 * tokens.css for why. This splits that single declaration into the two
 * registers the gates measure, so what is checked is exactly what the browser
 * resolves, and the two cannot drift.
 */

const OKLCH_G = /oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*(?:\/\s*[\d.]+\s*)?\)/g;

export function parseRegisters(css) {
  const registers = { light: {}, dark: {} };
  for (const line of css.split("\n")) {
    const decl = line.match(/^\s*(--[a-z0-9-]+)\s*:\s*(.+?);/);
    if (!decl) continue;
    const [name, value] = [decl[1], decl[2]];
    const colours = [...value.matchAll(OKLCH_G)].map((m) => [+m[1], +m[2], +m[3]]);
    if (colours.length === 0) continue;
    if (value.includes("light-dark(") && colours.length >= 2) {
      registers.light[name] = colours[0];
      registers.dark[name] = colours[1];
    } else {
      // A token outside light-dark() is register-independent by construction.
      registers.light[name] = colours[0];
      registers.dark[name] = colours[0];
    }
  }
  if (!Object.keys(registers.light).length) throw new Error("no tokens parsed from tokens.css");
  return registers;
}
