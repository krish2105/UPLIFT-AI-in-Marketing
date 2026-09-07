import path from "node:path";
import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  // A stray package-lock.json in the home directory makes Turbopack guess the
  // wrong workspace root. Pin it to this app.
  turbopack: { root: path.resolve(import.meta.dirname) },
  /* The API base is the one piece of environment the web app needs.
   *
   * The deployed default is written here rather than left as a dashboard step,
   * so a fresh clone of this repository deploys working. A forgotten
   * environment variable does not fail loudly: the app builds, serves, and
   * renders its honest "API unreachable" state on every tab, which reads as a
   * design decision rather than as a missing setting.
   *
   * NEXT_PUBLIC_API_BASE still overrides it, which is what the e2e suite and
   * local development use. */
  env: {
    NEXT_PUBLIC_API_BASE:
      process.env.NEXT_PUBLIC_API_BASE ??
      (process.env.VERCEL ? "https://mawsim-api.onrender.com" : "http://localhost:8000"),
  },
};

export default config;
