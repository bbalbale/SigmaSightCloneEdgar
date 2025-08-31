# Project Structure

## Overview
The project has been organized into two main sections to separate marketing and application concerns:

## Directory Structure

```
src/
├── app/
│   ├── (landing)/              # Marketing Landing Page
│   │   ├── page.tsx           # Landing page (route: /)
│   │   └── layout.tsx         # Landing-specific layout
│   ├── (app)/                 # Application Pages
│   │   ├── portfolio/         # Portfolio page (route: /portfolio)
│   │   │   └── page.tsx
│   │   └── layout.tsx         # App-specific layout
│   ├── layout.tsx             # Root layout
│   ├── error.tsx              # Global error handling
│   └── loading.tsx            # Global loading component
├── components/
│   ├── ui/                    # ShadCN UI components
│   ├── BasicDemoPage.tsx      # Landing page component
│   ├── Header.tsx             # Shared header
│   ├── ChatInput.tsx          # Chat input component
│   └── ThemeToggle.tsx        # Theme toggle component
├── contexts/
│   └── ThemeContext.tsx       # Theme management
└── styles/
    └── globals.css            # Global styles
```

## Route Groups
Using Next.js 13+ route groups to organize pages:

- `(landing)` - Marketing pages, SEO-focused
  - Route: `/` - Landing page with pricing, features, etc.
  
- `(app)` - Application pages, authenticated/functional
  - Route: `/portfolio` - Main portfolio dashboard

## Benefits of This Structure

### 1. **Clear Separation of Concerns**
- Marketing content separate from app functionality
- Different layouts for landing vs app pages
- Easier maintenance and development

### 2. **Scalability**
- Landing section can grow with more marketing pages
- App section can expand with new application features
- Independent styling and functionality

### 3. **Development Workflow**
- Landing page team can work independently
- App development team has clear boundaries
- Easier to manage different deployment strategies if needed

## Future Expansion

### Landing Section Future Pages:
```
(landing)/
├── page.tsx                   # Home/Landing
├── pricing/page.tsx           # Pricing details
├── features/page.tsx          # Feature showcase
├── about/page.tsx             # Company info
├── resources/
│   ├── blog/page.tsx          # Blog listing
│   └── docs/page.tsx          # Documentation
└── contact/page.tsx           # Contact form
```

### App Section Future Pages:
```
(app)/
├── portfolio/page.tsx         # Current: Portfolio dashboard
├── analytics/page.tsx         # Risk analytics page
├── performance/page.tsx       # Performance analysis
├── history/page.tsx          # Historical data
├── settings/page.tsx         # User settings
└── profile/page.tsx          # User profile
```

## Component Organization

### Shared Components (`/components/`)
- Components used by both landing and app
- UI components (buttons, inputs, etc.)
- Theme management

### Page-Specific Components
- Landing components in `(landing)/components/`
- App components in `(app)/components/`
- Keep components close to where they're used

## Current Implementation Status

✅ **Completed:**
- Route group structure established
- Landing page at `/`
- Portfolio app page at `/portfolio`
- Theme system working across both sections
- Navigation between landing and app

📋 **Next Steps:**
- Add landing-specific components directory
- Add app-specific components directory
- Expand each section with additional pages
- Implement different layouts for landing vs app