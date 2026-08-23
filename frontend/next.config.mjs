/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Type errors still fail the build; lint nits do not block the demo.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
