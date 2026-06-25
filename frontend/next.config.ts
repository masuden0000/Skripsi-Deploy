import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone', turbopack: {
    root: __dirname,
  },
  allowedDevOrigins: ["192.168.100.10", "localhost"],
};

export default nextConfig;
