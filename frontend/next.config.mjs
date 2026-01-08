/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone", // Enable for Docker deployment
  reactCompiler: true,
  compiler: {
    // Temporarily disabled to debug auth issues
    // removeConsole: process.env.NODE_ENV === "production",
  },
  async redirects() {
    return [
      {
        source: "/",
        destination: "/auth/v1/login",
        permanent: false,
      },
      {
        source: "/dashboard",
        destination: "/dashboard/overview",
        permanent: false,
      },
    ];
  },
  // Note: API proxying is handled by src/app/api/[...path]/route.ts
  // This gives us full control over cookie forwarding
};

export default nextConfig;
