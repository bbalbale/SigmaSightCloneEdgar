# SigmaSight Frontend Setup Guide

This guide will help you set up and run the SigmaSight frontend application locally.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** (version 18.0 or higher)
- **npm** (comes with Node.js)
- **Git** (for version control)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/elliottng/SigmaSight-BE.git
cd SigmaSight-BE
git checkout chatgpt
```

### 2. Navigate to Frontend Directory

```bash
cd frontend
```

### 3. Install Dependencies

```bash
npm install
```

### 4. Install shadcn/ui Components

```bash
# Initialize shadcn/ui with default settings
npx shadcn@latest init --defaults

# Add essential UI components
npx shadcn@latest add button card input dialog separator
```

### 5. Install MCP Playwright (for Visual Testing)

For development and design review agents:

```bash
# Install MCP Playwright server (if not already available)
# This enables the agents to take screenshots and validate UI changes
# Follow Claude Code documentation for MCP setup
```

### 6. Environment Configuration

Create a `.env` file in the frontend directory:

```bash
# Copy the example environment file
cp .env.example .env
```

Edit the `.env` file with your configuration:

```env
# Database (shared with backend)
DATABASE_URL=postgresql+asyncpg://sigmasight:sigmasight_dev@localhost:5432/sigmasight_db

# API Keys (required for full functionality)
POLYGON_API_KEY=your_polygon_api_key_here
FMP_API_KEY=your_fmp_api_key_here
TRADEFEEDS_API_KEY=your_tradefeeds_api_key_here
FRED_API_KEY=your_fred_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Authentication (must match backend)
SECRET_KEY=your_jwt_secret_here

# Environment Settings
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Backend Integration
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1
BACKEND_API_URL=http://localhost:8000/api/v1

# GPT Agent Integration
NEXT_PUBLIC_GPT_AGENT_URL=http://localhost:8787
GPT_AGENT_URL=http://localhost:8787

# Demo Portfolio IDs (from backend)
NEXT_PUBLIC_DEMO_INDIVIDUAL_PORTFOLIO=a3209353-9ed5-4885-81e8-d4bbc995f96c
NEXT_PUBLIC_DEMO_HIGH_NET_WORTH_PORTFOLIO=14e7f420-b096-4e2e-8cc2-531caf434c05
NEXT_PUBLIC_DEMO_HEDGE_FUND_PORTFOLIO=cf890da7-7b74-4cb4-acba-2205fdd9dff4

# Feature Flags
NEXT_PUBLIC_ENABLE_GPT_FEATURES=true
NEXT_PUBLIC_ENABLE_BACKEND_INTEGRATION=true
```

### 7. Start the Development Server

```bash
npm run dev
```

The application will be available at: **http://localhost:3005**

## Project Structure

```
frontend/
├── src/
│   ├── app/              # Next.js App Router
│   │   ├── layout.tsx    # Root layout
│   │   ├── page.tsx      # Main page
│   │   ├── loading.tsx   # Loading component
│   │   └── error.tsx     # Error boundary
│   ├── components/       # React components
│   │   └── BasicDemoPage.tsx  # Main landing page
│   ├── styles/          # Styling files
│   │   └── globals.css  # Global styles with OKLCH theme
│   └── lib/             # Utility libraries
│       ├── api.ts       # API utilities
│       ├── types.ts     # TypeScript types
│       └── utils.ts     # Helper functions
├── public/              # Static assets
├── _docs/              # Documentation
├── package.json        # Dependencies and scripts
├── next.config.js      # Next.js configuration
├── tailwind.config.js  # Tailwind CSS configuration
├── tsconfig.json       # TypeScript configuration
└── .env               # Environment variables (not tracked)
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## Environment Variables

### Required API Keys

To get full functionality, you'll need API keys from:

1. **OpenAI** - For AI-powered analysis features
   - Get from: https://platform.openai.com/api-keys
   - Set as: `OPENAI_API_KEY`

2. **Polygon.io** - For financial market data
   - Get from: https://polygon.io/dashboard/api-keys
   - Set as: `POLYGON_API_KEY`

3. **Financial Modeling Prep** - For financial data
   - Get from: https://financialmodelingprep.com/developer/docs
   - Set as: `FMP_API_KEY`

4. **FRED (Federal Reserve Economic Data)** - For economic data
   - Get from: https://fred.stlouisfed.org/docs/api/api_key.html
   - Set as: `FRED_API_KEY`

### Backend Integration

The frontend is designed to work with the SigmaSight backend:

- Backend should be running on `http://localhost:8000`
- GPT Agent should be running on `http://localhost:8787`
- Database should be accessible (see backend setup)

## Features

The frontend includes:

- **Landing Page** - 100% exact replica of sigmasight.io
- **shadcn/ui Components** - Professional UI component library
- **MCP Playwright Integration** - Visual testing and validation
- **Portfolio Analysis** - Risk analysis and correlation tools
- **AI Integration** - OpenAI-powered insights
- **Responsive Design** - Works on all device sizes
- **Dark Mode Support** - OKLCH color system
- **TypeScript** - Full type safety
- **Tailwind CSS** - Modern utility-first styling

## Troubleshooting

### Port Already in Use

If port 3005 is busy, Next.js will automatically try the next available port:

```bash
# Force a specific port
npm run dev -- -p 3006
```

### Missing Dependencies

If you encounter missing dependencies:

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Build Errors

Check TypeScript compilation:

```bash
npm run type-check
```

Fix any TypeScript errors before building.

### API Connection Issues

Ensure your `.env` file is properly configured and the backend services are running:

- Backend: `http://localhost:8000`
- Database: PostgreSQL running on port 5432
- GPT Agent: `http://localhost:8787` (if using AI features)

## Development Workflow

1. **Start Development Server**: `npm run dev`
2. **Make Changes**: Edit files in `src/`
3. **Hot Reload**: Changes appear automatically
4. **Type Check**: Run `npm run type-check` periodically
5. **Test Build**: Run `npm run build` before committing

## Production Deployment

```bash
# Build for production
npm run build

# Start production server
npm run start
```

## Security

- Never commit `.env` files with real API keys
- The `.gitignore` files protect sensitive information
- Use environment variables for all secrets
- API keys are automatically filtered from commits

## Support

For issues or questions:

1. Check this setup guide
2. Review the backend documentation
3. Check the console for error messages
4. Ensure all environment variables are set correctly

## Next Steps

After setup, you can:

- Explore the landing page at `http://localhost:3005`
- Connect to the backend for full functionality
- Customize the design in `src/components/BasicDemoPage.tsx`
- Add new features using the existing architecture