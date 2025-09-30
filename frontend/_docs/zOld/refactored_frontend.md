# SigmaSight Frontend Refactoring Plan

## Executive Summary
This document outlines a comprehensive refactoring plan for the SigmaSight frontend, creating a professional application structure with a data-rich home dashboard while maintaining existing authentication patterns.

## 1. Authentication Flow

### Current State
- Landing page (`/landing`) with Login button in top-right header → `/login`
- Root (`/`) redirects to `/portfolio`
- Login page (`/login`) handles demo accounts

### Refined Solution
**Keep Existing Landing Page Unchanged**
- Landing page (`/landing`) remains as-is with Login button in header
- `/login` page handles ALL authentication (demo accounts + user credentials)
- Authentication determines portfolio loading (1 user = 1 portfolio)
- After successful login → redirect to `/home` (new dashboard)
- No portfolio selector needed - portfolio is determined by user login

### Login Page Wireframe
```
┌────────────────────────────────────────────────────────────────────────────────┐
│                                                                                │
│                              SigmaSight                                       │
│                         ───────────────────────                               │
│                                                                                │
│                         Sign in to your account                               │
│                                                                                │
│     ┌──────────────────────────────────────────────────────────────┐         │
│     │ Email                                                        │         │
│     │ ┌──────────────────────────────────────────────────────────┐│         │
│     │ │ user@example.com                                         ││         │
│     │ └──────────────────────────────────────────────────────────┘│         │
│     └──────────────────────────────────────────────────────────────┘         │
│                                                                                │
│     ┌──────────────────────────────────────────────────────────────┐         │
│     │ Password                                                     │         │
│     │ ┌──────────────────────────────────────────────────────────┐│         │
│     │ │ ••••••••                                                 ││         │
│     │ └──────────────────────────────────────────────────────────┘│         │
│     └──────────────────────────────────────────────────────────────┘         │
│                                                                                │
│     ┌──────────────────────────────────────────────────────────────┐         │
│     │                         Sign In                              │         │
│     └──────────────────────────────────────────────────────────────┘         │
│                                                                                │
│     ─────────────────── Or use demo account ───────────────────              │
│                                                                                │
│     ┌──────────────────────────────────────────────────────────────┐         │
│     │ 📈 High Net Worth Portfolio                                  │         │
│     │    Multi-asset portfolio with advanced analytics            │         │
│     │    demo_hnw@sigmasight.com                                 │         │
│     └──────────────────────────────────────────────────────────────┘         │
│                                                                                │
│     ┌──────────────────────────────────────────────────────────────┐         │
│     │ 👤 Individual Investor                                       │         │
│     │    Personal investment portfolio                            │         │
│     │    demo_individual@sigmasight.com                          │         │
│     └──────────────────────────────────────────────────────────────┘         │
│                                                                                │
│     ┌──────────────────────────────────────────────────────────────┐         │
│     │ 🏢 Hedge Fund                                                │         │
│     │    Institutional portfolio with complex strategies          │         │
│     │    demo_hedgefundstyle@sigmasight.com                      │         │
│     └──────────────────────────────────────────────────────────────┘         │
│                                                                                │
│                    All demo accounts use: demo12345                           │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Application Structure

### Directory Organization
```
app/
├── landing/           (existing - NO CHANGES)
├── login/            (existing - handles all auth)
├── home/             (NEW - main dashboard)
├── portfolio_configuration/ (NEW - portfolio settings)
├── settings/         (NEW - user settings)
└── portfolio/        (LEGACY - keep for reference)
```

### Page Architecture
```
/home (Main Dashboard)
├── Portfolio metrics (8 cards)
├── Factor exposures
├── Position cards by type
└── AI Chat interface

/portfolio_configuration
├── Risk preferences
├── Position management
├── Rebalancing rules
└── Alert settings

/settings
├── User profile
├── Security settings
├── Data exports
└── API integrations
```

### Navigation Structure
```
[Left Sidebar - Persistent]
┌─────────────────────┐
│ SigmaSight         │
├─────────────────────┤
│ Home               │ (Active)
│ Portfolio Config   │
│ Settings           │
├─────────────────────┤
│ [User Name]        │
│ [Portfolio Name]   │
│ Logout             │
└─────────────────────┘
```
Note: No portfolio selector - determined by login

## 3. Home Dashboard Wireframe (Black/White/Grey Theme)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ■ SigmaSight                                                           John Doe        │
│ ├─ Home                                                               HNW Portfolio     │
│ ├─ Config                                                             Logout           │
│ └─ Settings                                                                            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│ EXPOSURES  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌──────┐         │
│            │$2.5M│ │$3.2M│ │-1.1M│ │$4.3M│ │$2.1M│ │$450K│ │1.72x│ │ 85%  │         │
│            │Equity│ │Long │ │Short│ │Gross│ │ Net │ │Cash │ │Lever│ │Divers│         │
│            └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └──────┘         │
│                                                                                         │
│ FACTORS    ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                  │
│            │ 1.2 │ │ 0.3 │ │-0.2 │ │ 0.8 │ │ 0.5 │ │-0.1 │ │ 0.4 │                  │
│            │Mkt  │ │Size │ │Value│ │Mom  │ │Qual │ │Vol  │ │Growth│                  │
│            └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘                  │
│                                                                                         │
│ LONGS      ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ → → →            │
│            │AAPL│ │MSFT│ │GOOGL│ │NVDA│ │AMZN│ │TSLA│ │META│ │BRK │                  │
│            │450K│ │380K│ │320K │ │280K│ │250K│ │220K│ │180K│ │160K│                  │
│            │18% │ │15% │ │13%  │ │11% │ │10% │ │9%  │ │7%  │ │6%  │                  │
│            └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘                  │
│                                                                                         │
│ SHORTS     ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐                → → →            │
│            │ARKK│ │COIN│ │HOOD│ │RIVN│ │SNAP│ │PINS│                                 │
│            │180K│ │150K│ │120K│ │100K│ │80K │ │60K │                                 │
│            │7%  │ │6%  │ │5%  │ │4%  │ │3%  │ │2%  │                                 │
│            └────┘ └────┘ └────┘ └────┘ └────┘ └────┘                                 │
│                                                                                         │
│ OPTIONS    [No options positions]                                                      │
│                                                                                         │
│ PRIVATE    [No private investments]                                                    │
│                                                                                         │
│ ┌───────────────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                        ▲           │ │
│ │ AI: Your portfolio shows strong tech concentration (65%). Consider diversifying   │ │
│ │ into defensive sectors to reduce volatility during market corrections.            │ │
│ │                                                                                   │ │
│ │ You: What's my biggest risk right now?                                           │ │
│ │                                                                                   │ │
│ │ AI: Your largest risk is sector concentration. Tech stocks represent 65% of      │ │
│ │ your long book. A 20% tech selloff would impact your portfolio by -$416K...      │ │
│ │                                                                        ▼           │ │
│ └───────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                         │
│     ┌─────────────────────────────────────────────────────────────────────────┐       │
│     │ Ask about your portfolio...                                      [Send] │       │
│     └─────────────────────────────────────────────────────────────────────────┘       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

## 4. Component Architecture

### Core Components Structure
```
components/
├── dashboard/
│   ├── MetricsCard.tsx         # Reusable metric display card
│   ├── FactorExposureCard.tsx  # Factor beta visualization
│   ├── PositionCard.tsx        # Compact position display
│   ├── PositionRow.tsx         # Horizontal scrollable row
│   └── DashboardLayout.tsx     # Main dashboard container
├── layout/
│   ├── AppSidebar.tsx          # Persistent navigation
│   ├── AppHeader.tsx           # Top bar with user menu
│   └── AppLayout.tsx           # Main app wrapper
└── ui/
    └── [ShadCN components]
```

### Data Flow Architecture
```
Page Component (portfolio/page.tsx)
    ↓
Portfolio Service (portfolioService.ts)
    ↓
API Client (Next.js Proxy)
    ↓
Backend API Endpoints
```

## 5. API Integration Plan

### Required Endpoints & Data Mapping

#### Portfolio Metrics (Top Cards)
**Endpoint**: `/api/v1/analytics/portfolio/{portfolio_id}/overview`
```typescript
interface PortfolioMetrics {
  equity_balance: number;      // → Equity Value card
  long_exposure: number;        // → Long Exposure card
  short_exposure: number;       // → Short Exposure card
  gross_exposure: number;       // → Gross Exposure card
  net_exposure: number;         // → Net Exposure card
  cash_balance: number;         // → Cash Balance card
  leverage: number;             // → Leverage card
}
```

#### Factor Exposures (Second Row)
**Endpoint**: `/api/v1/analytics/portfolio/{portfolio_id}/factor-exposures`
```typescript
interface FactorExposure {
  factor_name: string;
  beta: number;
  exposure_percentage: number;
}
```

#### Position Details (Position Rows)
**Endpoint**: `/api/v1/data/positions/details?portfolio_id={id}`
```typescript
interface Position {
  symbol: string;
  position_type: 'LONG' | 'SHORT' | 'OPTION' | 'PRIVATE';
  market_value: number;
  weight: number;
  unrealized_pnl: number;
}
```

## 6. Implementation Phases

### Phase 1: Authentication Unification (Day 1)
- [ ] Update landing page to single CTA
- [ ] Enhance /login page with better UX
- [ ] Implement portfolio type resolution
- [ ] Test authentication flow end-to-end

### Phase 2: Dashboard Layout (Days 2-3)
- [ ] Create AppLayout with sidebar navigation
- [ ] Implement responsive grid system
- [ ] Build MetricsCard component
- [ ] Build FactorExposureCard component
- [ ] Build PositionCard component
- [ ] Implement horizontal scrolling for position rows

### Phase 3: Data Integration (Days 4-5)
- [ ] Connect portfolio overview API
- [ ] Connect factor exposures API
- [ ] Connect positions API
- [ ] Implement real-time data updates
- [ ] Add loading states and error handling

### Phase 4: Polish & Optimization (Day 6)
- [ ] Add animations and transitions
- [ ] Implement dark mode support
- [ ] Performance optimization
- [ ] Accessibility audit
- [ ] Mobile responsive testing

## 7. Design System Configuration

### Color Palette
```scss
// Primary - SigmaSight Blue
$primary: #2563eb;
$primary-hover: #1e40af;

// Semantic Colors
$success: #10b981;
$warning: #f59e0b;
$error: #ef4444;
$info: #3b82f6;

// Neutrals
$gray-50: #f9fafb;
$gray-100: #f3f4f6;
$gray-200: #e5e7eb;
$gray-300: #d1d5db;
$gray-400: #9ca3af;
$gray-500: #6b7280;
$gray-600: #4b5563;
$gray-700: #374151;
$gray-800: #1f2937;
$gray-900: #111827;
```

### Typography Scale
```scss
// Headings
h1: 32px / 40px (2rem / 2.5rem)
h2: 24px / 32px (1.5rem / 2rem)
h3: 20px / 28px (1.25rem / 1.75rem)
h4: 16px / 24px (1rem / 1.5rem)

// Body
body-large: 16px / 24px
body-default: 14px / 20px
body-small: 12px / 16px
```

### Spacing System
```scss
// Base unit: 8px
$spacing-xs: 4px;   // 0.5x
$spacing-sm: 8px;   // 1x
$spacing-md: 16px;  // 2x
$spacing-lg: 24px;  // 3x
$spacing-xl: 32px;  // 4x
$spacing-2xl: 48px; // 6x
```

## 8. ShadCN Component Usage

### Priority Components
- Card (metrics and factor cards)
- Badge (status indicators)
- Button (actions)
- Tabs (navigation)
- ScrollArea (position rows)
- Sheet (chat overlay)
- Select (portfolio switcher)
- Avatar (user menu)
- Separator (visual dividers)
- Skeleton (loading states)

### Custom Variants
```tsx
// MetricsCard variant
<Card className="border-0 shadow-sm hover:shadow-md transition-shadow">
  <CardHeader className="pb-2">
    <CardTitle className="text-sm font-medium text-gray-600">
      {title}
    </CardTitle>
  </CardHeader>
  <CardContent>
    <div className="text-2xl font-semibold">{value}</div>
    <div className="text-sm text-gray-500">{subValue}</div>
  </CardContent>
</Card>
```

## 9. Performance Considerations

### Data Loading Strategy
1. **Initial Load**: Load portfolio overview first (metrics)
2. **Progressive Enhancement**: Load positions and factors after
3. **Caching**: Use React Query or SWR for data caching
4. **Real-time Updates**: WebSocket for price updates (future)

### Optimization Techniques
- Virtual scrolling for large position lists
- Memoization for expensive calculations
- Code splitting by route
- Lazy loading for non-critical components
- Image optimization for logos/icons

## 10. Mobile Responsiveness

### Breakpoint Strategy
```scss
sm: 640px   // Mobile landscape
md: 768px   // Tablet
lg: 1024px  // Desktop
xl: 1280px  // Wide desktop
```

### Mobile Layout Adjustments
- Stack metric cards vertically on mobile
- Collapse sidebar to hamburger menu
- Full-width position cards with vertical scroll
- Bottom sheet for chat on mobile
- Touch-optimized interactions

## 11. Future Enhancements

### Phase 2 Features (Post-MVP)
- Real-time price updates via WebSocket
- Advanced filtering and sorting
- Drag-and-drop position reordering
- Custom dashboard layouts
- Export functionality
- Multi-portfolio comparison view

### Option & Private Investment Support
When backend schemas are ready:
- Option Greeks display (Delta, Gamma, Vega, Theta)
- Expiration calendar view
- Private investment valuation metrics
- Liquidity timelines
- Custom asset categorization

### TODO: Enhanced Authentication (Future)
- Multi-factor authentication (MFA)
- SSO integration (Google, Microsoft)
- Multiple portfolios per user
- Role-based access control
- Session management improvements
- Remember me functionality

## 12. Success Metrics

### User Experience
- Page load time < 2 seconds
- Time to first meaningful paint < 1 second
- Smooth 60fps scrolling
- Zero layout shifts

### Business Metrics
- Increased user engagement (time on dashboard)
- Reduced support tickets for navigation
- Higher feature adoption rates
- Improved user retention

## Conclusion

This refactoring plan addresses your key requirements:

1. **Authentication**: Keep landing page unchanged with login button, centralize all auth through /login
2. **Directory Structure**: New pages in `/home`, `/portfolio_configuration`, `/settings` while keeping `/portfolio` as legacy
3. **Dashboard Design**: Horizontal layout with 8 metrics cards, left-aligned labels, black/white/grey theme
4. **User Experience**: 1 user = 1 portfolio (no selector), scrollable chat with fixed cards above
5. **Scalability**: Clean separation of concerns, ready for options and private investments

The implementation focuses on:
- **Minimal disruption**: Landing page unchanged, existing login enhanced
- **Clean architecture**: Clear directory structure with legacy preservation
- **Professional aesthetics**: Monochrome theme inspired by ShadCN examples
- **Efficient layout**: Horizontal design maximizes screen real estate

Next steps:
1. Implement login page enhancements for user credentials
2. Create `/home` directory and dashboard components
3. Build horizontal card layout with scrollable position rows
4. Integrate chat with scrollable conversation area
5. Test authentication flow with portfolio auto-loading