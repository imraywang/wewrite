/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 纯客户端工具（独立 FastAPI 后端）→ 静态导出，由后端/openresty 直接服务静态文件。
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
