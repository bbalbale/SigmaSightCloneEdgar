/** @type {import('next').NextConfig} */
const nextConfig = {
  // Docker optimization - creates standalone output
  output: 'standalone',

  // Next.js 16+ uses serverExternalPackages instead of experimental.serverComponentsExternalPackages
  serverExternalPackages: [],

  // Next.js 16+ uses turbopack configuration
  turbopack: {
    root: __dirname,
  },

  images: {
    // Next.js 16+ uses remotePatterns instead of domains
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
      },
    ],
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

    // Add support for importing .md files as raw strings
    config.module.rules.push({
      test: /\.md$/,
      type: 'asset/source',
    })

    return config
  },
}

module.exports = nextConfig