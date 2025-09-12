/** @type {import('next').NextConfig} */
const nextConfig = {
  // Docker optimization - creates standalone output
  output: 'standalone',
  
  experimental: {
    serverComponentsExternalPackages: []
  },
  images: {
    domains: ['localhost'],
    unoptimized: true
  },
  env: {
    CUSTOM_KEY: 'sigmasight-frontend',
  },
  
  // Performance optimizations for Docker
  compress: true,
  poweredByHeader: false,
  
  async redirects() {
    return [
      {
        source: '/',
        destination: '/landing',
        permanent: false,
      },
    ]
  },
  
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
        ],
      },
    ]
  },
  webpack: (config, { dev, isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
      }
    }
    
    // Add polling for Windows Docker development
    if (dev && !isServer && process.env.DOCKER_ENV === 'development') {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      }
    }
    
    return config
  },
}

module.exports = nextConfig