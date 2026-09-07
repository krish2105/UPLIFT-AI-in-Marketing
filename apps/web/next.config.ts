import path from "node:path";
import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  // A stray package-lock.json in the home directory makes Turbopack guess the
  // wrong workspace root. Pin it to this app.
  turbopack: { root: path.resolve(import.meta.dirname) },
  // The API base is the one piece of environment the web app needs. It is read
  // at build time on Vercel and falls back to a local dev server.
  env: { NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000" },
};

export default config;
