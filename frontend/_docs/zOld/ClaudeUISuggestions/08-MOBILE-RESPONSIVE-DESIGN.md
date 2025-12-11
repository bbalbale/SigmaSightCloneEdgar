# Mobile & Responsive Design Patterns

**Document Version**: 2.0
**Last Updated**: November 1, 2025
**Status**: Updated for current architecture (ThemeContext, Container pattern, 4 core pages)

---

## Overview

SigmaSight must be fully functional on desktop (≥768px) and mobile (<768px) devices. This document specifies responsive patterns and mobile-specific optimizations for the current architecture.

**Current Implementation Status**:
- ✅ ThemeContext with CSS custom properties
- ✅ Container pattern for all 4 core pages
- ✅ TopNavigationBar with 4 page buttons
- ❌ Mobile bottom navigation (to be implemented)
- ❌ Mobile-optimized components (to be implemented)

---

## Breakpoints

```css
/* Tailwind Breakpoints (Mobile First) */
--mobile: 0px       /* <768px - default */
--md: 768px         /* ≥768px - desktop */
--lg: 1024px        /* ≥1024px - wide desktop */
--xl: 1440px        /* ≥1440px - extra wide */
```

**Note**: We use Tailwind's `md:` breakpoint as the desktop cutoff (768px), not 1024px.

---

## Theme Integration

### CSS Custom Properties (Already Implemented ✅)

All mobile styles leverage the existing ThemeContext and CSS variables:

```css
/* Theme variables (defined in ThemeContext) */
var(--bg-primary)        /* Page background */
var(--bg-secondary)      /* Card background */
var(--bg-tertiary)       /* Muted sections */
var(--bg-elevated)       /* Dropdowns, modals */

var(--text-primary)      /* Primary text */
var(--text-secondary)    /* Secondary text */
var(--text-tertiary)     /* Muted text */

var(--border-primary)    /* Main borders */
var(--border-secondary)  /* Subtle borders */

var(--color-success)     /* Positive values */
var(--color-error)       /* Negative values */
var(--color-accent)      /* Brand accent */

/* Typography */
var(--font-display)      /* Headings */
var(--font-body)         /* Body text */
var(--font-mono)         /* Numbers, data */

var(--text-xs) through var(--text-3xl)  /* Font sizes */

/* Visual */
var(--border-radius)     /* Card corners */
var(--card-padding)      /* Card padding */
var(--card-gap)          /* Spacing */
```

**Benefits**:
- Theme switching (light/dark) works automatically across all breakpoints
- No need to duplicate theme styles for mobile
- Consistent colors and spacing everywhere

### Mobile-Specific Variables (To Add)

```css
:root {
  /* Touch targets */
  --tap-target-min: 44px;
  --bottom-nav-height: 56px;

  /* Mobile spacing */
  --spacing-mobile: 12px;
  --spacing-desktop: 24px;

  /* Mobile typography adjustments */
  --text-mobile-sm: 12px;
  --text-mobile-base: 14px;
}
```

---

## Mobile Navigation (< 768px)

### Bottom Navigation Bar (To Be Implemented)

```
┌────────────────────────────────┐
│                                │
│     Content Area               │
│     (scrollable)               │
│     (full screen height)       │
│                                │
├────────────────────────────────┤
│ [🎯]  [🔍]  [📊]  [✨]  [👤] │  ← Fixed bottom (56px)
└────────────────────────────────┘
```

**5 Icons** (matching TopNavigationBar):
1. 🎯 **Command Center** - Home base (Command icon)
2. 🔍 **Research & Analyze** - Position research (Search icon)
3. 📊 **Risk Metrics** - Portfolio analytics (TrendingUp icon)
4. ✨ **SigmaSight AI** - AI insights (Sparkles icon)
5. 👤 **User Menu** - Opens UserDropdown (User icon)

**Implementation**:
```typescript
// src/components/navigation/BottomNavigation.tsx
const navItems = [
  { href: '/command-center', icon: Command, label: 'Command Center' },
  { href: '/research-and-analyze', icon: Search, label: 'Research' },
  { href: '/risk-metrics', icon: TrendingUp, label: 'Risk' },
  { href: '/sigmasight-ai', icon: Sparkles, label: 'AI' },
]

// 5th item is UserDropdown trigger (opens menu, doesn't navigate)
<BottomNavigation
  items={navItems}
  className="md:hidden" // Only show on mobile
/>
```

**Features**:
- **Position**: Fixed at bottom (`position: fixed; bottom: 0`)
- **Height**: 56px with iOS safe area support (`padding-bottom: env(safe-area-inset-bottom)`)
- **Active State**: Highlight current page with accent color
- **Labels**: Hidden by default, show on long-press (tooltip)
- **Tap Targets**: 44x44px minimum (accessibility)
- **UserDropdown**: 5th icon opens dropdown menu above bottom nav (Settings, Logout)

### Desktop Navigation (≥768px) - Already Implemented ✅

```
┌────────────────────────────────────────────────────┐
│ [$] SigmaSight [🎨] [☰]  [🎯] [🔍] [📊] [✨] [👤] │
└────────────────────────────────────────────────────┘
```

**TopNavigationBar** (current implementation):
- **Left**: Logo + ThemeToggle + NavigationDropdown (all pages menu)
- **Right**: 4 page buttons + UserDropdown
- **Sticky**: `sticky top-0` with backdrop blur
- **Hide on Mobile**: Add `className="hidden md:flex"`

---

## Component Mobile Behavior

### HeroMetricsRow (Command Center)

**Current Desktop**: 6-column grid (`grid-cols-1 md:grid-cols-3 lg:grid-cols-6`)

**Mobile Enhancement Needed**:
```
Desktop (≥768px):
┌────────┬────────┬────────┬────────┬────────┬────────┐
│ Equity │ Target │ Gross  │  Net   │  Long  │ Short  │
└────────┴────────┴────────┴────────┴────────┴────────┘

Mobile (<768px) - OPTION A: Grid (current, works but not ideal):
┌──────────────────┐
│ Equity Balance   │
├──────────────────┤
│ Target Return    │
├──────────────────┤
│ Gross Exposure   │
└──────────────────┘
(scroll down for more)

Mobile (<768px) - OPTION B: Swipeable Carousel (recommended):
┌──────────────────┐
│ ← Equity  →      │  ← Swipe left/right
│ $500K            │
│ ● ○ ○ ○ ○ ○    │  ← Pagination dots
└──────────────────┘
```

**Implementation**: Use Embla Carousel or Swiper for horizontal scroll with snap points.

---

### HoldingsTable (Command Center)

**Current Desktop**: 11-column table

**Mobile Challenge**: Table overflow on small screens

**Mobile Solution - Compact Cards**:
```
Desktop:
┌─────────────────────────────────────────────────────┐
│ Symbol │ Type │ Shares │ Price │ Value │ P&L │ ... │
├────────┼──────┼────────┼───────┼───────┼─────┼─────┤
│ NVDA   │ LONG │  1000  │ $88   │ $88K  │+15% │ ... │
└─────────────────────────────────────────────────────┘

Mobile - Compact Position Cards:
┌────────────────────────────┐
│ NVDA  •  LONG             │
│ $88,000                    │
│ +$12,000 (+15.8%) 🟢     │
│ [Tap to expand ▼]         │  ← Tap opens bottom sheet
└────────────────────────────┘
```

**Implementation**:
- Detect screen size with `useMediaQuery` hook
- Render table on desktop, cards on mobile
- Bottom sheet for expanded details

---

### RiskMetricsRow (Command Center)

**Current Desktop**: 5-card grid

**Mobile**: Stack vertically (current implementation already works)

```
Desktop: [Card1] [Card2] [Card3] [Card4] [Card5]

Mobile:
[Card1]
[Card2]
[Card3]
[Card4]
[Card5]
```

**Enhancement**: Add collapse/expand for each card on mobile.

---

### ResearchTableView (Research & Analyze)

**Current**: Multi-column table with target prices, tags, aggregates

**Mobile Challenge**: Too many columns for small screens

**Mobile Solution**:
```
Desktop Table:
┌──────────────────────────────────────────────────────┐
│ Symbol │ Price │ Target │ Return │ Tags │ Actions   │
├────────┼───────┼────────┼────────┼──────┼───────────┤
│ NVDA   │ $88   │ $120   │ +36%   │ Tech │ [Edit]    │
└──────────────────────────────────────────────────────┘

Mobile Compact Cards:
┌────────────────────────────────┐
│ NVDA  •  $88 → $120           │
│ Target Return: +36.4%          │
│ [Tech] [AI] [Growth]           │  ← Tags
│ [Edit Target] [Add Tag]        │  ← Actions
└────────────────────────────────┘
```

**Features**:
- Show: Symbol, current price, target price, return, tags
- Hide: Analyst data, detailed columns
- Swipe-to-tag: Drag tag onto card to apply
- Tap to expand: Opens bottom sheet with full details

---

### Sticky Tag Bar (Research & Analyze)

**Current Desktop**: Sticky at top with full tag list + "Restore Sector Tags" button

**Mobile Issue**: Takes too much vertical space

**Mobile Solution**:
```
Desktop:
┌─────────────────────────────────────────────────────┐
│ [Tech] [Finance] [Healthcare] [+] [Restore Tags]    │  ← Sticky
└─────────────────────────────────────────────────────┘

Mobile - Collapsible:
┌────────────────────────────┐
│ [Show Tags ▼] (8)         │  ← Collapsed by default
└────────────────────────────┘

Mobile - Expanded:
┌────────────────────────────┐
│ [Hide Tags ▲]             │
│ [Tech] [Finance]          │  ← Horizontal scroll
│ [Healthcare] [+]          │
│ [Restore Tags]            │
└────────────────────────────┘
```

---

### Risk Components (Risk Metrics Page)

**Current**: Vertical sections, each with a component

**Mobile Enhancement**: Add collapsed/expanded states

```
Desktop - All Expanded:
┌─────────────────────┐
│ Volatility Metrics  │
│ [Chart and data]    │
├─────────────────────┤
│ Sector Exposure     │
│ [Chart and data]    │
├─────────────────────┤
│ Concentration       │
│ [Data]              │
└─────────────────────┘

Mobile - Collapsed by Default:
┌──────────────────────┐
│ Volatility Metrics ▼ │  ← Tap to expand
├──────────────────────┤
│ Sector Exposure ▼    │
├──────────────────────┤
│ Concentration ▼      │
└──────────────────────┘

Mobile - Expanded:
┌──────────────────────┐
│ Volatility Metrics ▲ │
│ [Simplified chart]   │
│ Key Stats: ...       │
└──────────────────────┘
```

**Charts**: Reduce size and complexity on mobile (fewer data points, smaller legends).

---

### AI Chat Interface (SigmaSight AI)

**Current Desktop**: Split layout (`grid-cols-1 lg:grid-cols-2`)
- Left: AI Insights cards
- Right: Claude chat

**Mobile**: Already stacks vertically ✅

**Enhancement**: Optimize chat input for mobile keyboards

```
Mobile:
┌────────────────────┐
│ Generated Insights │
│ [Cards...]         │
├────────────────────┤
│ Ask SigmaSight AI  │
│ [Chat interface]   │
│ [Input] [Send]     │  ← Optimized for thumb typing
└────────────────────┘
```

---

## Mobile Interaction Patterns

### 1. Bottom Sheets

**Use Case**: Position details, filters, expanded views

```
┌──────────────────────────────────┐
│ Position Cards                   │  ← Dimmed background
│ ...                              │
├══════════════════════════════════┤
│ [─]  NVDA Position Details       │  ← Bottom sheet
│ ─────────────────────────────    │
│ Market Value: $88,000            │
│ P&L: +$12,000 (+15.8%)          │
│ Beta: 1.85  Volatility: 32%     │
│ [Analyze Risk] [AI Explain]      │
└──────────────────────────────────┘
```

**Libraries**:
- `@radix-ui/react-dialog` (already used for modals)
- `vaul` (React bottom sheet library)

**Behavior**:
- Slides up from bottom
- Drag handle at top for dismissing
- Swipe down to close
- Backdrop dimmed, tap to close

---

### 2. Swipe Gestures

**Horizontal Swipe** (Hero Metrics Carousel):
```
← Swipe Left/Right →

[Equity Balance] → [Target Return] → [Gross Exposure]
```

**Swipe-to-Tag** (Research Table Cards):
```
Drag tag from top bar → Drop on position card
```

**Libraries**:
- Embla Carousel (lightweight, no dependencies)
- React DnD (drag and drop - already used?)

---

### 3. Pull-to-Refresh

**Standard Mobile Pattern**:
```
Pull down from top → Spinner appears → Refresh data
```

**Implementation**:
```typescript
import { usePullToRefresh } from '@/hooks/usePullToRefresh'

const { refetch } = useCommandCenterData()

usePullToRefresh(refetch)
```

**Library**: Custom hook or `react-pull-to-refresh`

---

### 4. Long-Press for Labels

**Bottom Navigation**: Icons only, labels on long-press

```typescript
// Show tooltip on long-press (500ms)
const handleTouchStart = (label: string) => {
  timeoutRef.current = setTimeout(() => {
    showTooltip(label)
  }, 500)
}

const handleTouchEnd = () => {
  clearTimeout(timeoutRef.current)
  hideTooltip()
}
```

---

## Touch Optimization

### Tap Targets

**Minimum Size**: 44x44px (Apple HIG, WCAG AAA)

```css
/* Ensure all interactive elements are touch-friendly */
.touch-target {
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Bottom nav items */
.bottom-nav-item {
  height: 56px;
  flex: 1;
  min-width: 56px; /* 5 items = ~75px each on 375px screen */
}
```

**Examples**:
- Buttons: 48px height minimum
- Bottom nav items: 56px height
- Table row cards: 64px minimum height
- Icons: 24x24px visual with 44x44px tap area

---

### Spacing

**Mobile-specific spacing**:

```css
/* Mobile spacing (default) */
.card-mobile {
  padding: 12px;
  gap: 8px;
  margin: 12px;
}

/* Desktop spacing (≥768px) */
@media (min-width: 768px) {
  .card-desktop {
    padding: 24px;
    gap: 16px;
    margin: 24px;
  }
}
```

**Or with Tailwind**:
```tsx
<div className="p-3 gap-2 m-3 md:p-6 md:gap-4 md:m-6">
```

---

## Layout Patterns

### Page Layout Structure

```tsx
// layout.tsx
<div className="flex min-h-screen flex-col">
  {/* Desktop: Full top nav */}
  <TopNavigationBar className="hidden md:flex" />

  {/* Main content area */}
  <main className="flex-1 pb-16 md:pb-0">
    {children}
  </main>

  {/* Mobile: Bottom nav */}
  <BottomNavigation className="md:hidden" />
</div>
```

**Key Details**:
- `pb-16` on mobile: Creates space for fixed bottom nav (56px + safe area)
- `md:pb-0` on desktop: No bottom nav, no extra padding needed
- Bottom nav has `position: fixed` and doesn't affect layout flow

---

### Container Padding

```tsx
// CommandCenterContainer.tsx
<div
  className="min-h-screen"
  style={{ backgroundColor: 'var(--bg-primary)' }}
>
  {/* Page description */}
  <div className="px-4 pt-4 pb-2">
    <div className="container mx-auto">
      <p className="text-sm text-muted-foreground">
        Portfolio overview, holdings, and risk metrics
      </p>
    </div>
  </div>

  {/* Content sections */}
  <section className="px-4 py-4">
    <div className="container mx-auto">
      {/* Components */}
    </div>
  </section>
</div>
```

**Mobile**: `px-4` = 16px horizontal padding (prevents content from touching edges)

---

## Responsive Utilities

### Media Query Hook

```typescript
// hooks/useMediaQuery.ts
export function useMediaQuery(query: string) {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    const media = window.matchMedia(query)
    setMatches(media.matches)

    const listener = () => setMatches(media.matches)
    media.addEventListener('change', listener)
    return () => media.removeEventListener('change', listener)
  }, [query])

  return matches
}

// Usage
const isMobile = useMediaQuery('(max-width: 767px)')
const isDesktop = useMediaQuery('(min-width: 768px)')
```

---

### Conditional Rendering

```tsx
// Show table on desktop, cards on mobile
const isMobile = useMediaQuery('(max-width: 767px)')

return isMobile ? (
  <PositionCards positions={positions} />
) : (
  <PositionsTable positions={positions} />
)
```

**Or with CSS** (preferred for performance):
```tsx
<>
  <PositionsTable className="hidden md:block" />
  <PositionCards className="md:hidden" />
</>
```

---

## Performance Optimization

### Mobile-Specific

**Lazy Loading**:
```tsx
// Lazy load heavy components on mobile
import dynamic from 'next/dynamic'

const ChartComponent = dynamic(
  () => import('@/components/charts/VolatilityChart'),
  {
    loading: () => <ChartSkeleton />,
    ssr: false // Charts don't need SSR
  }
)
```

**Reduced Motion**:
```css
/* Respect user preference */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Code Splitting**:
```tsx
// Load mobile/desktop variants separately
const BottomNavigation = dynamic(() =>
  import('@/components/navigation/BottomNavigation')
)
```

---

## Accessibility

### Mobile Accessibility

**Touch Targets**: 44x44px minimum (already covered)

**Screen Readers**:
```tsx
<button
  aria-label="Command Center"
  aria-current={isActive ? 'page' : undefined}
>
  <Command className="h-5 w-5" />
</button>
```

**Focus Indicators**:
```css
/* Visible focus for keyboard users */
.nav-button:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

**Long-Press Labels**:
```tsx
// Tooltip shows on long-press for icons
<Tooltip content="Command Center" trigger="longpress">
  <Command />
</Tooltip>
```

---

## Testing Checklist

### Devices to Test

**Mobile**:
- ✅ iPhone 14/15 (375x812, Mobile Safari)
- ✅ iPhone 14 Pro Max (430x932, Mobile Safari)
- ✅ Samsung Galaxy S23 (360x800, Chrome)
- ✅ Google Pixel 7 (412x915, Chrome)

**Tablet**:
- ✅ iPad Pro 12.9" (1024x1366, Safari)
- ✅ iPad Air (820x1180, Safari)

**Desktop**:
- ✅ 1920x1080 (Chrome, Firefox, Edge, Safari)
- ✅ 1440x900 (Chrome, Safari)

### Test Scenarios

**Navigation**:
- [ ] Bottom nav visible on mobile (<768px)
- [ ] Top nav visible on desktop (≥768px)
- [ ] Active page highlighted
- [ ] Long-press shows labels
- [ ] User dropdown works from bottom nav
- [ ] Settings link navigates correctly

**Components**:
- [ ] HeroMetricsRow: Grid on desktop, carousel on mobile
- [ ] HoldingsTable: Table on desktop, cards on mobile
- [ ] ResearchTableView: Table on desktop, cards on mobile
- [ ] Tag bar: Full on desktop, collapsible on mobile
- [ ] Risk components: Expanded on desktop, collapsed on mobile

**Interactions**:
- [ ] Tap targets are 44x44px minimum
- [ ] Swipe gestures work (carousel, swipe-to-tag)
- [ ] Pull-to-refresh triggers data reload
- [ ] Bottom sheets open/close correctly
- [ ] Long-press tooltips appear

**Performance**:
- [ ] Page loads in <3s on 4G
- [ ] Smooth 60fps scrolling
- [ ] No layout shift (CLS < 0.1)
- [ ] Images lazy load below fold

**Accessibility**:
- [ ] VoiceOver navigation works (iOS)
- [ ] TalkBack navigation works (Android)
- [ ] Focus indicators visible
- [ ] Color contrast ratio ≥4.5:1

---

## Summary

### Mobile Strategy (< 768px)

**Navigation**:
- ✅ Bottom navigation (5 icons: 4 pages + user menu)
- ❌ Hide top navigation bar

**Layout**:
- ✅ Single column, vertical stacking
- ✅ Full screen content (no top bar)
- ✅ 56px bottom nav with safe area insets

**Components**:
- ❌ Hero metrics → Swipeable carousel
- ❌ Holdings table → Compact position cards
- ❌ Research table → Compact cards with swipe-to-tag
- ❌ Tag bar → Collapsible
- ❌ Risk components → Collapsed by default

**Interactions**:
- ❌ Swipe gestures (carousel, actions)
- ❌ Pull-to-refresh
- ❌ Bottom sheets (details, filters)
- ❌ Long-press labels

**Theme**:
- ✅ CSS custom properties (auto theme switching)
- ✅ Consistent colors/spacing

### Desktop Strategy (≥ 768px)

**Navigation**:
- ✅ Top navigation bar (already implemented)
- ✅ Hide bottom navigation

**Layout**:
- ✅ Multi-column grids
- ✅ Tables for data display
- ✅ All sections expanded

**Theme**:
- ✅ Same CSS variables, auto theme switching

---

## Next Steps

See `09-MOBILE-IMPLEMENTATION-PLAN.md` for detailed phased implementation with:
- Week-by-week roadmap
- Component-specific implementation details
- Testing milestones
- Dependencies and libraries
