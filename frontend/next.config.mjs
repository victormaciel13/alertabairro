/** @type {import('next').NextConfig} */
const nextConfig = {
  // gera um servidor Node mínimo em .next/standalone (imagem Docker pequena)
  output: "standalone",
  poweredByHeader: false,
  // Em produção o Caddy manda /api para a API. No "npm run dev" fazemos o mesmo aqui.
  async rewrites() {
    if (process.env.NODE_ENV !== "development") return [];
    return [{ source: "/api/:path*", destination: "http://localhost:8000/:path*" }];
  },
};

export default nextConfig;
