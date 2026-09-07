import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  // The API base is the one piece of environment the web app needs. It is read
  // at build time on Vercel and falls back to a local dev server.
  env: { NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000" },
};

export default config;
