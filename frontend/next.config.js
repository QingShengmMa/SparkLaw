/** @type {import('next').NextConfig} */
const nextConfig = {
  // 禁用 Vercel 开发工具栏
  devIndicators: {
    buildActivity: false,
    appIsrStatus: false,
  },
  
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig
